"""
Bedienung des Skripts:
- Für Simulationsmodus (GUI): ros2 run chat chat --sim
  Öffnet eine grafische Benutzeroberfläche für die Simulation.
  Links: Bild und Pose-Anzeige, Rechts: Chat-Interface.
  Publiziert Pose an /chat und Text an /transcribed_text.
  Subscribed /action_sim für Simulation der Aktionen.

- Für Studienmodus: ros2 run chat chat --stu
  Automatisierter Modus für Studien mit 2 Runden (Testzweck).
  Zufällige Startpositionen und Zielbereiche.
  GUI-Interface mit automatischen Zielüberprüfungen.

- Für Bot-Modus: ros2 run chat chat --bot
  Subscribed /amcl_pose und publiziert empfangene Pose an /audio_record_pose.
  Gibt "Navigationsbefehl: " aus und wartet auf String.
  Publiziert Text an /transcribed_text.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from std_msgs.msg import String
import sys
import math
import threading
import json
import subprocess
import os
import random
import time
from .chat_model import ChatModel
from .insert_robot import update_robot_position
from .study_data_model import StudyDataModel
from .participant_dialog import get_participant_data

def is_position_navigable(x, y):
    """
    Prüft, ob eine Position (x, y) in einem der befahrbaren Bereiche liegt.
    """
    try:
        import importlib.util
        
        # Lade ROOM_LAYOUT aus JSON-Datei anstatt aus roomlayout.py
        prompt_dir = os.path.join(os.path.expanduser('~'), 'ros2_ws', 'src', 'prompt', 'prompt')
        roomlayout_json_path = os.path.join(prompt_dir, 'roomlayout.json')
        
        if os.path.exists(roomlayout_json_path):
            try:
                with open(roomlayout_json_path, 'r', encoding='utf-8') as f:
                    ROOM_LAYOUT = json.load(f)
            except Exception as e:
                print(f"Warnung: Konnte roomlayout.json nicht laden: {e}")
                return True  # Fallback if JSON can't be loaded
        else:
            return True  # Fallback if module can't be loaded
        
        navigable_areas = ROOM_LAYOUT.get("topology", {}).get("navigable_areas", [])
        
        for area in navigable_areas:
            bottom_left = area["bottom_left"]
            width = area["width"]
            height = area["height"]
            
            # Berechne die Grenzen des Bereichs
            left = bottom_left[0]
            right = left + width
            bottom = bottom_left[1]
            top = bottom + height
            
            # Prüfe ob die Position innerhalb des Bereichs liegt
            if left <= x <= right and bottom <= y <= top:
                return True
        
        return False
    except Exception as e:
        print(f"Fehler beim Prüfen der Position: {e}")
        return True  # Im Fehlerfall Position als gültig betrachten

def is_in_target_area(x, y, target_x, target_y, width=140, height=140):
    """
    Prüft, ob eine Position (x, y) innerhalb eines rechteckigen Zielbereichs liegt.
    
    Args:
        x, y: Position in Einheiten
        target_x, target_y: Zentrum des Zielbereichs in Einheiten
        width, height: Breite und Höhe des Zielbereichs in Einheiten (Standard: 140cm x 140cm)
    """
    half_width = width / 2
    half_height = height / 2
    
    # Prüfe ob Position innerhalb des Rechtecks liegt
    return (target_x - half_width <= x <= target_x + half_width and
            target_y - half_height <= y <= target_y + half_height)

def yaw_deg_to_quaternion(yaw_deg: float):
    yaw_rad = math.radians(float(yaw_deg) % 360)
    half = yaw_rad / 2.0
    qx = 0.0
    qy = 0.0
    qz = math.sin(half)
    qw = math.cos(half)
    return qx, qy, qz, qw

class ChatNode(Node):
    def __init__(self, mode):
        super().__init__('chat')
        self.mode = mode
        self.pose_pub = None
        self.text_pub = self.create_publisher(String, '/transcribed_text', 10)
        self.model = ChatModel()  # MVC Model für Zustandsverwaltung
        
        # Studiendatenerfassung
        self.study_data = None
        self.command_start_time = None  # Für Latenz-Messung
        
        if self.mode in ['sim', 'stu']:
            self.pose_pub = self.create_publisher(PoseStamped, '/chat', 10)
            # Subscriber für action_sim Topic
            self.create_subscription(String, '/action_sim', self._action_sim_cb, 10)
            # Subscriber für LLM-Antworten
            self.create_subscription(String, '/llm_response', self._llm_response_cb, 10)
            
            # Studienmodus: Datenerfassung initialisieren
            if self.mode == 'stu':
                self.study_data = StudyDataModel()
                
        elif self.mode == 'bot':
            self.pose_pub = self.create_publisher(PoseStamped, '/audio_record_pose', 10)
            self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self._pose_cb, 10)
            # Auch im Bot-Modus auf LLM-Antworten hören
            self.create_subscription(String, '/llm_response', self._llm_response_cb, 10)

    def _pose_cb(self, msg: PoseWithCovarianceStamped):
        out_msg = PoseStamped()
        out_msg.header = msg.header
        out_msg.pose = msg.pose.pose
        self.pose_pub.publish(out_msg)
        self.get_logger().info('Aktuelle Pose publiziert.')

    def _action_sim_cb(self, msg: String):
        """Callback für action_sim Topic - simuliert die empfangene Aktion."""
        try:
            action_data = json.loads(msg.data)
            aktion = action_data.get("Aktion")
            parameter = action_data.get("Parameter", {})
            
            # Latenz messen: Zeit von Befehlseingabe bis jetzt (Ausführung)
            if self.mode == 'stu' and self.study_data and self.study_data.has_current_participant() and self.command_start_time:
                latency = time.time() - self.command_start_time
                if self.study_data.current_participant.current_round:
                    self.study_data.current_participant.current_round.add_latency(latency)
                    self.get_logger().info(f"Latenz gemessen: {latency:.2f} Sekunden")
                self.command_start_time = None  # Reset für nächsten Befehl
            
            if not self.model.is_initialized():
                self.get_logger().error("Model nicht initialisiert - kann Aktion nicht simulieren")
                return
                
            self.get_logger().info(f"Simuliere Aktion: {aktion}")
            
            if aktion == "Navigieren":
                # Navigation - neue Position setzen
                zielposition = parameter.get("Zielposition", {})
                x_new = int(zielposition.get("x", 0))
                y_new = int(zielposition.get("y", 0))
                
                # DEBUG: Zustand vor Navigation
                x_before, y_before, alpha_before = self.model.get_current_pose()
                self.get_logger().info(f"🔍 VOR Navigation: Position=({x_before}, {y_before}), Orientierung={alpha_before}°")
                
                # Prüfe ob die Zielposition befahrbar ist
                if is_position_navigable(x_new, y_new):
                    self.model.simulate_navigate(x_new, y_new)
                    
                    # DEBUG: Zustand nach Navigation
                    x_after, y_after, alpha_after = self.model.get_current_pose()
                    self.get_logger().info(f"🔍 NACH Navigation: Position=({x_after}, {y_after}), Orientierung={alpha_after}°")
                    self.get_logger().info(f"🔍 Orientierungsänderung: {(alpha_after - alpha_before) % 360:.1f}°")
                    
                    self.get_logger().info(f"Navigation simuliert zu: x={x_new}, y={y_new}")
                else:
                    self.get_logger().warn(f"Zielposition ({x_new}, {y_new}) ist nicht befahrbar - Navigation abgebrochen")
                    return
                
            elif aktion == "Keine":
                # Keine Aktion - nur loggen
                answer = parameter.get("answer", "")
                self.get_logger().info(f"Keine Aktion: {answer}")
                return  # Keine Positionsänderung
                
            else:
                self.get_logger().error(f"Unbekannte Aktion: {aktion}")
                return
                
            # Aktualisierte Position publizieren
            x_cm, y_cm, alpha_deg = self.model.get_current_pose()
            
            # DEBUG: Finale Werte
            self.get_logger().info(f"🔍 FINALE Werte für Ausgabe: x={x_cm}, y={y_cm}, alpha={alpha_deg}°")
            
            self.publish_sim_pose(x_cm, y_cm, alpha_deg)
            
            # Roboterbild aktualisieren (mit Zielbereich im Studienmodus)
            target_area = self.model.current_target if self.mode == 'stu' else None
            update_robot_position(x_cm, y_cm, alpha_deg, target_area)
            
            # Studienmodus: Nach-Bild der aktuellen Interaktion erfassen
            if self.mode == 'stu' and self.study_data and self.study_data.has_current_participant():
                # Länger warten, damit das Bild vollständig aktualisiert wird
                time.sleep(1.0)  # Erhöht von 0.3 auf 1.0 Sekunden
                image_path = os.path.expanduser("~/ros2_ws/src/map/currentPosition.png")
                if os.path.exists(image_path):
                    self.study_data.set_interaction_after_image(image_path)
            
            # Studienmodus: Prüfe ob Ziel erreicht wurde
            if self.mode == 'stu':
                if self.model.check_target_reached():
                    self.get_logger().info(f"{self.model.current_round}. Ziel erreicht!")
                    
                    # Studiendaten: Runde beenden
                    if self.study_data and self.study_data.has_current_participant():
                        self.study_data.finish_round()
                        
                    self.view.handle_target_reached()
                    
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Ungültiges JSON in action_sim: {e}")
        except Exception as e:
            self.get_logger().error(f"Fehler beim Simulieren der Aktion: {e}")
            import traceback
            self.get_logger().error(f"Traceback: {traceback.format_exc()}")

    def _llm_response_cb(self, msg: String):
        """Callback für LLM-Antworten - leitet sie an die GUI weiter."""
        try:
            response_text = msg.data
            self.get_logger().info(f"LLM-Antwort erhalten (length: {len(response_text)} chars)")
            
            # Studienmodus: LLM-Antwort in aktueller Interaktion speichern
            if self.mode == 'stu' and self.study_data and self.study_data.has_current_participant():
                # Versuche explanation und reasoning zu extrahieren
                explanation, reasoning = self._extract_explanation_and_reasoning(response_text)
                self.study_data.update_current_interaction(explanation=explanation, reasoning=reasoning)
            
            # Für GUI-Anzeige: Extrahiere nur explanation aus JSON (falls es JSON ist)
            display_text = response_text
            if '{' in response_text and '}' in response_text:
                try:
                    import json
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    json_part = response_text[start_idx:end_idx]
                    response_data = json.loads(json_part)
                    
                    aktion = response_data.get("Aktion", "")
                    if aktion.lower() == "keine":
                        display_text = response_data.get("answer", "Keine Antwort verfügbar")
                    else:
                        display_text = response_data.get("explanation", "Keine Erklärung verfügbar")
                except:
                    # Falls JSON-Parsing fehlschlägt, verwende original text
                    pass
            
            # Weiterleitung an GUI (falls vorhanden)
            if hasattr(self, 'view') and self.view:
                self.view.add_chat_message("Turtlebot", display_text, "#3498db")
            elif self.mode == 'bot':
                # Im Bot-Modus auf Konsole ausgeben
                print(f"\n🤖 Turtlebot: {display_text}\n")
                
        except Exception as e:
            self.get_logger().error(f"Fehler beim Verarbeiten der LLM-Antwort: {e}")
            
    def _extract_explanation_and_reasoning(self, response_text: str) -> tuple:
        """Extrahiert explanation und reasoning aus der LLM-Antwort."""
        try:
            self.get_logger().info(f"DEBUG: Extracting from response_text (first 200 chars): {response_text[:200]}")
            
            # Versuche JSON-Struktur zu parsen
            if '{' in response_text and '}' in response_text:
                # Finde den JSON-Teil in der Antwort
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_part = response_text[start_idx:end_idx]
                
                self.get_logger().info(f"DEBUG: Extracted JSON part (first 200 chars): {json_part[:200]}")
                
                import json
                response_data = json.loads(json_part)
                explanation = response_data.get('explanation', '')
                reasoning = response_data.get('reasoning', '')
                
                self.get_logger().info(f"DEBUG: JSON-Parsing erfolgreich: explanation={len(explanation)} chars, reasoning={len(reasoning)} chars")
                return explanation, reasoning
            else:
                self.get_logger().warn(f"DEBUG: No JSON found in response_text")
                # Falls kein JSON, suche nach Mustern
                lines = response_text.split('\n')
                explanation = response_text
                reasoning = ''
                
                for i, line in enumerate(lines):
                    if 'reasoning' in line.lower() or 'begründung' in line.lower():
                        # Nehme alles ab dieser Zeile als reasoning
                        reasoning = '\n'.join(lines[i:])
                        explanation = '\n'.join(lines[:i])
                        break
                
                self.get_logger().info(f"DEBUG: Fallback parsing: explanation={len(explanation)} chars, reasoning={len(reasoning)} chars")
                return explanation.strip(), reasoning.strip()
                
        except json.JSONDecodeError as e:
            self.get_logger().warn(f"JSON-Parsing fehlgeschlagen: {e}")
            return response_text, ""
        except Exception as e:
            self.get_logger().warn(f"Konnte explanation/reasoning nicht extrahieren: {e}")
            return response_text, ""

    def publish_text(self, text: str):
        """Publiziert Text und erfasst Studiendaten."""
        # Studienmodus: Befehl erfassen
        if self.mode == 'stu' and self.study_data and self.study_data.has_current_participant():
            self.command_start_time = time.time()
            self.study_data.add_command(text, self.command_start_time)
            
        self.text_pub.publish(String(data=text))
        self.get_logger().info('Text publiziert.')

    def publish_sim_pose(self, x_cm: int, y_cm: int, yaw_deg: int):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.pose.position.x = float(x_cm)
        msg.pose.position.y = float(y_cm)
        msg.pose.position.z = float(yaw_deg)
        qx, qy, qz, qw = yaw_deg_to_quaternion(yaw_deg)
        msg.pose.orientation.x = qx
        msg.pose.orientation.y = qy
        msg.pose.orientation.z = qz
        msg.pose.orientation.w = qw
        self.pose_pub.publish(msg)
        self.get_logger().info(f'Sim-Pose publiziert: x={x_cm}, y={y_cm}, yaw={yaw_deg}°')

    def open_image(self):
        """Öffnet das currentPosition.png Bild automatisch."""
        image_path = os.path.expanduser("~/ros2_ws/src/map/currentPosition.png")
        try:
            # Versuche das Bild mit dem Standard-Bildbetrachter zu öffnen
            subprocess.Popen(['xdg-open', image_path])
            self.get_logger().info(f"Bild geöffnet: {image_path}")
        except Exception as e:
            self.get_logger().warn(f"Konnte Bild nicht öffnen: {e}")

    def run_simulation_loop(self):
        """Führt die kontinuierliche Simulation aus."""
        # Initiale Pose eingeben mit Validierung
        while True:
            xyz_raw = _prompt_input('Startpose: x, y, alpha: ')
            try:
                x, y, alpha = parse_xyz(xyz_raw)
                
                # Prüfe ob die Position befahrbar ist
                if is_position_navigable(x, y):
                    break
                else:
                    print("Diese Pose ist nicht erreichbar. Bitte wählen Sie eine Position in einem befahrbaren Bereich.")
                    
            except ValueError as e:
                print(f"Eingabefehler: {e}")
        
        # Model initialisieren
        self.model.set_initial_pose(x, y, alpha)
        
        # Initiale Pose publizieren
        self.publish_sim_pose(x, y, alpha)
        
        # Roboterbild mit initialer Position aktualisieren
        update_robot_position(x, y, alpha)
        
        # Bild automatisch öffnen
        self.open_image()
        
        # Kontinuierliche Eingabeschleife
        while True:
            text = _prompt_input('Navigationsbefehl oder "Stop": ')
            
            if text.lower() in ['stop', 'stopp']:
                self.get_logger().info("Stop-Befehl erhalten. Beende Simulation.")
                break
                
            self.publish_text(text)
            
            # Kurz warten, damit die Aktionssimulation verarbeitet werden kann
            time.sleep(0.5)

    def select_random_start_position(self):
        """Delegiert an Model - MVC Architektur."""
        return self.model.select_random_start_position()
            
    def select_random_target(self):
        """Delegiert an Model - MVC Architektur."""
        return self.model.select_random_target()
        
    def start_new_round(self):
        """Delegiert an Model und publiziert Updates - MVC Architektur."""
        if self.model.start_new_round():
            # Position publizieren und Bild aktualisieren ZUERST
            x, y, alpha = self.model.get_current_pose()
            self.publish_sim_pose(x, y, alpha)
            target_area = self.model.current_target if self.mode == 'stu' else None
            update_robot_position(x, y, alpha, target_area)
            
            # Studiendaten: Neue Runde starten
            if self.mode == 'stu' and self.study_data and self.study_data.has_current_participant():
                self.study_data.start_round(self.model.current_round)
                
                # Kurz warten, damit das Bild aktualisiert wird, DANN erfassen
                time.sleep(0.5)
                image_path = os.path.expanduser("~/ros2_ws/src/map/currentPosition.png")
                if os.path.exists(image_path):
                    self.study_data.set_round_start_image(image_path)
            
            self.get_logger().info(f"Runde {self.model.current_round} gestartet")
            return True
        return False
        
    def next_round(self):
        """Geht zur nächsten Runde über und publiziert Updates - MVC Architektur."""
        if self.model.next_round():
            # Position publizieren und Bild aktualisieren ZUERST
            x, y, alpha = self.model.get_current_pose()
            self.publish_sim_pose(x, y, alpha)
            target_area = self.model.current_target if self.mode == 'stu' else None
            update_robot_position(x, y, alpha, target_area)
            
            # Studiendaten: Neue Runde starten
            if self.mode == 'stu' and self.study_data and self.study_data.has_current_participant():
                self.study_data.start_round(self.model.current_round)
                
                # Kurz warten, damit das Bild aktualisiert wird, DANN erfassen
                time.sleep(0.5)
                image_path = os.path.expanduser("~/ros2_ws/src/map/currentPosition.png")
                if os.path.exists(image_path):
                    self.study_data.set_round_start_image(image_path)
                
            self.get_logger().info(f"Runde {self.model.current_round} gestartet")
            return True
        return False

    def run_gui_simulation(self):
        """Führt die GUI-basierte Simulation aus."""
        from .chat_view import ChatView
        
        # Starte GUI
        gui = ChatView(self, self.model)
        self.view = gui
        gui.run()

def _prompt_input(prompt: str) -> str:
    print(prompt, end='', flush=True)
    return sys.stdin.readline().strip()

def parse_xyz(inp: str):
    parts = inp.replace(' ', '').split(',')
    if len(parts) != 3:
        raise ValueError('Bitte im Format "x, y, alpha" eingeben')
    x = int(parts[0])
    y = int(parts[1])
    alpha = int(parts[2])
    return x, y, alpha

def main(args=None):
    if len(sys.argv) < 2 or sys.argv[1] not in ['--sim', '--stu', '--bot']:
        print("Verwendung: ros2 run chat chat --sim | --stu | --bot")
        print("  --sim : GUI-basierte Simulation")
        print("  --stu : Studienmodus mit 2 automatischen Runden (Testzweck)")
        print("  --bot : Bot-Modus")
        return

    mode = sys.argv[1][2:]  # 'sim', 'stu' oder 'bot'
    rclpy.init(args=args)
    node = ChatNode(mode)

    try:
        if mode in ['sim', 'stu']:
            # GUI-basierte Simulation
            # Starte ROS2 Spinning in separatem Thread
            spin_thread = threading.Thread(target=rclpy.spin, args=(node,))
            spin_thread.daemon = True
            spin_thread.start()
            
            # Führe GUI-Simulation im Hauptthread aus
            node.run_gui_simulation()
            
        elif mode == 'bot':
            spin_thread = threading.Thread(target=rclpy.spin, args=(node,))
            spin_thread.start()
            print("🤖 Gib deinen Befehl, um den Turtlebot ins Ziel zu steuern. Oder hast du eine Frage?")
            text = _prompt_input('Navigationsbefehl: ')
            node.publish_text(text)
            rclpy.shutdown()
            spin_thread.join()
            
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer beendet.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
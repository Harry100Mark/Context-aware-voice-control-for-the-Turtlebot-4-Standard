import os
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
import google.generativeai as genai
import json
import re
import math
import threading

# Lokaler Import der Zeichenfunktion und Prompt-Builder
from . import draw_currentPosition
from . import promptBuilder
from .transformation import back_transformation, forward_transformation


class PromptGoogleNode(Node):
    """Minimaler Node: 
    - subscribed auf /chat (PoseStamped von chat.py)
    - erzeugt draw_currentPosition.png über draw_map
    - analysiert Objekte um den Turtlebot über perspectiveTaker
    - verwendet Google Gemini 2.5 Pro für AI-Antworten
    """

    def __init__(self):
        super().__init__('prompt_google')

        # Zielpfad für das Bild im Home-Workspace: ~/ros2_ws/src/map/draw_currentPosition.png
        home = os.path.expanduser('~')
        base_ws = os.path.join(home, 'ros2_ws')
        map_dir = os.path.join(base_ws, 'src', 'map')
        os.makedirs(map_dir, exist_ok=True)
        self.dynamic_pose_image_path = os.path.join(map_dir, 'draw_currentPosition.png')

        # Zwischenspeicher für vorbereiteten Prompt
        self.prepared_prompt = None

        # Subscriber: Startpose-Topic (vom chat-Node publiziert)
        self.create_subscription(PoseStamped, '/chat', self._start_pose_cb, 10)
        
        # Subscriber: Audio-Record-Pose-Topic (vom chat-Node im Bot-Modus publiziert)
        self.create_subscription(PoseStamped, '/audio_record_pose', self._audio_record_pose_cb, 10)
        
        # Subscriber: Text-Topic (vom chat-Node publiziert)
        self.create_subscription(String, '/transcribed_text', self._text_cb, 10)
        
        # Publisher: Action Command Topic (für action_executor)
        self.action_command_publisher = self.create_publisher(String, '/action_command', 10)
        
        # Publisher: Action Sim Topic (für chat --sim Simulation)
        self.action_sim_publisher = self.create_publisher(String, '/action_sim', 10)
        
        # Publisher: Action Stop Topic (für action_executor)
        self.action_stop_publisher = self.create_publisher(String, '/action_stop', 10)
        
        self.get_logger().info('prompt_google bereit. Warte auf Startpose und Text von chat.py (/chat oder /audio_record_pose)...')
        
        # Konfiguriere Google Gemini API
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            self.get_logger().error('GOOGLE_API_KEY Umgebungsvariable nicht gesetzt!')
            raise ValueError('GOOGLE_API_KEY ist erforderlich')
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')  # Neuestes Gemini Modell
        self.chat_session = None  # Chat-Sitzung für kontextbezogene Konversation
        self.get_logger().info('Google Gemini API konfiguriert')

    def _start_pose_cb(self, msg: PoseStamped):
        """Callback: erhält Startposition und -orientierung von chat.py über /chat Topic.
        Verwendet AUSSCHLIESSLICH die Koordinaten, die Sie über chat.py Terminal eingeben:
        - Ihre Terminal-Eingabe erfolgt bereits in cm als int-Werte
        - chat.py konvertiert diese zu Map-Metern und sendet sie über PoseStamped
        - Wir konvertieren zurück zu Ihren ursprünglichen cm-Werten
        """
        try:
            # Rückkonvertierung zu Ihren ursprünglichen Terminal-Eingabe-Werten (cm)
            x_cm = int(msg.pose.position.x)
            y_cm = int(msg.pose.position.y) 
            yaw_img_deg = int(msg.pose.position.z)  # Bildwinkel (int)

            self.get_logger().info(f'Pose von /chat empfangen - Verwende Terminal-Eingabe: x={x_cm}cm, y={y_cm}cm, yaw={yaw_img_deg}°')
            
            # Gemeinsame Verarbeitung
            self._process_pose(x_cm, y_cm, yaw_img_deg)

        except Exception as e:
            self.get_logger().error(f'Fehler beim Verarbeiten der /chat Pose: {e}')

    def _audio_record_pose_cb(self, msg: PoseStamped):
        """Callback: erhält Position und Orientierung von chat.py über /audio_record_pose Topic.
        Diese Pose kommt aus dem ROS2 Map-Koordinatensystem und muss rücktransformiert werden.
        """
        try:
            # Koordinaten aus ROS2 Map-System (in Metern)
            x_map_m = msg.pose.position.x
            y_map_m = msg.pose.position.y
            
            # Orientierung aus Quaternion extrahieren
            import math
            qx = msg.pose.orientation.x
            qy = msg.pose.orientation.y
            qz = msg.pose.orientation.z
            qw = msg.pose.orientation.w
            
            # Quaternion zu Yaw (in Radians) konvertieren
            yaw_rad = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
            
            self.get_logger().info(f'Pose von /audio_record_pose empfangen - Map-Koordinaten: x={x_map_m:.3f}m, y={y_map_m:.3f}m, yaw={math.degrees(yaw_rad):.1f}°')
            
            # Rücktransformation von Map-Koordinaten zu Bild-Koordinaten
            x_cm, y_cm, yaw_img_deg = back_transformation(x_map_m, y_map_m, yaw_rad)
            
            # Zu Integer konvertieren (wie bei Terminal-Eingabe)
            x_cm = int(round(x_cm))
            y_cm = int(round(y_cm))
            yaw_img_deg = int(round(yaw_img_deg))
            
            self.get_logger().info(f'Nach Rücktransformation - Bild-Koordinaten: x={x_cm}cm, y={y_cm}cm, yaw={yaw_img_deg}°')
            
            # Gemeinsame Verarbeitung
            self._process_pose(x_cm, y_cm, yaw_img_deg)

        except Exception as e:
            self.get_logger().error(f'Fehler beim Verarbeiten der /audio_record_pose: {e}')

    def _process_pose(self, x_cm: int, y_cm: int, yaw_img_deg: int):
        """Gemeinsame Verarbeitung für beide Pose-Quellen.
        """
        try:
            self.get_logger().info(f'Verarbeite Pose: x={x_cm}cm, y={y_cm}cm, yaw={yaw_img_deg}°')

            # Bild erzeugen mit cm-Werten direkt
            draw_currentPosition.generate_current_pose_image(
                x_cm=x_cm,
                y_cm=y_cm,
                yaw_img_deg=yaw_img_deg,
                out_path=self.dynamic_pose_image_path,
            )
            self.get_logger().info(f'draw_currentPosition.png aktualisiert')

        except Exception as e:
            self.get_logger().error(f'Fehler beim Verarbeiten der Pose: {e}')
            return  # Beende Verarbeitung bei Fehler

        # System-Instruktionen für KI-Prompt definieren
        self.system_instructions = (
            """
            Du bist ein intelligenter Assistent für einen Turtlebot-Roboter. Deine Aufgabe ist es, menschliche Befehle in präzise JSON-Aktionsbefehle umzuwandeln.

            
            Schritt 1: Aktionstyp identifizieren:
                A.1) Analysiere den folgenden Befehl des Menschen: {Einfügepunkt: neuen Prompt}
                A.2) Entscheide um welche der folgenden Aktionen es sich handelt: Navigieren, Drehen, Distanz_zurücklegen. Hier sind ein paar Infos und Beispiele dazu:
                    - Navigieren: Wenn der Turtlebot zu einer bestimmten Zielposition fahren soll oder einen Weg beschrieben bekommt oder er sich in eine bestimmte Richtung bewegen soll oder er sich relativ zu einem Objekt positionieren soll. Beispiele: "Fahr zum Tisch", "Am Schrank vorbei", "Bieg ab", "Kannst du bitte hinter den nächsten Tisch fahren?", "Beweg dich zum Tisch neben dem Fenster vor dir", "Fahr rechts neben den Karton links von hinter dir", "Fahr vorbei", "Fahr nach 2 Meter nach rechts", "Fahr um die Ecke", "Fahr vorwärts", "Fahr hinter dich"
                    - Distanz_zurücklegen: Wenn der Turtlebot rückwärts ODER vorwärts fahren soll UND eine bestimmte Distanz zurücklegen soll manchmal auch mit einer bestimmten Geschwindigkeit. Beispiele: "Fahr einen Meter geradeaus", "Fahr langsam ein kleines Stück rückwärts", "Ein kleines Stück vor"
                    - Drehen: Wenn der Turtlebot sich auf der Stelle drehen soll. Manchmal soll er auch in eine bestimmte Richtung schauen. Beispiele: "Dreh dich nach links", "Schau nach rechts", "Dreh dich um.", "Schau zur Tür."
                A.3) Entscheide, um welchen Fall es sich handelt. Fall 1: Navigieren, Fall 2: Distanz_zurücklegen, Drehen.
                A.4) Gib zurück: "Es handelt sich die Aktion >Aktion< und Fall >1 oder 2<."

                
            Schritt 2: Aktion ausführen:


                Fall 1: Die Aktion ist 'Navigieren':
                    Diese Aktion ist in mehrere Teilaufgaben zerlegt ist, damit du Schritt für Schritt mithilfe deiner In-Context Learning und Chain of Thought Fähigkeiten eine richtige Lösung finden kannst.
                    A.1) Startposition identifizieren: Bild des Raumplans: {Einfügepunkt: Bild der jetzigen Pose}, JSON Beschreibung des Raumplans: {Einfügepunkt: JSON des Raumplans}. Schaue genau, an welcher Position sich der Turtlebot auf dem Bild befindet (kleiner, blauer, runder Roboter mit Sichtfeld und rotem Pfeil, der die Fahrrichtung anzeigt). An welcher Position (x,y) befindet sich der Turtlebot ungefähr? Lese hierfür die Achsenbeschriftung genau ab. Die genaue Position wird auch im Kästchen neben dem Turtlebot angezeigt und auch in der Überschrift des Bildes. Nun verifiziere diese Position auch mittels der JSON des Raumplans. Gib zurück: {"position": {"x": >x<, "y": >y<}}.
                    A.2) Startorientierung identifizieren: Bestimme im Bild die Himmelsrichtung, in welche der Turtlebot schaut. Schaut er nach Süden, Norden, Westen, Osten oder etwas dazwischen z.B. Nordosten? Nutze zum Lösen dieser Aufgabe den roten Pfeil, der die Fahrtrichtung des Turtlebots anzeigt. Die Richtung, in die der Turtlebot schaut, lässt sich auch unter seiner Position und in der Überschrift verifizieren. Auch die Orientierung lässt sich mit der JSON des Raumplans verifizieren. Gib zurück: {"orientation": {"direction": ">Himmelsrichtung<", "degrees": >Orientierung in Grad<}}.
                    A.3) Himmelsrichtungen des Bildes lernen: Der Raumplan hat die folgenden Dimensionen im Bild: von -29 bis 689 auf der x-Achse und von 0 bis 654 auf der y-Achse. Norden ist im Bild oben und bedeutet größere y-Werte. Westen ist im Bild links und bedeutet kleinere x-Werte. Wenn sich der Turtlebot nun an der Position x=100, y=100 befinde und wir einen Punkt suchen, der nordöstlich vom Turtlebot liegt, käme der Punkt x=200, y=200 dann in Frage bzw. liegt der nordöstlich des Turtlebots? Was ist mit dem Punkt x=0, y=0? Gib zurück: {"directions": {"point_200_200": ">Himmelsrichtung<", "point_0_0": ">Himmelsrichtung<"}}.
                    A.4) Perspektive des Turtlebots übernehmen: Wenn du nun unter Berücksichtigung der Position und der Orientierung des Turtlebots dir im Bild überlegst: Was sich VOR dem Turtlebot befindet, RECHTS von ihm, LINKS von ihm, HINTER ihm (Aus Sicht des Turtlebots). Welche Hindernisse (z.B. Tische oder ähnliches) sieht der Turtlebot dann vor sich, rechts von sich, links von sich, hinter sich? Beispielsweise gibt dir alles, was sich innerhalb des Sichtfelds des Turtlebots befindet, Aufschluss darüber, was der Turtlebot unmittelbar vor sich sieht. Und wenn der Turtlebot z.B. nach Westen schaut, dann bedeutet "rechts von ihm" alles, was sich nördlich des Turtlebots befindet. Und wenn der Turtlebot z.B. nach Südosten sieht, dann bedeutet "hinter ihm" alles, was sich nordwestlich von ihm befindet. Deine Ergebnisse kannst du anschließend ebenfalls mit der JSON der Roboterperspektive: {Einfügepunkt: JSON der Roboterperspektive} verifizieren. Gib zurück: {"perspectives": {"front": ">Alle Objekte, die vor ihm sind<", "back": ">Alle Objekte, die hinter ihm sind<", "right": ">Alle Objekte, die rechts von ihm sind<", "left": ">Alle Objekte, die links von ihm sind<"}}. Wichtig ist es im weiteren IMMER die Perspektive des Roboters einzunehmen.
                    A.5) Befahrbaren Bereich erkennen: Schaue dir im Bild den befahrbaren Bereich, welcher in hellgrün dargestellt ist und dunkelgrün umrandet ist, genau an. Alle Zielkoordinaten, die im befahrbaren Bereich liegen sind vom Turtlebot sicher anfahrbar, da sie genügend Sicherheitsabstand zu umliegenden Hindernissen einhalten. Suche dir 3 Punkte im Bild, welche im befahrbaren Bereich liegen. Nun schaue, ob diese 3 Punkte ebenfalls in einem der befahrbaren Bereiche aus der JSON des Raumplans liegen, um deine Ergebnisse zu verifizieren. Das bedeutet du sollst die 3 Punkte (x,y) ausgeben und explizit nennen in welcher der Polygone navigable_areas sich die Punkte befinden und dies zeigen. Gib für alle 3 Punkte zurück: {"points": [{"point": {"x": >x<, "y": >y<}, "area": {"bottom_left": [>x_bottom_left<, >y_bottom_left<], "width": >width<, "height": >height<, "center": [>center_x<, >center_y<]}, "verification": ">x_bottom_left< <= x = >x< <= >x_bottom_left< + >width< und >y_bottom_left< <= y = >y< <= >y_bottom_left< + >height<"}, {"point": {"x": >x<, "y": >y<}, "area": {"bottom_left": [>x_bottom_left<, >y_bottom_left<], "width": >width<, "height": >height<, "center": [>center_x<, >center_y<]}, "verification": ">x_bottom_left< <= x = >x< <= >x_bottom_left< + >width< und >y_bottom_left< <= y = >y< <= >y_bottom_left< + >height<"}, {"point": {"x": >x<, "y": >y<}, "area": {"bottom_left": [>x_bottom_left<, >y_bottom_left<], "width": >width<, "height": >height<, "center": [>center_x<, >center_y<]}, "verification": ">x_bottom_left< <= x = >x< <= >x_bottom_left< + >width< und >y_bottom_left< <= y = >y< <= >y_bottom_left< + >height<"}] }.
                    A.6) Pfade erkennen: 2 Punkte im befahrbaren Bereich bilden einen Pfad, wenn auch jeder Punkt, der diese beiden Punkte miteinander verbindet, wiederum im befahrbaren Bereich liegt. Beispiele sind die Punkte (x=420, y=90) und (x=660, y=90). Solche Pfade lassen sich leicht erkennen, da man zwischen den beiden dunkelgrünen Rändern des befahrbaren Bereichs, die parallel zueinander verlaufen, 2 beliebige Punkte im hellgrünen Bereich wählen kann. Gib zurück: {"path": {"points": [{"x": 660, "y": 620}, {"x": 480, "y": 620}], "explanation": ">Erklärung<"}}.
                    **Die Beispiele in A.7 und A.8 dienen nur zum Verständnis der Methode. Übernehme unter keinen Umständen die Zielkoordinaten oder andere Werte aus diesen Beispielen für deine finale Lösung. Berechne die Lösung für den neuen Kontext immer vollständig neu.**
                    A.7) Um die Ecke fahren lernen (Chain of Thought mit Verifikation):

                        Ein Befehl wie "biege links ab" oder "fahre um den Tisch herum" bedeutet, dass der Turtlebot einen Zielpunkt ansteuern soll, der nicht auf direktem Weg über eine gerade Verbindung erreichbar ist, weil ein Hindernis im Weg ist.
                        Um die korrekten Zielkoordinaten zu finden, befolge diese Schritte:

                        A.7.1) Identifiziere das relevante Hindernis.
                            Analysiere den Befehl und die Turtlebotperspektive in diesem Beispiel (Die Position und Orientierung und Perspektive des Turtlebots gelten NUR für dieses Beispiel A7): 
                            JSON der Roboterperspektive: {Einfügepunkt: JSON der Roboterperspektive}, Bild des Raumplans: {Einfügepunkt: Bild}, Navigationsbefehl: 'Biege links ab'.
                            Welches Hindernis in der Nähe des Turtlebots blockiert die gewünschte Fahrtrichtung, sodass der Turtlebot nicht auf einer geraden Verbindung etwas weiter Richtung links (aus seiner Perspektive Süden) fahren kann? Bei der Auswahl des Hindernisses sind größere Hindernisse wie Schränke und Tische kleineren Hindernissen wie Stühlen und Kartons zu bevorzugen, außer das Hindernis wurde explizit angegeben, dann wähle dies.
                            Verifiziere, dass das Hindernis die Fahrtrichtung blockiert, indem du prüfst, ob seine y-Koordinaten (z. B. center_y ± height/2) kleiner sind als die y-Koordinate des Turtlebots und seine x-Koordinaten (z. B. center_x ± width/2) in der Nähe der Turtlebotposition liegen. Gib zurück: { "obstacle": { "name": ">Objektname<", "type": ">Typ des Hindernisses (z.B. table, cabinet, dresser)<", "center": [>center_x<, >center_y<], "dimensions": {"width": >width<, "height": >height<}, "explanation": "Das Hindernis >Objektname< blockiert die Fahrtrichtung, weil seine y-Koordinaten (von >center_y< - >height</2< bis >center_y< + >height</2<) kleiner als die Turtlebot-y-Position sind und seine x-Koordinaten (von >center_x< - >width</2< bis >center_x< + >width</2<) in der Nähe der Turtlebot-x-Position liegen." } }
                            

                        A.7.2) Finde einen potenziellen Zielpunkt und validiere die Positionierung.
                            Analysiere die relative Position des Turtlebots zum identifizierten Hindernis und bestimme basierend auf der Abbiegerichtung die korrekte Zielposition.
                            
                            a) Bestimme die aktuelle relative Position des Turtlebots zum Hindernis:

                                Nutze die JSON der Roboterperspektive, um eindeutig zu bestimmen, wo sich das Hindernis relativ zum Turtlebot befindet:
                                - Hindernis ist VOR dem Turtlebot → Turtlebot befindet sich in entgegengesetzter Richtung zur Orientierung
                                  (Orientierung Süden → Turtlebot ist NÖRDLICH des Hindernisses)
                                  (Orientierung Norden → Turtlebot ist SÜDLICH des Hindernisses)
                                  (Orientierung Osten → Turtlebot ist WESTLICH des Hindernisses)
                                  (Orientierung Westen → Turtlebot ist ÖSTLICH des Hindernisses)
                                - Hindernis ist RECHTS vom Turtlebot → Turtlebot befindet sich links zur Orientierung
                                - Hindernis ist LINKS vom Turtlebot → Turtlebot befindet sich rechts zur Orientierung  
                                - Hindernis ist HINTER dem Turtlebot → Turtlebot befindet sich in gleicher Richtung zur Orientierung
                            
                            b) Bestimme die Zielposition basierend auf Orientierung und Abbiegerichtung:

                                1. Fall: Turtlebot NÖRDLICH des Hindernisses
                                    - Orientierung Westen + Links abbiegen → Ziel: WESTLICH des Hindernisses
                                    (x_ziel < Hindernis center_x - width/2, y_ziel ≈ Hindernis center_y ± height/2)
                                    - Orientierung Osten + Rechts abbiegen → Ziel: ÖSTLICH des Hindernisses  
                                    (x_ziel > Hindernis center_x + width/2, y_ziel ≈ Hindernis center_y ± height/2)
                                    - Orientierung Süden + Links abbiegen → Ziel: ÖSTLICH des Hindernisses
                                    - Orientierung Süden + Rechts abbiegen → Ziel: WESTLICH des Hindernisses

                                2. Fall: Turtlebot SÜDLICH des Hindernisses
                                    - Orientierung Westen + Rechts abbiegen → Ziel: WESTLICH des Hindernisses
                                    - Orientierung Osten + Links abbiegen → Ziel: ÖSTLICH des Hindernisses
                                    - Orientierung Norden + Links abbiegen → Ziel: WESTLICH des Hindernisses  
                                    - Orientierung Norden + Rechts abbiegen → Ziel: ÖSTLICH des Hindernisses

                                3. Fall: Turtlebot WESTLICH des Hindernisses
                                    - Orientierung Norden + Rechts abbiegen → Ziel: NÖRDLICH des Hindernisses
                                    (y_ziel > Hindernis center_y + height/2, x_ziel ≈ Hindernis center_x ± width/2)
                                    - Orientierung Süden + Links abbiegen → Ziel: NÖRDLICH des Hindernisses
                                    - Orientierung Osten + Links abbiegen → Ziel: NÖRDLICH des Hindernisses
                                    - Orientierung Osten + Rechts abbiegen → Ziel: SÜDLICH des Hindernisses

                                4. Fall: Turtlebot ÖSTLICH des Hindernisses
                                    - Orientierung Norden + Links abbiegen → Ziel: NÖRDLICH des Hindernisses
                                    - Orientierung Süden + Rechts abbiegen → Ziel: NÖRDLICH des Hindernisses  
                                    - Orientierung Westen + Rechts abbiegen → Ziel: NÖRDLICH des Hindernisses
                                    - Orientierung Westen + Links abbiegen → Ziel: SÜDLICH des Hindernisses
                                    (y_ziel < Hindernis center_y - height/2, x_ziel ≈ Hindernis center_x ± width/2)
                            
                            c) Wähle eine passende navigable_area und validiere:

                                - Suche eine navigable_area, die in der berechneten Zielregion liegt
                                - Wähle den Zenterpunkt dieser Area als Zielpunkt (x_ziel, y_ziel)
                                - Validiere mathematisch, dass die gewählten Koordinaten die Positionierungsanforderungen erfüllen
                                
                                Gib zurück: {
                                    "target": {
                                        "point": {"x": x_ziel, "y": y_ziel}, 
                                        "area": {
                                            "bottom_left": [x_bottom_left, y_bottom_left], 
                                            "width": width, 
                                            "height": height, 
                                            "center": [center_x, center_y]
                                        },
                                        "explanation": "Erklärung zur Wahl der Area"
                                    },
                                    "validation": {
                                        "turtlebot_current_position": {"x": x_robot, "y": y_robot},
                                        "turtlebot_orientation": "Himmelsrichtung",
                                        "turn_direction": "links/rechts",
                                        "obstacle_position": {"center_x": center_x, "center_y": center_y, "width": width, "height": height},
                                        "relative_position_to_obstacle": "nördlich/südlich/östlich/westlich",
                                        "target_relative_position": "nördlich/südlich/östlich/westlich", 
                                        "mathematical_validation": {
                                            "requirement": "Beschreibung der mathematischen Anforderung (z.B. x_ziel < center_x - width/2)",
                                            "actual_values": "Eingesetzte Werte (z.B. 150 < 200 - 50/2 = 175)",
                                            "satisfied": true/false
                                        }
                                    }
                                }
                                
                        A.8) Hinter ein Hindernis fahren lernen (Chain of Thought mit Verifikation):

                            Ein Befehl wie "fahre hinter den Tisch" oder "fahre hinter den Tisch beim Schrank" bedeutet, dass der Turtlebot einen Zielpunkt ansteuern soll, der sich aus seiner Perspektive "hinter" einem spezifizierten Hindernis befindet. Wenn kein Hindernis angegeben wird, dann wähle ein größeres aus dem Sichtfeld des Turtlebots vor ihm.
                            Um die korrekten Zielkoordinaten zu finden, befolge diese Schritte:

                            A.8.1) Identifiziere das Zielhindernis.
                                Analysiere den Befehl und die Turtlebotperspektive in diesem Beispiel (Die Position und Orientierung und Perspektive des Turtlebots gelten NUR für dieses Beispiel A8):
                                JSON der Roboterperspektive: {Einfügepunkt: JSON der Roboterperspektive}, Bild des Raumplans: {Einfügepunkt: Bild}, Navigationsbefehl: 'Fahre hinter den Tisch beim Schrank'.
                                Welcher Tisch ist gemeint? Wenn ein Referenzobjekt angegeben ist (z.B. "beim Schrank"), suche den Tisch, der am nächsten zu diesem Referenzobjekt liegt. Messe die Distanzen zwischen allen Tischen und dem Referenzobjekt und wähle den nächstgelegenen.
                                Gib zurück: { "target_obstacle": { "name": ">Tischname<", "type": "table", "center": [>center_x<, >center_y<], "dimensions": {"width": >width<, "height": >height<}, "reference_object": ">Referenzobjekt<", "explanation": "Der Tisch >Tischname< ist der nächstgelegene Tisch zum >Referenzobjekt< mit einer Distanz von >Distanz< cm." } }

                            A.8.2) Bestimme die relative Position des Turtlebots zum Zielhindernis.
                                Nutze die JSON der Roboterperspektive, um eindeutig zu bestimmen, wo sich der Turtlebot relativ zum Zielhindernis befindet:
                                
                                - Hindernis ist VOR dem Turtlebot → Turtlebot befindet sich in entgegengesetzter Richtung zur Orientierung
                                  (Orientierung Süden → Turtlebot ist NÖRDLICH des Hindernisses)
                                  (Orientierung Norden → Turtlebot ist SÜDLICH des Hindernisses)
                                  (Orientierung Osten → Turtlebot ist WESTLICH des Hindernisses)
                                  (Orientierung Westen → Turtlebot ist ÖSTLICH des Hindernisses)
                                - Hindernis ist RECHTS vom Turtlebot → Turtlebot befindet sich links zur Orientierung
                                - Hindernis ist LINKS vom Turtlebot → Turtlebot befindet sich rechts zur Orientierung  
                                - Hindernis ist HINTER dem Turtlebot → Turtlebot befindet sich in gleicher Richtung zur Orientierung
                                
                                Gib zurück: { "turtlebot_relative_position": "nördlich/südlich/östlich/westlich" }

                            A.8.3) Finde die Zielkoordinaten "hinter dem Hindernis" und validiere.
                                Basierend auf der aktuellen Position des Turtlebots, bestimme wo sich "hinter dem Hindernis" befindet:
                                
                                1. Fall: Turtlebot NÖRDLICH des Hindernisses
                                    → "Hinter dem Hindernis" = SÜDLICH des Hindernisses
                                    (y_ziel < center_y - height/2, x_ziel ≈ center_x ± width/2)
                                
                                2. Fall: Turtlebot SÜDLICH des Hindernisses  
                                    → "Hinter dem Hindernis" = NÖRDLICH des Hindernisses
                                    (y_ziel > center_y + height/2, x_ziel ≈ center_x ± width/2)
                                
                                3. Fall: Turtlebot ÖSTLICH des Hindernisses
                                    → "Hinter dem Hindernis" = WESTLICH des Hindernisses
                                    (x_ziel < center_x - width/2, y_ziel ≈ center_y ± height/2)
                                
                                4. Fall: Turtlebot WESTLICH des Hindernisses
                                    → "Hinter dem Hindernis" = ÖSTLICH des Hindernisses
                                    (x_ziel > center_x + width/2, y_ziel ≈ center_y ± height/2)
                                
                                Wähle eine passende navigable_area, die in der berechneten "hinter dem Hindernis" Region liegt und validiere mathematisch.
                                
                                Gib zurück: {
                                    "behind_target": {
                                        "point": {"x": x_ziel, "y": y_ziel}, 
                                        "area": {
                                            "bottom_left": [x_bottom_left, y_bottom_left], 
                                            "width": width, 
                                            "height": height, 
                                            "center": [center_x, center_y]
                                        },
                                        "explanation": "Erklärung zur Wahl der Area hinter dem Hindernis"
                                    },
                                    "validation": {
                                        "turtlebot_current_position": {"x": x_robot, "y": y_robot},
                                        "obstacle_position": {"center_x": center_x, "center_y": center_y, "width": width, "height": height},
                                        "turtlebot_relative_position": "nördlich/südlich/östlich/westlich",
                                        "behind_direction": "südlich/nördlich/westlich/östlich", 
                                        "mathematical_validation": {
                                            "requirement": "Beschreibung der mathematischen Anforderung (z.B. y_ziel < center_y - height/2)",
                                            "actual_values": "Eingesetzte Werte (z.B. 150 < 200 - 50/2 = 175)",
                                            "satisfied": true/false
                                        }
                                    }
                                }
                    
                        
                        Solltest du im folgenden einen solchen Befehl erhalten, dann wende diese Schritte auch auf den NEUEN KONTEXT mathematisch korrekt (Das bedeutet du sollst nicht nur das Antwortmuster auswendig lernen, sondern  wenn es um Zahlen geht die Lösung auch NACHGERECHNET haben) an.
                        Anhand der vorherigen Schritte hast du gelernt, wie du solche Aufgaben zu lösen hast. Verwende deine Reasoning-Fähigkeiten, um für den neuen Prompt und den neuen zugehörigen Kontext passende Zielkoordinaten (x,y) zu bestimmen. Mehrere Antworten sind richtig, da ein gewisser Bereich die Aufgabe sinnvoll erfüllt. Entscheide dich für Zielkoordinaten (x, y), die die Aufgabe am besten lösen und in dem befahrbaren Bereich (hellgrün mit dunkelgrünem Rand) liegen. Verifiziere explizit, dass sie in einem der Polygone des befahrbaren Bereichs aus der navigable_areas JSON liegen. Zeige deine Überprüfung, indem du das passende Polygon nennst und zeigst, dass die X- und Y-Werte innerhalb dessen Grenzen liegen. Wenn deine erste Wahl ungültig ist, suche neue Koordinaten und wiederhole die Überprüfung.

                Fall 2: Die Aktion ist 'Distanz_zurücklegen' oder 'Drehen':
                    - Wenn der Befehl eine einfache Bewegung ohne spezifisches Ziel ist (z.B. "fahre einen Meter vorwärts", "dreh dich um 90 Grad nach rechts"), sind die komplexen Analyseschritte A.1-A.7 NICHT notwendig. Formatiere deine Antwort direkt gemäß der passenden Ontologie.
                    - Beachte hierzu folgende Regeln: Die Lineargeschwindigkeit soll vom Wert her zwischen 0.1 und 0.35 liegen und vom Typ float sein. Die Winkelgeschwindigkeit soll vom Wert her zwischen 5 und 105 liegen und vom Typ int sein. Die Distanz soll vom Typ float sein und zwischen 0.1 und 1.5 liegen. Der Winkel und die Zielorientierung sollen vom Typ int sein und zwischen 0 und 360 liegen.

            Schritt 3: Du bekommst nun zu den 4 verschiedenen Aktionen jeweils ein paar Beispiele (Few-Shot Learning):
                    
                NAVIGIEREN BEISPIELE:
                    Du bekommst jetzt ein paar Beispiele, wo ein Mensch dem Turtlebot einen Navigationsbefehl gibt, und wie ein solcher Befehl in sinnvolle Zielkoordinaten (x,y) übersetzt wird. Diese Zielkoordinaten dürfen nur in dem befahrbaren Bereich liegen.
                    Beispiel 1:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 2:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 3:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    JSON der Roboterperspektive: {Einfügepunkt: Perspektive des Roboters}
                    Beispiel 4:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 5:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 6:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 7:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 8:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 9:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    JSON der Roboterperspektive: {Einfügepunkt: Perspektive des Roboters}
                    Beispiel 10:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}

                DISTANZ_ZURÜCKLEGEN BEISPIELE:
                    Beispiel 11:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 12:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    
                DREHEN BEISPIELE:
                    Beispiel 13:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}
                    Beispiel 14:
                    Bild des Raumplans: {Einfügepunkt: Bild}
                    JSON der Position und Orientierung: {Einfügepunkt: Roboter Position und Orientierung als JSON}
                    Befehl des Menschen:{Einfügepunkt: Navigationsbefehl}
                    erwartete Antwort: {Einfügepunkt: gewünschte Ausgabe mit Erklärung}


            Schritt 4: Löse die Aufgabe:
            **Die Beispiele in Schritt 3 dienen nur zum Verständnis der Methode. Übernehme unter keinen Umständen die Zielkoordinaten oder andere Werte aus diesen Beispielen für deine finale Lösung. Berechne die Lösung für den neuen Kontext immer vollständig neu.**
            Bild des Raumplans: {Einfügepunkt: Bild}
            JSON Beschreibung des Raumplans: {Einfügepunkt: JSON des Raumplans}
            Befehl des Menschen: "{Einfügepunkt: neuen Prompt}"

            Berücksichtige für deine finale Antwort die folgende Ontologie:
            {
                "Aktion": "Navigieren",
                "Parameter": {
                    "Zielposition": {
                        "x": x,
                        "y": y,
                        "z": 0
                    }
                },
                "Einheit": "Zentimeter",
                "explanation": explanation,
                "verification": {
                    "text": "Der Punkt (x_goal, y_goal) liegt im befahrbaren Bereich mit bottom_left=[bottom_left_x, bottom_left_y], width=width, height=height, da bottom_left_x <= x = x_goal <= bottom_left_x + width und bottom_left_y <= y = y_goal <= bottom_left_y + height.",
                    "values": {
                        "x_goal": x_goal,
                        "y_goal": y_goal,
                        "bottom_left_x": bottom_left_x,
                        "bottom_left_y": bottom_left_y,
                        "width": width,
                        "height": height,
                        "x_min": bottom_left_x,
                        "x_max": bottom_left_x + width,
                        "y_min": bottom_left_y,
                        "y_max": bottom_left_y + height
                    }
                }
            }
            {
                "Aktion": "Drehen",
                "Parameter": {
                    "Winkelgeschwindigkeit": Winkelgeschwindigkeit,
                    "Winkel": Winkel,
                    "im_Uhrzeigersinn": im_Uhrzeigersinn
                },
                "Einheit": "Grad"
            }
            {
                "Aktion": "Distanz_zurücklegen",
                "Parameter": {
                    "Lineargeschwindigkeit": Lineargeschwindigkeit,
                    "Distanz": Distanz,
                    "soll_Vorwärts": soll_Vorwärts
                },
                "Einheit": "Meter"
            }
            Antworte mit NUR einer JSON.
            """
        )

        # Prompt über promptBuilder erweitern (inkl. Roboterperspektive-Analyse)
        try:
            self.prepared_prompt = promptBuilder.build_prompt(
                system_instructions=self.system_instructions,
                image_path=self.dynamic_pose_image_path,
                turtlebot_x=x_cm,
                turtlebot_y=y_cm,
                turtlebot_heading=yaw_img_deg
            )
            
            # Extrahiere Orientierung aus den promptBuilder-Daten für Validierung
            # Der promptBuilder verwendet bereits die gleiche angle_to_compass Funktion
            try:
                from .fewshot import create_turtlebot_json
                turtlebot_data = create_turtlebot_json(x_cm, y_cm, yaw_img_deg)
                compass_direction = turtlebot_data["orientation"]["compass_direction"]
                self.get_logger().info(f"✅ Orientierung aus promptBuilder-Daten: {compass_direction}")
                
            except Exception as e:
                self.get_logger().warn(f"Warnung: Konnte Orientierung nicht aus promptBuilder-Daten extrahieren: {e}")
                # Fallback zu direkter Konvertierung
                from .draw_currentPosition import angle_to_compass
                _, _, compass_direction = angle_to_compass(yaw_img_deg)
            
            self.get_logger().info("✅ Prompt vorbereitet (inkl. Objektanalyse, Beispiele). Warte auf Text-Eingabe...")

        except Exception as e:
            self.get_logger().error(f'Fehler beim promptBuilder: {e}')
            self.prepared_prompt = self.system_instructions  # Fallback zum ursprünglichen Prompt

    def _publish_action_command(self, validated_data):
        """Transformiert die Koordinaten (falls Navigieren) und publisht das Action Command."""
        try:
            action = validated_data.get("Aktion")
            
            if action == "Navigieren":
                # Extrahiere die Zielkoordinaten (in cm)
                x_cm = validated_data["Parameter"]["Zielposition"]["x"]
                y_cm = validated_data["Parameter"]["Zielposition"]["y"]
                
                self.get_logger().info(f'Original-Koordinaten (Bild): x={x_cm}cm, y={y_cm}cm')
                
                # ZUERST: Publishe an /action_sim mit ORIGINAL-Koordinaten (vor Transformation)
                action_sim = validated_data.copy()  # Verwende Original-JSON
                action_sim_json_str = json.dumps(action_sim, ensure_ascii=False, indent=2)
                
                sim_msg = String()
                sim_msg.data = action_sim_json_str
                self.action_sim_publisher.publish(sim_msg)
                
                self.get_logger().info('✅ Action Sim (Original-Koordinaten) erfolgreich gepublished')
                self.get_logger().info(f'Action Sim JSON: {action_sim_json_str}')
                
                # DANN: Transformiere von Bild-Koordinaten (cm) zu Map-Koordinaten (m)
                # Dummy-Winkel von 0 Grad, da nur Position transformiert wird
                x_map_m, y_map_m, _ = forward_transformation(x_cm, y_cm, 0.0)
                
                self.get_logger().info(f'Transformierte Koordinaten (Map): x={x_map_m:.3f}m, y={y_map_m:.3f}m')
                
                # Erstelle das Action Command JSON für action_executor mit transformierten Koordinaten
                action_command = {
                    "Aktion": "Navigieren",
                    "Parameter": {
                        "Zielposition": {
                            "x": x_map_m,
                            "y": y_map_m,
                            "z": 0.0
                        }
                    }
                }
                
            elif action == "Distanz_zurücklegen":
                # Für Distanz_zurücklegen: keine Koordinatentransformation nötig
                # Publishe Original-Daten an beide Topics
                action_sim = validated_data.copy()
                action_sim_json_str = json.dumps(action_sim, ensure_ascii=False, indent=2)
                
                sim_msg = String()
                sim_msg.data = action_sim_json_str
                self.action_sim_publisher.publish(sim_msg)
                
                self.get_logger().info('✅ Action Sim (Distanz_zurücklegen) erfolgreich gepublished')
                
                action_command = validated_data.copy()
                self.get_logger().info(f'Distanz_zurücklegen: {validated_data["Parameter"]}')
                
            elif action == "Drehen":
                # Für Drehen: keine Koordinatentransformation nötig
                # Publishe Original-Daten an beide Topics
                action_sim = validated_data.copy()
                action_sim_json_str = json.dumps(action_sim, ensure_ascii=False, indent=2)
                
                sim_msg = String()
                sim_msg.data = action_sim_json_str
                self.action_sim_publisher.publish(sim_msg)
                
                self.get_logger().info('✅ Action Sim (Drehen) erfolgreich gepublished')
                
                action_command = validated_data.copy()
                self.get_logger().info(f'Drehen: {validated_data["Parameter"]}')
                
            else:
                self.get_logger().error(f'Unbekannte Aktion: {action}')
                return
            
            # Konvertiere zu JSON String für action_command
            action_json_str = json.dumps(action_command, ensure_ascii=False, indent=2)
            
            # Publishe das Action Command
            msg = String()
            msg.data = action_json_str
            self.action_command_publisher.publish(msg)
            
            self.get_logger().info('✅ Action Command erfolgreich gepublished')
            self.get_logger().info(f'Action Command JSON: {action_json_str}')
            
            # Starte Stop-Listener in separatem Thread
            self._start_stop_listener()
            
        except Exception as e:
            self.get_logger().error(f'Fehler beim Publishen des Action Commands: {e}')

    def _start_stop_listener(self):
        """Startet einen Thread, der auf Stop-Eingaben wartet."""
        def stop_listener():
            try:
                print("\n" + "="*50)
                print("AKTION GESTARTET")
                print("="*50)
                print("Gib 'Stop' ein, wenn die Aktion abgebrochen werden soll:")
                user_input = input().strip()
                
                if user_input.lower() in ['stop', 'stopp', 's']:
                    print("Stop-Befehl erkannt - sende Stopp-Signal...")
                    
                    # Sende Stop-Signal an action_executor
                    stop_msg = String()
                    stop_msg.data = "stop"
                    self.action_stop_publisher.publish(stop_msg)
                    
                    print("Stopp-Signal gesendet")
                else:
                    print("ℹ Eingabe ignoriert (keine Stop-Eingabe)")
                    
            except Exception as e:
                self.get_logger().error(f'Fehler im Stop-Listener: {e}')
        
        # Starte Thread für Stop-Listener
        stop_thread = threading.Thread(target=stop_listener, daemon=True)
        stop_thread.start()

    def _text_cb(self, msg: String):
        """Callback: erhält Text-Eingabe von chat.py.
        Verwendet die finale JSON direkt von Gemini 2.5 Pro, wenn sie gültig ist.
        """
        if self.prepared_prompt is None:
            self.get_logger().warn('Noch kein vorbereiteter Prompt vorhanden. Warte auf Startpose...')
            return

        user_text = msg.data.strip()
        self.get_logger().info(f'📝 Text erhalten: "{user_text}"')

        # Finalen Platzhalter ersetzen
        final_prompt = self.prepared_prompt.replace(
            "{Einfügepunkt: neuen Prompt}",
            user_text
        )

        # Starte eine neue, saubere Chat-Sitzung für diese Anfrage
        self.chat_session = self.model.start_chat(history=[])

        try:
            self.get_logger().info("🚀 Sende an Google Gemini 2.5 Pro...")
            response = self.chat_session.send_message(
                final_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=10000,
                    temperature=0.7,
                )
            )
            gemini_response = response.text
            self.get_logger().info("=== GOOGLE GEMINI ANTWORT ===")
            print("="*60, "\n", gemini_response, "\n", "="*60)

            # Versuche JSON aus der Antwort zu extrahieren
            try:
                # Extrahiere JSON zwischen ```json und ``` oder direkt als JSON
                json_match = re.search(r'```json\s*(.*?)\s*```', gemini_response, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1).strip()
                else:
                    # Fallback: Versuche JSON direkt zu finden
                    json_match = re.search(r'\{.*\}', gemini_response, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(0).strip()
                    else:
                        raise ValueError("Kein JSON-Block gefunden")

                # Parse das JSON
                final_json = json.loads(json_text)
                
                # Einfache Validierung der erforderlichen Felder
                if "Aktion" not in final_json:
                    raise ValueError("Aktion fehlt im JSON")
                if "Parameter" not in final_json:
                    raise ValueError("Parameter fehlt im JSON")
                
                self.get_logger().info("✅ Gültiges JSON von Gemini erhalten und wird direkt verwendet.")
                self._publish_action_command(final_json)
                
            except (json.JSONDecodeError, ValueError) as e:
                self.get_logger().error(f"❌ Konnte kein gültiges JSON aus der Antwort extrahieren: {e}")
                self.get_logger().error("Gemini Antwort war nicht im erwarteten JSON-Format")

        except Exception as e:
            self.get_logger().error(f'Fehler während der Gemini-Konversation: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = PromptGoogleNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
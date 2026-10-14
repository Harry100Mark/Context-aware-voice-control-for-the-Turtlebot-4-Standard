import os
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import json
import re
import math
import threading
import base64
from datetime import datetime
from PIL import Image

# Lokaler Import der Zeichenfunktion und Prompt-Builder
from . import draw_currentPosition
from . import promptBuilder
from .transformation import back_transformation, forward_transformation


class PromptGoogleNode(Node):
    """Minimaler Node: 
    - subscribed auf /chat (PoseStamped von chat.py)
    - erzeugt draw_currentPosition.png über draw_map
    - analysiert Objekte um den Turtlebot über perspectiveTaker
    - verwendet Google Gemini 2.5 Flash für AI-Antworten
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
        
        # Datenfile für die Speicherung der vorherigen Befehle/Reasoning zwischen Runden
        self.data_file = os.path.join(base_ws, 'src', 'prompt', 'previous_data.json')
        
        # Lade vorherige Daten falls vorhanden
        self.previous_command = None
        self.previous_pose = None
        self.previous_reasoning = None
        self._load_previous_data()
        
        # Aktuelle Pose (wird in _process_pose gesetzt)
        self.current_pose = None

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
        
        # Publisher: LLM Response Topic (für chat-Interface)
        self.llm_response_publisher = self.create_publisher(String, '/llm_response', 10)
        
        self.get_logger().info('prompt_google bereit. Warte auf Startpose und Text von chat.py (/chat oder /audio_record_pose)...')
        
        # Konfiguriere Google Gemini API
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            self.get_logger().error('GOOGLE_API_KEY Umgebungsvariable nicht gesetzt!')
            raise ValueError('GOOGLE_API_KEY ist erforderlich')
        
        genai.configure(api_key=api_key)
        
        # Modell per ENV wählbar (Standard: gemini-2.5-pro als leistungsstärkstes Modell)
        model_name = os.getenv('GOOGLE_GEMINI_MODEL', 'gemini-2.5-pro')
        self.model = genai.GenerativeModel(model_name)
        
        # Konfiguriere Generation-Config für optimierte Performance und reduzierte Filtering
        self.generation_config = genai.types.GenerationConfig(
            max_output_tokens=int(os.getenv('MAX_OUTPUT_TOKENS', '8192')),  # Höhere Token-Anzahl für vollständige Antworten
            temperature=float(os.getenv('TEMPERATURE', '0.1')),             # Niedrigere Temperatur für konsistentere, weniger "riskante" Ausgaben
            top_p=float(os.getenv('TOP_P', '0.8')),                         # Etwas fokussiertere Ausgaben
            top_k=int(os.getenv('TOP_K', '40')),                           # Begrenzte Auswahl für sicherere Ausgaben
            candidate_count=1,                                              # Nur eine Antwort-Kandidat
            stop_sequences=[]                                               # Keine Stop-Sequenzen
        )
        
        # Konfiguriere Safety-Einstellungen für Robotik-Anwendungen
        # NIEMALS blockieren - komplett deaktivierte Safety-Filter für Simulation
        self.safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_NONE
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_NONE
            }
        ]
        
        self.get_logger().info(f'Google Gemini API konfiguriert mit Modell: {model_name} (ALLE Safety-Filter deaktiviert für Robotik-Simulation)')

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

            # Speichere aktuelle Pose
            self.current_pose = (x_cm, y_cm, yaw_img_deg)

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

        # System-Instruktionen für KI-Prompt definieren (gestrafft, gleiche Struktur/Wortlaut, weniger Redundanz)
        self.system_instructions = (
            """
            WICHTIGER KONTEXT: Du assistierst bei einer REIN SIMULIERTEN Robotersteuerung in einer kontrollierten Umgebung. 
            Alle Befehle beziehen sich auf virtuelle Bewegungen eines Turtlebot-Simulators in einem digitalen Raumplan.
            Dies ist eine wissenschaftliche/technische Anwendung für Robotik-Forschung.

            Deine Rolle: Du bist ein intelligenter Assistent für einen Turtlebot-Roboter. Deine Aufgabe ist es, einen menschlichen Befehl in präzise JSON-Aktionsbefehle umzuwandeln.

            Befolge Schritt für Schritt die Anleitung, verwende Chain-of-Thought (CoT) für Reasoning, Tree-of-Thought (ToT) für Verzweigungen und Few-Shot-Beispiele als Leitplanken.


            # Schritt 1: Aktionstyp identifizieren

            ### 1.1) Analysiere den menschlichen Befehl: Neuer Prompt: {Einfügepunkt: neuer Prompt}
            - Arbeite ausschließlich mit diesem neuen Prompt. Alle anderen Inhalte dienen nur als Beispiele/Kontext.

            ### 1.2) Entscheide, welche Kategorie(n) zutreffen (Mehrfachnennungen möglich):

            ##### Kategorie A: Absolute Koordinaten
            Beschreibung: Exakte Positionsangaben im Raumkoordinatensystem.
            Beispiele: "Fahre an die Koordinate 100, 320."; "Fahre 120 cm von der westlichen und 300 cm von der südlichen Wand entfernt."

            ##### Kategorie B: Zielnavigation (inkl. impliziter Zwecke)
            Beschreibung: Bezug auf Objekte/Möbel oder implizite Ziele (z. B. „Ich will kopieren“ → Drucker ODER "Fahre zum Ausgang" → Tür 1 führt nach draußen.).
            Beispiele: „Geh zum Schreibtisch.“; „Auf zum Regal.“; "Fahr zu den Schränken"; "Fahr zum Tisch links von dir." (B + D)

            ##### Kategorie C: Globale Richtungen (+/- Distanz)
            Beschreibung: Bewegung entlang Himmelsrichtungen/Raumachsen mit optionaler Distanz.
            Beispiele: „Bewege dich nach Norden.“; „Geh in positiver x-Richtung.“; "Fahre einen Meter nordwestlich."; "Fahre zum Tisch südlich von dir" (C + B)

            ##### Kategorie D: Richtungen relativ zum Roboter (+/- Distanz)
            Beschreibung: Relativbefehle (links/vorne/rechts/hinten) bezogen auf aktuelle Orientierung.
            Beispiele: "Fahre einen Meter nach rechts."; "Fahr rückwärts."; "Biege links ab."; "Fahr um die Ecke."

            ##### Kategorie E: Bereiche und semantische Zonen
            Beschreibung: Ziel ist eine Fläche/Zone (z. B. „Arbeitsbereich“, „hintere linke Ecke“).
            Beispiele: „Geh in die hintere linke Ecke.“; "Fahr in die Mitte des Raums."; "Fahr in die Tischecke." (E + F)

            ##### Kategorie F: Relative/Relationale Navigation
            Beschreibung: Ziel über Relationen zu Bezugspunkten (neben, zwischen, hinter, gegenüber, vorbei an …).
            Beispiele: „Fahre vor das Fenster“; „Hinter den Tisch“; "Zwischen die Tische"; "1 m links vom Regal"; "am Tisch vorbei"

            ##### Kategorie G: Mehrschritt-/Pfadbefehle
            Beschreibung: Sequentielle Kombinationen mehrerer Teilbefehle/Kategorien.
            Beispiele: „Zum Tisch, dann links zum Fenster.“; "bis zum Roboter → links → zum Regal gegenüber vom Karton"

            ##### Kategorie J: Korrekturbefehle
            Beschreibung: Korrigiert/ändert die letzte Aktion (ggf. mit anderer Kategorie kombiniert).
            Beispiele: "Weiter."; "Die andere Ecke."; "Fahr zurück."; "Das andere links."

            ##### Kategorie K: Keine
            Beschreibung: Kein Navigationsbefehl (z. B. Smalltalk/Frage oder unbekannter Zielort).
            Beispiele: "Guten Tag."; "Welche Objekte siehst du?"; "Fahr zur Tankstelle."

            Wichtige Info: Wenn unsicher, überprüfe dich kurz (CoT/ToT) und begründe deine Wahl.

            ### 1.3) Gib zurück: "1.3) Es handelt sich um die Kategorie(n) >Kategorie(n)<. Hier ist eine Erklärung: >Erklärung<."

            # Few-Shot Galerie (kompakt)
            {Einfügepunkt: Few-Shot Beispiele}


            # Schritt 2: Umgebung des Turtlebots kennenlernen

            Analysiere das Raumplan-Bild: {Einfügepunkt: Bild der jetzigen Pose}, die JSON-Beschreibung inkl. topologischem Graph: {Einfügepunkt: JSON des Raumplans} sowie die JSON der Roboterperspektive: {Einfügepunkt: JSON der Roboterperspektive}. Kontext-Prompt: {Einfügepunkt: neuer Prompt}

            ### 2.1) Startpose identifizieren
            - Turtlebot (runder Kreis mit Sichtfeld), Position an Achsen ablesbar, Orientierung über roten Pfeil. Auch in JSON vorhanden.
            Gib zurück: "2.1) Der Roboter befindet sich an der Position >x, y< und schaut in Richtung >Himmelsrichtung<."

            ### 2.2) Himmelsrichtungen verstehen
            - Bilddimensionen: x: -29..689, y: 0..654. Norden = oben (größere y), Westen = links (kleinere x).
            - Bestimme die Richtung zu z. B. Tisch 10 und plausibilisiere mit Roboterperspektive.
            Gib zurück: "2.2) Vom Turtlebot aus gesehen befindet sich Tisch 10 in Richtung >Himmelsrichtung<." Oder mit kurzer Korrektur, falls nötig.

            ### 2.3) Perspektive übernehmen
            - Bestimme je ein Objekt vor/rechts/links/hinter dem Turtlebot; verifiziere mit Roboterperspektive.
            Gib zurück: "2.3) Vor: >Objekt<, rechts: >Objekt<, links: >Objekt<, hinter: >Objekt<."

            ### 2.4) Befahrbarkeit verstehen
            - Navigierbare Bereiche sind hellgrün (mehrere Polygone in JSON). Nur diese Koordinaten sind befahrbar.
            - Zeige kurz a) warum (480,300) befahrbar ist, b) warum (360,360) nicht, c) einen befahrbaren Punkt nördlich von Tisch 6.
            Gib zurück-Beispiele:
            - a) "2.4a) (480,300) befahrbar: area_index >area_index<. Beweis: >[bottom_left]< <= [x,y] <= >[bottom_left]+[width,height]<."
            - b) "2.4b) (360,360) nicht befahrbar: liegt im Objekt >Objekt</in keiner navigable_area. Beweis: |[360,360]->center| < >diameter<|."
            - c) "2.4c) >(x,y)< nördlich von Tisch 6 befahrbar. Beweis: >y< > >center+height/2< und >[bottom_left]< <= [x,y] <= >[bottom_left]+[width,height]<."


            # Schritt 3: Ausführung (nur für die in 1.2 gewählten Kategorien)

            Hinweise zu Few-Shot: Du siehst Beispiele. Nicht die Parameter kopieren; nutze sie zum Lernen der Vorgehensweise.

            ### zu Kategorie A: Absolute Koordinaten
            - x,y direkt/indirekt angegeben (ggf. aus Wandabständen ableiten).
            Wichtige Info für Schritt 4: Aktion = Navigation.

            ### zu Kategorie B: Zielnavigation (inkl. impliziter Zwecke)
            1) Bestimme Ziel-Typ(en) (type). Gib zurück: ">Das Ziel ist >type(s)<."
            2) Liste potenzielle Ziele. Gib zurück: "Potenzielle Ziele: >...<."
            3) Verfeinere: Kombination mit anderen Kategorien? Nähe/Sichtfeld/Fahrtrichtung? Historie (Alter Befehl und alte Pose)? Konstellationen (mehrere Ziele nebeneinander)?
            4) Entscheide Ziel. Gib zurück: "Gemeint ist/sind >Ziel<."
            5) Wähle befahrbaren Bereich passend zur Lage (z. B. südlich des Ziels, wenn Roboter südlich kommt).
            6) Wähle wenige befahrbare Kandidatenkoordinaten (z. B. Nodes). Gib zurück: "Koordinaten >...< sind befahrbar und erfüllen >Bedingung<."
            7) Wähle beste Zielkoordinate und begründe kurz inkl. Befahrbarkeitsbeweis.
            8) Kurz gegenprüfen (keine Rechenfehler).
            Wichtige Info: Aktion = Navigation.

            ### zu Kategorie C: Globale Richtungen (+/- Distanz)
            1) Fallklassifikation: A) „um Hindernis/Abbiegen“, B) exakte Distanz, C) vage Distanz, D) nur Richtung. Gib zurück: "Fall >A/B/C/D< (ggf. Kombination)."
            2) Kontextanalyse per Bild/Graph/Perspektive: Hindernisse/Ziele in Richtung bestimmen.
               - B: Prüfe Ziel an Distanz; ggf. Bereich hinter Hindernis.
               - C: „weit“ = weiter entfernte/geschützte Ziele; „ein Stück“ = nahe Ziele.
               - D: Wähle sinnvolles Ziel in Richtung per Kontext.
               - A: Relevantestes Hindernis in Richtung finden. Gib zurück: "Relevantes Hindernis: >...<, weil >...<." Bestimme befahrbaren Node in der Zielrichtung: "Zielkoordinate: (x,y)."
            3) Gib Zielkoordinaten und Befahrbarkeitsbeweis zurück.

            ### zu Kategorie D: Richtungen relativ zum Roboter (+/- Distanz)
            1) Bestimme Himmelsrichtung relativ zur Orientierung. Gib zurück: "Die Richtung ist >Himmelsrichtung<."
            2) Fall A: mit Ziel (kombiniere mit anderer Kategorie, filtere auf die Richtung). Fall B: nur Richtung → kontextabhängiges Ziel.
               - Prüfe Bereiche/Hindernisse/Wände in ~2 m in der Richtung per Bild/Graph. Gib zurück: "In Richtung >...<: >...<."
               - Wähle Kandidatenbereiche/-koordinaten, verfeinere nach Distanz/Relationen, wähle beste Zielkoordinate + Beweis.

            ### zu Kategorie E: Bereiche/Zonen
            1) Analysiere Zone/Begriff, mappe auf Ansammlungen von Objekten/Flächen/Wände.
            2) Liste potenzielle Bereiche; verfeinere mit anderen Kategorien oder Nähe/Sichtfeld.
            3) Wähle Bereich und darin befahrbare Kandidatenkoordinaten, wähle beste + Beweis.
            Wichtige Info: Aktion = Navigation.

            ### zu Kategorie F: Relative/Relationale Navigation
            1) Bezugspunkte (types) bestimmen. Gib zurück: "Die Bezugspunkte sind >...<."
            2) Bestimme Lage des Roboters zu den Bezugspunkten (N/W/S/O) und leite daraus rechts/links/vor/hinter relativ zu den Bezugspunkten ab. Gib zurück: "Der Roboter befindet sich >Himmelsrichtung< vom Bezugspunkt >Bezugspunkt<. Die Relation >Relation< meint also >Himmelsrichtung< vom >Bezugspunkt<."
               - Unterschied zu D: Zuerst Perspektive vom Roboter hin zum Bezugspunkt einnehmen, dann relative Richtungen interpretieren.
               - Beispiel: Roboter nördlich vom Regal → "Tür links vom Regal"? → Lösung: Roboter ist nördlich vom Regal → Regal ist südlich vom Roboter → links vom Regal meint östlich vom Regal → Tür 3 ist das Ziel.
               - Beispielaufgabe: Roboter ist südlich von der Kommode → "Whiteboard rechts von der Kommode?" → Gib zurück: ">Whiteboard2 oder Whiteboard1<, weil >Begründung<."
            3) Mehrdeutigkeiten auflösen: andere Kategorien, Nähe/Sichtfeld, Historie; prüfe, wo befahrbare Zonen die Relation erfüllen (Graph).
            4) Wähle beste Zielkoordinate + Beweis.
            Wichtige Info: Aktion = Navigation.

            ### zu Kategorie G: Mehrschritt/Pfad
            - Schritte strikt nacheinander. Zielpose der Aktion i ist Startpose für i+1.
            - Richtungsfahrt aktualisiert Pose (z. B. 1 m West → x -= 100, yaw=180°).
            - Nach Navigation ist exakte yaw ggf. unbekannt → plausibel schätzen per Graph/Pfadverlauf.

            ### zu Kategorie J: Korrekturbefehle
            1) Betrachte alten Befehl + alte Pose (und ggf. altes Reasoning).
            2) Was war falsch/verbesserbar? 3) Wiederhole die letzte Ableitung mit korrigierter Zielsetzung ab letzter Pose.

            ### zu Kategorie K: Keine
            - Unklarer Wunsch: "Das habe ich nicht verstanden. Bitte formuliere deinen Befehl oder deine Frage neu."
            - Frage: kurz beantworten (1 Satz).
            Wichtige Info: Aktion = Keine.


            # Schritt 4: Ontologie (Ausgabeformat)

            explanation ist die knappe Nutzerantwort (Ich-Form) - nenne keine Namen wie 'Tisch 10' und keine Zielkoordinaten (x,y), sondern beschreibe bezüglich des Raums für den Menschen, der den echten Raum sieht.
            reasoning erklärt den Prozess für Entwickler.
            Endformat (Top-Level) – genau dieses JSON-konforme Schema ausgeben:

            {
                "Aktion": "Navigieren" | "Keine",
                "Parameter": { "Zielposition": { "x": int, "y": int, "z": 0 } },
                "Einheiten": { "Position": "Zentimeter" },
                "verification": {
                    "text": "Beweis-String für Befahrbarkeit.",
                    "values": {
                        "x_goal": float, "y_goal": float,
                        "bottom_left_x": float, "bottom_left_y": float,
                        "width": float, "height": float,
                        "x_min": float, "x_max": float,
                        "y_min": float, "y_max": float
                    }
                },
                "explanation": "Kurze Erklärung des Reasonings (1 Satz).",
                "reasoning": "Detaillierte Erklärung des Reasonings (darf mehr als 1 Satz sein)."
            }
            """
        )

        # Prompt über promptBuilder erweitern (inkl. Roboterperspektive-Analyse)
        try:
            self.prepared_prompt = promptBuilder.build_prompt(
                system_instructions=self.system_instructions,
                image_path=self.dynamic_pose_image_path,
                turtlebot_x=x_cm,
                turtlebot_y=y_cm,
                turtlebot_heading=yaw_img_deg,
                previous_command=self.previous_command,
                previous_pose=self.previous_pose,
                previous_reasoning=self.previous_reasoning
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
                
                # Konvertiere zu JSON String für action_command
                action_json_str = json.dumps(action_command, ensure_ascii=False, indent=2)
                
                # Publishe das Action Command
                msg = String()
                msg.data = action_json_str
                self.action_command_publisher.publish(msg)
                
                self.get_logger().info('✅ Action Command erfolgreich gepublished')
                self.get_logger().info(f'Action Command JSON: {action_json_str}')
                
            elif action == "Keine":
                # Für "Keine" Aktion: publishe nur an action_sim, kein action_command nötig
                action_sim = validated_data.copy()
                action_sim_json_str = json.dumps(action_sim, ensure_ascii=False, indent=2)
                
                sim_msg = String()
                sim_msg.data = action_sim_json_str
                self.action_sim_publisher.publish(sim_msg)
                
                self.get_logger().info('✅ Action Sim (Keine Aktion) erfolgreich gepublished')
                self.get_logger().info(f'Action Sim JSON: {action_sim_json_str}')
                
                # Keine weitere Aktion erforderlich
                return
                
            else:
                self.get_logger().error(f'Unbekannte Aktion: {action}')
                return
            
            # Starte Stop-Listener in separatem Thread (nur für Navigieren)
            if action == "Navigieren":
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
        # Ersetze beide möglichen Platzhalter-Varianten für den neuen Prompt
        final_prompt = (
            self.prepared_prompt
            .replace("{Einfügepunkt: neuen Prompt}", user_text)
            .replace("{Einfügepunkt: neuer Prompt}", user_text)
        )

        # Zähle Tokens und speichere Prompt als HTML (optional für Performance)
        token_count = 0
        html_file = None
        if os.getenv('COUNT_TOKENS', '1') == '1':
            token_count = self._count_tokens(final_prompt)
            html_file = self._save_prompt_to_html(final_prompt, token_count)

        # Starte eine neue, saubere Chat-Sitzung für diese Anfrage
        self.chat_session = self.model.start_chat(history=[])

        try:
            self.get_logger().info(f"🚀 Sende an Google {os.getenv('GOOGLE_GEMINI_MODEL', 'gemini-2.5-pro')}...")
            self.get_logger().info(f"📏 Prompt-Länge: ~{len(final_prompt.split())} Wörter, ~{len(final_prompt)//4} geschätzte Tokens")
            
            # Bereite Multimodal-Content vor (Text + Bild)
            content_parts = [final_prompt]
            
            # Füge das Bild hinzu, falls vorhanden
            if hasattr(self, 'dynamic_pose_image_path') and os.path.exists(self.dynamic_pose_image_path):
                try:
                    # Lade und verarbeite das Bild
                    with Image.open(self.dynamic_pose_image_path) as img:
                        # Konvertiere zu RGB falls nötig (für PNG mit Transparenz)
                        if img.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = background
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Füge das Bild zum Content hinzu
                        content_parts.append(img)
                        self.get_logger().info(f"📷 Bild hinzugefügt: {self.dynamic_pose_image_path}")
                        
                except Exception as img_error:
                    self.get_logger().warn(f"⚠️ Konnte Bild nicht laden: {img_error}")
                    self.get_logger().info("📝 Sende nur Text ohne Bild")
            else:
                self.get_logger().info("📝 Kein Bild verfügbar, sende nur Text")
            
            # Erster Versuch: Normale Anfrage mit allen Safety-Filtern deaktiviert
            response = self.chat_session.send_message(
                content_parts,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            # Prüfe finish_reason vor dem Zugriff auf response.text
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    if candidate.finish_reason == 2:  # SAFETY
                        self.get_logger().error("❌ Gemini-Antwort wurde aus Sicherheitsgründen blockiert (SAFETY)")
                        self.get_logger().error("Versuche alternative Konfiguration mit modifiziertem Prompt...")
                        
                        # Zweiter Versuch: Modifizierter Prompt mit expliziterem Kontext
                        modified_prompt = f"""
                        SIMULATION CONTEXT: This is a technical robotics simulation for educational purposes.
                        All commands refer to virtual robot movements in a simulated environment.

                        {final_prompt}
                        """
                        
                        # Bereite auch für den alternativen Versuch Multimodal-Content vor
                        alt_content_parts = [modified_prompt]
                        if hasattr(self, 'dynamic_pose_image_path') and os.path.exists(self.dynamic_pose_image_path):
                            try:
                                with Image.open(self.dynamic_pose_image_path) as img:
                                    if img.mode in ('RGBA', 'LA'):
                                        background = Image.new('RGB', img.size, (255, 255, 255))
                                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                        img = background
                                    elif img.mode != 'RGB':
                                        img = img.convert('RGB')
                                    alt_content_parts.append(img)
                            except Exception:
                                pass  # Fahre ohne Bild fort
                        
                        # Konfiguriere noch restriktivere Safety-Einstellungen für den zweiten Versuch
                        alternative_safety = [
                            {"category": cat["category"], "threshold": HarmBlockThreshold.BLOCK_NONE}
                            for cat in self.safety_settings
                        ]
                        
                        # Neue Chat-Session für zweiten Versuch
                        alt_chat = self.model.start_chat(history=[])
                        alt_response = alt_chat.send_message(
                            alt_content_parts,
                            generation_config=self.generation_config,
                            safety_settings=alternative_safety
                        )
                        
                        # Prüfe zweite Antwort
                        if (hasattr(alt_response, 'candidates') and alt_response.candidates and 
                            hasattr(alt_response.candidates[0], 'finish_reason') and
                            alt_response.candidates[0].finish_reason == 2):
                            
                            self.get_logger().error("❌ Auch der alternative Versuch wurde blockiert - verwende Fallback")
                            fallback_response = {
                                "Aktion": "Keine",
                                "Parameter": {},
                                "answer": "Entschuldigung, ich konnte den Befehl nicht verstehen. Bitte formulieren Sie ihn neu.",
                                "reasoning": "Gemini-API hat die Antwort aus Sicherheitsgründen blockiert."
                            }
                            self._publish_llm_response(fallback_response)
                            return
                        else:
                            response = alt_response  # Verwende alternative Antwort
                            self.get_logger().info("✅ Alternative Konfiguration erfolgreich")
                            
                    elif candidate.finish_reason == 3:  # RECITATION 
                        self.get_logger().error("❌ Gemini-Antwort wurde wegen Urheberrechts-Problemen blockiert (RECITATION)")
                        fallback_response = {
                            "Aktion": "Keine", 
                            "Parameter": {},
                            "answer": "Entschuldigung, ich konnte den Befehl nicht verarbeiten. Bitte versuchen Sie es erneut.",
                            "reasoning": "Gemini-API hat die Antwort wegen möglicher Urheberrechts-Verletzungen blockiert."
                        }
                        self._publish_llm_response(fallback_response)
                        return
                    elif candidate.finish_reason not in [0, 1]:  # 0=UNSPECIFIED, 1=STOP (normal)
                        self.get_logger().error(f"❌ Gemini-Antwort unvollständig. Finish reason: {candidate.finish_reason}")
                        fallback_response = {
                            "Aktion": "Keine",
                            "Parameter": {},
                            "answer": "Die Antwort wurde unvollständig übertragen. Bitte versuchen Sie es erneut.",
                            "reasoning": f"Gemini-API finish_reason: {candidate.finish_reason}"
                        }
                        self._publish_llm_response(fallback_response)
                        return
            
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
                
                # Extrahiere und publiziere LLM-Antwort für Chat
                self._publish_llm_response(final_json)
                
                # Speichere die aktuellen Daten für die nächste Runde
                if self.current_pose is not None:
                    reasoning = self._extract_reasoning_from_response(gemini_response)
                    self._save_current_data(user_text, self.current_pose, reasoning)
                
            except (json.JSONDecodeError, ValueError) as e:
                self.get_logger().error(f"❌ Konnte kein gültiges JSON aus der Antwort extrahieren: {e}")
                self.get_logger().error("Gemini Antwort war nicht im erwarteten JSON-Format")

        except Exception as e:
            # Spezielle Behandlung für Safety-Filter-Fehler
            error_msg = str(e)
            if "finish_reason" in error_msg and "2" in error_msg:
                self.get_logger().error('❌ Gemini Safety-Filter hat die Antwort blockiert')
                self.get_logger().error('💡 Tipp: Versuchen Sie eine andere Formulierung des Befehls')
                
                # Publiziere Fehlermeldung an Chat
                fallback_response = {
                    "Aktion": "Keine",
                    "Parameter": {},
                    "answer": "Der Befehl konnte aufgrund von Sicherheitsrichtlinien nicht verarbeitet werden. Bitte formulieren Sie ihn anders.",
                    "reasoning": "Google Gemini Safety-Filter Aktivierung"
                }
                self._publish_llm_response(fallback_response)
                
            elif "response.text" in error_msg and "valid" in error_msg:
                self.get_logger().error('❌ Gemini-Antwort wurde gefiltert (kein gültiger Content)')
                self.get_logger().error('💡 Möglicherweise Safety-Filter oder andere Beschränkungen')
                
                # Publiziere Fehlermeldung an Chat
                fallback_response = {
                    "Aktion": "Keine",
                    "Parameter": {},
                    "answer": "Die Antwort wurde gefiltert. Bitte versuchen Sie eine andere Formulierung.",
                    "reasoning": "Gemini Content-Filter aktiviert"
                }
                self._publish_llm_response(fallback_response)
                
            else:
                self.get_logger().error(f'Allgemeiner Fehler während der Gemini-Konversation: {e}')
                
                # Publiziere allgemeine Fehlermeldung an Chat
                fallback_response = {
                    "Aktion": "Keine",
                    "Parameter": {},
                    "answer": "Es gab einen technischen Fehler. Bitte versuchen Sie es erneut.",
                    "reasoning": f"Technischer Fehler: {str(e)}"
                }
                self._publish_llm_response(fallback_response)

    def _load_previous_data(self):
        """Lädt die vorherigen Daten aus der JSON-Datei."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.previous_command = data.get('previous_command')
                    self.previous_pose = data.get('previous_pose')
                    self.previous_reasoning = data.get('previous_reasoning')
                    self.get_logger().info(f"Vorherige Daten geladen: Command={bool(self.previous_command)}, "
                                         f"Pose={bool(self.previous_pose)}, Reasoning={bool(self.previous_reasoning)}")
            else:
                self.get_logger().info("Keine vorherigen Daten vorhanden")
        except Exception as e:
            self.get_logger().warn(f"Fehler beim Laden der vorherigen Daten: {e}")
            self.previous_command = None
            self.previous_pose = None
            self.previous_reasoning = None

    def _save_current_data(self, command: str, pose: tuple, reasoning: str):
        """Speichert die aktuellen Daten für die nächste Runde."""
        try:
            data = {
                'previous_command': command,
                'previous_pose': pose,
                'previous_reasoning': reasoning
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.get_logger().info("Aktuelle Daten für nächste Runde gespeichert")
        except Exception as e:
            self.get_logger().error(f"Fehler beim Speichern der aktuellen Daten: {e}")

    def _extract_reasoning_from_response(self, gemini_response: str) -> str:
        """Extrahiert den Reasoning-Prozess aus der Gemini-Antwort."""
        try:
            # Suche nach Reasoning-Prozess in der Antwort
            # Kann verschiedene Formate haben, z.B.:
            # "Reasoning-Prozess: ..." oder direkt den Text vor dem JSON
            
            # Entferne JSON-Block aus der Antwort
            response_without_json = re.sub(r'```json.*?```', '', gemini_response, flags=re.DOTALL)
            response_without_json = re.sub(r'\{.*\}', '', response_without_json, flags=re.DOTALL)
            
            # Bereinige die Antwort
            reasoning = response_without_json.strip()
            
            # Falls zu kurz, verwende gesamte ursprüngliche Antwort
            if len(reasoning) < 50:
                reasoning = gemini_response
                
            return reasoning
            
        except Exception as e:
            self.get_logger().warn(f"Fehler beim Extrahieren des Reasoning: {e}")
            return gemini_response  # Fallback: gesamte Antwort verwenden

    def _publish_llm_response(self, json_data):
        """Publiziert die LLM-Antwort für das Chat-Interface."""
        try:
            # Publiziere das VOLLSTÄNDIGE JSON als String, damit chat.py explanation und reasoning extrahieren kann
            import json
            full_json_string = json.dumps(json_data, ensure_ascii=False, indent=2)
            
            # Publiziere das vollständige JSON
            msg = String()
            msg.data = full_json_string
            self.llm_response_publisher.publish(msg)
            
            self.get_logger().info(f"Vollständiges LLM-JSON publiziert (length: {len(full_json_string)} chars)")
            
        except Exception as e:
            self.get_logger().error(f"Fehler beim Publizieren der LLM-Antwort: {e}")

    def _count_tokens(self, prompt_text):
        """Zählt die Anzahl der Input-Tokens für den gegebenen Prompt."""
        try:
            token_count = self.model.count_tokens(prompt_text)
            self.get_logger().info(f"📊 Token-Anzahl: {token_count.total_tokens} Tokens")
            return token_count.total_tokens
        except Exception as e:
            self.get_logger().warn(f"Fehler beim Zählen der Tokens: {e}")
            return 0

    def _save_prompt_to_html(self, prompt_text, token_count):
        """Speichert den kompletten Prompt als HTML-Datei mit eingebetteten Bildern."""
        try:
            # Erstelle Verzeichnis für HTML-Exports
            home = os.path.expanduser('~')
            base_ws = os.path.join(home, 'ros2_ws')
            html_dir = os.path.join(base_ws, 'src', 'prompt', 'prompt_exports')
            os.makedirs(html_dir, exist_ok=True)
            
            # Timestamp für eindeutigen Dateinamen
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = os.path.join(html_dir, f"prompt_{timestamp}.html")
            
            # HTML-Template erstellen
            html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini Prompt Export - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .prompt-content {{ background-color: #f9f9f9; padding: 20px; border-radius: 5px; }}
        .image-container {{ margin: 20px 0; text-align: center; }}
        .image-container img {{ max-width: 800px; border: 1px solid #ddd; border-radius: 5px; }}
        .token-info {{ background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin-bottom: 20px; }}
        pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Gemini 2.5 Pro - Prompt Export</h1>
        <p><strong>Timestamp:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Node:</strong> prompt_google2</p>
    </div>
    
    <div class="token-info">
        <h2>📊 Token-Information</h2>
        <p><strong>Input-Tokens:</strong> {token_count}</p>
        <p><strong>Modell:</strong> {os.getenv('GOOGLE_GEMINI_MODEL', 'gemini-2.5-pro')}</p>
    </div>
    
    <div class="prompt-content">
        <h2>📝 Prompt-Inhalt</h2>
        <pre>{prompt_text.replace('<', '&lt;').replace('>', '&gt;')}</pre>
    </div>
"""

            # Suche nach Bildreferenzen im Prompt und konvertiere sie zu Base64
            # Verschiedene Patterns für Bildpfade im Prompt
            image_refs = []
            
            # Pattern 1: "Bild: path.png"
            pattern1_refs = re.findall(r'Bild: (.*?\.png)', prompt_text)
            image_refs.extend(pattern1_refs)
            
            # Pattern 2: "Bild der aktuellen Roboterposition: file://path.png"
            pattern2_refs = re.findall(r'Bild der aktuellen Roboterposition: (file://.*?\.png)', prompt_text)
            image_refs.extend(pattern2_refs)
            
            # Pattern 3: Andere Bildmuster falls nötig
            pattern3_refs = re.findall(r'file://(.*?\.png)', prompt_text)
            image_refs.extend(pattern3_refs)
            
            # Entferne Duplikate
            image_refs = list(set(image_refs))
            
            if image_refs:
                html_content += "\n    <div class='image-container'>\n        <h2>🖼️ Eingebettete Bilder</h2>\n"
                for img_path in image_refs:
                    # Behandle file:// URLs
                    if img_path.startswith('file://'):
                        actual_path = img_path.replace('file://', '')
                    else:
                        actual_path = img_path
                    
                    if os.path.exists(actual_path):
                        try:
                            # Konvertiere Bild zu Base64
                            with open(actual_path, 'rb') as img_file:
                                img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            
                            html_content += f"""
        <div>
            <h3>{os.path.basename(actual_path)}</h3>
            <img src="data:image/png;base64,{img_data}" alt="{os.path.basename(actual_path)}">
            <p><em>Original: {img_path}</em></p>
            <p><em>Pfad: {actual_path}</em></p>
        </div>
"""
                        except Exception as e:
                            html_content += f"<p>❌ Fehler beim Laden von {actual_path}: {e}</p>\n"
                    else:
                        html_content += f"<p>❌ Bild nicht gefunden: {img_path} (Pfad: {actual_path})</p>\n"
                html_content += "    </div>\n"

            html_content += """
</body>
</html>"""

            # Speichere HTML-Datei
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.get_logger().info(f"💾 Prompt gespeichert als HTML: {html_file}")
            return html_file
            
        except Exception as e:
            self.get_logger().error(f"Fehler beim Speichern der HTML-Datei: {e}")
            return None


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
# prompt.py (angepasst)

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseWithCovarianceStamped
from geometry_msgs.msg import PoseStamped
import openai, base64, json, os, math, re
from .....Python_Project import transformations as tfm # type: ignore
from typing import Optional
from PIL import Image, ImageDraw

class TextProcessorNode(Node):
    def __init__(self):
        super().__init__('text_processor')
        # Subscriptions
        self.create_subscription(String, '/transcribed_text', self.text_callback, 10)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.pose_callback, 10)
        self.create_subscription(PoseStamped, '/audio_record_pose', self.audio_pose_callback, 10)
        # Publisher
        self.publisher = self.create_publisher(String, '/action_command', 10)
        self.publisher_raster = self.create_publisher(String, '/action_command_raster', 10)
        # State
        # Toggle to include images in LLM messages (default: on). Set LLM_INCLUDE_IMAGES=0 to disable.
        _inc = os.getenv('LLM_INCLUDE_IMAGES', '1').strip().lower()
        self.include_images = not (_inc in ('0', 'false', 'no'))
        # Prompt logging toggles
        _log = os.getenv('LLM_LOG_PROMPT', '0').strip().lower()
        self.log_prompt = _log in ('1', 'true', 'yes', 'on', 'debug')
        _log_img = os.getenv('LLM_LOG_PROMPT_IMAGES', '0').strip().lower()
        self.log_prompt_images = _log_img in ('1', 'true', 'yes', 'on', 'debug')
        # OpenAI defaults
        _raw_key = os.getenv('OPENAI_API_KEY', '')
        self.api_key = _raw_key.strip()
        if _raw_key and _raw_key != self.api_key:
            self.get_logger().warn('OPENAI_API_KEY enthielt führende/abschließende Leerzeichen und wurde bereinigt.')
        _raw_model = os.getenv('OPENAI_MODEL', 'gpt-4.1')
        self.model_name = _raw_model.strip()
        self.current_pose = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.current_audio_pose: Optional[PoseStamped] = None
        self.last_amcl_pose: Optional[PoseWithCovarianceStamped] = None
        self.current_pose_image_path: Optional[str] = None
        self.current_pose_image_timestamp: Optional[float] = None
        # Deferred logic
        self.pending_transcription: Optional[str] = None
        self.wait_deadline: Optional[float] = None
        self.image_max_age_sec = 2.0
        self.max_wait_for_image_sec = 1.0
        self.retry_interval_sec = 0.2
        self.create_timer(self.retry_interval_sec, self._retry_pending)
        # Paths (dynamisch ab HOME + 'ros2_ws')
        home = os.path.expanduser('~')
        base_ws = os.path.join(home, 'ros2_ws')
        map_dir = os.path.join(base_ws, 'src', 'map')
        self.base_map_path = os.path.join(map_dir, 'RaumplanRaster.png')
        self.robot_sprite_path = os.path.join(map_dir, 'Turtlebot_robot_target_units.png')
        self.dynamic_pose_image_path = os.path.join(map_dir, 'Raumplan_currentPose.png')
        self.target_pose_image_path = os.path.join(map_dir, 'Raumplan_Zielposition.png')
        # Transformationen ausgelagert nach transformations.py
        # Layout (Pixel≈cm Koordinaten auf Karte)
        self.room_layout = {
            'Tisch_1': {'Position': {'x': 499, 'y': 468, 'z': 0}, 'Beschreibung': 'Arbeitsplatz mit Computer und grauem Stuhl.'},
            'Tisch_2': {'Position': {'x': 624, 'y': 468, 'z': 0}, 'Beschreibung': 'Tisch am Fenster mit Telefon und blauem Stuhl.'},
            'Tisch_3': {'Position': {'x': 643, 'y': 248, 'z': 0}, 'Beschreibung': 'Tisch mit 2 Stühlen am Fenster.'},
            'Tisch_4': {'Position': {'x': 643, 'y': 368, 'z': 0}, 'Beschreibung': 'Tisch am Fenster mit einem Stuhl und Karton.'},
            'Tisch_5': {'Position': {'x': 622, 'y': 142, 'z': 0}, 'Beschreibung': 'Arbeitsplatz mit Computer am Fenster.'},
            'Tisch_6': {'Position': {'x': 486, 'y': 142, 'z': 0}, 'Beschreibung': 'Tisch mit 3 Stühlen.'},
            'Tisch_7': {'Position': {'x': 141, 'y': 163, 'z': 0}, 'Beschreibung': 'Tisch mit Kartons und 2 Stühlen.'},
            'Tisch_8': {'Position': {'x': 40, 'y': 41, 'z': 0}, 'Beschreibung': 'Tisch an der Wand.'},
            'Tisch_9': {'Position': {'x': 40, 'y': 142, 'z': 0}, 'Beschreibung': 'Tisch in der Ecke.'},
            'Tisch_10': {'Position': {'x': 338, 'y': 300, 'z': 0}, 'Beschreibung': 'Runder Tisch mit 4 blauen Stühlen.'},
            'Kommode': {'Position': {'x': 190, 'y': 22, 'z': 0}, 'Beschreibung': 'Kommode am Whiteboard mit Telefon.'},
            'Regal': {'Position': {'x': 144, 'y': 451, 'z': 0}, 'Beschreibung': 'Regal mit Ordnern.'},
            'Fenster_1': {'Position': {'x': 701, 'y': 62, 'z': 0}, 'Beschreibung': ''},
            'Fenster_2': {'Position': {'x': 701, 'y': 192, 'z': 0}, 'Beschreibung': ''},
            'Fenster_3': {'Position': {'x': 701, 'y': 329, 'z': 0}, 'Beschreibung': ''},
            'Fenster_4': {'Position': {'x': 701, 'y': 467, 'z': 0}, 'Beschreibung': ''},
            'Fenster_5': {'Position': {'x': 701, 'y': 604, 'z': 0}, 'Beschreibung': ''},
            'Roboter_Pepper': {'Position': {'x': 270, 'y': 40, 'z': 0}, 'Beschreibung': 'Roboter namens Pepper. Dieser wird NICHT gesteuert im Gegensatz zum Turtlebot.'},
            'Karton_1': {'Position': {'x': 577, 'y': 285, 'z': 0}, 'Beschreibung': 'geöffneter Karton.'},
            'Karton_2': {'Position': {'x': 171, 'y': 218, 'z': 0}, 'Beschreibung': 'geöffneter Karton.'},
            'Karton_3': {'Position': {'x': 126, 'y': 218, 'z': 0}, 'Beschreibung': 'geöffneter Karton.'},
            'Tür_1': {'Position': {'x': -29, 'y': 324, 'z': 0}, 'Beschreibung': 'Haupteingang zum Flur.'},
            'Tür_2': {'Position': {'x': 52, 'y': 472, 'z': 0}, 'Beschreibung': 'Tür zum Serverraum.'},
            'Tür_3': {'Position': {'x': 249, 'y': 472, 'z': 0}, 'Beschreibung': 'Tür zum Serverraum.'},
            'Whiteboard_1': {'Position': {'x': 120, 'y': 3, 'z': 0}, 'Beschreibung': 'kleines Whiteboard.'},
            'Whiteboard_2': {'Position': {'x': 430, 'y': 3, 'z': 0}, 'Beschreibung': 'großes Whiteboard.'},
            'Mülleimer': {'Position': {'x': 15, 'y': 225, 'z': 0}, 'Beschreibung': ''},
        }
        base_map_dir = map_dir
        self.example_image_sequences = [
            {"prompt": "Fahre zum Ausgang.", "expected": {"Aktion": "Navigieren", "Parameter": {"Zielposition": {"x": 30, "y": 324, "z": 0}, "Zielorientierung": 180}, "Einheit": "Zentimeter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt1.png')},
            {"prompt": "Du musst hinter den Tisch.", "expected": {"Aktion": "Navigieren", "Parameter": {"Zielposition": {"x": 470, "y": 560, "z": 0}, "Zielorientierung": 300}, "Einheit": "Zentimeter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt2.png')},
            {"prompt": "Bieg' rechts ab.", "expected": {"Aktion": "Navigieren", "Parameter": {"Zielposition": {"x": 480, "y": 32, "z": 0}, "Zielorientierung": 0}, "Einheit": "Zentimeter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt3.png')},
            {"prompt": "Kannst du bitte zum nächsten Pc kommen?", "expected": {"Aktion": "Navigieren", "Parameter": {"Zielposition": {"x": 420, "y": 540, "z": 0}, "Zielorientierung": 330}, "Einheit": "Zentimeter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt4.png')},
            {"prompt": "Beweg dich auf die andere Seite des Raumes und schau zu Pepper.", "expected": {"Aktion": "Navigieren", "Parameter": {"Zielposition": {"x": 390, "y": 90, "z": 0}, "Zielorientierung": 200}, "Einheit": "Zentimeter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt5.png')},
            {"prompt": "Fahr links am Stuhl vorbei.", "expected": {"Aktion": "Navigieren", "Parameter": {"Zielposition": {"x": 340, "y": 420, "z": 0}, "Zielorientierung": 180}, "Einheit": "Zentimeter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt6.png')},
            {"prompt": "Dreh dich um 60 Grad nach rechts und mach einen Salto.", "expected": {"Aktion": "Drehen", "Parameter": {"Winkelgeschwindigkeit": 30, "Winkel": 60, "im_Uhrzeigersinn": True}, "Einheit": "Grad"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt7.png')},
            {"prompt": "Fahre langsam ein Stück zurück", "expected": {"Aktion": "Geradeausfahren", "Parameter": {"Lineargeschwindigkeit": 0.1, "Distanz": 0.3, "soll_Vorwärts": False}, "Einheit": "Meter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt8.png')},
            {"prompt": "Fahre hinter den Tisch", "expected": {"Aktion": "Navigieren", "Parameter": {"Zielposition": {"x": 480, "y": 33, "z": 0}, "Zielorientierung": 90}, "Einheit": "Zentimeter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt9.png')},
            {"prompt": "Fahr nach links.", "expected": {"Aktion": "Navigieren", "Parameter": {"Zielposition": {"x": 355, "y": 175, "z": 0}, "Zielorientierung": 245}, "Einheit": "Zentimeter"}, "image": os.path.join(base_map_dir, 'Raumplan_Prompt10.png')},
        ]
        # Beispiel-Posen (x, y, Orientierung) passend zu den 8 Beispielbildern
        self.example_poses = [
            {"x": 630, "y": 40, "orientierung": 180},
            {"x": 500, "y": 400, "orientierung": 110},
            {"x": 330, "y": 150, "orientierung": 270},
            {"x": 240, "y": 420, "orientierung": 210},
            {"x": 600, "y": 570, "orientierung": 180},
            {"x": 340,  "y": 420, "orientierung": 180},
            {"x": 510, "y": 390, "orientierung": 210},
            {"x": 390, "y": 570, "orientierung": 90},
            {"x": 480, "y": 240, "orientierung": 270},
            {"x": 470, "y": 290, "orientierung": 260},
        ]
        # Aktuelle Pixelpose
        self.current_pose_pixel = None
        self.system_instructions = (
            """
            Berücksichtige die folgende Ontologie:
            {{"Aktion": "Drehen", "Parameter": {{"Winkelgeschwindigkeit": Winkelgeschwindigkeit, "Winkel": Winkel, "im_Uhrzeigersinn": im_Uhrzeigersinn}}, "Einheit": "Grad"}}
            {{"Aktion": "Geradeausfahren", "Parameter": {{"Lineargeschwindigkeit": Lineargeschwindigkeit, "Distanz": Distanz, "soll_Vorwärts": soll_Vorwärts}}, "Einheit": "Meter"}}
            {{"Aktion": "Navigieren", "Parameter": {{"Zielposition": {{"x": x, "y": y, "z": 0}, "Zielorientierung": Zielorientierung}}, "Einheit": "Zentimeter"}}
            Du bekommst nun einen Prompt in menschlicher Sprache und du musst eine zur JSON-Ontologie JSON-konforme Antwort zurückgeben. Jede Aktion, die nicht in der Ontologie ist, soll ignoriert werden. 
            Die Lineargeschwindigkeit soll vom Wert her zwischen 0.1 und 0.35 liegen und vom Typ float sein. Die Winkelgeschwindigkeit soll vom Wert her zwischen 4 und 105 liegen und vom Typ int sein. Die Distanz soll vom Typ float sein. Der Winkel und die Zielorientierung sollen vom Typ int sein und zwischen 0 und 360 liegen. Die Werte von x, y und z der Zielposition sollen vom Typ int sein. x und y sollen einen Sicherheitsabstand von 18 zu umliegenden Objekten einhalten und dürfen nur auf dem befahrbaren Boden liegen (schaue hierzu auf das Bild zum Raumplan).

            Wichtige Regeln für die Interpretation:
            - Übernimm immer die Perspektive des Turtlebot-Roboters. Das Bild zeigt den Raumplan mit der aktuellen Position des Roboters (markiert mit dem Roboter-Sprite) und seinem Sichtfeld (FOV) als blauen Kegel. Der Kegel zeigt, was "vor dem Roboter" liegt – interpretiere relative Begriffe wie "vor dir", "hinter den Tisch vor dir", "rechts ab" oder "die andere Seite" basierend darauf:
            - "Vor dir": Objekte oder Bereiche innerhalb oder nahe am FOV-Kegel.
            - "Hinter etwas": Die Rückseite eines Objekts aus Robotersicht (z.B. hinter einem Tisch bedeutet eine Position auf der gegenüberliegenden Seite des Tisches, relativ zur aktuellen Blickrichtung).
            - "Rechts/links": Relativ zur aktuellen Orientierung (Bildkonvention: 0° rechts, 90° unten, 180° links, 270° oben).
            - Verwende das Raumlayout (JSON mit Positionen und Beschreibungen) zusammen mit dem Bild, um Objekte zu identifizieren. Wähle das passendste Objekt basierend auf Nähe, Sichtbarkeit im FOV und Prompt-Beschreibung (z.B. "der Tisch vor dir" = der Tisch im FOV).
            - Die Positionsangaben (x, y, z) im Raumlayout beziehen sich auf die Mittelpunkte der Objekte und sind in Zentimetern relativ zum Koordinatensystem des Bildes angegeben.
            - Für Navigieren-Befehle: Berechne eine Zielposition in Zentimetern (Raster-Einheiten), die sicher erreichbar ist. Die Zielorientierung sollte so gewählt werden, dass der Roboter am Ziel auf das intendierte Objekt oder in die gewünschte Richtung schaut.
            - Die Beispiele dienen nur zum Lernen des Formats und der Ontologie und der Semantik. Für den finalen Prompt (nach den Beispielen) verwende AUSSCHLIESSLICH das zuletzt bereitgestellte Bild mit der aktuellen Roboterpose – kopiere KEINE Werte aus den Beispielen, sondern denke neu (verwende deine Reasoning-Fähigkeiten) basierend auf dem NEUEN Kontext.
            - Gib nur das JSON-Objekt aus, ohne zusätzlichen Text, Erklärungen oder Markdown.

            Du erhälst nun ein paar Beispiele mit Bildern des Raumplans, inklusive Roboterpose des Turtlebots, zugehörigen Beispielprompts und den erwarteten Ausgaben.
            """
        )
    
    # ---------- Logging helpers ----------
    def _redact_messages_for_log(self, messages):
        """Return a copy of messages suitable for logging.
        - Redact base64 image URLs unless self.log_prompt_images is True.
        - Trim very long strings for readability.
        """
        def trim_text(s: str, max_len: int = 4000):
            if not isinstance(s, str):
                return s
            return s if len(s) <= max_len else (s[:max_len] + f"... <trimmed {len(s)-max_len} chars>")

        redacted = []
        for m in messages:
            mc = {k: v for k, v in m.items()}
            content = mc.get('content')
            if isinstance(content, list):
                new_content = []
                for part in content:
                    p = dict(part)
                    if p.get('type') == 'image_url' and isinstance(p.get('image_url'), dict):
                        url = p['image_url'].get('url')
                        if isinstance(url, str) and url.startswith('data:image/'):
                            if self.log_prompt_images:
                                # Keep but trim to avoid terminal overflow
                                p['image_url']['url'] = trim_text(url, 1000)
                            else:
                                p['image_url']['url'] = f"<image data url redacted; length={len(url)}>"
                    elif p.get('type') in ('input_text', 'text') and isinstance(p.get('text'), str):
                        p['text'] = trim_text(p['text'])
                    new_content.append(p)
                mc['content'] = new_content
            elif isinstance(content, str):
                mc['content'] = trim_text(content)
            redacted.append(mc)
        return redacted
    # ---------- Helpers ----------
    def _encode_image_to_data_url(self, path: str) -> str:
        try:
            with open(path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            ext = os.path.splitext(path)[1].lower().replace('.', '') or 'png'
            if ext not in ('png', 'jpg', 'jpeg', 'webp'):
                ext = 'png'
            return f'data:image/{ext};base64,{b64}'
        except Exception as e:
            self.get_logger().warn(f'Bild konnte nicht geladen werden ({path}): {e}')
            return ''
    # Verbleibende lokale Helper (Bild-Encoding / Bild-Erzeugung); Winkel & Umrechnung in tfm
    def _quaternion_to_yaw_deg(self, q):  # optional: delegieren an tfm.quaternion_to_yaw_deg
        return tfm.quaternion_to_yaw_deg(q)

    def _extract_first_json(self, text: str) -> str:
        """Extrahiert das erste balancierte JSON-Objekt aus beliebigem Model-Output.

        Entfernt initiale Markdown-Codefences und durchsucht dann per Klammerzählung.
        Wirft ValueError falls kein gültiges Objekt gefunden.
        """
        if not text:
            raise ValueError("Leerer Text")
        t = text.strip()
        # Code fences entfernen (am Anfang / am Ende)
        if t.startswith('```'):
            # entferne ersten Fence inkl. evtl. Sprache
            t = re.sub(r'^```[a-zA-Z0-9]*\s*', '', t)
            # entferne letzten fence (falls vorhanden)
            t = re.sub(r'```\s*$', '', t).strip()
        start = t.find('{')
        if start == -1:
            raise ValueError("Keine öffnende '{' gefunden")
        depth = 0
        in_string = False
        escape = False
        for i, ch in enumerate(t[start:], start=start):
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            else:
                if ch == '"':
                    in_string = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return t[start:i+1]
        raise ValueError("Unvollständiges JSON-Objekt")

    def _generate_pose_image(self, u: float, v: float, orientation_insert_deg: float, x_cm: float = None, y_cm: float = None):
        """Erzeugt Bild mit Roboter + FOV wie in insert_robot.py.

        orientation_insert_deg: 0° rechts, 90° unten (Bildkonvention)
        x_cm, y_cm: Raster-Koordinaten zur Metadaten-Speicherung
        """
        try:
            base = Image.open(self.base_map_path).convert('RGBA')
            robot = Image.open(self.robot_sprite_path).convert('RGBA')
        except Exception as e:
            self.get_logger().error(f'Bildladen fehlgeschlagen: {e}')
            return

        # FOV Parameter (analog insert_robot)
        FOV_DEGREES = 90
        FOV_RANGE_UNITS = 200.0  # cm (Raster-Einheiten)
        FOV_COLOR = (100, 180, 255, 80)
        if FOV_DEGREES > 0 and FOV_RANGE_UNITS > 0:
            try:
                range_px_x = FOV_RANGE_UNITS / tfm.SCALE_X_UNITS_PER_PIXEL
                range_px_y = FOV_RANGE_UNITS / tfm.SCALE_Y_UNITS_PER_PIXEL
                half_angle = FOV_DEGREES / 2.0
                start_angle = orientation_insert_deg - half_angle
                step = max(2, int(FOV_DEGREES / 15))
                angles = [start_angle + i * (FOV_DEGREES / step) for i in range(step + 1)]
                import math
                points = [(u, v)]
                for a in angles:
                    rad = math.radians(a)
                    xpt = u + math.cos(rad) * range_px_x
                    ypt = v + math.sin(rad) * range_px_y
                    points.append((xpt, ypt))
                overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(overlay)
                draw.polygon(points, fill=FOV_COLOR)
                base.alpha_composite(overlay)
            except Exception as fe:
                self.get_logger().warn(f'FOV Zeichnung fehlgeschlagen: {fe}')

        # Sprite drehen (wie insert_robot: Original schaut nach unten -> 0° rechts => cw = -90 Offset)
        cw_degrees = orientation_insert_deg - 90.0
        if cw_degrees % 360:
            robot = robot.rotate(-cw_degrees, resample=Image.BICUBIC, expand=True)
        rw, rh = robot.size
        base.paste(robot, (int(round(u - rw/2)), int(round(v - rh/2))), mask=robot)
        try:
            base.save(self.dynamic_pose_image_path)
            self.current_pose_image_path = self.dynamic_pose_image_path
            self.current_pose_image_timestamp = self.get_clock().now().nanoseconds / 1e9
            meta = {"x": int(round(u)), "y": int(round(v)), "orientierung": orientation_insert_deg % 360.0}
            if x_cm is not None and y_cm is not None:
                meta['raster_x_cm'] = round(x_cm, 2)
                meta['raster_y_cm'] = round(y_cm, 2)
            self.current_pose_pixel = meta
        except Exception as e:
            self.get_logger().error(f'Speichern Pose-Bild fehlgeschlagen: {e}')

    def _generate_target_image_from_raster(self, x_cm: float, y_cm: float, orientation_img_deg: float):
        """Erzeugt Raumplan_Zielposition.png an Rasterkoordinaten (cm) mit Bildwinkel (0° rechts, 90° unten)."""
        try:
            u, v = tfm.raster_cm_to_pixel(x_cm, y_cm)
            base = Image.open(self.base_map_path).convert('RGBA')
            robot = Image.open(self.robot_sprite_path).convert('RGBA')
            cw_degrees = orientation_img_deg - 90.0
            if cw_degrees % 360:
                robot = robot.rotate(-cw_degrees, resample=Image.BICUBIC, expand=True)
            rw, rh = robot.size
            base.paste(robot, (int(round(u - rw/2)), int(round(v - rh/2))), mask=robot)
            base.save(self.target_pose_image_path)
            self.get_logger().info(f'Zielbild gespeichert: {self.target_pose_image_path} (u={u:.1f}, v={v:.1f}, ori={orientation_img_deg:.1f}°)')
        except Exception as e:
            self.get_logger().error(f'Erzeugung Zielbild fehlgeschlagen: {e}')

    # ---------- Callbacks ----------
    def pose_callback(self, msg: PoseWithCovarianceStamped):
        self.current_pose = {'x': msg.pose.pose.position.x, 'y': msg.pose.pose.position.y, 'z': msg.pose.pose.position.z}
        self.last_amcl_pose = msg

    def audio_pose_callback(self, msg: PoseStamped):
        # Keine automatische Bildgenerierung mehr; nur Zustand speichern
        self.current_audio_pose = msg

    # ---------- Deferred transcription handling ----------
    def _ensure_pose_image(self) -> bool:
        # Passiv: wir erzeugen kein Bild mehr selbst; nutzen nur vorhandenes, wenn frisch genug
        now = self.get_clock().now().nanoseconds / 1e9
        ts = self.current_pose_image_timestamp
        if self.current_pose_image_path and ts and now - ts <= self.image_max_age_sec:
            return True
        # Falls extern (chat.py) das Bild erzeugt hat, prüfen wir einfach, ob die Datei existiert
        try:
            if os.path.exists(self.dynamic_pose_image_path):
                self.current_pose_image_path = self.dynamic_pose_image_path
                self.current_pose_image_timestamp = now
                return True
        except Exception:
            pass
        return False

    def _retry_pending(self):
        if not self.pending_transcription:
            return
        now = self.get_clock().now().nanoseconds / 1e9
        if self._ensure_pose_image() or (self.wait_deadline and now >= self.wait_deadline):
            text = self.pending_transcription
            self.pending_transcription = None
            self.wait_deadline = None
            self._process_transcription(text)

    def text_callback(self, msg: String):
        text = msg.data.strip()
        if any(bad in text.lower() for bad in ('untertitel','copyright','amara.org')):
            return
        if self.pending_transcription:
            self.pending_transcription = text
            return
        if not self._ensure_pose_image():
            self.pending_transcription = text
            self.wait_deadline = (self.get_clock().now().nanoseconds / 1e9) + self.max_wait_for_image_sec
            return
        self._process_transcription(text)

    # ---------- Core processing ----------
    def _process_transcription(self, transcribed_text: str):
        room_layout_json = json.dumps(self.room_layout, ensure_ascii=False)
        # Ensure the room layout appears before the examples announcement inside the system prompt
        _sys = self.system_instructions
        _anchor = "Du erhälst nun"
        _idx = _sys.find(_anchor)
        if _idx == -1:
            _anchor_alt = "Du erhältst nun"
            _idx = _sys.find(_anchor_alt)
        if _idx != -1:
            _sys_with_layout = _sys[:_idx] + f"\nRaumlayout: {room_layout_json}\n" + _sys[_idx:]
        else:
            _sys_with_layout = _sys + f"\nRaumlayout: {room_layout_json}"
        messages = [{"role": "system", "content": _sys_with_layout}]
        for idx, ex in enumerate(self.example_image_sequences):
            data_url = self._encode_image_to_data_url(ex['image']) if self.include_images else ''
            user_content = []
            if data_url:
                user_content.append({"type": "image_url", "image_url": {"url": data_url}})
            user_content.append({"type": "input_text", "text": ex['prompt']})
            if idx < len(self.example_poses):
                pose_meta = self.example_poses[idx]
                user_content.append({"type": "input_text", "text": f"Beispiel-Roboterpose des Turtlebots: x={pose_meta['x']}, y={pose_meta['y']}, Orientierung={pose_meta['orientierung']}"})
            messages.append({"role": "user", "content": user_content})
            messages.append({"role": "assistant", "content": json.dumps(ex['expected'], ensure_ascii=False)})
        # Combine current image, pose description, and the transcribed prompt into a single user message
        user_content = []
        if self.current_pose_image_path and self.include_images:
            data_url = self._encode_image_to_data_url(self.current_pose_image_path)
            if data_url:
                user_content.append({"type": "image_url", "image_url": {"url": data_url}})
            pose_text = 'Aktuelle Pose des Turtlebots, der gesteuert werden soll.'
            if self.current_audio_pose:
                p = self.current_audio_pose.pose.position
                yaw = tfm.quaternion_to_yaw_deg(self.current_audio_pose.pose.orientation)
                pose_text += f' MeterPose: x={p.x:.2f}, y={p.y:.2f}, yaw={yaw:.1f}°'
            if self.current_pose_pixel:
                # Zusätzlich Raster-Koordinaten zurückrechnen (Pixel -> cm) zur Transparenz
                x_cm, y_cm = tfm.pixel_to_raster_cm(self.current_pose_pixel['x'], self.current_pose_pixel['y'])
                pose_text += (f" PixelPose: x={self.current_pose_pixel['x']}, y={self.current_pose_pixel['y']}, Orientierung={self.current_pose_pixel['orientierung']:.1f}" \
                               f" RasterPose_cm: x={x_cm:.1f}, y={y_cm:.1f}")
            # Insert pose context (after image if present)
            if self.current_pose_image_path:
                user_content.append({"type": "input_text", "text": pose_text})
        # Finally, add the actual transcribed prompt
        user_content.append({"type": "input_text", "text": transcribed_text})
        messages.append({"role": "user", "content": user_content})
        try:
            # OpenAI path
            openai.api_key = self.api_key
            try:
                if self.log_prompt:
                    red = self._redact_messages_for_log(messages)
                    self.get_logger().info("OpenAI Request messages:" + "\n" + json.dumps(red, ensure_ascii=False, indent=2))
                resp = openai.chat.completions.create(model=self.model_name, messages=messages)     #, temperature=0.0
                content = resp.choices[0].message.content.strip()
            except Exception:
                linear = self.system_instructions + '\nBeispiele:\n' + '\n'.join(
                    [f"Prompt: {ex['prompt']} -> {json.dumps(ex['expected'], ensure_ascii=False)}" for ex in self.example_image_sequences]
                ) + f"\nAktueller Prompt: {transcribed_text}"
                if self.log_prompt:
                    self.get_logger().info("OpenAI Request (linear fallback):\n" + linear)
                resp = openai.chat.completions.create(model=self.model_name, messages=[{"role":"system","content": self.system_instructions},{"role":"user","content": linear}])    #, temperature=0.3
                content = resp.choices[0].message.content.strip()
            # Vollständige Modell-Antwort loggen
            self.get_logger().info(f"LLM komplette Antwort: {content}")
            try:
                json_str = self._extract_first_json(content)
                self.get_logger().info(f"Rohes extrahiertes JSON: {json_str}")
                data = json.loads(json_str)
            except Exception as parse_err:
                self.get_logger().error(f'Ungueltiges JSON (Extraktion fehlgeschlagen): {parse_err}; Output: {content}')
                return
            try:
                data = tfm.transform_navigation_goal_json(data)
            except Exception as t_err:
                self.get_logger().warn(f'Transformationsfehler: {t_err}')
            transformed_json = json.dumps(data, ensure_ascii=False)
            self.get_logger().info(f"Publiziere Aktion JSON: {transformed_json}")
            self.publisher.publish(String(data=transformed_json))
            # Zusätzlich: Original JSON (Raster/cm) an chat.py weitergeben
            try:
                original = json.loads(json_str)
                if isinstance(original, dict):
                    self.publisher_raster.publish(String(data=json.dumps(original, ensure_ascii=False)))
                    self.get_logger().info('Raster-JSON an /action_command_raster publiziert.')
            except Exception as ie:
                self.get_logger().warn(f'Raster-JSON Publish übersprungen: {ie}')
        except Exception as e:
            self.get_logger().error(f'LLM Fehler: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = TextProcessorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
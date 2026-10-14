"""
Chat View - GUI Interface für den Turtlebot Simulator im MVC Pattern.
Implementiert eine moderne GUI mit Bildanzeige und Chat-Interface.
"""
import tkinter as tk
import threading
import time
import os
import json
from tkinter import ttk, scrolledtext, messagebox
from PIL import Image, ImageTk
from pathlib import Path
from .insert_robot import update_robot_position
from .participant_dialog import get_participant_data

def is_position_navigable(x, y):
    """
    Prüft, ob eine Position (x, y) in einem der befahrbaren Bereiche liegt.
    """
    try:
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
            return True  # Fallback if JSON can't be loaded
        
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

class ChatView:
    """View-Klasse für die GUI des Turtlebot Simulators."""
    
    def __init__(self, chat_node, model):
        self.chat_node = chat_node
        self.model = model
        self.root = tk.Tk()
        self.root.title("Turtlebot Simulator - Chat Interface")
        # Fenstergröße je nach Modus anpassen
        if chat_node.mode == 'stu':
            self.root.geometry("1600x1000")  # Noch größer für Studienmodus
            # Fenster zentrieren
            self.root.update_idletasks()
            width = self.root.winfo_reqwidth()
            height = self.root.winfo_reqheight()
            pos_x = (self.root.winfo_screenwidth() // 2) - (width // 2)
            pos_y = (self.root.winfo_screenheight() // 2) - (height // 2)
            self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        else:
            self.root.geometry("1200x800")  # Standard für Simulationsmodus
        self.root.configure(bg='#f0f0f0')
        
        # Studienmodus-spezifische Attribute
        self.is_study_mode = (chat_node.mode == 'stu')
        
        # GUI-Zustand
        self.initial_image_path = os.path.expanduser("~/ros2_ws/src/map/Raumplan.png")  # Verwende Raumplan.png initial
        self.image_path = os.path.expanduser("~/ros2_ws/src/map/currentPosition.png")
        self.using_current_position = False  # Flag to track which image to use
        self.current_image = None
        self.last_modified = 0
        self.waiting_for_initial_pose = True
        self.waiting_for_participant_data = self.is_study_mode  # Neues Flag für Studienmodus
        self.last_known_pose = None
        
        # Setup GUI
        self.setup_gui()
        
        # Initiales Bild laden (vor Pose-Eingabe)
        self.update_image()
        
        if self.is_study_mode:
            # Studienmodus: Zeige zuerst Raumplan.png, dann Teilnehmer-Dialog
            self.show_initial_study_interface()
        else:
            # Normale Simulation: Initiale Pose-Eingabe
            self.request_initial_pose()
        
        # Callback für Aktionsantworten registrieren und Monitoring starten
        # Starte Monitoring erst NACH dem Dialog
        self.setup_action_monitoring()
        self.setup_image_monitoring()
        
    def setup_gui(self):
        """Erstellt die GUI-Elemente."""
        # Hauptcontainer
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Linke Seite - Bild und Pose-Info
        left_frame = ttk.LabelFrame(main_frame, text="Turtlebot Status", padding="10")
        left_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        # Pose-Anzeige (nur im Simulationsmodus)
        if not self.is_study_mode:
            self.pose_label = ttk.Label(left_frame, text="Position: - | Orientierung: -", 
                                       font=('Arial', 12, 'bold'), foreground='#2c3e50')
            self.pose_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
            image_row = 1
        else:
            image_row = 0
        
        # Bild-Container
        image_frame = ttk.Frame(left_frame)
        image_frame.grid(row=image_row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
        
        # Bild-Label
        self.image_label = ttk.Label(image_frame, text="Lade Bild...", anchor='center')
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Rechte Seite - Chat Interface
        right_frame = ttk.LabelFrame(main_frame, text="Chat Interface", padding="10")
        right_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        # Studienmodus: Extra Info-Panel
        if self.is_study_mode:
            study_info_frame = ttk.LabelFrame(right_frame, text="Studien-Information", padding="5")
            study_info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
            study_info_frame.columnconfigure(0, weight=1)
            
            self.round_label = ttk.Label(study_info_frame, text="Runde: - / 2", 
                                        font=('Arial', 12, 'bold'), foreground='#e74c3c')
            self.round_label.grid(row=0, column=0, sticky=tk.W)
            
            chat_row = 1
        else:
            chat_row = 0
        
        # Chat-Display
        self.chat_display = scrolledtext.ScrolledText(
            right_frame, 
            wrap=tk.WORD, 
            width=50, 
            height=30 if not self.is_study_mode else 25,
            font=('Arial', 10),
            bg='#ffffff',
            fg='#2c3e50'
        )
        self.chat_display.grid(row=chat_row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.chat_display.config(state=tk.DISABLED)
        
        # Eingabe-Frame
        input_frame = ttk.Frame(right_frame)
        input_frame.grid(row=chat_row+1, column=0, sticky=(tk.W, tk.E))
        input_frame.columnconfigure(0, weight=1)
        
        # Text-Eingabe
        self.text_entry = ttk.Entry(
            input_frame, 
            font=('Arial', 12),
            width=40
        )
        self.text_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.text_entry.bind('<Return>', self.on_send_message)
        
        # Im Studienmodus initial deaktivieren bis Teilnehmer-Daten eingegeben
        if self.is_study_mode:
            self.text_entry.config(state='disabled')
        
        # Send-Button
        self.send_button = ttk.Button(
            input_frame, 
            text="Senden",
            command=self.on_send_message,
            style='Accent.TButton'
        )
        self.send_button.grid(row=0, column=1)
        
        # Im Studienmodus initial deaktivieren bis Teilnehmer-Daten eingegeben
        if self.is_study_mode:
            self.send_button.config(state='disabled')
        
        # Status-Label
        self.status_label = ttk.Label(right_frame, text="Bereit für Eingabe...", 
                                     foreground='#27ae60', font=('Arial', 9))
        self.status_label.grid(row=chat_row+2, column=0, sticky=tk.W, pady=(5, 0))
        
        # Style konfigurieren
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
        
    def setup_image_monitoring(self):
        """Startet die Bildüberwachung in einem separaten Thread."""
        self.monitor_thread = threading.Thread(target=self.monitor_image, daemon=True)
        self.monitor_thread.start()
        
    def setup_action_monitoring(self):
        """Startet die Überwachung von Aktionsantworten."""
        self.action_monitor_thread = threading.Thread(target=self.monitor_actions, daemon=True)
        self.action_monitor_thread.start()
        
    def monitor_actions(self):
        """Überwacht Änderungen in der Model-Position für Aktionsantworten."""
        while True:
            try:
                if self.model.is_initialized() and not self.waiting_for_initial_pose:
                    current_pose = self.model.get_current_pose()
                    
                    # Prüfe auf Änderungen
                    if self.last_known_pose is None:
                        self.last_known_pose = current_pose
                    elif current_pose != self.last_known_pose:
                        # Position hat sich geändert - zeige Aktionsantwort
                        x, y, alpha = current_pose
                        
                        # Aktionsantwort je nach Modus anzeigen
                        if self.is_study_mode:
                            action_text = "✅ Aktion ausgeführt"
                        else:
                            action_text = f"✅ Aktion ausgeführt - Position: ({x}, {y}) cm, Orientierung: {alpha}°"
                            
                        try:
                            # Roboterbild aktualisieren
                            self.update_robot_image(x, y, alpha)
                            self.root.after(0, lambda: self.add_chat_message("System", action_text, "#27ae60"))
                            self.root.after(0, lambda: self.status_label.config(text="Bereit für Eingabe...", foreground='#27ae60'))
                        except tk.TclError:
                            # GUI wurde bereits geschlossen
                            break
                        self.last_known_pose = current_pose
                        
                        # Studienmodus: Prüfe ob Ziel erreicht wurde (MVC-konform)
                        if self.is_study_mode and not self.model.target_reached:
                            if self.model.check_target_reached():
                                target_msg = f"Ziel erreicht!"
                                try:
                                    self.root.after(0, lambda: self.add_chat_message("System", target_msg, "#e74c3c"))
                                    self.root.after(1000, self.handle_target_reached)  # 1 Sekunde warten, dann Countdown starten
                                except tk.TclError:
                                    break
                        
            except Exception as e:
                print(f"Fehler beim Überwachen der Aktionen: {e}")
                
            time.sleep(0.5)
        
    def monitor_image(self):
        """Überwacht die Bilddatei auf Änderungen und aktualisiert die Anzeige."""
        while True:
            try:
                if os.path.exists(self.image_path):
                    current_modified = os.path.getmtime(self.image_path)
                    if current_modified != self.last_modified:
                        self.last_modified = current_modified
                        # Thread-sichere GUI-Aktualisierung
                        try:
                            self.root.after(0, self.update_image)
                        except tk.TclError:
                            # GUI wurde bereits geschlossen
                            break
                        
                # Pose-Info aktualisieren (nur im Simulationsmodus)
                if self.model.is_initialized() and not self.is_study_mode:
                    x, y, alpha = self.model.get_current_pose()
                    pose_text = f"Position: ({x}, {y}) cm | Orientierung: {alpha}°"
                    try:
                        self.root.after(0, lambda: self.pose_label.config(text=pose_text))
                    except tk.TclError:
                        # GUI wurde bereits geschlossen
                        break
                    
            except Exception as e:
                print(f"Fehler beim Überwachen des Bildes: {e}")
                
            time.sleep(0.5)  # Check alle 500ms
            
    def update_image(self):
        """Aktualisiert das angezeigte Bild."""
        try:
            # Bestimme welches Bild verwendet werden soll
            if self.is_study_mode:
                if self.waiting_for_participant_data:
                    # Studienmodus: Vor Teilnehmer-Dialog -> Raumplan.png
                    current_image_path = self.initial_image_path
                else:
                    # Studienmodus: Nach Teilnehmer-Dialog -> currentPosition.png
                    current_image_path = self.image_path
            else:
                # Normaler Modus: Entscheidung basierend auf using_current_position
                current_image_path = self.image_path if self.using_current_position else self.initial_image_path
            
            if os.path.exists(current_image_path):
                # Lade und skaliere das Bild
                pil_image = Image.open(current_image_path)
                
                # Berechne neue Größe (größer für Studienmodus, Seitenverhältnis beibehalten)
                if self.is_study_mode:
                    max_width, max_height = 1000, 800  # Noch größer für Studienmodus
                else:
                    max_width, max_height = 800, 600  # Standard für Simulationsmodus
                ratio = min(max_width/pil_image.width, max_height/pil_image.height)
                new_width = int(pil_image.width * ratio)
                new_height = int(pil_image.height * ratio)
                
                # Verwende kompatible Resampling-Methode
                try:
                    # Neuere PIL-Versionen
                    pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                except AttributeError:
                    # Ältere PIL-Versionen
                    pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                
                # Konvertiere zu PhotoImage und halte Referenz
                self.current_image = ImageTk.PhotoImage(pil_image)
                self.image_label.config(image=self.current_image, text="")
                
                # Debug-Info für Studienmodus
                if self.is_study_mode:
                    if self.waiting_for_participant_data:
                        image_name = "Raumplan.png (vor Dialog)"
                    else:
                        image_name = "currentPosition.png (nach Dialog)"
                    print(f"Bild aktualisiert: {image_name} ({new_width}x{new_height})")
                
            else:
                self.image_label.config(text="Kein Bild verfügbar", image="")
                print(f"Bild nicht gefunden: {current_image_path}")
                
        except Exception as e:
            print(f"Fehler beim Laden des Bildes: {e}")
            self.image_label.config(text=f"Fehler beim Laden: {e}", image="")
            
    def update_robot_image(self, x, y, alpha):
        """Aktualisiert das Roboterbild mit neuen Koordinaten."""
        try:
            # Roboterposition im Bild aktualisieren
            target_area = self.model.current_target if self.is_study_mode else None
            success = update_robot_position(x, y, alpha, target_area)
            if success:
                # Im Studienmodus: Nur wechseln wenn Teilnehmer-Daten bereits eingegeben
                # Im normalen Modus: Wie bisher
                if not self.is_study_mode:
                    self.using_current_position = True
                # Thread-sichere GUI-Aktualisierung nach kurzer Wartezeit
                self.root.after(200, self.update_image)  # 200ms warten, damit Bild geschrieben wird
            else:
                print("Fehler beim Aktualisieren des Roboterbildes")
        except Exception as e:
            print(f"Fehler beim Aktualisieren des Roboterbildes: {e}")
            
    def start_study_mode(self):
        """Startet den Studienmodus nach erfolgreicher Teilnehmer-Eingabe."""
        self.waiting_for_initial_pose = False
        self.using_current_position = True
        
        # Erste Runde starten
        if self.chat_node.start_new_round():
            self.update_study_info()
            self.add_chat_message("System", f"Studienmodus gestartet - Runde {self.model.current_round} von {self.model.max_rounds}", "#3498db")
            self.add_chat_message("System", "Beginnen Sie mit der Navigation zum Zielbereich.", "#27ae60")
            self.add_chat_message("System", "Gib deinen Befehl, um den Turtlebot ins Ziel zu steuern. Oder hast du eine Frage?", "#7f8c8d")
            
            # Reset des Bildüberwachungsflags für neue Runde
            self.last_modified = 0
            
            # Roboterbild mit Zielbereich aktualisieren
            x, y, alpha = self.model.get_current_pose()
            self.update_robot_image(x, y, alpha)
            
            # Focus auf Eingabefeld
            self.text_entry.config(state='normal')  # Eingabe aktivieren
            self.send_button.config(state='normal')  # Button aktivieren
            self.text_entry.focus_set()
            # Setze initial bekannte Pose
            self.last_known_pose = (x, y, alpha)
        
    def update_study_info(self):
        """Aktualisiert die Studien-Informationen im GUI."""
        if self.is_study_mode:
            self.round_label.config(text=f"Runde: {self.model.current_round} / {self.model.max_rounds}")
            
    def handle_target_reached(self):
        """Behandelt das Erreichen eines Ziels im Studienmodus."""
        if self.model.current_round >= self.model.max_rounds:
            self.add_chat_message("System", f"{self.model.current_round}. Ziel erreicht!")
            # Alle Runden abgeschlossen - Post-Study Fragebogen anzeigen
            self.show_post_study_questionnaire()
        else:
            # Ziel erreicht mit Countdown-Info
            self.add_chat_message("System", f"{self.model.current_round}. Ziel erreicht! Neue Runde startet in 5 Sekunden.")
            # Countdown für nächste Runde starten (ohne weitere Nachrichten)
            self.start_round_countdown()
    
    def start_round_countdown(self):
        """Startet den 5-Sekunden-Countdown für die nächste Runde."""
        self.countdown_remaining = 5
        self.countdown_tick()
        
    def countdown_tick(self):
        """Führt einen Countdown-Tick aus (ohne Chat-Nachrichten)."""
        if self.countdown_remaining > 0:
            # Kein Chat-Output mehr, nur still countdown
            self.countdown_remaining -= 1
            # Nächster Tick in 1 Sekunde
            self.root.after(1000, self.countdown_tick)
        else:
            # Countdown beendet - starte nächste Runde
            self.start_next_round()
    
    def start_next_round(self):
        """Startet die nächste Runde nach dem Countdown."""
        if self.chat_node.next_round():
            self.add_chat_message("System", "Neue Runde gestartet!")
            self.update_study_info()
            self.add_chat_message("System", "Navigieren Sie zum neuen Zielbereich.", "#27ae60")
            self.add_chat_message("System", "Gib deinen Befehl, um den Turtlebot ins Ziel zu steuern. Oder hast du eine Frage?", "#7f8c8d")
            
            # Roboterbild mit neuem Zielbereich aktualisieren
            x, y, alpha = self.model.get_current_pose()
            
            # Reset des Bildüberwachungsflags für neue Runde
            self.last_modified = 0
            
            # Roboterbild aktualisieren
            self.update_robot_image(x, y, alpha)
            
            # Wichtig: Neue Pose als bekannte Pose setzen
            self.last_known_pose = (x, y, alpha)
            
    def show_initial_study_interface(self):
        """Zeigt die initiale Studien-Oberfläche mit Raumplan.png und startet dann Teilnehmer-Dialog."""
        # Zeige zuerst das Hauptfenster mit Raumplan.png
        self.add_chat_message("System", "Willkommen zur Roboter-Navigation-Studie!", "#3498db")
        self.add_chat_message("System", "Bitte geben Sie zunächst Ihre Teilnehmerdaten ein.", "#27ae60")
        
        # Kurz warten, damit das Fenster angezeigt wird, dann Dialog öffnen
        self.root.after(500, self.show_participant_dialog)

    def show_participant_dialog(self):
        """Zeigt den Teilnehmer-Dialog im Vordergrund."""
        # Hauptfenster in den Vordergrund bringen
        self.root.lift()
        self.root.focus_force()
        
        # Teilnehmer-Dialog anzeigen
        participant_data = get_participant_data(self.root)
        
        if not participant_data:
            # Benutzer hat abgebrochen
            self.root.quit()
            return
            
        age, gender, tech_background = participant_data
        
        # Studiendaten initialisieren
        if self.chat_node.study_data:
            self.chat_node.study_data.start_new_participant(age, gender, tech_background)
            self.add_chat_message("System", f"Teilnehmer erfasst: {age} Jahre, {gender}, Tech: {tech_background}", "#3498db")
        
        # WICHTIG: Nach Dialog-Schließung - Wechsel zu currentPosition.png
        self.waiting_for_participant_data = False
        self.using_current_position = True  # Aktiviere currentPosition.png
        
        # Bild sofort aktualisieren, um den Wechsel anzuzeigen
        self.update_image()
        
        # Jetzt Studie starten
        self.start_study_mode()
        
    def show_post_study_questionnaire(self):
        """Zeigt den Post-Study Fragebogen nach Abschluss aller Runden."""
        self.add_chat_message("System", "🎉 Alle 2 Runden erfolgreich abgeschlossen!", "#27ae60")
        self.add_chat_message("System", "Bitte beantworten Sie abschließend drei kurze Fragen.", "#3498db")
        
        # Chat-Eingabe deaktivieren
        self.text_entry.config(state='disabled')
        self.send_button.config(state='disabled')
        
        # Post-Study Dialog anzeigen
        dialog = PostStudyQuestionnaireDialog(self.root)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            satisfaction, comprehensibility, usefulness = dialog.result
            
            # Antworten speichern
            if self.chat_node.study_data and self.chat_node.study_data.has_current_participant():
                self.chat_node.study_data.set_post_study_ratings(satisfaction, comprehensibility, usefulness)
                self.chat_node.study_data.finish_participant()
                self.add_chat_message("System", "📊 Studiendaten wurden gespeichert.", "#27ae60")
                
            self.add_chat_message("System", "Vielen Dank für Ihre Teilnahme!", "#27ae60")
            self.add_chat_message("System", "Studienmodus beendet. Sie können das Fenster schließen.", "#3498db")
        else:
            # Benutzer hat abgebrochen - trotzdem speichern
            if self.chat_node.study_data and self.chat_node.study_data.has_current_participant():
                self.chat_node.study_data.finish_participant()
                self.add_chat_message("System", "📊 Studiendaten wurden gespeichert.", "#27ae60")
                
            self.add_chat_message("System", "Studienmodus beendet.", "#3498db")

    def request_initial_pose(self):
        """Fordert die initiale Pose über einen Dialog an."""
        dialog = InitialPoseDialog(self.root)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            x, y, alpha = dialog.result
            # Model initialisieren
            self.model.set_initial_pose(x, y, alpha)
            # Roboterbild mit initialer Position aktualisieren
            self.update_robot_image(x, y, alpha)
            # Pose publizieren
            self.chat_node.publish_sim_pose(x, y, alpha)
            # Status aktualisieren
            self.waiting_for_initial_pose = False
            self.add_chat_message("System", f"Startpose gesetzt: ({x}, {y}, {alpha}°)", "#3498db")
            self.add_chat_message("System", "Bereit für Navigationsbefehle. Geben Sie 'Stop' ein, um zu beenden.", "#27ae60")
            self.add_chat_message("System", "Gib deinen Befehl, um den Turtlebot ins Ziel zu steuern. Oder hast du eine Frage?", "#7f8c8d")
            # Focus auf Eingabefeld
            self.text_entry.focus_set()
            # Setze initial bekannte Pose
            self.last_known_pose = (x, y, alpha)
        else:
            # Benutzer hat abgebrochen
            self.root.quit()
            
    def on_send_message(self, event=None):
        """Behandelt das Senden einer Nachricht."""
        if self.waiting_for_initial_pose:
            return
            
        message = self.text_entry.get().strip()
        if not message:
            return
            
        # Nachricht zur Chat-Anzeige hinzufügen
        self.add_chat_message("Benutzer", message, "#2c3e50")
        
        # Eingabefeld leeren
        self.text_entry.delete(0, tk.END)
        
        # Stop-Befehl behandeln
        if message.lower() in ['stop', 'stopp']:
            self.add_chat_message("System", "Programm wird beendet...", "#e74c3c")
            self.root.after(1000, self.root.quit)
            return
            
        # Status aktualisieren
        self.status_label.config(text="Verarbeite Befehl...", foreground='#f39c12')
        
        # Befehl an ROS publizieren
        self.chat_node.publish_text(message)
        
        # Aktuelle Pose für Vergleich speichern
        if self.model.is_initialized():
            self.last_known_pose = self.model.get_current_pose()
        
    def wait_for_action_response(self, original_message):
        """Wartet auf eine Aktionsantwort und zeigt sie an."""
        # Diese Methode wird nun durch monitor_actions ersetzt
        pass
        
    def add_chat_message(self, sender, message, color="#2c3e50"):
        """Fügt eine Nachricht zur Chat-Anzeige hinzu mit WhatsApp-ähnlichem Styling."""
        self.chat_display.config(state=tk.NORMAL)
        
        # Zeitstempel
        timestamp = time.strftime("%H:%M:%S")
        
        # Nachrichtentyp bestimmen und entsprechend formatieren
        if sender == "Benutzer":
            # Benutzer-Nachrichten: hellgrün umrandet
            formatted_message = f"[{timestamp}] {sender}: {message}\n"
            # Füge Nachricht hinzu
            start_index = self.chat_display.index(tk.END + "-1c")
            self.chat_display.insert(tk.END, formatted_message + "\n")
            end_index = self.chat_display.index(tk.END + "-1c")
            
            # Hellgrüne Umrandung für Benutzer (WhatsApp-Style)
            self.chat_display.tag_add("user_msg", start_index, end_index)
            self.chat_display.tag_config("user_msg", 
                                       background="#e8f5e8",  # Hellgrüner Hintergrund
                                       relief="solid", 
                                       borderwidth=1,
                                       lmargin1=10, lmargin2=10, rmargin=10,
                                       spacing1=2, spacing3=2)
                                       
        elif sender == "Turtlebot":
            # Roboter/LLM-Nachrichten: blau umrandet mit "Roboter:" prefix
            formatted_message = f"[{timestamp}] Roboter: {message}\n"
            # Füge Nachricht hinzu
            start_index = self.chat_display.index(tk.END + "-1c")
            self.chat_display.insert(tk.END, formatted_message + "\n")
            end_index = self.chat_display.index(tk.END + "-1c")
            
            # Blaue Umrandung für Roboter (WhatsApp-Style)
            self.chat_display.tag_add("robot_msg", start_index, end_index)
            self.chat_display.tag_config("robot_msg", 
                                       background="#e8f4fd",  # Hellblauer Hintergrund
                                       relief="solid", 
                                       borderwidth=1,
                                       lmargin1=10, lmargin2=10, rmargin=10,
                                       spacing1=2, spacing3=2)
                                       
        else:
            # System-Nachrichten: "Systemnachricht:" prefix
            formatted_message = f"[{timestamp}] Systemnachricht: {message}\n"
            # Füge Nachricht hinzu
            start_index = self.chat_display.index(tk.END + "-1c")
            self.chat_display.insert(tk.END, formatted_message + "\n")
            end_index = self.chat_display.index(tk.END + "-1c")
            
            # Standard-Styling für Systemnachrichten
            self.chat_display.tag_add("system_msg", start_index, end_index)
            self.chat_display.tag_config("system_msg", 
                                       foreground=color,
                                       lmargin1=5, lmargin2=5, rmargin=5,
                                       spacing1=1, spacing3=1)
        
        # Scroll nach unten
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
    def run(self):
        """Startet die GUI-Hauptschleife."""
        self.root.mainloop()


class InitialPoseDialog:
    """Dialog für die Eingabe der initialen Pose."""
    
    def __init__(self, parent):
        self.result = None
        
        # Dialog erstellen
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Startpose eingeben")
        self.dialog.geometry("450x400")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.resizable(False, False)
        
        # Dialog zentrieren
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # GUI-Elemente
        self.setup_dialog()
        
        # Focus auf erstes Eingabefeld
        self.x_entry.focus_set()
        
    def setup_dialog(self):
        """Erstellt die Dialog-Elemente."""
        main_frame = ttk.Frame(self.dialog, padding="25")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titel
        title_label = ttk.Label(main_frame, text="Turtlebot Startpose", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # Beschreibung
        desc_label = ttk.Label(main_frame, 
                              text="Geben Sie die Startposition und -orientierung für den Turtlebot ein:",
                              font=('Arial', 10),
                              wraplength=400)
        desc_label.pack(pady=(0, 20))
        
        # Eingabefelder
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(pady=15)
        
        # X-Koordinate
        ttk.Label(fields_frame, text="X (cm):", font=('Arial', 11)).grid(row=0, column=0, sticky=tk.W, padx=(0, 12), pady=12)
        self.x_entry = ttk.Entry(fields_frame, font=('Arial', 11), width=18)
        self.x_entry.grid(row=0, column=1, pady=12)
        self.x_entry.insert(0, "100")
        
        # Y-Koordinate
        ttk.Label(fields_frame, text="Y (cm):", font=('Arial', 11)).grid(row=1, column=0, sticky=tk.W, padx=(0, 12), pady=12)
        self.y_entry = ttk.Entry(fields_frame, font=('Arial', 11), width=18)
        self.y_entry.grid(row=1, column=1, pady=12)
        self.y_entry.insert(0, "100")
        
        # Alpha (Orientierung)
        ttk.Label(fields_frame, text="Alpha (°):", font=('Arial', 11)).grid(row=2, column=0, sticky=tk.W, padx=(0, 12), pady=12)
        self.alpha_entry = ttk.Entry(fields_frame, font=('Arial', 11), width=18)
        self.alpha_entry.grid(row=2, column=1, pady=12)
        self.alpha_entry.insert(0, "0")
        
        # Hinweis
        hint_label = ttk.Label(main_frame, 
                              text="Orientierung: 0° = Osten, 90° = Norden, 180° = Westen, 270° = Süden",
                              font=('Arial', 8),
                              foreground='#7f8c8d',
                              wraplength=400)
        hint_label.pack(pady=(15, 25))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok, style='Accent.TButton')
        ok_button.pack(side=tk.LEFT, padx=(0, 12))
        
        cancel_button = ttk.Button(button_frame, text="Abbrechen", command=self.on_cancel)
        cancel_button.pack(side=tk.LEFT)
        
        # Style für Buttons
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
        
        # Enter-Taste binden
        self.dialog.bind('<Return>', lambda e: self.on_ok())
        
    def on_ok(self):
        """Behandelt OK-Button."""
        try:
            x = int(self.x_entry.get())
            y = int(self.y_entry.get())
            alpha = int(self.alpha_entry.get())
            
            # Prüfe ob die Position befahrbar ist
            if not is_position_navigable(x, y):
                messagebox.showerror("Ungültige Position", 
                                   "Diese Pose ist nicht erreichbar. Bitte wählen Sie eine Position in einem befahrbaren Bereich.")
                return
            
            self.result = (x, y, alpha)
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("Eingabefehler", 
                               "Bitte geben Sie gültige ganze Zahlen ein.")
            
    def on_cancel(self):
        """Behandelt Abbrechen-Button."""
        self.dialog.destroy()


class PostStudyQuestionnaireDialog:
    """Dialog für den Post-Study Fragebogen mit 3 Likert-Skala Fragen."""
    
    def __init__(self, parent):
        self.result = None
        
        # Dialog erstellen - kleineres Fenster, nicht Vollbild
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Abschlussfragen")
        self.dialog.geometry("750x520")  # Kompakter ohne die Beschreibung
        self.dialog.configure(bg='#f8f9fa')
        self.dialog.resizable(False, False)
        
        # Dialog zentrieren
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Dialog in den Vordergrund bringen
        self.dialog.lift()
        self.dialog.focus_force()
        
        # Variables für Antworten ZUERST definieren
        self.satisfaction_var = tk.IntVar()
        self.comprehensibility_var = tk.IntVar()
        self.usefulness_var = tk.IntVar()
        
        # GUI-Elemente
        self.setup_dialog()
        
        # Focus auf Dialog
        self.dialog.focus_set()
        
    def setup_dialog(self):
        """Erstellt die Dialog-Elemente."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titel
        title_label = ttk.Label(main_frame, text="Abschlussfragen", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Fragen mit Likert-Skala
        questions_frame = ttk.Frame(main_frame)
        questions_frame.pack(pady=10, fill=tk.X)
        
        # Frage 1: Zufriedenheit
        self.create_likert_question(
            questions_frame, 
            "Wie zufrieden waren Sie mit den ausgeführten Aktionen des Roboters?",
            self.satisfaction_var,
            ["Gar nicht zufrieden", "Wenig zufrieden", "Neutral", "Zufrieden", "Sehr zufrieden"]
        )
        
        # Separator
        ttk.Separator(questions_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Frage 2: Nachvollziehbarkeit  
        self.create_likert_question(
            questions_frame,
            "Wie nachvollziehbar war das Verhalten des Roboters für Sie?",
            self.comprehensibility_var,
            ["Gar nicht nachvollziehbar", "Wenig nachvollziehbar", "Neutral", "Nachvollziehbar", "Sehr nachvollziehbar"]
        )
        
        # Separator
        ttk.Separator(questions_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Frage 3: Nützlichkeit
        self.create_likert_question(
            questions_frame,
            "Wie hoch schätzen Sie die Nützlichkeit des Systems für einfache Hol- und Bringaufgaben ein?",
            self.usefulness_var,
            ["Gar nicht nützlich", "Wenig nützlich", "Neutral", "Nützlich", "Sehr nützlich"]
        )
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15)
        
        save_button = ttk.Button(button_frame, text="Speichern und Beenden", 
                                command=self.on_save, style='Accent.TButton')
        save_button.pack()
        
        # Style für Buttons
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 11, 'bold'))
        
    def create_likert_question(self, parent, question_text, variable, scale_labels):
        """Erstellt eine Frage mit 5-Punkt-Likert-Skala und individuellen Labels."""
        # Container für diese Frage
        question_frame = ttk.Frame(parent)
        question_frame.pack(fill='x', pady=5)
        
        # Frage-Label
        question_label = ttk.Label(question_frame, text=question_text, 
                                  font=('Arial', 10), wraplength=600)
        question_label.pack(anchor='w', pady=(0, 8))
        
        # Container für Radio-Buttons
        radio_frame = ttk.Frame(question_frame)
        radio_frame.pack(anchor='w')
        
        # Radio-Buttons für 1-5 Skala mit individuellen Labels
        for i in range(1, 6):
            # Container für jeden Radio-Button mit Label darunter
            button_container = ttk.Frame(radio_frame)
            button_container.pack(side='left', padx=(0, 25))
            
            # Radio-Button
            radio = ttk.Radiobutton(button_container, text=str(i), variable=variable, value=i)
            radio.pack()
            
            # Beschreibendes Label unter dem Radio-Button
            desc_label = ttk.Label(button_container, text=scale_labels[i-1], 
                                  font=('Arial', 8), wraplength=80, justify='center')
            desc_label.pack(pady=(2, 0))
            
    def on_save(self):
        """Behandelt Speichern und Beenden Button."""
        satisfaction = self.satisfaction_var.get()
        comprehensibility = self.comprehensibility_var.get()
        usefulness = self.usefulness_var.get()
        
        # Validierung: Alle Fragen müssen beantwortet werden
        if satisfaction == 0 or comprehensibility == 0 or usefulness == 0:
            messagebox.showwarning("Unvollständig", 
                                 "Bitte beantworten Sie alle drei Fragen.")
            return
            
        self.result = (satisfaction, comprehensibility, usefulness)
        self.dialog.destroy()
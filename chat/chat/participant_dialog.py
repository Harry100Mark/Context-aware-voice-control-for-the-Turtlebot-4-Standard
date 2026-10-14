"""
Dialog für die Eingabe von Teilnehmerdaten am Beginn einer Studie.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Tuple, Optional


class ParticipantDialog:
    """Dialog zur Eingabe der Teilnehmerdaten."""
    
    def __init__(self, parent=None):
        self.result: Optional[Tuple[int, str, bool]] = None
        self.parent = parent
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.setup_ui()
        
    def center_window_properly(self):
        """Zentriert das Fenster korrekt, auch bei Multi-Monitor-Setups."""
        # Feste Fenstergröße setzen
        window_width = 700
        window_height = 550
        
        # Update, damit tkinter die korrekten Werte hat
        self.root.update_idletasks()
        
        # Versuche, das Fenster auf dem primären Monitor zu zentrieren
        # Fallback-Methode für Multi-Monitor-Setups
        try:
            # Erster Versuch: Nutze das Parent-Fenster als Referenz
            if self.parent:
                parent_x = self.parent.winfo_x()
                parent_y = self.parent.winfo_y()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()
                
                # Zentriere relativ zum Parent-Fenster
                x = parent_x + (parent_width // 2) - (window_width // 2)
                y = parent_y + (parent_height // 2) - (window_height // 2)
            else:
                # Zweiter Versuch: Nutze eine konservative Schätzung des primären Monitors
                # Annahme: Primärer Monitor ist 1920x1080 oder kleiner
                screen_width = min(1920, self.root.winfo_screenwidth())
                screen_height = min(1080, self.root.winfo_screenheight())
                
                x = (screen_width // 2) - (window_width // 2)
                y = (screen_height // 2) - (window_height // 2)
                
                # Sicherstellen, dass das Fenster nicht außerhalb des Bildschirms ist
                x = max(0, x)
                y = max(0, y)
                
        except Exception:
            # Fallback: Positioniere das Fenster links oben, aber sichtbar
            x = 100
            y = 100
            
        # Fenster positionieren
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Zusätzliche Maßnahmen für bessere Sichtbarkeit
        self.root.update()
        
    def setup_ui(self):
        """Erstellt die Benutzeroberfläche."""
        self.root.title("Teilnehmerdaten - Roboter-Navigation-Studie")
        self.root.geometry("700x550")  # Noch größer für bessere Sichtbarkeit
        self.root.resizable(False, False)
        
        # Robuste Zentrierung für Multi-Monitor-Setups
        self.center_window_properly()
        
        # Fenster immer im Vordergrund und modal
        if self.parent:
            self.root.transient(self.parent)
            self.root.grab_set()
        
        # Fenster in den Vordergrund bringen und fokussieren
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        
        # Nach 200ms topmost deaktivieren, aber Fokus behalten
        self.root.after(200, self._remove_topmost_and_focus)
        
        # Hauptframe
        main_frame = ttk.Frame(self.root, padding="40")  # Erhöht für bessere Sichtbarkeit
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Titel
        title_label = ttk.Label(main_frame, text="Teilnehmerdaten eingeben", 
                               font=("Arial", 18, "bold"))  # Noch größere Schrift
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 30))  # Mehr Abstand
        
        # Alter
        ttk.Label(main_frame, text="Alter:", font=("Arial", 14)).grid(row=1, column=0, sticky=tk.W, pady=15)  # Größere Schrift und mehr Abstand
        self.age_var = tk.StringVar()
        age_entry = ttk.Entry(main_frame, textvariable=self.age_var, width=20, font=("Arial", 14))  # Breitere Eingabe und größere Schrift
        age_entry.grid(row=1, column=1, sticky=tk.W, pady=15, padx=(15, 0))  # Mehr Abstand
        age_entry.focus()
        
        # Geschlecht
        ttk.Label(main_frame, text="Geschlecht:", font=("Arial", 14)).grid(row=2, column=0, sticky=tk.W, pady=15)  # Größere Schrift und mehr Abstand
        self.gender_var = tk.StringVar(value="male")
        
        gender_frame = ttk.Frame(main_frame)
        gender_frame.grid(row=2, column=1, sticky=tk.W, pady=15, padx=(15, 0))  # Mehr Abstand
        
        ttk.Radiobutton(gender_frame, text="Männlich", variable=self.gender_var, 
                       value="male", style='Large.TRadiobutton').pack(side=tk.LEFT)
        ttk.Radiobutton(gender_frame, text="Weiblich", variable=self.gender_var, 
                       value="female", style='Large.TRadiobutton').pack(side=tk.LEFT, padx=(20, 0))  # Mehr Abstand
        
        # Technischer Hintergrund
        ttk.Label(main_frame, text="Technischer Beruf/Studium\n(IT-Bereich):", font=("Arial", 14)).grid(
            row=3, column=0, sticky=tk.W, pady=15)  # Größere Schrift und mehr Abstand
        
        self.tech_var = tk.BooleanVar(value=False)
        
        tech_frame = ttk.Frame(main_frame)
        tech_frame.grid(row=3, column=1, sticky=tk.W, pady=15, padx=(15, 0))  # Mehr Abstand
        
        ttk.Radiobutton(tech_frame, text="Ja", variable=self.tech_var, 
                       value=True, style='Large.TRadiobutton').pack(side=tk.LEFT)
        ttk.Radiobutton(tech_frame, text="Nein", variable=self.tech_var, 
                       value=False, style='Large.TRadiobutton').pack(side=tk.LEFT, padx=(20, 0))  # Mehr Abstand
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(50, 0))  # Noch mehr Abstand
        
        ttk.Button(button_frame, text="Abbrechen", 
                  command=self.cancel, style='Large.TButton').pack(side=tk.LEFT, padx=(0, 20))  # Mehr Abstand
        ttk.Button(button_frame, text="Studie starten", 
                  command=self.ok, style='Large.TButton').pack(side=tk.LEFT)
        
        # Style für größere Buttons und Radiobuttons
        style = ttk.Style()
        style.configure('Large.TButton', font=('Arial', 14, 'bold'), padding=15)  # Größere Buttons
        style.configure('Large.TRadiobutton', font=('Arial', 13))  # Größere Radiobuttons
        
        # Enter-Taste für OK
        self.root.bind('<Return>', lambda e: self.ok())
        self.root.bind('<Escape>', lambda e: self.cancel())
        
        # Fokus auf Alter-Eingabe
        age_entry.focus_set()
        
    def _remove_topmost_and_focus(self):
        """Entfernt topmost-Attribut und stellt sicher, dass das Fenster fokussiert bleibt."""
        try:
            self.root.attributes('-topmost', False)
            self.root.lift()
            self.root.focus_force()
        except:
            pass  # Ignore errors if window is already destroyed
        
    def ok(self):
        """Validiert die Eingaben und schließt den Dialog."""
        try:
            age_str = self.age_var.get().strip()
            if not age_str:
                messagebox.showerror("Fehler", "Bitte geben Sie das Alter ein.")
                return
                
            age = int(age_str)
            if age < 10 or age > 100:
                messagebox.showerror("Fehler", "Bitte geben Sie ein gültiges Alter zwischen 10 und 100 ein.")
                return
                
            gender = self.gender_var.get()
            tech_background = self.tech_var.get()
            
            self.result = (age, gender, tech_background)
            self.root.destroy()
            
        except ValueError:
            messagebox.showerror("Fehler", "Bitte geben Sie eine gültige Zahl für das Alter ein.")
            
    def cancel(self):
        """Bricht den Dialog ab."""
        self.result = None
        self.root.destroy()
        
    def show(self) -> Optional[Tuple[int, str, bool]]:
        """Zeigt den Dialog und gibt das Ergebnis zurück."""
        self.root.wait_window()
        return self.result


def get_participant_data(parent=None) -> Optional[Tuple[int, str, bool]]:
    """Zeigt den Teilnehmer-Dialog und gibt die Daten zurück.
    
    Returns:
        Tuple (age, gender, technical_background) oder None wenn abgebrochen
    """
    dialog = ParticipantDialog(parent)
    return dialog.show()


# Test-Funktion
if __name__ == "__main__":
    # Test der Dialog-Funktionalität
    root = tk.Tk()
    root.withdraw()  # Verstecke Hauptfenster
    
    result = get_participant_data()
    if result:
        age, gender, tech = result
        print(f"Alter: {age}")
        print(f"Geschlecht: {gender}")
        print(f"Technischer Hintergrund: {tech}")
    else:
        print("Dialog abgebrochen")
    
    root.destroy()
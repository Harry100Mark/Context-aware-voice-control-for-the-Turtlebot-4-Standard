"""
Chat Model - Verwaltet den Zustand der Turtlebot Position und Orientierung im MVC Pattern.
"""

import math
import json
import os
import random
from typing import Optional

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
                ROOM_LAYOUT = None
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

class ChatModel:
    """Model-Klasse, die den aktuellen Zustand des Turtlebots verwaltet."""
    
    def __init__(self):
        self.x_cm = None
        self.y_cm = None
        self.alpha_deg = None
        
        # Studien-spezifische Attribute
        self.current_round = 1
        self.max_rounds = 11  # Finale Produktionsversion mit 11 Runden
        self.current_target = None
        self.target_reached = False
        
        # Speicherung für vorherige Befehle, Posen und Reasoning (für 2. Befehl pro Runde)
        self.previous_command = None
        self.previous_pose = None  # (x, y, alpha)
        self.previous_reasoning = None
        self.command_count_in_round = 0
        
        # Mögliche Startposen: (x, y) mit möglichen Alpha-Werten (exakt wie vorgegeben)
        self.start_positions = [
            (600, 90, [180, 90, 135]),
            (396, 160, [90, 270]),
            (630, 610, [180, 225]),
            (40, 340, [0, 330, 10]),
            (120, 595, [270, 0]),
            (245, 210, [0, 45, 90, 120]),
            (130, 380, [0, 270, 315]),
            (400, 510, [90, 180, 270]),
            (250, 500, [0, 60, 300]),
            (420, 420, [315, 135])
        ]
        
        # Mögliche Zielbereiche: (x, y) (exakt wie vorgegeben)
        self.target_areas = [
            (440, 120),
            (600, 600),
            (180, 580),
            (280, 590),
            (560, 420),
            (540, 260),
            (140, 240),
            (250, 200),
            (40, 330),
            (480, 360),
            (330, 440)
        ]
        
    def set_initial_pose(self, x_cm: int, y_cm: int, alpha_deg: int):
        """Setzt die initiale Position und Orientierung."""
        self.x_cm = x_cm
        self.y_cm = y_cm
        self.alpha_deg = alpha_deg % 360  # Normalisiere auf 0-359 Grad
        
    def get_current_pose(self):
        """Gibt die aktuelle Position und Orientierung zurück."""
        return self.x_cm, self.y_cm, self.alpha_deg
        
    def simulate_navigate(self, x_new: int, y_new: int):
        """Simuliert Navigation zu neuer Position mit automatischer Orientierungsberechnung."""
        if self.x_cm is not None and self.y_cm is not None:
            # Berechne neue Orientierung basierend auf A*-Pfad
            print(f"🚀 Navigation: von ({self.x_cm}, {self.y_cm}, {self.alpha_deg}°) zu ({x_new}, {y_new})")
            try:
                from . import pathfinder
                new_orientation, path_length = pathfinder.calculate_target_orientation(
                    self.x_cm, self.y_cm, x_new, y_new
                )
                
                old_orientation = self.alpha_deg
                if new_orientation > 0 or path_length > 0:  # Gültiges Ergebnis
                    self.alpha_deg = new_orientation % 360
                    orientation_change = (new_orientation - old_orientation) % 360
                    print(f"🧭 Orientierung aktualisiert: {old_orientation}° → {self.alpha_deg:.1f}° (Änderung: {orientation_change:.1f}°)")
                    print(f"📏 Pfadlänge durch Topologie: {path_length:.1f}cm")
                else:
                    print("⚠️ Orientierungsberechnung fehlgeschlagen (0°/0cm), behalte aktuelle Orientierung")
                    
            except Exception as e:
                print(f"⚠️ Fehler bei Orientierungsberechnung: {e}")
                print("   Behalte aktuelle Orientierung bei")
                import traceback
                print(f"   Traceback: {traceback.format_exc()}")
        else:
            print(f"🚀 Erste Navigation zu ({x_new}, {y_new}) ohne Orientierungsberechnung")
        
        # Setze neue Position
        self.x_cm = x_new
        self.y_cm = y_new
        print(f"📍 Neue Position gesetzt: ({self.x_cm}, {self.y_cm}, {self.alpha_deg}°)")
        
    def simulate_navigate_with_orientation(self, x_new: int, y_new: int, force_orientation: Optional[float] = None):
        """
        Simuliert Navigation zu neuer Position mit expliziter Orientierungskontrolle.
        
        Args:
            x_new, y_new: Neue Position in cm
            force_orientation: Optional - erzwinge diese Orientierung anstatt A*-Berechnung
        """
        if force_orientation is not None:
            # Verwende explizit gesetzte Orientierung
            self.x_cm = x_new
            self.y_cm = y_new
            self.alpha_deg = force_orientation % 360
            print(f"🧭 Orientierung explizit gesetzt: {self.alpha_deg:.1f}°")
        else:
            # Verwende A*-basierte Orientierungsberechnung
            self.simulate_navigate(x_new, y_new)
            
    def debug_pathfinding(self, target_x: int, target_y: int):
        """
        Debug-Funktion zur Analyse der Pfadberechnung.
        
        Args:
            target_x, target_y: Zielposition für Pfadanalyse
        """
        if not self.is_initialized():
            print("❌ Roboter nicht initialisiert für Pfadanalyse")
            return
            
        try:
            from . import pathfinder
            
            print(f"\n🔍 Pfadanalyse von ({self.x_cm}, {self.y_cm}) zu ({target_x}, {target_y}):")
            
            # Zeige Nodes in der Nähe des Roboters
            print("\n📍 Nodes um Roboterposition:")
            pathfinder.debug_topology_nodes(self.x_cm, self.y_cm, 75)
            
            # Zeige Nodes in der Nähe des Ziels
            print(f"\n🎯 Nodes um Zielposition:")
            pathfinder.debug_topology_nodes(target_x, target_y, 75)
            
            # Berechne Pfad und Orientierung
            orientation, path_length = pathfinder.calculate_target_orientation(
                self.x_cm, self.y_cm, target_x, target_y
            )
            
            print(f"\n✅ Ergebnis:")
            print(f"   Zielorientierung: {orientation:.1f}°")
            print(f"   Pfadlänge: {path_length:.1f}cm")
            
        except Exception as e:
            print(f"❌ Fehler bei Pfadanalyse: {e}")
        
    def is_initialized(self):
        """Prüft, ob das Model initialisiert wurde."""
        return all(val is not None for val in [self.x_cm, self.y_cm, self.alpha_deg])
        
    def is_in_target_area(self, x, y, target_x, target_y, width=140, height=140):
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
        
    def select_random_target(self):
        """Wählt einen zufälligen Zielbereich aus."""
        return random.choice(self.target_areas)
        
    def select_random_start_position(self):
        """Wählt eine zufällige Startposition aus, die nicht im aktuellen Zielbereich liegt."""
        max_attempts = 50  # Verhindere Endlosschleife
        attempts = 0
        
        while attempts < max_attempts:
            # Zufällige Startposition auswählen
            x, y, alpha_options = random.choice(self.start_positions)
            alpha = random.choice(alpha_options)
            
            # Prüfen ob diese Position im aktuellen Zielbereich liegt
            if self.current_target and self.is_in_target_area(x, y, self.current_target[0], self.current_target[1]):
                attempts += 1
                continue  # Neue Position wählen
                
            return x, y, alpha
            
        # Fallback: Nimm erste Position auch wenn sie im Zielbereich liegt
        x, y, alpha_options = self.start_positions[0]
        alpha = random.choice(alpha_options)
        return x, y, alpha
        
    def start_new_round(self):
        """Startet eine neue Studienrunde."""
        if self.current_round > self.max_rounds:
            return False  # Alle Runden abgeschlossen
            
        # Zuerst Zielbereich auswählen
        self.current_target = self.select_random_target()
        self.target_reached = False  # Flag zurücksetzen
        
        # Reset für neue Runde
        self.previous_command = None
        self.previous_pose = None
        self.previous_reasoning = None
        self.command_count_in_round = 0
        
        # Lösche auch die previous_data.json Datei für prompt_google2.py
        self._reset_prompt_previous_data()
        
        # Dann Startposition auswählen (nicht im Zielbereich)
        x, y, alpha = self.select_random_start_position()
        
        # Model initialisieren
        self.set_initial_pose(x, y, alpha)
        
        return True
        
    def next_round(self):
        """Geht zur nächsten Runde über."""
        self.current_round += 1
        self.target_reached = False  # Sicherstellen, dass Flag zurückgesetzt wird
        return self.start_new_round()
        
    def record_command_and_reasoning(self, command: str, reasoning: str):
        """Speichert den aktuellen Befehl und Reasoning für die nächste Runde.
        
        Args:
            command (str): Der Navigationsbefehl vom Menschen
            reasoning (str): Der Reasoning-Prozess des LLMs
        """
        self.command_count_in_round += 1
        
        # Speichere nur ab dem ersten Befehl für den nächsten Befehl
        if self.command_count_in_round >= 1:
            self.previous_command = command
            self.previous_pose = (self.x_cm, self.y_cm, self.alpha_deg) if self.is_initialized() else None
            self.previous_reasoning = reasoning
            
    def get_previous_data(self):
        """Gibt die vorherigen Daten zurück (für 2. Befehl pro Runde).
        
        Returns:
            tuple: (previous_command, previous_pose, previous_reasoning) oder (None, None, None)
        """
        # Nur ab dem zweiten Befehl pro Runde sind vorherige Daten verfügbar
        if self.command_count_in_round >= 2:
            return self.previous_command, self.previous_pose, self.previous_reasoning
        return None, None, None
        
    def _reset_prompt_previous_data(self):
        """Löscht die previous_data.json Datei für prompt_google2.py bei neuer Runde."""
        try:
            prompt_dir = os.path.join(os.path.expanduser('~'), 'ros2_ws', 'src', 'prompt')
            data_file = os.path.join(prompt_dir, 'previous_data.json')
            
            if os.path.exists(data_file):
                os.remove(data_file)
                print(f"✅ Previous data file reset for new round: {data_file}")
        except Exception as e:
            print(f"⚠️ Could not reset previous data file: {e}")
        
    def check_target_reached(self):
        """Prüft ob das aktuelle Ziel erreicht wurde."""
        if (self.current_target and not self.target_reached and 
            self.x_cm is not None and self.y_cm is not None):
            if self.is_in_target_area(self.x_cm, self.y_cm, self.current_target[0], self.current_target[1]):
                self.target_reached = True
                return True
        return False
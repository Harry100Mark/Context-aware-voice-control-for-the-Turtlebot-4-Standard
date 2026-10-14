"""
Datenmodell für die Roboter-Navigation-Studie.
Sammelt und verwaltet Teilnehmerdaten, Rundendaten und exportiert in CSV.
"""

import csv
import os
import re
import time
import shutil
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json


class CommandCategorizer:
    """Kategorisiert Befehle in verschiedene Typen."""
    
    CATEGORIES = {
        'navigation': [
            'gehe', 'fahre', 'navigiere', 'bewege', 'komm', 'zur', 'zum', 'nach',
            'links', 'rechts', 'vorwärts', 'rückwärts', 'geradeaus', 'vor', 'zurück',
            'position', 'koordinate', 'punkt', 'ort', 'stelle', 'bereich', 'zone'
        ],
        'orientation': [
            'drehe', 'dreh', 'wende', 'schaue', 'blicke', 'orientiere', 'richtung',
            'grad', 'winkel', 'norden', 'süden', 'osten', 'westen'
        ],
        'question': [
            'wo', 'was', 'wie', 'warum', 'wann', 'welche', 'kannst', 'bist',
            'frage', '?', 'hilfe', 'explain', 'erkläre', 'zeige', 'status'
        ],
        'stop': [
            'stop', 'halt', 'stopp', 'pause', 'warte', 'anhalten'
        ],
        'confirmation': [
            'ja', 'nein', 'ok', 'okay', 'gut', 'richtig', 'falsch', 'genau'
        ]
    }
    
    @classmethod
    def categorize_command(cls, command: str) -> str:
        """Kategorisiert einen Befehl basierend auf Schlüsselwörtern."""
        command_lower = command.lower().strip()
        
        # Prüfe jede Kategorie
        for category, keywords in cls.CATEGORIES.items():
            for keyword in keywords:
                if keyword in command_lower:
                    return category
        
        return 'other'


class RoundData:
    """Daten für eine einzelne Runde."""
    
    def __init__(self, round_number: int):
        self.round_number = round_number
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.commands: List[Dict] = []
        self.command_count = 0
        self.target_reached = False
        self.latencies: List[float] = []  # Speichert Latenz für jeden Befehl
        
        # Für HTML-Dokumentation
        self.interactions: List[Dict] = []  # Jede Interaktion: Befehl -> LLM -> Aktion
        self.start_image: Optional[str] = None  # Pfad zum Startbild der Runde
        
    def add_command(self, command: str, timestamp: float, category: str = None):
        """Fügt einen Befehl zur Runde hinzu."""
        if category is None:
            category = CommandCategorizer.categorize_command(command)
        
        command_data = {
            'command': command,
            'timestamp': timestamp,
            'category': category,
            'order': len(self.commands) + 1
        }
        self.commands.append(command_data)
        self.command_count += 1
        
    def add_latency(self, latency: float):
        """Fügt eine Latenz-Messung hinzu (Zeit von Befehlseingabe bis Ausführung)."""
        if latency > 0:
            self.latencies.append(latency)
            
    def set_start_image(self, image_path: str):
        """Setzt das Startbild der Runde."""
        self.start_image = image_path
        
    def add_interaction(self, command: str, explanation: str = None, reasoning: str = None, after_image: str = None):
        """Fügt eine vollständige Interaktion hinzu (Befehl -> LLM -> Aktion)."""
        interaction = {
            'command': command,
            'explanation': explanation,
            'reasoning': reasoning,
            'after_image': after_image,
            'timestamp': time.time()
        }
        self.interactions.append(interaction)
        
    def update_last_interaction(self, explanation: str = None, reasoning: str = None, after_image: str = None):
        """Aktualisiert die letzte Interaktion mit LLM-Daten oder Nach-Bild."""
        if self.interactions:
            if explanation is not None:
                self.interactions[-1]['explanation'] = explanation
                print(f"DEBUG: Updated explanation: {explanation[:100]}...")
            if reasoning is not None:
                self.interactions[-1]['reasoning'] = reasoning
                print(f"DEBUG: Updated reasoning: {reasoning[:100]}...")
                print(f"DEBUG: Full reasoning length: {len(reasoning)} characters")
            if after_image is not None:
                self.interactions[-1]['after_image'] = after_image
                print(f"DEBUG: Updated after_image: {after_image}")
        else:
            print("DEBUG: No interactions available to update")
        
    def finish_round(self):
        """Beendet die Runde und setzt die Endzeit."""
        self.end_time = time.time()
        self.target_reached = True
        
    def get_duration(self) -> float:
        """Gibt die Rundendauer in Sekunden zurück."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
        
    def get_command_categories_count(self) -> Dict[str, int]:
        """Zählt die Befehle nach Kategorien."""
        categories = {}
        for cmd in self.commands:
            category = cmd['category']
            categories[category] = categories.get(category, 0) + 1
        return categories
        
    def get_average_latency(self) -> float:
        """Berechnet durchschnittliche Latenz von Befehlseingabe bis Ausführung."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)


class ParticipantData:
    """Daten für einen Teilnehmer."""
    
    def __init__(self, age: int, gender: str, technical_background: bool):
        self.age = age
        self.gender = gender  # 'male' or 'female'
        self.technical_background = technical_background
        self.start_time = datetime.now()
        self.rounds: List[RoundData] = []
        self.current_round: Optional[RoundData] = None
        
        # Post-Study Fragebogen-Daten
        self.satisfaction_rating: Optional[int] = None  # 1-5 Likert-Skala
        self.comprehensibility_rating: Optional[int] = None  # 1-5 Likert-Skala  
        self.usefulness_rating: Optional[int] = None  # 1-5 Likert-Skala
        
    def start_round(self, round_number: int):
        """Startet eine neue Runde."""
        self.current_round = RoundData(round_number)
        self.rounds.append(self.current_round)
        
    def add_command_to_current_round(self, command: str, timestamp: float = None):
        """Fügt einen Befehl zur aktuellen Runde hinzu."""
        if self.current_round is None:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        self.current_round.add_command(command, timestamp)
        
    def finish_current_round(self):
        """Beendet die aktuelle Runde."""
        if self.current_round:
            self.current_round.finish_round()
            
    def get_total_commands(self) -> int:
        """Gesamtanzahl der Befehle über alle Runden."""
        return sum(round_data.command_count for round_data in self.rounds)
        
    def get_average_commands_per_round(self) -> float:
        """Durchschnittliche Anzahl Befehle pro Runde."""
        if not self.rounds:
            return 0.0
        return self.get_total_commands() / len(self.rounds)
        
    def get_total_command_categories(self) -> Dict[str, int]:
        """Gesamtanzahl der Befehle nach Kategorien."""
        total_categories = {}
        for round_data in self.rounds:
            for category, count in round_data.get_command_categories_count().items():
                total_categories[category] = total_categories.get(category, 0) + count
        return total_categories
        
    def set_post_study_ratings(self, satisfaction: int, comprehensibility: int, usefulness: int):
        """Setzt die Post-Study Fragebogen-Bewertungen."""
        self.satisfaction_rating = satisfaction
        self.comprehensibility_rating = comprehensibility  
        self.usefulness_rating = usefulness
        
    def get_average_latency(self) -> float:
        """Durchschnittliche Latenz über alle Runden."""
        latencies = [round_data.get_average_latency() for round_data in self.rounds]
        valid_latencies = [lat for lat in latencies if lat > 0]
        if not valid_latencies:
            return 0.0
        return sum(valid_latencies) / len(valid_latencies)


class StudyDataModel:
    """Hauptmodell für die Studiendatenerfassung."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser('~'), 'ros2_ws', 'study_data')
        
        self.data_dir = data_dir
        self.ensure_data_dir()
        
        self.current_participant: Optional[ParticipantData] = None
        self.participants: List[ParticipantData] = []
        
    def ensure_data_dir(self):
        """Stellt sicher, dass das Datenverzeichnis existiert."""
        os.makedirs(self.data_dir, exist_ok=True)
        
    def start_new_participant(self, age: int, gender: str, technical_background: bool):
        """Startet einen neuen Teilnehmer."""
        self.current_participant = ParticipantData(age, gender, technical_background)
        self.participants.append(self.current_participant)
        
    def start_round(self, round_number: int):
        """Startet eine neue Runde für den aktuellen Teilnehmer."""
        if self.current_participant:
            self.current_participant.start_round(round_number)
            
    def add_command(self, command: str, timestamp: float = None):
        """Fügt einen Befehl zur aktuellen Runde hinzu."""
        # Verwende die neue Methode mit Interaktions-Tracking
        self.add_command_with_interaction(command, timestamp)
            
    def finish_round(self):
        """Beendet die aktuelle Runde."""
        if self.current_participant:
            self.current_participant.finish_current_round()
            
    def finish_participant(self):
        """Beendet den aktuellen Teilnehmer und exportiert die Daten."""
        if self.current_participant:
            self.export_participant_data(self.current_participant)
            self.export_participant_html(self.current_participant)
            self.update_aggregated_data()
            
    def set_post_study_ratings(self, satisfaction: int, comprehensibility: int, usefulness: int):
        """Setzt die Post-Study Fragebogen-Bewertungen für den aktuellen Teilnehmer."""
        if self.current_participant:
            self.current_participant.set_post_study_ratings(satisfaction, comprehensibility, usefulness)
            
    def export_participant_data(self, participant: ParticipantData):
        """Exportiert die Daten eines Teilnehmers in eine CSV-Datei."""
        timestamp = participant.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"participant_{timestamp}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header für Teilnehmerdaten
            writer.writerow(['Participant_Info'])
            writer.writerow(['Age', participant.age])
            writer.writerow(['Gender', participant.gender])
            writer.writerow(['Technical_Background', participant.technical_background])
            writer.writerow(['Start_Time', participant.start_time.isoformat()])
            writer.writerow([])
            
            # Post-Study Fragebogen-Ergebnisse
            writer.writerow(['Post_Study_Questionnaire'])
            writer.writerow(['Satisfaction_Rating', participant.satisfaction_rating or 'N/A'])
            writer.writerow(['Comprehensibility_Rating', participant.comprehensibility_rating or 'N/A'])
            writer.writerow(['Usefulness_Rating', participant.usefulness_rating or 'N/A'])
            writer.writerow([])
            
            # Header für Rundendaten
            writer.writerow(['Round', 'Commands_Count', 'Duration_Seconds', 
                           'Navigation_Commands', 'Orientation_Commands', 
                           'Question_Commands', 'Stop_Commands', 
                           'Confirmation_Commands', 'Other_Commands', 
                           'Average_Latency'])
            
            # Rundendaten
            for round_data in participant.rounds:
                categories = round_data.get_command_categories_count()
                writer.writerow([
                    round_data.round_number,
                    round_data.command_count,
                    round_data.get_duration(),
                    categories.get('navigation', 0),
                    categories.get('orientation', 0),
                    categories.get('question', 0),
                    categories.get('stop', 0),
                    categories.get('confirmation', 0),
                    categories.get('other', 0),
                    round_data.get_average_latency()
                ])
                
            writer.writerow([])
            
            # Zusammenfassung
            writer.writerow(['Summary'])
            writer.writerow(['Total_Commands', participant.get_total_commands()])
            writer.writerow(['Average_Commands_Per_Round', participant.get_average_commands_per_round()])
            writer.writerow(['Average_Latency', participant.get_average_latency()])
            
            total_categories = participant.get_total_command_categories()
            for category, count in total_categories.items():
                writer.writerow([f'Total_{category.title()}_Commands', count])
                
    def export_participant_html(self, participant: ParticipantData):
        """Exportiert die Daten eines Teilnehmers als HTML-Dokumentation."""
        timestamp = participant.start_time.strftime("%Y%m%d_%H%M%S")
        
        # Normale Version
        filename = f"participant_{timestamp}.html"
        filepath = os.path.join(self.data_dir, filename)
        html_content = self._generate_html_content(participant, show_reasoning=False)
        
        with open(filepath, 'w', encoding='utf-8') as htmlfile:
            htmlfile.write(html_content)
            
        print(f"HTML-Dokumentation gespeichert: {filepath}")
        
        # Version mit sichtbarem Reasoning
        filename_with_reasoning = f"participant_{timestamp}_with_reasoning.html"
        filepath_with_reasoning = os.path.join(self.data_dir, filename_with_reasoning)
        html_content_with_reasoning = self._generate_html_content(participant, show_reasoning=True)
        
        with open(filepath_with_reasoning, 'w', encoding='utf-8') as htmlfile:
            htmlfile.write(html_content_with_reasoning)
            
        print(f"HTML-Dokumentation mit Reasoning gespeichert: {filepath_with_reasoning}")
        
    def _generate_html_content(self, participant: ParticipantData, show_reasoning: bool = False) -> str:
        """Generiert den HTML-Inhalt für die Teilnehmer-Dokumentation."""
        title_suffix = " (mit Reasoning)" if show_reasoning else ""
        reasoning_style = """
        .reasoning-section {
            background-color: #f8f9fa;
            border: 2px solid #6c757d;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
        }
        .reasoning-header {
            color: #495057;
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 14px;
        }
        """ if show_reasoning else ""
        
        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Studie Dokumentation - Teilnehmer {participant.start_time.strftime('%Y%m%d_%H%M%S')}{title_suffix}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .header {{
            background-color: #007bff;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .participant-info {{
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .round {{
            background-color: white;
            margin-bottom: 30px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .round-header {{
            background-color: #28a745;
            color: white;
            padding: 15px 20px;
            font-size: 18px;
            font-weight: bold;
        }}
        .round-content {{
            padding: 20px;
        }}
        .interaction {{
            border-left: 4px solid #007bff;
            margin-bottom: 25px;
            padding-left: 15px;
        }}
        .command {{
            background-color: #e7f3ff;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }}
        .llm-response {{
            background-color: #f0f8f0;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }}
        .image-container {{
            text-align: center;
            margin: 15px 0;
        }}
        .robot-image {{
            max-width: 600px;
            width: 100%;
            height: auto;
            border: 2px solid #ddd;
            border-radius: 8px;
        }}
        .image-caption {{
            font-style: italic;
            color: #666;
            margin-top: 5px;
        }}
        .questionnaire {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 20px;
            margin-top: 30px;
        }}
        .rating {{
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            margin-left: 10px;
        }}
        {reasoning_style}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Roboter-Navigation Studie - Dokumentation{title_suffix}</h1>
        <p>Teilnehmer: {participant.start_time.strftime('%d.%m.%Y %H:%M:%S')}</p>
    </div>
    
    <div class="participant-info">
        <h2>📋 Teilnehmerinformationen</h2>
        <p><strong>Alter:</strong> {participant.age} Jahre</p>
        <p><strong>Geschlecht:</strong> {participant.gender}</p>
        <p><strong>Technischer Hintergrund:</strong> {'Ja' if participant.technical_background else 'Nein'}</p>
        <p><strong>Startzeit:</strong> {participant.start_time.strftime('%d.%m.%Y %H:%M:%S')}</p>
        <p><strong>Anzahl Runden:</strong> {len(participant.rounds)}</p>
    </div>
"""
        
        # Runden hinzufügen
        for round_data in participant.rounds:
            html += self._generate_round_html(round_data, show_reasoning)
            
        # Post-Study Fragebogen
        if (participant.satisfaction_rating is not None or 
            participant.comprehensibility_rating is not None or 
            participant.usefulness_rating is not None):
            html += f"""
    <div class="questionnaire">
        <h2>📝 Abschlussfragebogen</h2>
        <p><strong>Zufriedenheit mit den Aktionen:</strong> 
           <span class="rating">{participant.satisfaction_rating or 'N/A'}/5</span></p>
        <p><strong>Nachvollziehbarkeit des Verhaltens:</strong> 
           <span class="rating">{participant.comprehensibility_rating or 'N/A'}/5</span></p>
        <p><strong>Nützlichkeit des Systems:</strong> 
           <span class="rating">{participant.usefulness_rating or 'N/A'}/5</span></p>
    </div>
"""
        
        html += """
</body>
</html>"""
        
        return html
        
    def _generate_round_html(self, round_data: RoundData, show_reasoning: bool = False) -> str:
        """Generiert HTML für eine einzelne Runde."""
        duration = round_data.get_duration()
        
        html = f"""
    <div class="round">
        <div class="round-header">
            🎯 Runde {round_data.round_number}
            <span style="float: right; font-size: 14px;">
                ⏱️ {duration:.1f}s | 💬 {len(round_data.interactions)} Befehle
            </span>
        </div>
        <div class="round-content">
"""
        
        # Startbild der Runde
        if round_data.start_image and os.path.exists(round_data.start_image):
            image_data = self._encode_image_to_base64(round_data.start_image)
            if image_data:
                html += f"""
            <div class="image-container">
                <img src="data:image/png;base64,{image_data}" alt="Startposition Runde {round_data.round_number}" class="robot-image">
                <div class="image-caption">🚀 Startposition Runde {round_data.round_number}</div>
            </div>
"""
        
        # Interaktionen
        for i, interaction in enumerate(round_data.interactions, 1):
            print(f"DEBUG: Processing interaction {i}: explanation={len(interaction.get('explanation', '') or '')} chars, reasoning={len(interaction.get('reasoning', '') or '')} chars")
            html += f"""
            <div class="interaction">
                <h4>💬 Befehl {i}</h4>
                <div class="command">
                    <strong>👤 Navigationsbefehl:</strong> {interaction.get('command', 'N/A')}
                </div>
"""
            
            if interaction.get('explanation'):
                html += f"""
                <div class="llm-response">
                    <strong>🤖 LLM Explanation:</strong> {interaction.get('explanation')}
                </div>
"""
            
            # Reasoning anzeigen - in beiden Versionen, aber unterschiedlich gestylt
            if interaction.get('reasoning'):
                if show_reasoning:
                    # Erweiterte Version: Hervorgehobenes Reasoning
                    html += f"""
                <div class="reasoning-section">
                    <div class="reasoning-header">🧠 LLM REASONING (Entwickler-Information):</div>
                    <div>{interaction.get('reasoning')}</div>
                </div>
"""
                else:
                    # Normale Version: Reasoning in normaler grüner Box
                    html += f"""
                <div class="llm-response">
                    <strong>🧠 LLM Reasoning:</strong> {interaction.get('reasoning')}
                </div>
"""
            
            # Nach-Bild
            if interaction.get('after_image') and os.path.exists(interaction.get('after_image')):
                image_data = self._encode_image_to_base64(interaction.get('after_image'))
                if image_data:
                    html += f"""
                <div class="image-container">
                    <img src="data:image/png;base64,{image_data}" alt="Nach Befehl {i}" class="robot-image">
                    <div class="image-caption">📍 Position nach Befehl {i}</div>
                </div>
"""
            
            html += "</div>"
        
        html += """
        </div>
    </div>
"""
        
        return html
        
    def _encode_image_to_base64(self, image_path: str) -> str:
        """Kodiert ein Bild als Base64 für HTML-Einbettung."""
        try:
            with open(image_path, 'rb') as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded
        except Exception as e:
            print(f"Fehler beim Kodieren des Bildes {image_path}: {e}")
            return ""
            
    def add_command_with_interaction(self, command: str, timestamp: float = None):
        """Fügt einen Befehl hinzu und startet eine neue Interaktion."""
        if self.current_participant and self.current_participant.current_round:
            if timestamp is None:
                timestamp = time.time()
                
            # Normale Befehlserfassung
            self.current_participant.add_command_to_current_round(command, timestamp)
            
            # Neue Interaktion starten
            self.current_participant.current_round.add_interaction(command)
            
    def update_current_interaction(self, explanation: str = None, reasoning: str = None):
        """Aktualisiert die aktuelle Interaktion mit LLM-Daten."""
        if (self.current_participant and 
            self.current_participant.current_round and 
            self.current_participant.current_round.interactions):
            print(f"DEBUG: Updating interaction with explanation: {explanation[:100] if explanation else 'None'}...")
            print(f"DEBUG: Updating interaction with reasoning: {reasoning[:100] if reasoning else 'None'}...")
            
            # Vor dem Update den aktuellen Zustand zeigen
            current_interaction = self.current_participant.current_round.interactions[-1]
            print(f"DEBUG: Before update - explanation: {len(current_interaction.get('explanation', '') or '')} chars")
            print(f"DEBUG: Before update - reasoning: {len(current_interaction.get('reasoning', '') or '')} chars")
            
            self.current_participant.current_round.update_last_interaction(
                explanation=explanation, reasoning=reasoning
            )
            
            # Nach dem Update den neuen Zustand zeigen
            print(f"DEBUG: After update - explanation: {len(current_interaction.get('explanation', '') or '')} chars")
            print(f"DEBUG: After update - reasoning: {len(current_interaction.get('reasoning', '') or '')} chars")
            
        else:
            print("DEBUG: Cannot update interaction - no current participant/round/interactions")
            
    def set_round_start_image(self, image_path: str):
        """Setzt das Startbild für die aktuelle Runde."""
        if self.current_participant and self.current_participant.current_round:
            # Kopiere das Bild in das Datenverzeichnis
            timestamp = self.current_participant.start_time.strftime("%Y%m%d_%H%M%S")
            round_num = self.current_participant.current_round.round_number
            target_filename = f"participant_{timestamp}_round_{round_num}_start.png"
            target_path = os.path.join(self.data_dir, target_filename)
            
            try:
                shutil.copy2(image_path, target_path)
                self.current_participant.current_round.set_start_image(target_path)
            except Exception as e:
                print(f"Fehler beim Kopieren des Startbildes: {e}")
                
    def set_interaction_after_image(self, image_path: str):
        """Setzt das Nach-Bild für die aktuelle Interaktion."""
        if (self.current_participant and 
            self.current_participant.current_round and 
            self.current_participant.current_round.interactions):
            
            # Kopiere das Bild in das Datenverzeichnis
            timestamp = self.current_participant.start_time.strftime("%Y%m%d_%H%M%S")
            round_num = self.current_participant.current_round.round_number
            interaction_num = len(self.current_participant.current_round.interactions)
            target_filename = f"participant_{timestamp}_round_{round_num}_cmd_{interaction_num}_after.png"
            target_path = os.path.join(self.data_dir, target_filename)
            
            try:
                shutil.copy2(image_path, target_path)
                self.current_participant.current_round.update_last_interaction(after_image=target_path)
            except Exception as e:
                print(f"Fehler beim Kopieren des Nach-Bildes: {e}")
                
    def update_aggregated_data(self):
        """Aktualisiert die aggregierten Daten über alle Teilnehmer."""
        filepath = os.path.join(self.data_dir, 'aggregated_results.csv')
        
        if not self.participants:
            return
            
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Study_Summary'])
            writer.writerow(['Total_Participants', len(self.participants)])
            writer.writerow(['Generation_Date', datetime.now().isoformat()])
            writer.writerow([])
            
            # Durchschnittswerte berechnen
            avg_age = sum(p.age for p in self.participants) / len(self.participants)
            male_count = sum(1 for p in self.participants if p.gender == 'male')
            tech_count = sum(1 for p in self.participants if p.technical_background)
            
            writer.writerow(['Average_Age', avg_age])
            writer.writerow(['Male_Participants', male_count])
            writer.writerow(['Female_Participants', len(self.participants) - male_count])
            writer.writerow(['Technical_Background_Count', tech_count])
            writer.writerow([])
            
            # Durchschnittliche Leistungsmetriken
            avg_commands_per_round = sum(p.get_average_commands_per_round() 
                                       for p in self.participants) / len(self.participants)
            avg_latency = sum(p.get_average_latency() 
                            for p in self.participants) / len(self.participants)
            
            writer.writerow(['Performance_Metrics'])
            writer.writerow(['Average_Commands_Per_Round', avg_commands_per_round])
            writer.writerow(['Average_Latency_Seconds', avg_latency])
            writer.writerow([])
            
            # Befehlskategorien-Durchschnitte
            all_categories = ['navigation', 'orientation', 'question', 'stop', 'confirmation', 'other']
            writer.writerow(['Command_Categories_Average'])
            
            for category in all_categories:
                total_category_commands = sum(
                    p.get_total_command_categories().get(category, 0) 
                    for p in self.participants
                )
                avg_category = total_category_commands / len(self.participants)
                writer.writerow([f'Average_{category.title()}_Commands', avg_category])
                
    def get_current_round_number(self) -> int:
        """Gibt die aktuelle Rundennummer zurück."""
        if self.current_participant and self.current_participant.rounds:
            return len(self.current_participant.rounds)
        return 0
        
    def has_current_participant(self) -> bool:
        """Prüft ob ein aktueller Teilnehmer vorhanden ist."""
        return self.current_participant is not None
#!/usr/bin/env python3
"""
Script to regenerate samples.json based on the existing data but with proper 'aktion' fields
and all 15 examples properly defined in fewshot.py format.
"""

import json
import os
from fewshot import generate_samples_json, load_room_layout

def main():
    # Load room layout
    room_layout = load_room_layout()
    if room_layout is None:
        print('Fehler: ROOM_LAYOUT konnte nicht geladen werden')
        return
    
    # Create complete sample_definitions list (15 examples, skipping the removed example 2)
    sample_definitions = [
        # Example 1: Fahre zum Ausgang
        {
            "robot_position": (600, 600, 180),
            "prompt": "Fahre zum Ausgang",
            "aktion": "Navigieren",
            "zielposition": {"x": 60, "y": 320, "z": 0},
            "explanation": "Mit Ausgang ist die Tür gemeint, die nach draußen führt.",
            "reasoning": "Der Raum hat insgesamt 3 Türen. Tür 2 und Tür 3 führen zum Serverraum und nur Tür 1 führt zum Flur (also nach draußen). Daher sind alle befahrbaren Koordinaten, die sich in der Nähe von Tür 1 befinden, korrekt."
        },
        # Example 3: Bieg rechts ab  
        {
            "robot_position": (420, 440, 135),
            "prompt": "Bieg rechts ab",
            "aktion": "Navigieren",
            "zielposition": {"x": 450, "y": 620, "z": 0},
            "explanation": "Der Roboter soll nach rechts abbiegen und um Tisch 6 herum navigieren.",
            "reasoning": "Das relevante Hindernis ist Tisch 6, weil er die gewünschte Fahrtrichtung blockiert. Turtlebot (420, 440) befindet sich SÜDWESTLICH von Tisch 6 (center: 496, 512). Orientierung Nordwest + Rechts abbiegen führt zu einem Ziel NÖRDLICH des Hindernisses. Der Zielpunkt (450, 620) liegt im befahrbaren Bereich und erfüllt die Anforderung."
        },
        # Example 4: Kannst du bitte zum nächsten Computer kommen?
        {
            "robot_position": (240, 260, 135),
            "prompt": "Kannst du bitte zum nächsten Computer kommen?",
            "aktion": "Navigieren", 
            "zielposition": {"x": 450, "y": 100, "z": 0},
            "explanation": "Der Roboter soll zum nächstgelegenen Computer navigieren.",
            "reasoning": "Im Raum gibt es 2 Tische mit PCs - Tisch 1 und Tisch 5. Der Turtlebot ist näher an Tisch 1 als an Tisch 5. Daher sind alle Koordinaten in der Nähe von Tisch 1 im befahrbaren Bereich korrekt."
        },
        # Example 5: Beweg dich auf die andere Seite des Raumes
        {
            "robot_position": (590, 90, 180),
            "prompt": "Beweg dich auf die andere Seite des Raumes",
            "aktion": "Navigieren",
            "zielposition": {"x": 180, "y": 580, "z": 0},
            "explanation": "Der Roboter soll zur gegenüberliegenden Seite des Raumes fahren.",
            "reasoning": "Der Turtlebot befindet sich in der südöstlichen Ecke des Raumes und soll sich zur nordwestlichen Ecke bewegen. Alle Koordinaten im nordwestlichen Quadranten des befahrbaren Bereichs sind korrekt."
        },
        # Example 6: Fahr rechts neben den Tisch hinter dir
        {
            "robot_position": (480, 330, 270),
            "prompt": "Fahr rechts neben den Tisch hinter dir",
            "aktion": "Navigieren",
            "zielposition": {"x": 400, "y": 510, "z": 0},
            "explanation": "Der Roboter soll sich westlich von Tisch 6 positionieren.",
            "reasoning": "Da der Turtlebot nach Süden gerichtet ist, ist der Tisch HINTER ihm derjenige, der sich NÖRDLICH befindet (Tisch 6). 'Rechts neben' bedeutet aus Sicht des nach Süden gerichteten Roboters westlich. Der Zielpunkt liegt westlich von Tisch 6 im befahrbaren Bereich."
        },
        # Example 7: Fahr links am Stuhl vorbei
        {
            "robot_position": (440, 300, 180),
            "prompt": "Fahr links am Stuhl vorbei",
            "aktion": "Navigieren",
            "zielposition": {"x": 300, "y": 260, "z": 0},
            "explanation": "Der Roboter soll südlich an Stuhl S1 vorbeifahren.",
            "reasoning": "Der Turtlebot ist nach Westen orientiert. 'Links am Stuhl vorbei' bedeutet südlich an einem der Stühle vor ihm vorbei. Dies trifft auf Stuhl S1 zu, da es südlich von S1 einen befahrbaren Pfad gibt. Der Zielpunkt liegt westlich und südlich von S1."
        },
        # Example 8: Fahr nach links
        {
            "robot_position": (390, 230, 90),
            "prompt": "Fahr nach links",
            "aktion": "Navigieren",
            "zielposition": {"x": 210, "y": 270, "z": 0},
            "explanation": "Der Roboter soll nach Westen fahren.",
            "reasoning": "Da der Turtlebot nach Norden orientiert ist, bedeutet 'links' westliche Richtung. Es gibt einen befahrbaren Pfad zwischen Tür 3 und Tisch 10 und weiter zwischen dem Regal und Tisch 10. Der Zielpunkt liegt auf diesem westlichen Pfad."
        },
        # Example 9: Fahr nach rechts um die Ecke
        {
            "robot_position": (300, 230, 0),
            "prompt": "Fahr nach rechts um die Ecke",
            "aktion": "Navigieren",
            "zielposition": {"x": 395, "y": 110, "z": 0},
            "explanation": "Der Roboter soll um Schrank 2 herum nach Südosten navigieren.",
            "reasoning": "Das relevante Hindernis ist Schrank 2, der die Fahrtrichtung nach rechts (Süden) blockiert. Turtlebot (300, 230) befindet sich nordwestlich von Schrank 2. Das Ziel liegt südöstlich des Hindernisses, um die Ecke herum."
        },
        # Example 10: Fahr vorwärts
        {
            "robot_position": (620, 95, 180),
            "prompt": "Fahr vorwärts",
            "aktion": "Navigieren",
            "zielposition": {"x": 210, "y": 270, "z": 0},
            "explanation": "Der Roboter soll in seine Blickrichtung (Westen) fahren.",
            "reasoning": "Der Turtlebot ist nach Westen gerichtet. 'Vorwärts' bedeutet westliche Bewegung. Es gibt mehrere befahrbare Koordinaten westlich bis zum Schrank 2. Der Zielpunkt liegt westlich der aktuellen Position im befahrbaren Bereich."
        },
        # Example 11: Fahr ein kleines Stück vor
        {
            "robot_position": (60, 300, 45),
            "prompt": "Fahr ein kleines Stück vor",
            "aktion": "Richtungsfahrt",
            "winkel": 0,
            "is_clockwise": True,
            "winkelgeschwindigkeit": 50,
            "distanz": 0.1,
            "lineargeschwindigkeit": 0.2,
            "is_forward": True,
            "explanation": "Der Roboter soll eine kurze Strecke vorwärts fahren.",
            "reasoning": "Der Befehl verlangt eine kleine Vorwärtsbewegung ohne Richtungsänderung. Die Parameter sind entsprechend für eine langsame, kurze Bewegung gewählt."
        },
        # Example 12: Fahr schnell einen Meter rückwärts
        {
            "robot_position": (300, 540, 225),
            "prompt": "Fahr schnell einen Meter rückwärts",
            "aktion": "Richtungsfahrt",
            "winkel": 0,
            "is_clockwise": True,
            "winkelgeschwindigkeit": 50,
            "distanz": 1.0,
            "lineargeschwindigkeit": 0.35,
            "is_forward": False,
            "explanation": "Der Roboter soll schnell rückwärts fahren.",
            "reasoning": "Der Befehl verlangt eine schnelle Rückwärtsbewegung über einen Meter. Die maximale Lineargeschwindigkeit wird für 'schnell' verwendet, is_forward ist False für Rückwärtsfahrt."
        },
        # Example 13: Dreh dich nach rechts
        {
            "robot_position": (480, 360, 0),
            "prompt": "Dreh dich nach rechts",
            "aktion": "Drehen",
            "winkel": 90,
            "is_clockwise": True,
            "winkelgeschwindigkeit": 50,
            "explanation": "Der Roboter soll eine 90°-Rechtsdrehung ausführen.",
            "reasoning": "Eine Rechtsdrehung entspricht einer Drehung im Uhrzeigersinn. 90° ist die Standard-Rechtsdrehung. Normale Winkelgeschwindigkeit wird verwendet.",
            "old_prompt": "Fahr zur Tür links vom Regal.",
            "old_position": (330, 480, 315)
        },
        # Example 14: Dreh dich langsam um
        {
            "robot_position": (360, 600, 180),
            "prompt": "Dreh dich langsam um",
            "aktion": "Drehen",
            "winkel": 180,
            "is_clockwise": True,
            "winkelgeschwindigkeit": 5,
            "explanation": "Der Roboter soll sich langsam um 180° drehen.",
            "reasoning": "Eine Wende um 180° wird mit minimaler Winkelgeschwindigkeit ausgeführt, da 'langsam' explizit verlangt wird. Die Drehrichtung ist beliebig, daher wird Uhrzeigersinn gewählt."
        },
        # Example 15: Geh zum Telefon
        {
            "robot_position": (500, 400, 90),
            "prompt": "Geh zum Telefon",
            "aktion": "Navigieren",
            "zielposition": {"x": 190, "y": 630, "z": 0},
            "explanation": "Der Roboter soll zur Kommode mit Telefon navigieren.",
            "reasoning": "Es gibt zwei Telefone im Raum - eins bei Tisch 2 und eins bei der Kommode. Da die Kommode als 'Kommode (mit Telefon)' bezeichnet ist, ist sie das primäre Telefonziel. Der Zielpunkt liegt in der Nähe der Kommode im befahrbaren Bereich."
        },
        # Example 16: Ich verstehe dich nicht
        {
            "robot_position": (200, 500, 270),
            "prompt": "Ich verstehe dich nicht",
            "aktion": "Keine",
            "answer": "Können Sie Ihren Befehl bitte präzisieren?"
        }
    ]
    
    # Generate samples.json
    samples_data = generate_samples_json(sample_definitions, room_layout)
    
    # Save to fewshots/samples.json
    fewshots_dir = os.path.join(os.path.dirname(__file__), 'fewshots')
    samples_path = os.path.join(fewshots_dir, 'samples.json')
    
    with open(samples_path, 'w', encoding='utf-8') as f:
        json.dump(samples_data, f, indent=2, ensure_ascii=False)
    
    print(f'Successfully generated samples.json with {len(sample_definitions)} examples')
    print(f'Saved to: {samples_path}')
    
    # Verify the generated file
    print('\\nGenerated structure:')
    for key, value in samples_data.items():
        if isinstance(value, list):
            print(f'{key}: {len(value)} items')
        else:
            print(f'{key}: {type(value)}')

if __name__ == "__main__":
    main()
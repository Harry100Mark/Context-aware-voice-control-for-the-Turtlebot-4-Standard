"""
Perspektive-Analysemodul für den Turtlebot.
Analysiert alle Objekte im Raum relativ zur Turtlebot-Position und -Orientierung.
"""

import json
import math
import os

def load_room_layout():
    """
    Lädt das ROOM_LAYOUT aus der roomlayout.json Datei.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'roomlayout.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Fehler beim Laden der roomlayout.json: {e}")
        return None

# Lade ROOM_LAYOUT aus JSON
ROOM_LAYOUT = load_room_layout()

def angle_to_compass(angle_deg):
    """
    Konvertiert einen Winkel in Grad zu einer Himmelsrichtung.
    0° = Osten/rechts, 90° = Norden/oben, 180° = Westen/links, 270° = Süden/unten
    
    Args:
        angle_deg: Winkel in Grad (0° = Osten/rechts, gegen den Uhrzeigersinn)
    Returns:
        tuple: (quantisierter_winkel_für_anzeige, quantisierter_winkel_für_matplotlib, himmelsrichtung_string)
    """
    # Winkel normalisieren auf [0, 360)
    normalized = angle_deg % 360
    
    # Quantisierung zu 8 Himmelsrichtungen (45° Schritte)
    if 337.5 <= normalized or normalized < 22.5:
        return 0, 0, "Osten"  # 0° = nach rechts
    elif 22.5 <= normalized < 67.5:
        return 45, 45, "Nordost"
    elif 67.5 <= normalized < 112.5:
        return 90, 90, "Norden"  # 90° = nach oben
    elif 112.5 <= normalized < 157.5:
        return 135, 135, "Nordwest"
    elif 157.5 <= normalized < 202.5:
        return 180, 180, "Westen"  # 180° = nach links
    elif 202.5 <= normalized < 247.5:
        return 225, 225, "Südwest"
    elif 247.5 <= normalized < 292.5:
        return 270, 270, "Süden"  # 270° = nach unten
    elif 292.5 <= normalized < 337.5:
        return 315, 315, "Südost"
    else:
        return 0, 0, "Osten"  # Fallback

def calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, object_x, object_y):
    """
    Berechnet den relativen Winkel eines Objekts zum Turtlebot.
    
    Args:
        turtlebot_x, turtlebot_y: Position des Turtlebots
        turtlebot_heading: Orientierung des Turtlebots in Grad
        object_x, object_y: Position des Objekts
    
    Returns:
        float: Relativer Winkel in Grad (-180 bis 180)
               0° = vor dem Roboter, 90° = rechts, -90° = links, ±180° = hinter
    """
    # Berechne Winkel vom Turtlebot zum Objekt (in mathematischen Koordinaten)
    dx = object_x - turtlebot_x
    dy = object_y - turtlebot_y
    
    # Winkel in Grad (0° = Osten, 90° = Norden, usw.)
    angle_to_object = math.degrees(math.atan2(dy, dx))
    
    # Relativer Winkel: Objektwinkel minus Roboterrichtung
    relative_angle = angle_to_object - turtlebot_heading
    
    # Normalisiere auf [-180, 180]
    while relative_angle > 180:
        relative_angle -= 360
    while relative_angle <= -180:
        relative_angle += 360
    
    return relative_angle

def classify_object_direction(relative_angle):
    """
    Klassifiziert die Richtung eines Objekts basierend auf dem relativen Winkel.
    
    Args:
        relative_angle: Relativer Winkel in Grad (-180 bis 180)
    
    Returns:
        str: "vor", "rechts", "hinter", oder "links"
    """
    # 90°-Sektoren:
    # vor: -45° bis +45°
    # links: +45° bis +135° (positive Winkel = gegen Uhrzeigersinn = links)
    # hinter: +135° bis +180° und -180° bis -135°
    # rechts: -135° bis -45° (negative Winkel = im Uhrzeigersinn = rechts)
    
    if -45 <= relative_angle <= 45:
        return "vor"
    elif 45 < relative_angle <= 135:
        return "links"  # Korrigiert: positive Winkel = links
    elif relative_angle > 135 or relative_angle <= -135:
        return "hinter"
    else:  # -135 < relative_angle < -45
        return "rechts"  # Korrigiert: negative Winkel = rechts

def analyze_objects_around_turtlebot(turtlebot_x, turtlebot_y, turtlebot_heading):
    """
    Analysiert alle Objekte im Raum relativ zur Turtlebot-Position und -Orientierung.
    
    Args:
        turtlebot_x, turtlebot_y: Position des Turtlebots in cm
        turtlebot_heading: Orientierung des Turtlebots in Grad
    
    Returns:
        dict: JSON-Struktur mit Objekten gruppiert nach Richtungen
    """
    # Konvertiere Orientierung zu Himmelsrichtung
    display_heading, matplotlib_heading, compass_direction = angle_to_compass(turtlebot_heading)
    
    # Initialisiere Richtungsdictionary
    directions = {
        "vor": [],
        "rechts": [],
        "hinter": [],
        "links": []
    }
    
    # Analysiere alle Tische
    for i, table in enumerate(ROOM_LAYOUT["tables"]):
        table_id = f"tisch_{i+1}"
        center = table["center"]
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
        direction = classify_object_direction(relative_angle)
        
        # Berechne Distanz
        distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
        
        obj_info = {
            "id": table_id,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Schränke
    for i, cabinet in enumerate(ROOM_LAYOUT["cabinets"]):
        cabinet_id = f"schrank_{i+1}"
        center = cabinet["center"]
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
        direction = classify_object_direction(relative_angle)
        
        distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
        
        obj_info = {
            "id": cabinet_id,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Regal
    shelf = ROOM_LAYOUT["shelf"]
    center = shelf["center"]
    relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
    direction = classify_object_direction(relative_angle)
    distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
    
    obj_info = {
        "id": "regal",
        "distance_cm": round(distance, 2),
        "relative_angle": round(relative_angle, 1)
    }
    directions[direction].append(obj_info)
    
    # Analysiere Kommode
    dresser = ROOM_LAYOUT["dresser"]
    center = dresser["center"]
    relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
    direction = classify_object_direction(relative_angle)
    distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
    
    obj_info = {
        "id": "kommode",
        "distance_cm": round(distance, 2),
        "relative_angle": round(relative_angle, 1)
    }
    directions[direction].append(obj_info)
    
    # Analysiere Pepper Roboter
    pepper = ROOM_LAYOUT["pepper"]
    center = pepper["center"]
    relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
    direction = classify_object_direction(relative_angle)
    distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
    
    obj_info = {
        "id": "pepper",
        "distance_cm": round(distance, 2),
        "relative_angle": round(relative_angle, 1)
    }
    directions[direction].append(obj_info)
    
    # Analysiere Mülleimer
    trashcan = ROOM_LAYOUT["trashcan"]
    center = trashcan["center"]
    relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
    direction = classify_object_direction(relative_angle)
    distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
    
    obj_info = {
        "id": "muelleimer",
        "distance_cm": round(distance, 2),
        "relative_angle": round(relative_angle, 1)
    }
    directions[direction].append(obj_info)
    
    # Analysiere Kartons
    for i, carton in enumerate(ROOM_LAYOUT["cartons"]):
        carton_id = f"karton_{i+1}"
        center = carton["center"]
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
        direction = classify_object_direction(relative_angle)
        distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
        
        obj_info = {
            "id": carton_id,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Stühle
    for i, chair in enumerate(ROOM_LAYOUT["chairs"]):
        chair_id = f"stuhl_{i+1}"
        center = chair["center"]
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
        direction = classify_object_direction(relative_angle)
        distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
        
        obj_info = {
            "id": chair_id,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Türen
    for i, door in enumerate(ROOM_LAYOUT["doors"]):
        door_id = f"tuer_{i+1}"
        # Berechne Zentrum der Tür aus from/to Koordinaten
        center_x = (door["from"][0] + door["to"][0]) / 2
        center_y = (door["from"][1] + door["to"][1]) / 2
        center = [center_x, center_y]
        
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center_x, center_y)
        direction = classify_object_direction(relative_angle)
        distance = math.sqrt((center_x - turtlebot_x)**2 + (center_y - turtlebot_y)**2)
        
        obj_info = {
            "id": door_id,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Fenster
    for i, window in enumerate(ROOM_LAYOUT["windows"]):
        window_id = f"fenster_{i+1}"
        # Berechne Zentrum des Fensters aus from/to Koordinaten
        center_x = (window["from"][0] + window["to"][0]) / 2
        center_y = (window["from"][1] + window["to"][1]) / 2
        center = [center_x, center_y]
        
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center_x, center_y)
        direction = classify_object_direction(relative_angle)
        distance = math.sqrt((center_x - turtlebot_x)**2 + (center_y - turtlebot_y)**2)
        
        obj_info = {
            "id": window_id,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Whiteboards
    for i, whiteboard in enumerate(ROOM_LAYOUT["whiteboards"]):
        whiteboard_id = f"whiteboard_{i+1}"
        # Berechne Zentrum des Whiteboards aus from/to Koordinaten
        center_x = (whiteboard["from"][0] + whiteboard["to"][0]) / 2
        center_y = (whiteboard["from"][1] + whiteboard["to"][1]) / 2
        center = [center_x, center_y]
        
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center_x, center_y)
        direction = classify_object_direction(relative_angle)
        distance = math.sqrt((center_x - turtlebot_x)**2 + (center_y - turtlebot_y)**2)
        
        obj_info = {
            "id": whiteboard_id,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Wandsegmente
    wall_points = ROOM_LAYOUT["walls"]["points"]
    for i in range(len(wall_points) - 1):
        wall_id = f"wand_{i+1}"
        # Berechne Zentrum des Wandsegments
        from_point = wall_points[i]
        to_point = wall_points[i + 1]
        center_x = (from_point[0] + to_point[0]) / 2
        center_y = (from_point[1] + to_point[1]) / 2
        center = [center_x, center_y]
        
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center_x, center_y)
        direction = classify_object_direction(relative_angle)
        distance = math.sqrt((center_x - turtlebot_x)**2 + (center_y - turtlebot_y)**2)
        
        # Berechne Länge des Wandsegments
        segment_length = math.sqrt((to_point[0] - from_point[0])**2 + (to_point[1] - from_point[1])**2)
        
        obj_info = {
            "id": wall_id,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Sortiere Objekte in jeder Richtung nach Distanz (nächste zuerst)
    for direction in directions:
        directions[direction].sort(key=lambda obj: obj["distance_cm"])
    
    # Erstelle finale JSON-Struktur
    result = {
        "turtlebot": {
            "position": {
                "x": turtlebot_x,
                "y": turtlebot_y
            },
            "orientation": {
                "angle_degrees": turtlebot_heading,
                "compass_direction": compass_direction
            }
        },
        "object_analysis": {
            "description": "Objekte gruppiert nach Richtung relativ zum Turtlebot (90°-Sektoren)",
            "sector_definitions": {
                "vor": "−45° bis +45° relativ zur Turtlebot-Orientierung",
                "links": "+45° bis +135° relativ zur Turtlebot-Orientierung (positive Winkel = links)", 
                "hinter": "+135° bis +180° und −180° bis −135° relativ zur Turtlebot-Orientierung",
                "rechts": "−135° bis −45° relativ zur Turtlebot-Orientierung (negative Winkel = rechts)"
            },
            "directions": directions
        },
        "summary": {
            "total_objects": sum(len(directions[d]) for d in directions),
            "objects_per_direction": {d: len(directions[d]) for d in directions}
        }
    }
    
    return result
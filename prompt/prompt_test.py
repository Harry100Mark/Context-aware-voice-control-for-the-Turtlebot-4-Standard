import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os
import sys
import json
import math
from prompt.draw import angle_to_compass

# =============================================================================
# 1. RAUMKONFIGURATION (JSON-STRUKTUR)
# =============================================================================
# Wandpunkte des Raumes
WALLS = {
    "points": [
        [315, 0],
        [689, 0],
        [689, 654],
        [0, 654],
        [0, 389],
        [-29, 389],
        [-29, 270],
        [0, 270],
        [0, 182],
        [315, 182],
        [315, 0]
    ]
}

# Türen mit Positionen
DOORS = [
    {
        "name": "Tür 1",
        "from": [-29, 275],
        "to": [-29, 384]
    },
    {
        "name": "Tür 2",
        "from": [5, 182],
        "to": [99, 182]
    },
    {
        "name": "Tür 3",
        "from": [189, 182],
        "to": [310, 182]
    }
]

# Fenster mit Positionen
WINDOWS = [
    {
        "name": "Fenster 1",
        "from": [689, 39],
        "to": [689, 123]
    },
    {
        "name": "Fenster 2",
        "from": [689, 162],
        "to": [689, 246]
    },
    {
        "name": "Fenster 3",
        "from": [689, 285],
        "to": [689, 369]
    },
    {
        "name": "Fenster 4",
        "from": [689, 408],
        "to": [689, 492]
    },
    {
        "name": "Fenster 5",
        "from": [689, 531],
        "to": [689, 615]
    }
]

# Whiteboards
WHITEBOARDS = [
    {
        "name": "Whiteboard 1",
        "from": [65, 654],
        "to": [165, 654]
    },
    {
        "name": "Whiteboard 2",
        "from": [210, 654],
        "to": [610, 654]
    }
]

# Tische (rechteckig und rund)
TABLES = [
    {
        "name": "Tisch 1 (PC)",
        "center": [498.5, 186],
        "width": 121,
        "height": 80
    },
    {
        "name": "Tisch 2 (mit Telefon)",
        "center": [624, 186],
        "width": 130,
        "height": 80
    },
    {
        "name": "Tisch 3",
        "center": [643, 286],
        "width": 92,
        "height": 120
    },
    {
        "name": "Tisch 4",
        "center": [643, 406],
        "width": 92,
        "height": 120
    },
    {
        "name": "Tisch 5 (PC)",
        "center": [622.5, 512],
        "width": 133,
        "height": 80
    },
    {
        "name": "Tisch 6",
        "center": [496, 512],
        "width": 120,
        "height": 80
    },
    {
        "name": "Tisch 7 (Kartons)",
        "center": [141, 491],
        "width": 120,
        "height": 80
    },
    {
        "name": "Tisch 8",
        "center": [40, 511.5],
        "width": 81,
        "height": 121
    },
    {
        "name": "Tisch 9",
        "center": [40, 613],
        "width": 80,
        "height": 82
    },
    {
        "name": "Tisch 10 (rund)",
        "center": [338, 354],
        "diameter": 100
    }
]

# Kartons
CARTONS = [
    {
        "name": "Karton 1",
        "center": [577, 368.5],
        "width": 40,
        "height": 45
    },
    {
        "name": "Karton 2",
        "center": [125.5, 436.5],
        "width": 45,
        "height": 29
    },
    {
        "name": "Karton 3",
        "center": [170.5, 436.5],
        "width": 45,
        "height": 29
    }
]

# Schränke
CABINETS = [
    {
        "name": "Schrank 1",
        "center": [522.5, 25.5],
        "width": 333,
        "height": 51
    },
    {
        "name": "Schrank 2",
        "center": [336.5, 139.5],
        "width": 43,
        "height": 85
    }
]

# Regal
SHELF = {
    "name": "Regal",
    "center": [144, 203],
    "width": 80,
    "height": 42
}

# Kommode
DRESSER = {
    "name": "Kommode",
    "center": [190, 632],
    "width": 80,
    "height": 44,
    "description": "mit Telefon"
}

# Pepper Roboter
PEPPER = {
    "name": "Pepper",
    "center": [260, 624],
    "width": 40,
    "height": 40,
    "description": "ist ein Roboter"
}

# Mülleimer
TRASHCAN = {
    "name": "Mülleimer",
    "center": [35, 420],
    "diameter": 30
}

# Stühle mit Positionen und Farben
CHAIRS = [
    {
        "name": "Stuhl 1",
        "center": [338, 294],
        "width": 20,
        "height": 20,
        "color": "blau"
    },
    {
        "name": "Stuhl 2",
        "center": [398, 354],
        "width": 20,
        "height": 20,
        "color": "blau"
    },
    {
        "name": "Stuhl 3",
        "center": [338, 414],
        "width": 20,
        "height": 20,
        "color": "blau"
    },
    {
        "name": "Stuhl 4",
        "center": [278, 354],
        "width": 20,
        "height": 20,
        "color": "blau"
    },
    {
        "name": "Stuhl 5",
        "center": [529, 136],
        "width": 20,
        "height": 20,
        "color": "grau"
    },
    {
        "name": "Stuhl 6",
        "center": [657, 136],
        "width": 20,
        "height": 20,
        "color": "blau"
    },
    {
        "name": "Stuhl 7",
        "center": [587, 256],
        "width": 20,
        "height": 20,
        "color": "schwarz"
    },
    {
        "name": "Stuhl 8",
        "center": [587, 316],
        "width": 20,
        "height": 20,
        "color": "blau"
    },
    {
        "name": "Stuhl 9",
        "center": [587, 436],
        "width": 20,
        "height": 20,
        "color": "grau"
    },
    {
        "name": "Stuhl 10",
        "center": [526, 462],
        "width": 20,
        "height": 20,
        "color": "grau"
    },
    {
        "name": "Stuhl 11",
        "center": [466, 462],
        "width": 20,
        "height": 20,
        "color": "grau"
    },
    {
        "name": "Stuhl 12",
        "center": [466, 562],
        "width": 20,
        "height": 20,
        "color": "blau"
    },
    {
        "name": "Stuhl 13",
        "center": [655, 562],
        "width": 20,
        "height": 20,
        "color": "blau"
    },
    {
        "name": "Stuhl 14",
        "center": [171, 541],
        "width": 20,
        "height": 20,
        "color": "grau"
    },
    {
        "name": "Stuhl 15",
        "center": [111, 541],
        "width": 20,
        "height": 20,
        "color": "schwarz"
    }
]

# Befahrbare Bereiche als Rechtecke (aktualisiert aus draw.py)
NAVIGABLE_AREAS = [
    {
        "bottom_left": [20, 295],
        "width": 250,
        "height": 30,
        "center": [145.0, 310.0]
    },
    {
        "bottom_left": [20, 325],
        "width": 230,
        "height": 45,
        "center": [135.0, 347.5]
    },
    {
        "bottom_left": [25, 205],
        "width": 60,
        "height": 90,
        "center": [55.0, 250.0]
    },
    {
        "bottom_left": [25, 370],
        "width": 225,
        "height": 20,
        "center": [137.5, 380.0]
    },
    {
        "bottom_left": [75, 390],
        "width": 195,
        "height": 15,
        "center": [172.5, 397.5]
    },
    {
        "bottom_left": [75, 405],
        "width": 10,
        "height": 30,
        "center": [80.0, 420.0]
    },
    {
        "bottom_left": [85, 245],
        "width": 335,
        "height": 20,
        "center": [252.5, 255.0]
    },
    {
        "bottom_left": [85, 265],
        "width": 225,
        "height": 20,
        "center": [197.5, 275.0]
    },
    {
        "bottom_left": [85, 285],
        "width": 185,
        "height": 10,
        "center": [177.5, 290.0]
    },
    {
        "bottom_left": [105, 575],
        "width": 335,
        "height": 10,
        "center": [272.5, 580.0]
    },
    {
        "bottom_left": [105, 585],
        "width": 115,
        "height": 5,
        "center": [162.5, 587.5]
    },
    {
        "bottom_left": [105, 590],
        "width": 25,
        "height": 45,
        "center": [117.5, 612.5]
    },
    {
        "bottom_left": [205, 205],
        "width": 215,
        "height": 40,
        "center": [312.5, 225.0]
    },
    {
        "bottom_left": [205, 555],
        "width": 215,
        "height": 20,
        "center": [312.5, 565.0]
    },
    {
        "bottom_left": [215, 405],
        "width": 55,
        "height": 30,
        "center": [242.5, 420.0]
    },
    {
        "bottom_left": [225, 435],
        "width": 85,
        "height": 120,
        "center": [267.5, 495.0]
    },
    {
        "bottom_left": [250, 385],
        "width": 20,
        "height": 5,
        "center": [260.0, 387.5]
    },
    {
        "bottom_left": [270, 425],
        "width": 40,
        "height": 10,
        "center": [290.0, 430.0]
    },
    {
        "bottom_left": [305, 585],
        "width": 135,
        "height": 50,
        "center": [372.5, 610.0]
    },
    {
        "bottom_left": [310, 445],
        "width": 130,
        "height": 10,
        "center": [375.0, 450.0]
    },
    {
        "bottom_left": [310, 455],
        "width": 110,
        "height": 100,
        "center": [365.0, 505.0]
    },
    {
        "bottom_left": [345, 75],
        "width": 325,
        "height": 5,
        "center": [507.5, 77.5]
    },
    {
        "bottom_left": [370, 265],
        "width": 190,
        "height": 20,
        "center": [465.0, 275.0]
    },
    {
        "bottom_left": [370, 425],
        "width": 190,
        "height": 10,
        "center": [465.0, 430.0]
    },
    {
        "bottom_left": [370, 435],
        "width": 70,
        "height": 10,
        "center": [405.0, 440.0]
    },
    {
        "bottom_left": [380, 80],
        "width": 290,
        "height": 30,
        "center": [525.0, 95.0]
    },
    {
        "bottom_left": [380, 110],
        "width": 120,
        "height": 20,
        "center": [440.0, 120.0]
    },
    {
        "bottom_left": [380, 130],
        "width": 40,
        "height": 75,
        "center": [400.0, 167.5]
    },
    {
        "bottom_left": [410, 285],
        "width": 150,
        "height": 40,
        "center": [485.0, 305.0]
    },
    {
        "bottom_left": [410, 385],
        "width": 130,
        "height": 40,
        "center": [475.0, 405.0]
    },
    {
        "bottom_left": [420, 250],
        "width": 140,
        "height": 15,
        "center": [490.0, 257.5]
    },
    {
        "bottom_left": [430, 325],
        "width": 130,
        "height": 5,
        "center": [495.0, 327.5]
    },
    {
        "bottom_left": [430, 330],
        "width": 110,
        "height": 55,
        "center": [485.0, 357.5]
    },
    {
        "bottom_left": [440, 595],
        "width": 230,
        "height": 40,
        "center": [555.0, 615.0]
    },
    {
        "bottom_left": [500, 575],
        "width": 125,
        "height": 20,
        "center": [562.5, 585.0]
    },
    {
        "bottom_left": [540, 415],
        "width": 20,
        "height": 10,
        "center": [550.0, 420.0]
    },
    {
        "bottom_left": [560, 110],
        "width": 70,
        "height": 20,
        "center": [595.0, 120.0]
    }
]

# =============================================================================
# 2. KONVERTIERTE DATENSTRUKTUREN FÜR KOMPATIBILITÄT
# =============================================================================
# Diese Rechtecke definieren ALLE befahrbaren Flächen im Raum (mit 20cm Sicherheitsabstand zu Hindernissen)
# Konvertiert aus dem neuen JSON-Format für Rückwärtskompatibilität
NAVIGABLE_RECTANGLES = []
for i, area in enumerate(NAVIGABLE_AREAS):
    bottom_left = area["bottom_left"]
    width = area["width"]
    height = area["height"]
    center = area["center"]
    NAVIGABLE_RECTANGLES.append({
        "id": f"nav_area_{i+1}",
        "min_x": bottom_left[0],
        "max_x": bottom_left[0] + width,
        "min_y": bottom_left[1],
        "max_y": bottom_left[1] + height,
        "center": tuple(center),
        "description": "Befahrbarer Bereich"
    })

# =============================================================================
# 3. OBJEKTDATENBANK MIT BOUNDING BOXES (konvertiert aus JSON)
# =============================================================================
# Konvertiere alle Objekte aus dem JSON-Format in die ursprüngliche Struktur
OBJECTS = {}
# Tische
for i, table in enumerate(TABLES):
    table_id = f"tisch_{i+1}"
    center = table["center"]
    # Behandle runden Tisch separat
    if "diameter" in table:
        diameter = table["diameter"]
        radius = diameter / 2
        OBJECTS[table_id] = {
            "type": "table",
            "name": table["name"],
            "center": tuple(center),
            "size": (diameter, diameter),
            "bounds": {
                "min_x": center[0] - radius,
                "max_x": center[0] + radius,
                "min_y": center[1] - radius,
                "max_y": center[1] + radius
            },
            "description": f"Runder Tisch mit Durchmesser {diameter}cm"
        }
    else:
        # Rechteckiger Tisch
        width = table["width"]
        height = table["height"]
        OBJECTS[table_id] = {
            "type": "table",
            "name": table["name"],
            "center": tuple(center),
            "size": (width, height),
            "bounds": {
                "min_x": center[0] - width / 2,
                "max_x": center[0] + width / 2,
                "min_y": center[1] - height / 2,
                "max_y": center[1] + height / 2
            },
            "description": f"Rechteckiger Tisch {width}x{height}cm"
        }

# Schränke
for i, cabinet in enumerate(CABINETS):
    cabinet_id = f"schrank_{i+1}"
    center = cabinet["center"]
    width = cabinet["width"]
    height = cabinet["height"]
    OBJECTS[cabinet_id] = {
        "type": "cabinet",
        "name": cabinet["name"],
        "center": tuple(center),
        "size": (width, height),
        "bounds": {
            "min_x": center[0] - width / 2,
            "max_x": center[0] + width / 2,
            "min_y": center[1] - height / 2,
            "max_y": center[1] + height / 2
        },
        "description": f"Schrank {width}x{height}cm"
    }

# Regal
shelf_center = SHELF["center"]
shelf_width = SHELF["width"]
shelf_height = SHELF["height"]
OBJECTS["regal"] = {
    "type": "shelf",
    "name": SHELF["name"],
    "center": tuple(shelf_center),
    "size": (shelf_width, shelf_height),
    "bounds": {
        "min_x": shelf_center[0] - shelf_width / 2,
        "max_x": shelf_center[0] + shelf_width / 2,
        "min_y": shelf_center[1] - shelf_height / 2,
        "max_y": shelf_center[1] + shelf_height / 2
    },
    "description": f"Regal {shelf_width}x{shelf_height}cm"
}

# Kommode
dresser_center = DRESSER["center"]
dresser_width = DRESSER["width"]
dresser_height = DRESSER["height"]
OBJECTS["kommode"] = {
    "type": "dresser",
    "name": f"{DRESSER['name']} ({DRESSER['description']})",
    "center": tuple(dresser_center),
    "size": (dresser_width, dresser_height),
    "bounds": {
        "min_x": dresser_center[0] - dresser_width / 2,
        "max_x": dresser_center[0] + dresser_width / 2,
        "min_y": dresser_center[1] - dresser_height / 2,
        "max_y": dresser_center[1] + dresser_height / 2
    },
    "description": f"Kommode {dresser_width}x{dresser_height}cm {DRESSER['description']}"
}

# Pepper Roboter
pepper_center = PEPPER["center"]
pepper_width = PEPPER["width"]
pepper_height = PEPPER["height"]
OBJECTS["pepper"] = {
    "type": "robot",
    "name": f"{PEPPER['name']} ({PEPPER['description']})",
    "center": tuple(pepper_center),
    "size": (pepper_width, pepper_height),
    "bounds": {
        "min_x": pepper_center[0] - pepper_width / 2,
        "max_x": pepper_center[0] + pepper_width / 2,
        "min_y": pepper_center[1] - pepper_height / 2,
        "max_y": pepper_center[1] + pepper_height / 2
    },
    "description": f"Pepper Roboter {pepper_width}x{pepper_height}cm"
}

# Mülleimer
trash_center = TRASHCAN["center"]
trash_diameter = TRASHCAN["diameter"]
trash_radius = trash_diameter / 2
OBJECTS["muelleimer"] = {
    "type": "bin",
    "name": TRASHCAN["name"],
    "center": tuple(trash_center),
    "size": (trash_diameter, trash_diameter),
    "bounds": {
        "min_x": trash_center[0] - trash_radius,
        "max_x": trash_center[0] + trash_radius,
        "min_y": trash_center[1] - trash_radius,
        "max_y": trash_center[1] + trash_radius
    },
    "description": f"Runder Mülleimer Durchmesser {trash_diameter}cm"
}

# Kartons
for i, carton in enumerate(CARTONS):
    carton_id = f"karton_{i+1}"
    center = carton["center"]
    width = carton["width"]
    height = carton["height"]
    OBJECTS[carton_id] = {
        "type": "box",
        "name": carton["name"],
        "center": tuple(center),
        "size": (width, height),
        "bounds": {
            "min_x": center[0] - width / 2,
            "max_x": center[0] + width / 2,
            "min_y": center[1] - height / 2,
            "max_y": center[1] + height / 2
        },
        "description": f"Karton {width}x{height}cm"
    }

# =============================================================================
# 4. STÜHLE MIT RÄUMLICHER ZUORDNUNG (konvertiert aus JSON)
# =============================================================================
# Konvertiere Stühle aus JSON-Format
CHAIRS_LEGACY = {}
for i, chair in enumerate(CHAIRS):
    chair_id = f"stuhl_{i+1}"
    center = chair["center"]
    color = chair["color"]
    # Versuche Tischzuordnung basierend auf Position zu bestimmen
    table_assignment = "unbekannt"
    # Spezielle Zuordnungen für Stühle um runden Tisch (Tisch 10)
    round_table_center = [338, 354]
    distance_to_round = ((center[0] - round_table_center[0])**2 + (center[1] - round_table_center[1])**2)**0.5
    if distance_to_round < 80:  # Näher als 80cm zum runden Tisch
        table_assignment = "tisch_10"
        if center[1] < round_table_center[1]:
            position = "south"
        elif center[1] > round_table_center[1]:
            position = "north"
        elif center[0] < round_table_center[0]:
            position = "west"
        else:
            position = "east"
    else:
        # Zuordnung zu anderen Tischen basierend auf Nähe
        min_distance = float('inf')
        closest_table = "unbekannt"
        position = "unknown"
        for j, table in enumerate(TABLES):
            if "diameter" in table:  # Skip round table
                continue
            table_center = table["center"]
            distance = ((center[0] - table_center[0])**2 + (center[1] - table_center[1])**2)**0.5
            if distance < min_distance:
                min_distance = distance
                closest_table = f"tisch_{j+1}"
                # Bestimme relative Position
                if center[1] < table_center[1]:
                    position = "south"
                elif center[1] > table_center[1]:
                    position = "north"
                elif center[0] < table_center[0]:
                    position = "west"
                else:
                    position = "east"
        if min_distance < 100:  # Nur wenn näher als 100cm
            table_assignment = closest_table
    CHAIRS_LEGACY[chair_id] = {
        "center": tuple(center),
        "color": color,
        "table": table_assignment,
        "position": position if 'position' in locals() else "unknown"
    }

# =============================================================================
# 5. TÜREN UND DURCHGÄNGE (konvertiert aus JSON)
# =============================================================================
# Konvertiere Türen aus JSON-Format in das ursprüngliche Format
DOORS_LEGACY = {}
for i, door in enumerate(DOORS):
    door_id = f"tuer_{i+1}"
    from_pos = door["from"]
    to_pos = door["to"]
    # Bestimme Orientierung und Position
    if from_pos[0] == to_pos[0]:  # Gleiche x-Koordinate = vertikal
        orientation = "vertical"
        position = (from_pos[0], (from_pos[1] + to_pos[1]) / 2)
        width = abs(to_pos[1] - from_pos[1])
    else:  # Gleiche y-Koordinate = horizontal
        orientation = "horizontal"
        position = ((from_pos[0] + to_pos[0]) / 2, from_pos[1])
        width = abs(to_pos[0] - from_pos[0])
    DOORS_LEGACY[door_id] = {
        "position": position,
        "orientation": orientation,
        "width": width,
        "description": door["name"]
    }

# =============================================================================
# 4. BEFAHRBARKEITS-PRÜFUNG
# =============================================================================
def is_position_navigable(x, y):
    """
    Prüft ob eine Koordinate (x,y) befahrbar ist.
    WICHTIG: Dies ist die zentrale Funktion zur Validierung von Zielkoordinaten!
    Jede Position (x,y) MUSS in einem der NAVIGABLE_AREAS Rechtecke liegen.
    Args:
        x, y: Koordinaten in cm
    Returns:
        bool: True wenn Position befahrbar, False sonst
    """
    # Prüfe direkt gegen die befahrbaren Bereiche aus NAVIGABLE_AREAS
    for i, area in enumerate(NAVIGABLE_AREAS):
        bottom_left = area["bottom_left"]
        width = area["width"]
        height = area["height"]
        
        # Bereich-Grenzen berechnen
        min_x = bottom_left[0]
        max_x = bottom_left[0] + width
        min_y = bottom_left[1]
        max_y = bottom_left[1] + height
        
        # Prüfe ob Punkt innerhalb dieses befahrbaren Rechtecks liegt
        if min_x <= x <= max_x and min_y <= y <= max_y:
            return True
    
    # Punkt liegt in keinem befahrbaren Bereich
    return False

def find_nearest_navigable_area(x, y):
    """
    Findet den nächstgelegenen befahrbaren Bereich für Debug-Zwecke.
    """
    min_distance = float('inf')
    nearest_area = None
    
    for i, area in enumerate(NAVIGABLE_AREAS):
        bottom_left = area["bottom_left"]
        width = area["width"]
        height = area["height"]
        center = area["center"]
        
        # Distanz zum Zentrum berechnen
        distance = ((x - center[0])**2 + (y - center[1])**2)**0.5
        
        if distance < min_distance:
            min_distance = distance
            nearest_area = {
                'index': i+1,
                'bounds': f"x=[{bottom_left[0]}-{bottom_left[0] + width}], y=[{bottom_left[1]}-{bottom_left[1] + height}]",
                'center': center,
                'distance': distance
            }
    return nearest_area

# =============================================================================
# 5. HILFSFUNKTIONEN FÜR INTERAKTIVE ANALYSE
# =============================================================================
def find_clicked_object(x, y):
    """
    Findet das Objekt an den gegebenen Koordinaten.
    Args:
        x, y: Koordinaten in cm
    Returns:
        str: Name des Objekts oder None wenn kein Objekt gefunden
    """
    # Prüfe alle Objekte
    for obj_id, obj_data in OBJECTS.items():
        bounds = obj_data["bounds"]
        if (bounds["min_x"] <= x <= bounds["max_x"] and
            bounds["min_y"] <= y <= bounds["max_y"]):
            return obj_data["name"]
    # Prüfe Stühle (neue JSON-basierte Struktur)
    for chair in CHAIRS:
        chair_x, chair_y = chair["center"]
        chair_color = chair["color"]
        chair_name = chair["name"]
        # Stühle sind 20x20cm groß
        if (chair_x - 10 <= x <= chair_x + 10 and
            chair_y - 10 <= y <= chair_y + 10):
            return f"{chair_name} ({chair_color})"
    return None

def interactive_room_analysis(mode='collect'):
    """
    Öffnet das Raumbild und ermöglicht interaktive Analyse durch Klicken.
    Je nach Modus werden Koordinaten gesammelt oder auf Befahrbarkeit getestet.
    Args:
        mode (str): 'collect' zum Sammeln, 'test' zum Testen.
    """
    # Prüfe ob draw.png existiert
    if not os.path.exists('draw.png'):
        print("Fehler: 'draw.png' nicht gefunden. Bitte zuerst 'draw.py' ausführen.")
        return

    # Lade das Bild ganz normal
    img = mpimg.imread('draw.png')
    
    # Erstelle ein einfaches Fenster - genau wie das originale Bild
    fig, ax = plt.subplots(figsize=(16, 14))
    
    # Zeige das Bild ohne jegliche Veränderung
    ax.imshow(img)
    ax.axis('off')  # Keine Achsen, keine Labels, nichts
    
    # Berechne die Koordinaten-Transformation vom Bild zu den echten Koordinaten
    # Das Bild hat die Dimensionen wie in draw.py: extent=[-80, 750, -60, 743]
    img_height, img_width = img.shape[:2]
    
    def pixel_to_coord(pixel_x, pixel_y):
        """Konvertiert Pixel-Koordinaten zu echten Koordinaten"""
        # Koordinaten-Bereich aus draw.py
        coord_min_x, coord_max_x = -80, 750
        coord_min_y, coord_max_y = -60, 743
        
        # Konvertierung
        real_x = coord_min_x + (pixel_x / img_width) * (coord_max_x - coord_min_x)
        real_y = coord_max_y - (pixel_y / img_height) * (coord_max_y - coord_min_y)
        
        return real_x, real_y

    def on_click(event):
        """Callback-Funktion für Mausklicks auf das Bild."""
        if event.inaxes != ax:
            return
        
        # Konvertiere Pixel-Koordinaten zu echten Koordinaten
        x, y = pixel_to_coord(event.xdata, event.ydata)

        if mode == 'test':
            # Test-Modus: Befahrbarkeit prüfen und ausgeben
            navigable = is_position_navigable(x, y)
            status = "befahrbar" if navigable else "nicht befahrbar"
            
            # Objekt an der geklickten Position finden
            clicked_object = find_clicked_object(x, y)
            object_info = f", Objekt: {clicked_object}" if clicked_object else ", Objekt: keines"
            
            print(f"({int(x)}, {int(y)}): {status}{object_info}")
            
            # Optional: Nächstgelegenen Bereich finden, wenn nicht befahrbar
            if not navigable:
                nearest_area = find_nearest_navigable_area(x, y)
                if nearest_area:
                    print(f"  -> Nächstgelegener Bereich: #{nearest_area['index']} bei ({int(nearest_area['center'][0])}, {int(nearest_area['center'][1])})")

        elif mode == 'collect':
            # Sammel-Modus: Koordinaten runden und speichern
            rounded_x = int(5 * round(x / 5))
            rounded_y = int(5 * round(y / 5))

            # Gerundete Koordinaten im Terminal ausgeben
            print(f"({rounded_x}, {rounded_y})")

            # Gerundete Koordinaten in eine Datei schreiben (im Anfügemodus)
            with open("gefilterte_koordinaten2.txt", "a") as f:
                f.write(f"{rounded_x},{rounded_y}\n")

    # Event-Handler registrieren
    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show()

# =============================================================================
# 6. TURTLEBOT KONFIGURATION UND JSON AUSGABE
# =============================================================================
"""
Funktionen zum Erstellen und Ausgeben von Turtlebot-Konfigurationen als JSON.

Die Turtlebot-Position und -Orientierung werden wie in draw.py behandelt:
- Position: x, y Koordinaten in cm
- Orientierung: Winkel in Grad, wird automatisch zu 8 Himmelsrichtungen quantisiert
- Durchmesser: Physische Größe des Turtlebots (Standard: 30cm wie in draw.py)

Die JSON-Ausgabe enthält:
- Exakte Position und quantisierte Orientierung
- Physische Eigenschaften (Durchmesser, Radius)
- Bounding Box (Grenzen des Roboters)
- Status (ob Position befahrbar ist)
- Bei nicht befahrbaren Positionen: Nächstgelegener befahrbarer Bereich

Verwendung:
1. Über Kommandozeile: python prompt_test.py --turtlebot <x> <y> <alpha> [diameter]
2. Im Python-Code: add_turtlebot(x, y, alpha, diameter)
3. Beispiele anzeigen: python prompt_test.py --example

NEUE OBJEKTANALYSE-FUNKTIONEN:
- analyze_objects_around_turtlebot(): Analysiert alle Objekte relativ zum Turtlebot
- print_objects_around_turtlebot(): Gibt Objektanalyse formatiert aus
- Kommandozeile: python prompt_test.py --objects <x> <y> <alpha>

Die Objektanalyse klassifiziert alle Objekte im Raum in 4 Richtungssektoren:
- vor: −45° bis +45° relativ zur Turtlebot-Orientierung
- links: +45° bis +135° relativ zur Turtlebot-Orientierung (positive Winkel = links)
- hinter: +135° bis +180° und −180° bis −135° relativ zur Turtlebot-Orientierung
- rechts: −135° bis −45° relativ zur Turtlebot-Orientierung (negative Winkel = rechts)
"""

def create_turtlebot_json(x, y, alpha, diameter=30):
    """
    Erstellt eine JSON-Repräsentation des Turtlebots mit Position, Orientierung und Durchmesser.
    
    Args:
        x (float): X-Koordinate in cm
        y (float): Y-Koordinate in cm  
        alpha (float): Orientierung in Grad (wird zu Himmelsrichtung quantisiert)
        diameter (float): Durchmesser des Turtlebots in cm (Standard: 30cm wie in draw.py)
    
    Returns:
        dict: JSON-Struktur mit Turtlebot-Daten
    """
    # Konvertiere Winkel zu Himmelsrichtung (verwendet die gleiche Logik wie draw.py)
    display_heading, matplotlib_heading, compass_direction = angle_to_compass(alpha)
    
    # Prüfe ob Position befahrbar ist
    navigable = is_position_navigable(x, y)
    
    # Erstelle JSON-Struktur
    turtlebot_data = {
        "name": "Turtlebot",
        "type": "robot",
        "position": {
            "x": round(x, 2),
            "y": round(y, 2)
        },
        "orientation": {
            "angle_degrees": round(alpha, 2),
            "display_heading": display_heading,
            "matplotlib_heading": matplotlib_heading,
            "compass_direction": compass_direction
        },
        "physical_properties": {
            "diameter": diameter,
            "radius": diameter / 2
        },
        "bounds": {
            "min_x": round(x - diameter/2, 2),
            "max_x": round(x + diameter/2, 2),
            "min_y": round(y - diameter/2, 2),
            "max_y": round(y + diameter/2, 2)
        },
        "status": {
            "position_navigable": navigable,
            "position_valid": navigable
        }
    }
    
    # Zusätzliche Informationen wenn Position nicht befahrbar
    if not navigable:
        nearest_area = find_nearest_navigable_area(x, y)
        if nearest_area:
            turtlebot_data["status"]["nearest_navigable_area"] = {
                "area_id": nearest_area['index'],
                "center": nearest_area['center'],
                "distance_cm": round(nearest_area['distance'], 2)
            }
    
    return turtlebot_data

def print_turtlebot_json(x, y, alpha, diameter=30):
    """
    Gibt die JSON-Repräsentation des Turtlebots formatiert aus.
    
    Args:
        x (float): X-Koordinate in cm
        y (float): Y-Koordinate in cm  
        alpha (float): Orientierung in Grad
        diameter (float): Durchmesser des Turtlebots in cm (Standard: 30cm)
    """
    turtlebot_json = create_turtlebot_json(x, y, alpha, diameter)
    
    print("="*60)
    print("TURTLEBOT JSON KONFIGURATION")
    print("="*60)
    print(json.dumps(turtlebot_json, indent=2, ensure_ascii=False))
    print("="*60)
    
    return turtlebot_json

def add_turtlebot(x, y, alpha, diameter=30):
    """
    Praktische Hilfsfunktion zum schnellen Hinzufügen eines Turtlebots.
    Gibt sowohl JSON-Daten zurück als auch formatierte Ausgabe.
    
    Args:
        x (float): X-Koordinate in cm
        y (float): Y-Koordinate in cm  
        alpha (float): Orientierung in Grad
        diameter (float): Durchmesser des Turtlebots in cm (Standard: 30cm)
    
    Returns:
        dict: JSON-Struktur des Turtlebots
    
    Beispiel:
        >>> turtlebot = add_turtlebot(500, 390, 180)
        >>> print(f"Turtlebot Orientierung: {turtlebot['orientation']['compass_direction']}")
    """
    return print_turtlebot_json(x, y, alpha, diameter)

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
    for i, table in enumerate(TABLES):
        table_id = f"tisch_{i+1}"
        center = table["center"]
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
        direction = classify_object_direction(relative_angle)
        
        # Berechne Distanz
        distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
        
        obj_info = {
            "id": table_id,
            "name": table["name"],
            "type": "table",
            "center": center,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Schränke
    for i, cabinet in enumerate(CABINETS):
        cabinet_id = f"schrank_{i+1}"
        center = cabinet["center"]
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
        direction = classify_object_direction(relative_angle)
        
        distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
        
        obj_info = {
            "id": cabinet_id,
            "name": cabinet["name"],
            "type": "cabinet",
            "center": center,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Regal
    center = SHELF["center"]
    relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
    direction = classify_object_direction(relative_angle)
    distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
    
    obj_info = {
        "id": "regal",
        "name": SHELF["name"],
        "type": "shelf",
        "center": center,
        "distance_cm": round(distance, 2),
        "relative_angle": round(relative_angle, 1)
    }
    directions[direction].append(obj_info)
    
    # Analysiere Kommode
    center = DRESSER["center"]
    relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
    direction = classify_object_direction(relative_angle)
    distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
    
    obj_info = {
        "id": "kommode",
        "name": f"{DRESSER['name']} ({DRESSER['description']})",
        "type": "dresser",
        "center": center,
        "distance_cm": round(distance, 2),
        "relative_angle": round(relative_angle, 1)
    }
    directions[direction].append(obj_info)
    
    # Analysiere Pepper Roboter
    center = PEPPER["center"]
    relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
    direction = classify_object_direction(relative_angle)
    distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
    
    obj_info = {
        "id": "pepper",
        "name": f"{PEPPER['name']} ({PEPPER['description']})",
        "type": "robot",
        "center": center,
        "distance_cm": round(distance, 2),
        "relative_angle": round(relative_angle, 1)
    }
    directions[direction].append(obj_info)
    
    # Analysiere Mülleimer
    center = TRASHCAN["center"]
    relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
    direction = classify_object_direction(relative_angle)
    distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
    
    obj_info = {
        "id": "muelleimer",
        "name": TRASHCAN["name"],
        "type": "bin",
        "center": center,
        "distance_cm": round(distance, 2),
        "relative_angle": round(relative_angle, 1)
    }
    directions[direction].append(obj_info)
    
    # Analysiere Kartons
    for i, carton in enumerate(CARTONS):
        carton_id = f"karton_{i+1}"
        center = carton["center"]
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
        direction = classify_object_direction(relative_angle)
        distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
        
        obj_info = {
            "id": carton_id,
            "name": carton["name"],
            "type": "box",
            "center": center,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1)
        }
        directions[direction].append(obj_info)
    
    # Analysiere Stühle
    for i, chair in enumerate(CHAIRS):
        chair_id = f"stuhl_{i+1}"
        center = chair["center"]
        relative_angle = calculate_relative_angle(turtlebot_x, turtlebot_y, turtlebot_heading, center[0], center[1])
        direction = classify_object_direction(relative_angle)
        distance = math.sqrt((center[0] - turtlebot_x)**2 + (center[1] - turtlebot_y)**2)
        
        obj_info = {
            "id": chair_id,
            "name": f"{chair['name']} ({chair['color']})",
            "type": "chair",
            "center": center,
            "distance_cm": round(distance, 2),
            "relative_angle": round(relative_angle, 1),
            "color": chair["color"]
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

def print_objects_around_turtlebot(turtlebot_x, turtlebot_y, turtlebot_heading):
    """
    Gibt die Objektanalyse um den Turtlebot formatiert aus.
    
    Args:
        turtlebot_x, turtlebot_y: Position des Turtlebots in cm
        turtlebot_heading: Orientierung des Turtlebots in Grad
    """
    analysis = analyze_objects_around_turtlebot(turtlebot_x, turtlebot_y, turtlebot_heading)
    
    print("="*60)
    print("OBJEKTANALYSE RUND UM DEN TURTLEBOT")
    print("="*60)
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    print("="*60)
    
    return analysis

# =============================================================================
# 7. BEISPIEL TESTS UND HAUPTPROGRAMM
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # Interaktiver Modus zum Sammeln von Koordinaten
        interactive_room_analysis(mode='collect')
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Interaktiver Modus zum Testen der Befahrbarkeit
        interactive_room_analysis(mode='test')
    elif len(sys.argv) > 1 and sys.argv[1] == "--turtlebot":
        # Turtlebot JSON-Ausgabe
        if len(sys.argv) >= 5:
            try:
                x = float(sys.argv[2])
                y = float(sys.argv[3])
                alpha = float(sys.argv[4])
                diameter = float(sys.argv[5]) if len(sys.argv) > 5 else 30.0
                print_turtlebot_json(x, y, alpha, diameter)
            except ValueError:
                print("Fehler: Ungültige Parameter. Verwendung: python prompt_test.py --turtlebot <x> <y> <alpha> [diameter]")
                print("Beispiel: python prompt_test.py --turtlebot 500 390 180 30")
        else:
            print("Verwendung: python prompt_test.py --turtlebot <x> <y> <alpha> [diameter]")
            print("  x, y: Position in cm")
            print("  alpha: Orientierung in Grad (wird zu Himmelsrichtung konvertiert)")
            print("  diameter: Durchmesser in cm (optional, Standard: 30)")
            print("\nBeispiele:")
            print("  python prompt_test.py --turtlebot 500 390 180")
            print("  python prompt_test.py --turtlebot 338 354 90 25")
    elif len(sys.argv) > 1 and sys.argv[1] == "--objects":
        # Objektanalyse um Turtlebot
        if len(sys.argv) >= 5:
            try:
                x = float(sys.argv[2])
                y = float(sys.argv[3])
                alpha = float(sys.argv[4])
                print_objects_around_turtlebot(x, y, alpha)
            except ValueError:
                print("Fehler: Ungültige Parameter. Verwendung: python prompt_test.py --objects <x> <y> <alpha>")
                print("Beispiel: python prompt_test.py --objects 500 390 180")
        else:
            print("Verwendung: python prompt_test.py --objects <x> <y> <alpha>")
            print("  x, y: Position des Turtlebots in cm")
            print("  alpha: Orientierung des Turtlebots in Grad")
            print("\nAnalysiert alle Objekte im Raum relativ zur Turtlebot-Position:")
            print("  vor: −45° bis +45° relativ zur Orientierung")
            print("  links: +45° bis +135° relativ zur Orientierung (positive Winkel = links)")
            print("  hinter: +135° bis +180° und −180° bis −135°")
            print("  rechts: −135° bis −45° relativ zur Orientierung (negative Winkel = rechts)")
            print("\nBeispiele:")
            print("  python prompt_test.py --objects 500 390 180")
            print("  python prompt_test.py --objects 338 354 90")
    elif len(sys.argv) > 1 and sys.argv[1] == "--example":
        # Beispiele für verschiedene Turtlebot-Positionen
        print("BEISPIELE FÜR TURTLEBOT KONFIGURATIONEN:")
        print("\n1. Turtlebot in befahrbarem Bereich, Blickrichtung Westen:")
        add_turtlebot(500, 390, 180)
        
        print("\n2. Turtlebot beim runden Tisch, Blickrichtung Nordost:")
        add_turtlebot(338, 354, 45, 25)
        
        print("\n3. Turtlebot in anderem befahrbaren Bereich, Blickrichtung Norden:")
        add_turtlebot(480, 300, 92)
        
        print("\n4. Verschiedene Orientierungen (alle werden zu Himmelsrichtungen quantisiert):")
        for angle in [0, 45, 90, 135, 180, 225, 270, 315, 360]:
            _, _, compass = angle_to_compass(angle)
            print(f"  {angle}° -> {compass}")
            
        print("\n5. Objektanalyse um den Turtlebot:")
        print("Analysiere Objekte um Turtlebot bei (480, 300) mit Blickrichtung Norden (90°):")
        print_objects_around_turtlebot(480, 300, 90)
    # Im nicht-interaktiven Modus wird nichts ausgeführt.
    else:
        pass
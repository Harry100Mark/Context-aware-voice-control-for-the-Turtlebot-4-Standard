import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import json
import os
import importlib.util

# Import handling für sowohl direktes Ausführen als auch Modul-Import
try:
    from .perspectiveTaker import analyze_objects_around_turtlebot
except ImportError:
    from perspectiveTaker import analyze_objects_around_turtlebot
import shapely.affinity
import json

# Import handling für node_finder
try:
    from .node_finder import find_nearest_navigable_node, add_nearest_node_to_pose
except ImportError:
    from node_finder import find_nearest_navigable_node, add_nearest_node_to_pose

def load_room_layout():
    """Lädt ROOM_LAYOUT aus roomlayout.json"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    roomlayout_json_path = os.path.join(current_dir, 'roomlayout.json')
    
    if os.path.exists(roomlayout_json_path):
        with open(roomlayout_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"roomlayout.json nicht gefunden in {roomlayout_json_path}")

def find_navigable_area_for_point(x, y, room_layout):
    """Findet die navigable_area, in der sich ein Punkt befindet"""
    point = Point(x, y)
    
    # Navigable areas sind unter topology
    topology = room_layout.get("topology", room_layout)
    navigable_areas = topology.get("navigable_areas", [])
    
    matching_areas = []
    
    for area in navigable_areas:
        bottom_left = area["bottom_left"]
        width = area["width"]
        height = area["height"]
        
        # Prüfe ob der Punkt in diesem Bereich liegt
        if (bottom_left[0] <= x <= bottom_left[0] + width and
            bottom_left[1] <= y <= bottom_left[1] + height):
            matching_areas.append(area)
    
    if not matching_areas:
        return None
    
    # Wähle die kleinste Area (spezifischste)
    smallest_area = min(matching_areas, key=lambda a: a["width"] * a["height"])
    return smallest_area

def create_verification_text(x_goal, y_goal, navigable_area):
    """Erstellt den verification Text für einen Zielpunkt"""
    if not navigable_area:
        return {
            "text": f"FEHLER: Punkt ({x_goal}, {y_goal}) liegt in keinem befahrbaren Bereich.",
            "values": {
                "x_goal": x_goal,
                "y_goal": y_goal,
                "error": "No navigable area found"
            }
        }
    
    bottom_left_x = navigable_area["bottom_left"][0]
    bottom_left_y = navigable_area["bottom_left"][1]
    width = navigable_area["width"]
    height = navigable_area["height"]
    x_min = bottom_left_x
    x_max = bottom_left_x + width
    y_min = bottom_left_y
    y_max = bottom_left_y + height
    
    text = (f"Der Punkt ({x_goal}, {y_goal}) liegt im befahrbaren Bereich mit "
            f"bottom_left=[{bottom_left_x}, {bottom_left_y}], width={width}, height={height}, "
            f"da {x_min} <= x = {x_goal} <= {x_max} und {y_min} <= y = {y_goal} <= {y_max}.")
    
    return {
        "text": text,
        "values": {
            "x_goal": x_goal,
            "y_goal": y_goal,
            "bottom_left_x": bottom_left_x,
            "bottom_left_y": bottom_left_y,
            "width": width,
            "height": height,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max
        }
    }

def create_sample_output(sample_def, room_layout):
    """Erstellt EXAMPLE_OUTPUT JSON für ein Sample basierend auf der Definition"""
    
    # Check if this is a multi-action sample (has 'actions' key) or single action
    if "actions" in sample_def:
        # Multi-action sample
        actions_list = []
        
        for action_def in sample_def["actions"]:
            aktion = action_def["aktion"]
            
            if aktion == "Navigieren":
                ziel = action_def["zielposition"]
                navigable_area = find_navigable_area_for_point(ziel["x"], ziel["y"], room_layout)
                verification = create_verification_text(ziel["x"], ziel["y"], navigable_area)
                
                action_entry = {
                    "aktion": "Navigieren",
                    "parameters": {
                        "zielposition": {
                            "x": ziel["x"],
                            "y": ziel["y"],
                            "z": 0
                        }
                    },
                    "units": {
                        "position": "Zentimeter"
                    },
                    "verification": verification
                }
                
            elif aktion == "Richtungsfahrt":
                params = action_def.get("parameters", action_def)
                action_entry = {
                    "aktion": "Richtungsfahrt",
                    "parameters": {
                        "winkel": params["winkel"],
                        "is_clockwise": params["is_clockwise"],
                        "winkelgeschwindigkeit": params["winkelgeschwindigkeit"],
                        "distanz": params["distanz"],
                        "lineargeschwindigkeit": params["lineargeschwindigkeit"],
                        "is_forward": params["is_forward"]
                    },
                    "units": {
                        "winkel": "Grad",
                        "distanz": "Zentimeter",
                        "geschwindigkeiten": "m/s oder Grad/s"
                    }
                }
                
            elif aktion == "Drehen":
                params = action_def.get("parameters", action_def)
                action_entry = {
                    "aktion": "Drehen",
                    "parameters": {
                        "winkel": params["winkel"],
                        "is_clockwise": params["is_clockwise"],
                        "winkelgeschwindigkeit": params["winkelgeschwindigkeit"]
                    },
                    "units": {
                        "winkel": "Grad",
                        "geschwindigkeit": "Grad/Sekunde"
                    }
                }
                
            elif aktion == "Keine":
                action_entry = {
                    "aktion": "Keine",
                    "answer": action_def.get("answer", "")
                }
            
            actions_list.append(action_entry)
        
        return {
            "actions": actions_list,
            "explanation": sample_def.get("explanation", ""),
            "reasoning": sample_def.get("reasoning", sample_def.get("explanation", ""))
        }
    
    else:
        # Single action sample - move explanation/reasoning outside actions array
        aktion = sample_def["aktion"]
        
        if aktion == "Navigieren":
            ziel = sample_def["zielposition"]
            navigable_area = find_navigable_area_for_point(ziel["x"], ziel["y"], room_layout)
            verification = create_verification_text(ziel["x"], ziel["y"], navigable_area)
            
            return {
                "actions": [
                    {
                        "aktion": "Navigieren",
                        "parameters": {
                            "zielposition": {
                                "x": ziel["x"],
                                "y": ziel["y"],
                                "z": 0
                            }
                        },
                        "units": {
                            "position": "Zentimeter"
                        },
                        "verification": verification
                    }
                ],
                "explanation": sample_def.get("explanation", ""),
                "reasoning": sample_def.get("reasoning", sample_def.get("explanation", ""))
            }
        
        elif aktion == "Richtungsfahrt":
            # Check if parameters are in nested dict or directly in sample_def
            params = sample_def.get("parameters", sample_def)
            
            return {
                "actions": [
                    {
                        "aktion": "Richtungsfahrt",
                        "parameters": {
                            "winkel": params["winkel"],
                            "is_clockwise": params["is_clockwise"],
                            "winkelgeschwindigkeit": params["winkelgeschwindigkeit"],
                            "distanz": params["distanz"],
                            "lineargeschwindigkeit": params["lineargeschwindigkeit"],
                            "is_forward": params["is_forward"]
                        },
                        "units": {
                            "winkel": "Grad",
                            "distanz": "Zentimeter",
                            "geschwindigkeiten": "m/s oder Grad/s"
                        }
                    }
                ],
                "explanation": sample_def.get("explanation", ""),
                "reasoning": sample_def.get("reasoning", sample_def.get("explanation", ""))
            }
        
        elif aktion == "Drehen":
            # Check if parameters are in nested dict or directly in sample_def
            params = sample_def.get("parameters", sample_def)
            
            return {
                "actions": [
                    {
                        "aktion": "Drehen",
                        "parameters": {
                            "winkel": params["winkel"],
                            "is_clockwise": params["is_clockwise"],
                            "winkelgeschwindigkeit": params["winkelgeschwindigkeit"]
                        },
                        "units": {
                            "winkel": "Grad",
                            "geschwindigkeit": "Grad/Sekunde"
                        }
                    }
                ],
                "explanation": sample_def.get("explanation", ""),
                "reasoning": sample_def.get("reasoning", sample_def.get("explanation", ""))
            }
        
        elif aktion == "Keine":
            return {
                "actions": [
                    {
                        "aktion": "Keine",
                        "answer": sample_def.get("answer", "")
                    }
                ],
                "explanation": sample_def.get("explanation", ""),
                "reasoning": sample_def.get("reasoning", sample_def.get("explanation", ""))
            }
        
        else:
            raise ValueError(f"Unbekannte Aktion: {aktion}")

def get_compass_direction(angle):
    """Konvertiert einen Winkel in eine Kompassrichtung"""
    # Normalisiere den Winkel auf 0-360
    angle = angle % 360
    
    directions = {
        0: "Osten", 45: "Nordost", 90: "Norden", 135: "Nordwest",
        180: "Westen", 225: "Südwest", 270: "Süden", 315: "Südost"
    }
    
    # Finde die nächste Richtung
    min_diff = float('inf')
    best_direction = "Osten"
    
    for dir_angle, direction in directions.items():
        diff = min(abs(angle - dir_angle), abs(angle - dir_angle + 360), abs(angle - dir_angle - 360))
        if diff < min_diff:
            min_diff = diff
            best_direction = direction
    
    return best_direction

def create_sample_pose(sample_def, room_layout):
    """Erstellt EXAMPLE_POSE JSON für ein Sample"""
    robot_x, robot_y, robot_heading = sample_def["robot_position"]
    
    # Finde die navigable_area für die Roboterposition
    navigable_area = find_navigable_area_for_point(robot_x, robot_y, room_layout)
    
    # Berechne center der navigable_area
    center = None
    if navigable_area:
        bottom_left = navigable_area["bottom_left"]
        width = navigable_area["width"]
        height = navigable_area["height"]
        center = [
            bottom_left[0] + width / 2,
            bottom_left[1] + height / 2
        ]
    
    # Erstelle Basis-Pose
    pose = {
        "name": "Turtlebot",
        "type": "robot",
        "position": {
            "x": float(robot_x),
            "y": float(robot_y)
        },
        "orientation": {
            "angle_degrees": float(robot_heading),
            "display_heading": robot_heading,
            "matplotlib_heading": robot_heading,
            "compass_direction": get_compass_direction(robot_heading)
        },
        "current_navigable_area": navigable_area if navigable_area else None
    }
    
    # Füge Referenz zum nächsten navigable Node hinzu
    pose = add_nearest_node_to_pose(pose, room_layout)
    
    return pose

def generate_samples_json(sample_definitions, room_layout):
    """Generiert die komplette samples.json Struktur"""
    example_prompts = [sample["prompt"] for sample in sample_definitions]
    example_outputs = [create_sample_output(sample, room_layout) for sample in sample_definitions]
    example_poses = [create_sample_pose(sample, room_layout) for sample in sample_definitions]
    
    # Füge old_prompt und old_position hinzu wenn vorhanden
    example_old_prompts = []
    example_old_positions = []
    
    for sample in sample_definitions:
        if "old_prompt" in sample:
            example_old_prompts.append(sample["old_prompt"])
        else:
            example_old_prompts.append(None)
            
        if "old_position" in sample:
            example_old_positions.append(sample["old_position"])
        else:
            example_old_positions.append(None)
    
    return {
        "EXAMPLE_PROMPTS": example_prompts,
        "EXAMPLE_OUTPUTS": example_outputs,
        "EXAMPLE_POSES": example_poses,
        "EXAMPLE_OLD_PROMPTS": example_old_prompts,
        "EXAMPLE_OLD_POSITIONS": example_old_positions
    }

def normalize_angle(angle):
    """Normalisiert einen Winkel auf den Bereich [-180, 180)"""
    while angle >= 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

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

def create_room_plan(robot_x=500, robot_y=390, robot_heading=180, show_fov=True):
    """
    Erstellt einen detaillierten Raumplan basierend auf den neuen Koordinaten.
    Args:
        robot_x, robot_y: Position des Turtlebots in cm
        robot_heading: Blickrichtung in Grad (wird zu Himmelsrichtung quantisiert)
        show_fov: Ob Sichtfeld angezeigt werden soll
    """
    # Roboterrichtung zu Himmelsrichtung konvertieren
    display_heading, matplotlib_heading, compass_direction = angle_to_compass(robot_heading)
    
    fig, ax = plt.subplots(1, 1, figsize=(16, 14))
    # === BEFAHRBARER BEREICH BERECHNEN ===
    safety_margin = 20 # 20cm Sicherheitsabstand
    # Raum-Polygon (innerer Bereich)
    room_points = [(315,0),(689,0),(689,654),(0,654),(0,389),(-29,389),(-29,270),(0,270),(0,182),(315,182)]
    room_polygon = Polygon(room_points)
    # Liste aller Hindernisse (Objekte im Raum)
    obstacles = []
    # Wände als Hindernisse (äußerer Rand)
    wall_buffer = 5 # Zusätzlicher Puffer für Wände
    outer_walls = [
        Polygon([(315-wall_buffer, -wall_buffer), (689+wall_buffer, -wall_buffer),
                 (689+wall_buffer, 0), (315, 0)]), # Südwand
        Polygon([(689, 0), (689+wall_buffer, 0), (689+wall_buffer, 654+wall_buffer),
                 (689, 654)]), # Ostwand
        Polygon([(0, 654), (689, 654), (689, 654+wall_buffer),
                 (0, 654+wall_buffer)]), # Nordwand
        Polygon([(-wall_buffer, 389), (0, 389), (0, 654+wall_buffer),
                 (-wall_buffer, 654+wall_buffer)]), # Westwand oben
        Polygon([(-29-wall_buffer, 270), (-29, 270), (-29, 389),
                 (-29-wall_buffer, 389)]), # Westwand Mitte
        Polygon([(-wall_buffer, 182), (0, 182), (0, 270),
                 (-wall_buffer, 270)]), # Westwand unten
        Polygon([(0, 182-wall_buffer), (315, 182-wall_buffer), (315, 182),
                 (0, 182)]), # Südwand unten
        Polygon([(315, 0), (315+wall_buffer, 0), (315+wall_buffer, 182),
                 (315, 182)]) # Innenwand vertikal bei x=315
    ]
    obstacles.extend(outer_walls)
    # Tische als rechteckige Hindernisse
    tables_rect = {
        'Tisch 1\n(PC)': {'pos': (498.5, 186), 'size': (121, 80)},
        'Tisch 2\n(mit Telefon)': {'pos': (624, 186), 'size': (130, 80)},
        'Tisch 3': {'pos': (643, 286), 'size': (92, 120)},
        'Tisch 4': {'pos': (643, 406), 'size': (92, 120)},
        'Tisch 5\n(PC)': {'pos': (622.5, 512), 'size': (133, 80)},
        'Tisch 6': {'pos': (496, 512), 'size': (120, 80)},
        'Tisch 7\n(Kartons)': {'pos': (141, 491), 'size': (120, 80)},
        'Tisch 8': {'pos': (40, 511.5), 'size': (81, 121)},
        'Tisch 9': {'pos': (40, 613), 'size': (80, 82)},
    }
    for data in tables_rect.values():
        x, y = data['pos']
        w, h = data['size']
        table_poly = Polygon([(x-w/2, y-h/2), (x+w/2, y-h/2),
                              (x+w/2, y+h/2), (x-w/2, y+h/2)])
        obstacles.append(table_poly)
    # Runder Tisch (korrigiert)
    circle_points = []
    for angle in np.linspace(0, 2*np.pi, 32):
        circle_points.append((338 + 50*np.cos(angle), 354 + 50*np.sin(angle)))
    obstacles.append(Polygon(circle_points))
    # Stühle um den runden Tisch (korrigiert - alle 4 Stühle)
    round_table_chairs = [(338, 294), (398, 354), (338, 414), (278, 354)]
    for x, y in round_table_chairs:
        chair_poly = Polygon([(x-10, y-10), (x+10, y-10), (x+10, y+10), (x-10, y+10)])
        obstacles.append(chair_poly)
    # Schränke
    schrank1 = Polygon([(356, 0), (689, 0), (689, 51), (356, 51)])
    schrank2 = Polygon([(315, 97), (358, 97), (358, 182), (315, 182)])
    obstacles.extend([schrank1, schrank2])
    # Regal
    regal = Polygon([(104, 182), (184, 182), (184, 224), (104, 224)])
    obstacles.append(regal)
    # Kommode
    kommode = Polygon([(150, 610), (230, 610), (230, 654), (150, 654)])
    obstacles.append(kommode)
    # Kartons
    kartons_data = [
        {'pos': (577, 368.5), 'size': (40, 45)},
        {'pos': (125.5, 436.5), 'size': (45, 29)},
        {'pos': (170.5, 436.5), 'size': (45, 29)}
    ]
    for karton in kartons_data:
        x, y = karton['pos']
        w, h = karton['size']
        karton_poly = Polygon([(x-w/2, y-h/2), (x+w/2, y-h/2),
                               (x+w/2, y+h/2), (x-w/2, y+h/2)])
        obstacles.append(karton_poly)
    # Pepper Roboter (als Rechteck)
    pepper_poly = Polygon([(260-20, 624-20), (260+20, 624-20), (260+20, 624+20), (260-20, 624+20)])
    obstacles.append(pepper_poly)
    # Mülleimer (als Kreis)
    muelleimer_points = []
    for angle in np.linspace(0, 2*np.pi, 16):
        muelleimer_points.append((35 + 15*np.cos(angle), 420 + 15*np.sin(angle)))
    obstacles.append(Polygon(muelleimer_points))
    # Übrige Stühle (ohne die um den runden Tisch)
    other_chairs = [
        (529, 136), (657, 136), (587, 256), (587, 316), (587, 436),
        (526, 462), (466, 462), (466, 562), (655, 562), (171, 541), (111, 541)
    ]
    for x, y in other_chairs:
        chair_poly = Polygon([(x-10, y-10), (x+10, y-10), (x+10, y+10), (x-10, y+10)])
        obstacles.append(chair_poly)
    # Alle Hindernisse mit Sicherheitsabstand erweitern
    buffered_obstacles = []
    for obstacle in obstacles:
        try:
            buffered = obstacle.buffer(safety_margin)
            if buffered.is_valid:
                buffered_obstacles.append(buffered)
        except:
            continue
    # === ORTHOGONALER BEFAHRBARER BEREICH ===
    # Berechne befahrbaren Bereich mit orthogonalen Bounding Boxes um Objekte
    
    # Für jedes Hindernis erstelle eine orthogonale Bounding Box mit 20cm Puffer
    forbidden_rectangles = []
    
    # Alle buffered obstacles in orthogonale Rechtecke umwandeln
    for buffered_obstacle in buffered_obstacles:
        if hasattr(buffered_obstacle, 'bounds'):
            minx, miny, maxx, maxy = buffered_obstacle.bounds
            forbidden_rectangles.append({
                'x': minx, 'y': miny, 
                'width': maxx - minx, 'height': maxy - miny
            })
    
    # Erstelle ein feines Raster und prüfe für jeden Punkt ob er befahrbar ist
    grid_size = 5  # 5cm Raster für feinere Auflösung
    navigable_grid = {}  # Dictionary für befahrbare Zellen
    
    # Raumgrenzen mit 20cm Puffer
    room_bounds = {
        'min_x': 20, 'max_x': 669,  # 689-20
        'min_y': 20, 'max_y': 634   # 654-20
    }
    
    # Anpassung für spezielle Raumbereiche (L-förmiger Raum)
    for x in range(room_bounds['min_x'], room_bounds['max_x'], grid_size):
        for y in range(room_bounds['min_y'], room_bounds['max_y'], grid_size):
            # Prüfe ob Punkt im gültigen Raumbereich liegt
            point_in_room = False
            
            # Bereich 1: Hauptraum rechts (x >= 315)
            if x >= 335 and y >= 20 and y <= 634:  # 315+20 = 335
                point_in_room = True
            # Bereich 2: Linker oberer Bereich 
            elif x >= 20 and x < 335 and y >= 202 and y <= 634:  # 182+20 = 202
                point_in_room = True
            # Bereich 3: Linker unterer Bereich (Türbereich)
            elif x >= -9 and x < 20 and y >= 290 and y <= 369:  # -29+20=-9, 270+20=290, 389-20=369
                point_in_room = True
            
            if not point_in_room:
                continue
                
            # Prüfe ob Punkt von einem Hindernis blockiert wird
            point_free = True
            
            for forbidden_rect in forbidden_rectangles:
                rect_x = forbidden_rect['x']
                rect_y = forbidden_rect['y'] 
                rect_w = forbidden_rect['width']
                rect_h = forbidden_rect['height']
                
                if (rect_x <= x <= rect_x + rect_w and 
                    rect_y <= y <= rect_y + rect_h):
                    point_free = False
                    break
            
            if point_free:
                grid_x, grid_y = x // grid_size, y // grid_size
                navigable_grid[(grid_x, grid_y)] = (x, y)
    
    # Zusammenfassen von benachbarten Rasterzellen zu größeren Rechtecken
    def merge_rectangles(grid_dict):
        """Führt benachbarte Rasterzellen zu größeren Rechtecken zusammen"""
        merged_rectangles = []
        used_cells = set()
        
        # Sortiere Zellen für systematisches Zusammenfassen
        sorted_cells = sorted(grid_dict.keys())
        
        for start_cell in sorted_cells:
            if start_cell in used_cells:
                continue
                
            start_x, start_y = start_cell
            
            # Finde maximale Breite in dieser Zeile
            max_width = 1
            while (start_x + max_width, start_y) in grid_dict and (start_x + max_width, start_y) not in used_cells:
                max_width += 1
            
            # Finde maximale Höhe für diese Breite
            max_height = 1
            can_extend_height = True
            while can_extend_height:
                # Prüfe ob alle Zellen in der nächsten Zeile verfügbar sind
                for w in range(max_width):
                    if (start_x + w, start_y + max_height) not in grid_dict or (start_x + w, start_y + max_height) in used_cells:
                        can_extend_height = False
                        break
                if can_extend_height:
                    max_height += 1
            
            # Markiere alle verwendeten Zellen
            for w in range(max_width):
                for h in range(max_height):
                    used_cells.add((start_x + w, start_y + h))
            
            # Erstelle Rechteck in echten Koordinaten
            real_x, real_y = grid_dict[start_cell]
            rect_width = max_width * grid_size
            rect_height = max_height * grid_size
            
            merged_rectangles.append({
                'x': real_x, 'y': real_y,
                'width': rect_width, 'height': rect_height
            })
        
        return merged_rectangles
    
    # Führe Zusammenfassung durch
    merged_navigable_areas = merge_rectangles(navigable_grid)

    # print(merged_navigable_areas)  # Auskommentiert für weniger Ausgabe
    
    # Zeichne zusammengefasste befahrbare Bereiche
    label_var = 'Befahrbarer Bereich'
    navigable_patches = []
    
    for i, rect in enumerate(merged_navigable_areas):
        x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
        
        # Rechteck füllen (ohne Rand)
        rect_patch = patches.Rectangle((x, y), w, h, 
                                     facecolor='lightgreen', alpha=0.3,
                                     edgecolor='none',  # Kein einzelner Rand
                                     label=label_var if i == 0 else None)
        ax.add_patch(rect_patch)
        navigable_patches.append(rect_patch)
        
        # Speichere Rechteck-Info für Rand-Berechnung
        rect['patch'] = rect_patch
    
    # Berechne und zeichne nur äußere Ränder der befahrbaren Bereiche
    def draw_outer_edges(rectangles):
        """Zeichnet nur die äußerste Kontur des gesamten befahrbaren Bereichs"""
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        
        # Konvertiere alle Rechtecke zu Shapely Polygonen
        navigable_polygons = []
        for rect in rectangles:
            x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
            poly = Polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
            navigable_polygons.append(poly)
        
        # Vereinige alle Polygone zu einer zusammenhängenden Form
        if navigable_polygons:
            try:
                unified_area = unary_union(navigable_polygons)
                
                # Zeichne nur die äußere Kontur der vereinigten Form
                if hasattr(unified_area, 'geoms'):
                    # MultiPolygon - mehrere getrennte Bereiche
                    for geom in unified_area.geoms:
                        if hasattr(geom, 'exterior') and geom.exterior:
                            x_coords, y_coords = geom.exterior.xy
                            ax.plot(x_coords, y_coords, color='darkgreen', linewidth=2, zorder=10)
                else:
                    # Single Polygon - ein zusammenhängender Bereich
                    if hasattr(unified_area, 'exterior') and unified_area.exterior:
                        x_coords, y_coords = unified_area.exterior.xy
                        ax.plot(x_coords, y_coords, color='darkgreen', linewidth=2, zorder=10)
                        
                        # Zeichne auch innere Löcher (falls vorhanden)
                        for interior in unified_area.interiors:
                            xi, yi = interior.xy
                            ax.plot(xi, yi, color='darkgreen', linewidth=2, zorder=10)
                            
            except Exception as e:
                print(f"Fehler beim Vereinigen der befahrbaren Bereiche: {e}")
                # Fallback: zeichne alle Rechtecke einzeln
                for rect in rectangles:
                    x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
                    ax.plot([x, x+w, x+w, x, x], [y, y, y+h, y+h, y], 
                           color='darkgreen', linewidth=2, zorder=10)
    
    # Zeichne nur die äußeren Ränder
    draw_outer_edges(merged_navigable_areas)
    # === WÄNDE ===
    wall_points = [(315,0),(689,0),(689,654),(0,654),(0,389),(-29,389),(-29,270),(0,270),(0,182),(315,182),(315,0)]
    wall_x = [p[0] for p in wall_points]
    wall_y = [p[1] for p in wall_points]
    ax.plot(wall_x, wall_y, 'k-', linewidth=3, label='Wände')
    # === TÜREN ===
    # Tür 1
    ax.plot([-29, -29], [275, 384], 'brown', linewidth=8, alpha=0.8, label='Türen')
    ax.text(-45, 330, 'Tür 1 (Flur)', fontsize=8, ha='center', va='center', rotation=90,
            bbox=dict(boxstyle="round,pad=0.3", facecolor='wheat', alpha=0.7))
    # Tür 2
    ax.plot([5, 99], [182, 182], 'brown', linewidth=8, alpha=0.8)
    ax.text(52, 170, 'Tür 2 (Server)', fontsize=8, ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='wheat', alpha=0.7))
    # Tür 3
    ax.plot([189, 310], [182, 182], 'brown', linewidth=8, alpha=0.8)
    ax.text(249, 170, 'Tür 3 (Server)', fontsize=8, ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='wheat', alpha=0.7))
    # === FENSTER ===
    windows = [
        (39, 123), (162, 246), (285, 369), (408, 492), (531, 615)
    ]
    for i, (y_start, y_end) in enumerate(windows, 1):
        ax.plot([689, 689], [y_start, y_end], 'lightblue', linewidth=8, alpha=0.7)
        ax.text(705, (y_start + y_end)/2, f'F{i}', fontsize=8, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='lightblue', alpha=0.8))
    # === WHITEBOARDS ===
    # Whiteboard 1
    ax.plot([65, 165], [654, 654], 'white', linewidth=8, alpha=1.0)
    ax.plot([65, 165], [654, 654], 'black', linewidth=2)
    ax.text(115, 642, 'WB 1', fontsize=8, ha='center', va='center')
    # Whiteboard 2
    ax.plot([210, 610], [654, 654], 'white', linewidth=8, alpha=1.0)
    ax.plot([210, 610], [654, 654], 'black', linewidth=2)
    ax.text(410, 642, 'Whiteboard 2', fontsize=8, ha='center', va='center')
    # === TISCHE ===
    for name, data in tables_rect.items():
        x, y = data['pos']
        w, h = data['size']
        rect = patches.Rectangle((x-w/2, y-h/2), w, h,
                                 facecolor='saddlebrown', edgecolor='black', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, y, name, fontsize=7, ha='center', va='center',
                color='white', weight='bold')
    # === RUNDER TISCH ===
    circle = patches.Circle((338, 354), 50, facecolor='saddlebrown',
                            edgecolor='black', linewidth=1.5)
    ax.add_patch(circle)
    ax.text(338, 354, 'Tisch 10\n(rund)', fontsize=8, ha='center', va='center',
            color='white', weight='bold')
    # === SCHRÄNKE ===
    schrank1 = patches.Rectangle((522.5-166.5, 25.5-25.5), 333, 51,
                                 facecolor='darkslategray', edgecolor='black', linewidth=1.5)
    ax.add_patch(schrank1)
    ax.text(522.5, 25.5, 'Schrank 1', fontsize=7, ha='center', va='center', color='white')
    schrank2 = patches.Rectangle((336.5-21.5, 139.5-42.5), 43, 85,
                                 facecolor='darkslategray', edgecolor='black', linewidth=1.5)
    ax.add_patch(schrank2)
    ax.text(336.5, 139.5, 'Schrank\n2', fontsize=7, ha='center', va='center', color='white')
    # === REGAL ===
    regal = patches.Rectangle((144-40, 203-21), 80, 42,
                              facecolor='darkgoldenrod', edgecolor='black', linewidth=1.5)
    ax.add_patch(regal)
    ax.text(144, 203, 'Regal', fontsize=8, ha='center', va='center', color='white')
    # === KOMMODE ===
    kommode = patches.Rectangle((190-40, 632-22), 80, 44,
                                facecolor='darkgoldenrod', edgecolor='black', linewidth=1.5)
    ax.add_patch(kommode)
    ax.text(190, 632, 'Kommode\n(mit Telefon)', fontsize=8, ha='center', va='center', color='white')
    # === KARTONS ===
    kartons = [
        {'pos': (577, 368.5), 'size': (40, 45), 'name': 'K1'},
        {'pos': (125.5, 436.5), 'size': (45, 29), 'name': 'K2'},
        {'pos': (170.5, 436.5), 'size': (45, 29), 'name': 'K3'}
    ]
    for karton in kartons:
        x, y = karton['pos']
        w, h = karton['size']
        rect = patches.Rectangle((x-w/2, y-h/2), w, h,
                                 facecolor='burlywood', edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text(x, y, karton['name'], fontsize=7, ha='center', va='center')
    # === ROBOTER PEPPER ===
    pepper = patches.Rectangle((260-20, 624-20), 40, 40, facecolor='lightcoral',
                               edgecolor='darkred', linewidth=2)
    ax.add_patch(pepper)
    ax.text(260, 624, 'Pepper', fontsize=8, ha='center', va='center',
            color='white', weight='bold')
    # === MÜLLEIMER ===
    muelleimer = patches.Circle((35, 420), 15, facecolor='gray',
                                edgecolor='black', linewidth=1.5)
    ax.add_patch(muelleimer)
    ax.text(35, 420, 'M', fontsize=8, ha='center', va='center',
            color='white', weight='bold')
    # === STÜHLE (mit Farben und Beschriftung) ===
    chairs_detailed = [
        {'pos': (338, 294), 'color': 'blue', 'name': 'S1 (blau)'},
        {'pos': (398, 354), 'color': 'blue', 'name': 'S2 (blau)'},
        {'pos': (338, 414), 'color': 'blue', 'name': 'S3 (blau)'},
        {'pos': (278, 354), 'color': 'blue', 'name': 'S4 (blau)'},
        {'pos': (529, 136), 'color': 'gray', 'name': 'S5 (grau)'},
        {'pos': (657, 136), 'color': 'blue', 'name': 'S6 (blau)'},
        {'pos': (587, 256), 'color': 'black', 'name': 'S7 (schwarz)'},
        {'pos': (587, 316), 'color': 'blue', 'name': 'S8 (blau)'},
        {'pos': (587, 436), 'color': 'gray', 'name': 'S9 (grau)'},
        {'pos': (526, 462), 'color': 'gray', 'name': 'S10 (grau)'},
        {'pos': (466, 462), 'color': 'gray', 'name': 'S11 (grau)'},
        {'pos': (466, 562), 'color': 'blue', 'name': 'S12 (blau)'},
        {'pos': (655, 562), 'color': 'blue', 'name': 'S13 (blau)'},
        {'pos': (171, 541), 'color': 'gray', 'name': 'S14 (grau)'},
        {'pos': (111, 541), 'color': 'black', 'name': 'S15 (schwarz)'},
    ]
    # Farbmapping für bessere Sichtbarkeit
    color_map = {
        'blue': 'royalblue',
        'gray': 'lightgray',
        'black': 'black'
    }
    for chair in chairs_detailed:
        x, y = chair['pos']
        color = color_map.get(chair['color'], chair['color'])
        # Stuhl als Rechteck (20x20cm)
        rect = patches.Rectangle((x-10, y-10), 20, 20, facecolor=color,
                                edgecolor='darkgray', linewidth=1.5)
        ax.add_patch(rect)
        # Beschriftung neben Stuhl (für KI-Interpretation)
        text_color = 'white' if color == 'black' else 'black'
        ax.text(x, y-16, chair['name'], fontsize=6, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
    # === TURTLEBOT (DYNAMISCH) ===
    turtlebot = patches.Circle((robot_x, robot_y), 15, facecolor='darkblue',
                               edgecolor='blue', linewidth=3)
    ax.add_patch(turtlebot)
    ax.text(robot_x, robot_y, 'TB4', fontsize=9, ha='center', va='center',
            color='white', weight='bold')
    # Koordinaten und Himmelsrichtung anzeigen
    heading_rad = np.radians(matplotlib_heading)
    dx_u, dy_u = np.cos(heading_rad), np.sin(heading_rad)
    label_x = robot_x + (40 if dx_u < 0 else 0)  # wenn Pfeil nach links zeigt, Text nach rechts schieben
    label_y = robot_y + 30  # unterhalb des Roboters
    ax.text(
        label_x,
        label_y,
        f'({robot_x},{robot_y})\n{compass_direction}',
        fontsize=9,
        ha='center',
        va='center',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.8),
        zorder=10,
    )
    # === SICHTFELD (FOV) ===
    if show_fov:
        # Sichtfeld Parameter: 90° Öffnungswinkel
        fov_distance = 360 # Reichweite in cm
        fov_angle = 90 # Öffnungswinkel in Grad (reduziert von 100° auf 90°)
        # Berechnung der Sichtfeld-Punkte (mit matplotlib_heading für korrekte Darstellung)
        start_angle = matplotlib_heading - fov_angle/2
        end_angle = matplotlib_heading + fov_angle/2
        # Kegel-Punkte berechnen
        angles = np.linspace(np.radians(start_angle), np.radians(end_angle), 20)
        fov_x = [robot_x] + [robot_x + fov_distance * np.cos(angle) for angle in angles] + [robot_x]
        fov_y = [robot_y] + [robot_y + fov_distance * np.sin(angle) for angle in angles] + [robot_y]
        ax.plot(fov_x, fov_y, color='purple', linestyle='--', alpha=0.6, linewidth=1.5, label='Sichtfeld', zorder=2)
    
    # Blickrichtung-Pfeil (mit matplotlib_heading für korrekte Darstellung)
    # Pfeil startet am Rand des Turtlebot-Kreises (Radius=15), Länge 25% kürzer
    arrow_length = 90 * 0.75  # 25% kürzer
    radius = 15
    angle_rad = np.radians(matplotlib_heading)
    start_x = robot_x + radius * np.cos(angle_rad)
    start_y = robot_y + radius * np.sin(angle_rad)
    dx = arrow_length * np.cos(angle_rad)
    dy = arrow_length * np.sin(angle_rad)
    ax.arrow(start_x, start_y, dx, dy, head_width=12, head_length=8,
         fc='red', ec='red', linewidth=3, zorder=5)
    # === KOORDINATENGITTER ===
    # Hauptgitter alle 60cm
    for x in range(-60, 750, 60):
        ax.axvline(x, color='lightgray', linewidth=0.5, alpha=0.6)
    for y in range(0, 720, 60):
        ax.axhline(y, color='lightgray', linewidth=0.5, alpha=0.6)
    # Koordinatenbeschriftung
    for x in range(0, 720, 120):
        ax.text(x, -25, str(x), fontsize=9, ha='center', va='top', weight='bold')
    for y in range(0, 680, 120):
        ax.text(-25, y, str(y), fontsize=9, ha='right', va='center', weight='bold')
    # === FORMATIERUNG ===
    ax.set_xlim(-80, 750)
    ax.set_ylim(-60, 743) # Genug Platz unten für das X-Label
    ax.set_aspect('equal')
    ax.set_xlabel('x [cm]', fontsize=12, weight='bold')
    ax.set_ylabel('y [cm]', fontsize=12, weight='bold')
    # Titel mit fig.suptitle für bessere Positionierung oberhalb des Grids
    fig.suptitle(f'Raumplan - Turtlebot Position: ({robot_x}, {robot_y}) - Richtung: {compass_direction}',
                 fontsize=14, weight='bold', y=0.98)
    # Erweiterte Legende mit befahrbarem Bereich
    legend_elements = [
        plt.Line2D([0], [0], color='k', linewidth=3, label='Wände'),
        plt.Line2D([0], [0], color='brown', linewidth=4, label='Türen'),
        plt.Line2D([0], [0], color='lightblue', linewidth=4, label='Fenster'),
        patches.Patch(color='lightgreen', alpha=0.3, label='Befahrbarer Bereich (≥20cm Abstand)'),
        patches.Patch(color='saddlebrown', label='Tische'),
        patches.Patch(color='darkslategray', label='Schränke'),
        patches.Patch(color='darkgoldenrod', label='Regal/Kommode'),
        patches.Patch(color='burlywood', label='Kartons'),
        patches.Patch(color='darkblue', label='Turtlebot'),
        patches.Patch(color='lightcoral', label='Pepper (Roboter)'),
        patches.Patch(color='gray', label='Mülleimer'),
        patches.Patch(color='royalblue', label='Stühle (blau)'),
        patches.Patch(color='lightgray', label='Stühle (grau)'),
        patches.Patch(color='black', label='Stühle (schwarz)'),
        plt.Line2D([0], [0], color='purple', linestyle='--', linewidth=1.5, label='Sichtfeld')
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)
        # Ausgabe der Eckpunkte NACH dem Zeichnen (auskommentiert für weniger Ausgabe)
    """
    print("
" + "="*50)
    print("ECKDATEN DER GEZEICHNETEN BEFAHRBAREN BEREICHE")
    print("="*50)
    final_nav_areas = []
    for i, patch in enumerate(navigable_patches):
        bbox = patch.get_bbox()
        corners = {
            'id': i + 1,
            'x': bbox.x0,
            'y': bbox.y0,
            'width': bbox.width,
            'height': bbox.height,
            'corners': [
                (round(bbox.x0, 2), round(bbox.y0, 2)),      # bottom-left
                (round(bbox.x1, 2), round(bbox.y0, 2)),      # bottom-right
                (round(bbox.x1, 2), round(bbox.y1, 2)),      # top-right
                (round(bbox.x0, 2), round(bbox.y1, 2))       # top-left
            ]
        }
        final_nav_areas.append(corners)
        print(f"Bereich #{corners['id']}: x={corners['x']:.2f}, y={corners['y']:.2f}, w={corners['width']:.2f}, h={corners['height']:.2f}")
        print(f"  -> Eckpunkte: {corners['corners']}")
    print("="*50)
    """

    # Anpassung der Margen, um Platz für Labels und Titel zu schaffen
    plt.subplots_adjust(left=0.1, right=0.8, top=0.95, bottom=0.1)
    return fig, ax

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
    
    # Lade ROOM_LAYOUT aus JSON-Datei
    try:
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        roomlayout_json_path = os.path.join(current_dir, 'roomlayout.json')
        
        if os.path.exists(roomlayout_json_path):
            with open(roomlayout_json_path, 'r', encoding='utf-8') as f:
                ROOM_LAYOUT = json.load(f)
        else:
            # Fallback: einfache Dummy-Struktur
            ROOM_LAYOUT = {"navigable_areas": []}
    except Exception as e:
        # Fallback: einfache Dummy-Struktur
        ROOM_LAYOUT = {"navigable_areas": []}
    
    # Finde die aktuelle navigable area, in der sich der Roboter befindet
    current_navigable_area = None
    
    # Navigable areas sind jetzt in der topology gespeichert
    navigable_areas = ROOM_LAYOUT.get("topology", {}).get("navigable_areas", [])
    
    for area in navigable_areas:
        bottom_left = area["bottom_left"]
        width = area["width"]
        height = area["height"]
        
        # Prüfe ob der Roboter innerhalb dieser Area ist
        if (bottom_left[0] <= x <= bottom_left[0] + width and 
            bottom_left[1] <= y <= bottom_left[1] + height):
            current_navigable_area = {
                "bottom_left": bottom_left,
                "width": width,
                "height": height,
                "center": area["center"]
            }
            break
    
    # Erstelle JSON-Struktur (ohne status)
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
        "current_navigable_area": current_navigable_area
    }
    
    # Füge Referenz zum nächsten navigable Node hinzu
    turtlebot_data = add_nearest_node_to_pose(turtlebot_data, ROOM_LAYOUT)
    
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

# === VERWENDUNG ===
if __name__ == "__main__":
    # Erweiterte Sample-Definitionen mit allen benötigten Daten (exakt aus samples.py übernommen)
    sample_definitions = [
        {
            ### Zielnavigation (B)
            # Beispiel 1
            "robot_position": (600, 600, 180),
            "prompt": "Fahre zum Ausgang",
            "aktion": "Navigieren",
            "zielposition": {"x": 25, "y": 330, "z": 0},
            "explanation": "Ich navigiere zur Tür 1, weil sie der einzige Ausgang ist.",
            "reasoning": """Es handelt sich um Befehlskategorie B und I, denn mit Ausgang ist eine Tür gemeint.
            Es gibt 3 Türen im Raum: Tür 1 (Flur), Tür 2 (Server) und Tür 3 (Server).
            Nur Tür 1 führt nach draußen, also ist Tür 1 der Ausgang.
            Auf dem Bild ist westlich von Tür 1 ein hellgrüner Bereich, was bedeutet, dass dort ein befahrbarer Bereich ist.
            Befahrbare Nodes östlich von Tür 1, die mit ihr benachbart sind, bestätigen das. "id_25_300", "id_25_325", "id_25_350", "id_25_250", "id_25_275", "id_25_375"
            Diese Nodes liegen in den navigable_areas mit area_index 0, 1 und 3.
            Tür 1 liegt zwischen (-29, 275) und (-29, 384).
            "id_25_300", "id_25_325", "id_25_350" liegen nah am Zentrum und eher mittig von Tür 1.
            "id_25_325" liegt am mittigsten, da das Zentrum von Tür 1 bei (-29, 329.5) liegt.
            Da "id_25_325" in der navigable_area mit area_index 1 liegt und im topologischem Graphen liegt, ist die Zielkoordinate befahrbar und die beste Wahl.
            """
        },
        {
            # Beispiel 2
            "robot_position": (360, 600, 270),
            "prompt": "Fahr zum Tisch",
            "aktion": "Navigieren",
            "zielposition": {"x": 390, "y": 435, "z": 0},
            "explanation": "Der runde Tisch mit den blauen Stühlen befindet sich in der Nähe vor mir, daher werde ich dort hin fahren.",
            "reasoning": """Es handelt sich um Befehlskategorie B, denn es ist ein Zielobjekt angegeben.
            potenzielle Ziele sind alle Tische (1 bis 10).
            Der Befehl wurde nicht weiter spezifiziert, daher muss erstmal geschaut werden, welche Tische sich vor dem Turtlebot und in seiner Nähe befinden.
            vor dem Turtlebot sind Tisch 1 und Tisch 2 und Tisch 3 und Tisch 10.
            Am nähsten ist Tisch 6.
            Von den Tischen vor dem Turtlebot ist Tisch 10 am nähsten.
            Tisch 10 ist nicht viel weiter weg als Tisch 6 nicht viel mehr als einen Meter.
            Tischt 10 liegt genau in Fahrtrichtung.
            Tisch 6 und Tisch 10 können beide angefahren werden, da sie befahrbare Nodes in ihrer Nähe haben.
            Der Turtlebot liegt nördlich von Tisch 10 und Nordwestlich (etwas mehr westlich) von Tisch 6 mit Fahrtrichtung Süden.
            Die befahrbaren Nodes "id_275_425", "id_400_425" und "Stuhl 3" befinden sich nördlich von Tisch 10. Und nördlich von Stuhl 3 befinden sich die befahrbaren Nodes "id_300_435", "id_325_450", "id_350_450", "id_375_435".
            Tisch 6 hat westlich die befahrbaren Nodes "id_405_555", "id_435_450", "id_405_480", "id_405_495", "id_405_510", "id_405_525", "id_405_540"
            Der Turtlebot ist sehr nah am befahrbaren Nachbarn "id_405_540" von Tisch 6. Da er sich bereits so nah am potenziellen Ziel Tisch 6 befindet, dieser aber nicht wie Tisch 10 direkt vor ihm liegt, ist vermutlich Tisch 10 die bessere Wahl.
            "id_275_425" und "id_400_425" sind näher an Tisch 10 dran.
            "id_400_425" ist näher am Turtlebot dran und befindet sich nördlich vom Tisch 10 genauso wie der Turtlebot sich nördlich vom Tisch 10 befindet.
            "id_390_435" ist ein befahrbarer Node in der navigable_area mit area_index 24.
            Wähle id_390_435 als Zielkoordinate.
            """
        },
        {
            ### Globale Richtungen (C)
            # Beispiel 3
            "robot_position": (500, 355, 180),
            "prompt": "Fahre zum Tisch südlich von dir.",
            "aktion": "Navigieren",
            "zielposition": {"x": 500, "y": 260, "z": 0},
            "explanation": "Südlich in der Nähe von mir befindet sich der Tisch mit Computer, daher werde ich zu ihm fahren.",
            "reasoning": """Der Befehl entspricht Befehlskategorie C und ist mit Befehlskategorie B - einer Zielnavigation - kombiniert.
            Das Ziel ist ein Tisch. Es gibt insgesamt 10 Tische: Tisch 1 bis Tisch 10.
            Es ist ein Tisch gemeint, der sich südlich vom Turtlebot befindet.
            Der Turtlebot schaut in Richtung Westen. Südlich bedeutet links aus der Perspektive des Turtlebots.
            Anhand des Bildes und anhand der JSON der Roboterperspetive lässt sich erkennen, dass Tisch 1 und Tisch 2 sich südlich vom Turtlebot befinden.
            Der Turtlebot befindet sich nördlich von Tisch 1 und Tisch 2.
            potenzielle Ziele sind Tisch 1 und Tisch 2. Es muss weiter analysiert werden, welcher von beiden gemeint ist.
            Der relative Winkel von Tisch 1 liegt bei ca. 90 Grad, während der von Tisch 2 eher bei ca. 120 Grad liegt. Das bedeutet Tisch 1 liegt südlicher als Tisch 2.
            Prüfe, ob Tisch 1 und 2 befahrbar sind. Suche zuerst nach befahrbaren Nodes nördlich von Tisch 1 und Tisch 2, weil sich der Turtlebot nördlich der Tische befindet.
            Die befahrbaren Nodes "id_435_255", "id_450_255", "id_465_255", "id_480_255", "id_495_255", "id_510_255", "id_525_255", "id_540_255" und "id_555_255" sind direkte nördliche Nachbarn von Tisch 1.
            Tisch 2 hat als nördlichen Nachbarn nur "Stuhl 7" als nichtbefahrbaren Node. Stuhl 7 hat nur "id_555_270" und "id_555_285" als befahrbare Nachbar-Nodes im Westen.
            Tisch 1 kann nördlich direkt angefahren werden und befindet sich südlicher als Tisch 2. Die relative Distance in der JSON Roboterperspektive ist auch kleiner zu Tisch 1 als zu Tisch 2.
            Suche nach der passenden befahrbaren Bereichen nördlich von Tisch 1. Die befahrbaren Nachbarn befinden sich alle in der navigable_area mit area_index 30.
            Auch (500, 250) befindet sich in der navigable_area, denn [420,250] <= [500,250] <= [420+140,250+15].
            Aber das befindet sich am Rande des befahrbaren Bereichs. (500, 260) hält mehr Abstand zum Rand und ist befahrbar, denn [420,250] <= [500,260] <= [420+140,250+15], also liegt es auch in der navigable_area mit area_index 30.
            Wähle (500,260) Als Zielkoordinate.
            """
        },
        {
            # Beispiel 4
            "robot_position": (120, 360, 270),
            "prompt": "Fahre einen Meter nach Norden.",
            "aktion": "Richtungsfahrt",
            "winkel": 180,
            "is_clockwise": True,
            "winkelgeschwindigkeit": 40,
            "distanz": 45,
            "lineargeschwindigkeit": 1.5,
            "is_forward": True,
            "explanation": "Weil ein Karton im Weg ist, fahre ich nur 45 Zentimeter nach Norden.",
            "reasoning": """Es handelt sich um Befehlskategorie C.
            Die Richtung - in die der Turtlebot fahren soll - ist Norden.
            Es ist eine genaue Distanz angegeben - nämlich 1 Meter, was 100 Zentimetern entspricht.
            100 Zentimeter nach Norden bedeutet 100 Einheiten entlang der positiven y-Achse.
            Der Turtlebot befindet sich momentan an der Position (120,360). Die Zielkoordinate wäre somit (120,460).
            Schaue nun, ob der Zielort befahrbar ist. Der näcshte befahrbare Node zum Turtlebot ist "id_120_360".
            "id_120_360" hat im Norden den befahrbaren Node "id_120_375" als Nachbarn.
            "id_120_375" hat im Norden den befahrbaren Node "id_120_390" als Nachbarn.
            "id_120_390" hat im Norden den Node "Karton 2" als Nachbarn.
            "id_120_390" liegt in der navigable_area mit area_index 4. (120,405) liegt noch in der navigable_area, denn [75,390] <= [120,405] <= [75+195,390+15].
            Der Turtlebot könnte 45 Zentimeter nach Norden fahren. Muss überprüfen, ob es nördlich von Karton 2 einen befahrbaren Bereich gibt, der ebenfalls in Frage kommt.
            Nördlich von Karton 2 ist Tisch 7 im Bild und ist auch der direkte nördliche Nachbar von Karton 2.
            Nördlich von Tisch 7 ist Stuhl 14 und Stuhl 15. Stuhl 14 ist auch ein direkter Nachbar von Tisch 7.
            Nördlich von Stuhl 14 befinden sich die direkten befahrbaren Nodes "id_135_585", "id_150_585", "id_165_585", "id_180_585" und "id_210_555".
            "id_120_585 existiert ebenfalls und ist der westliche Nachbar von "id_135_585".
            "id_120_585 befindet sich in der navigable_area mit area_index 10.
            Diese hat "bottom_left": [105,590], "width": 25, "height": 45 Was bedeutet, dass (120,590) der südlichste befahrbare Node in der area ist.
            (120,590) liegt 230 Zentimeter weiter nördlich vom Turtlebot.
            (120,405) befindet sich 55 Zentimeter zu weit südlich vom gewünschten Ziel und (120,590) befindet sich 185 Zentimeter zu weit nördlich vom gewünschten Ziel.
            Daher ist (120,590) die bessere Wahl.
            (120,590) ist direkt anfahrbar, denn (120,360)->(120,375)->(120,390)->(120,405) ergeben einen direkten befahrbaren Pfad.
            (120,360 bis 405) liegen in area_index 1 und 3 und 4.
            Daher ist eine Richtungsfahrt die korrekte Aktion.
            Der Turtlebot muss die Orientierung 90 haben, um sich nach Norden zu drehen. Das entspricht einer Drehung von 180 Grad im Uhrzeigersinn.
            Der Turtlebot muss eine Distanz von 45 Zentimetern vorwärts zurücklegen, sobald er sich gedreht hat.
            """
        },
        {
            ### Richtungen relativ zum Roboter (D)
            # Beispiel 5
            "robot_position": (580, 610, 180),
            "prompt": "Fahr um die Ecke.",
            "aktion": "Navigieren",
            "zielposition": {"x": 405, "y": 495, "z": 0},
            "explanation": "Fahre nach links um die Ecke von Tisch 6, da diese in der Nähe und links vor dem Turtlebot liegt.",
            "reasoning": """ Es handelt sich um Befehlskategorie D, denn man fährt entweder links oder rechts um eine Ecke.
            Der Roboter soll 'um die Ecke' fahren, aber es ist nicht angegeben, ob er links oder rechts um die Ecke fahren soll.
            Beide Fälle - 'links um die Ecke' und 'rechts um die Ecke' fahren - müssen betrachtet werden.
            Der Turtlebot schaut nach Westen. Daher bedeutet links Richtung Süden und rechts bedeutet Richtung Norden.
            Gesucht ist eine Ecke in der Nähe oder vor dem Turtlebot, an der er seine Fahrt Richtung Süden oder Norden weiter fortführen kann.
            Vor dem Turtlebot - das heißt westlich in seiner Fahrtrichtung - befinden sich Whiteboard 2, Pepper, Kommode, Tisch 9, Tisch 8, Tisch 7, Tisch 6, Tisch 10, Regal, Karton 1 und Karton 2 und Whiteboard 1. Dort sind auch mehrere Stühle, Mülleimer und weitere Objekte, die aber aufgrund ihrer kleinen größe vermutlich eher nicht umfahren werden sollen. 
            Links bzw. südlich vom Turtlebot befinden sich Tisch 4, Tisch 3, Tisch 2, Tisch 1, Schrank 2, Schrank 1 und auch weitere Stühle und ein Karton.
            rechts bzw. nördlich vom Turtlebot befinden sich eine Objekte. 
            Versuche die Auswahl zu verfeinern, indem nur die Objekte betrachtet werden, die sich in der Nähe des Turtlebots befinden.
            Von den größeren Objekten (Schrank, Tisch, Kartons, Schränke) befindet sich Tisch 5 am nächsten anhand der relativen Distanz zum Turtlebot.
            Als zweitnächstes vor dem Turtlebot befindet sich Tisch 6 vor dem Turtlebot. Als dritt- und viertnächstes Tisch 4 und Whiteboard 2.
            Der Turtlebot ist in Fahrtrichtung Westen. Wenn er seine Fahrtrichtung nach Westen weiter fortführt bevor er am Hindernis vorbei und dann nach Norden oder Süden fährt, dann befindet er sicht westlich vom Hindernis.
            Das relevante Objekt muss westlich befahrbar sein, damit der Turtlebot sich westlich vom Hindernis positionieren kann.
            potenzielle Hindernisse sind Tisch 5, Tisch 6, Whiteboard 2, Tisch 4.
            Tisch 6 befindet sich im Bild westlich von Tisch 5. Tisch 4 befindet sich im Bild südlich von Tisch 5. 
            Tisch 6 hat die westlichen befahrbaren Nachbarn "id_405_555", "id_405_480", "id_405_495", "id_405_510", "id_405_525" und "id_405_540" im topologischen Graphen.
            Tisch 5 hat Tisch 6 als Nachbarn im Westen.
            Tisch 4 hat "Stuhl 9" und "Karton 1" als westliche Nachbarn. 
            Stuhl 9 hat nur "id_555_420" als befahrbaren Nachbarn im Süden.
            Karton 1 hat die befahrbaren Nodes "id_525_390", "id_525_345", "id_525_360", "id_525_375" und "id_555_420" als Nachbarn im Westen.
            Tisch 5 ist im Westen nicht befahrbar, da dort Tisch 6 steht. Das heißt der Turtlebot kann nicht links um die Ecke von Tisch 5 fahren.
            Whiteboard 2 hat nur befahrbare Nodes im Süden als Nachbarn und ansonsten die nördliche Wand. Der Turtlebot kann nicht Richtung Norden um die Ecke von Whiteboard 2 fahren, weil dort eine Wand ist.
            Im Bild und an den Koordinaten von Tisch 6 und Tisch 4 lässt sich erkennen, dass Tisch 4 südöstlich von Tisch 6 liegt.
            Tisch 4 hat Tisch 5 im Norden als Nachbarn und Tisch 5 hat Tisch 6 im Westen als Nachbarn.
            Der Turtlebot kann nicht an Tisch 4 um die Ecke fahren, denn er müsste dafür an Tisch 5 um die Ecke fahren, aber Tisch 6 liegt westlich von Tisch 5.
            Die westlichen Nachbarn "id_405_555", "id_405_480", "id_405_495", "id_405_510", "id_405_525" und "id_405_540" liegen südlich und westlich vom Turtlebot, der sich an der Position (680,610) befindet.
            Tisch 6 hat sein Zentrum bei (496,512). Das bedeutet erst eine Zielkoordinate in der Nähe, die weiter westlich und südlich liegt als das Zentrum bedeutet, dass der Turtlebot tatsächlich um die Ecke gefahren wäre.
            "id_405_480", "id_405_495" und "id_405_510" liegen weiter westlich und südlich vom Zentrum von Tisch 6 und sind in dessen Nähe.
            Alle 3 stellen potenzielle Zielkoordinaten da.
            Wähle (405,495) Als Zielkoordinaten, da sie nicht zu weit südlich vom Zentrum von Tisch 6 sind, aber auch nicht zu weit nördlich.
            (405,495) liegt in der navigable_area mit area_index 20 und ist somit befahrbar. Es handelt sich um eine Navigation.
            """
        },
        {
            # Beispiel 6
            "robot_position": (400, 180, 135),
            "prompt": "Fahr nach links.",
            "aktion": "Navigieren",
            "zielposition": {"x": 260, "y": 220, "z": 0},
            "explanation": "Biege links hinter dem Schrank ab, weil das links zur Fahrtrichtung liegt.",
            "reasoning": """Es handelt sich um Befehlskategorie D, weil links aus der Perspektive des Turtlebots als Fahrtrichtung angegeben ist.
            Der Turtlebot schaut nach Nordwesten. Das bedeutet links ist aus seiner Perspektive Südwesten.
            links - nicht mal einen Meter entfernt vom Turtlebot - befindet sich Schrank 2.
            'Fahr nach links' könnte auch 'biege links ab' bedeuten.
            Weil Schrank 2 westlich vom Turtlebot ist, kann der Turtlebot nur bis zum Schrank fahren, links abbiegen oder südlich fahren.
            Östlich von Schrank 2 befinden sich die befahrbaren Nachbarknoten "id_390_105", "id_390_120", "id_390_135", "id_390_150", "id_390_165" und "id_390_180"
            Nördlich von Schrank 2 befinden sich die befahrbaren Nachbarknoten "id_345_210" und "id_360_210"
            Der Turtlebot befindet sich in der Nähe vom befahrbaren Node id_405_180 und südwestlich davon befindet sich der befahrbare Node id_390_165, dessen westlicher Nachbar Schrank 2 ist, in der navigable_area mit area_index 27.
            Die navigable_area mit area_index 27 hat die Geometrie "bottom_left": [380,130], "width": 40, "height": 75. Das bedeutet der südwestlichste Punkt, an den der Turtlebot nach südwesten fahren könnte wäre (380,160), da er sich 20 Zentimeter südlich und 20 Zentimeter westlich von seiner jetzigen Position befindet und noch in der navigable_area liegt.
            Der Turtlebot könnte auch an die Position (400,130) fahren, was ebenfalls in der navigable_area liegt und weiter südlich vom Turtlebot liegt, wenn er nach Süden fahren würde.
            Wenn aber 'links abbiegen' gemeint war, dann könnte es sein, dass der Turtlebot, der gerade nach Nordwesten schaut, erst nördlich von Schrank 2 und anschließend weiter westlich fahren soll.
            Nördlich von Schrank 2 befanden sich die befahren Nachbarknoten "id_345_210" und "id_360_210"
            Schrank 2 hat sein Zentrum bei (336.5,139.5). Um links abzubiegen, sollte das Ziel also nicht nur nördlich, sondern auch westlich vom Zentrum von Schrank 2 liegen.
            id_345_210 liegt in der navigable_area mit area_index 12 und der Geometrie "bottom_left": [205,205], "width": 215, "height": 40.
            Ein Punkt, der einen Meter westlich von der aktuellen Position des Turtlebots und nördlich von Schrank 2 liegen würde, wäre beispielsweise (300,210) oder auch (300,220)
            Möglicherweise ist dem Bild zufolge Tür 3 oder auch das Regal das eigentlich Ziel. Daher wäre auch der Punt (260,220) ein guter Kanditat.
            Links abbiegen macht mehr Sinn, als näher an den Schrank 2 nach Südwesten zu fahren oder auch Richtig Süden zu fahren.
            Wähle (260,220) Als Zielkoordinate und es handelt sich um eine Navigation.
            Die Zielkoordinate liegt in der navigable_area mit area_index 12 und ist somit befahrbar.
            """
        },
        {
            ### Bereichsangaben und semantische Zonen (E)
            # Beispiel 7
            "robot_position": (440, 300, 45),
            "prompt": "Fahr in die Tischecke.",
            "aktion": "Navigieren",
            "zielposition": {"x": 555, "y": 420, "z": 0},
            "explanation": "Fahre in die Ecke der Tische beim Karton, weil sie in Fahrtrichtung liegt.",
            "reasoning": """Es handelt sich um Kategorie E, weil die Tischecke einen befahrbaren Bereich meint, der durch Tische gebildet wird.
            Vor und in der Nähe des Turtlebots befinden sich der JSON der Roboterperspektive zufolge Tisch 10, Tisch 6, Tisch 5, Tisch 4, Tisch 3, Tisch 2, Tisch 1.
            Eine Tischecke wird dadurch gebildet, dass 2 Tische L-förmig zueinanderstehen, sodass der Turtlebot in diesen Eckbereich fahren kann.
            Tisch 10 ist rund und steht alleine in der Mitte des Raumes, daher kann Tisch 10 keine Ecke zusammen mit anderen Tischen bilden.
            Dem Bild zufolge bilden Tisch 5 und Tisch 4 eine solche L-Form ebenso wie Tisch 2 und Tisch 3 genauso wie Tisch 7 und Tisch 8.
            Die Ecke zwischen Tisch 5 und Tisch 4 ist nach Süden von Tisch 5 und Westen von Tisch 4 hin geöffnet.
            Die Ecke zwischen Tisch 2 und Tisch 3 ist nach Norden von Tisch 2 und Westen von Tisch 3 hin geöffnet.
            Die Ecke zwischen Tisch 7 und Tisch 8 ist nach Norden von Tisch 7 und Osten von Tisch 8 hin geöffnet.
            Tisch 5 und Tisch 4 befinden sich in Fahrtrichtung des Turtlebots, da sie sich laut JSON der Roboterperspetive vor dem Turtlebot befinden.
            Durch die Geometrie von Tisch 5 und Tisch 4 ist die Ecke durch die Punkte (556,472),(597,472),(597,346) beschrieben.
            Gemeint ist der Bereich, der sich etwas südlich von Tisch 5 und westlich von Tisch 4 befindet.
            westlich von Tisch 4 befindet sich Karton 1 im topologischen Graphen.
            Südlich von Tisch 5 befindet sich Tisch 4 im topologischen Graphen.
            Nördlich von Karton 1 befindet sich der befahrbare Knotenpunkt "id_555_420". Dieser befindet sich vom Eckpunkt (597,472) nur 42 Zentimeter in x-Richtung und 52 Zentimeter in y-Richtung entfernt.
            id_555_420 befindet sich in der navigable_area mit area_index 35 mit der Geometrie "bottom_left": [540,415], "width": 20, "height": 10.
            Der Punkt (540,415) befindet sich auch in der navigable_area und ist auch noch in der Tischecke.
            Der Punkt (555.420) erfüllt die Anforderungen aber besser und wird daher gewählt. Es handelt sich um eine Navigation.
            """
        },
        {
            # Beispiel 8
            "robot_position": (420, 620, 0),
            "prompt": "Fahr in die Ecke.",
            "aktion": "Navigieren",
            "zielposition": {"x": 210, "y": 270, "z": 0},
            "explanation": "Fahre in die nordöstliche Ecke des Raumes, da sie vor dem Turtlebot liegt.",
            "reasoning": """Es handelt sich um Befehlskategorie E, weil kein Zielobjekt, sondern ein Bereich angegeben ist.
            Eine Ecke wird durch eine L-förmige Konstellation von Hindernissen gebildet, wobei nicht angegeben ist, um welche Hindernisse es sich handelt.
            Vor dem Turtlebot befindet sich Tisch 5. In der Nähe des Turtlebots befindet sich Tisch 6 und Pepper.
            Der Turtlebot befindet sich nördlich des Raumes und schaut RIchtung Osten.
            Anhand des Bildes lässt sich auch erkennen, dass die Turtlebot auf die nordöstliche Ecke des Raumes zufährt, die durch Wand Nord und Wand Ost gebildet wird und durch die Koordinate (689,654) definiert wird.
            Tisch 5 und Wand Ost bilden ebenso eine Ecke, die durch die Koordinate (689,552) definiert.
            Nördlich von Tisch 5 befinden sich die befahrbaren Nachbarknoten "id_540_585", "id_555_585", "id_570_585", "id_585_585" und "id_600_585".
            Südlich von Whiteboard 2 befinden sich die befahrbaren Nachbarknoten "id_570_630", "id_585_630", "id_600_630", "id_615_630" und "id_630_630" Wenn man nur die östlicheren wählt.
            Wand Nord hat auch befahrbare Nachbarknoten im Süden in der Nähe der Ecke  "id_645_630", "id_660_630", "id_615_630" und "id_630_630"
            Beide Ecken sind befahrbar und liegen dicht beieinander. 
            Die navigable_area mit area_index 33 liegt zugrunde und es sollten Koordinaten östlich in ihr gewählt werden.
            Vermutlich ist die Ecke der Wände gemeint, da sie durch Wände gebildet ist und dadurch größer ist, als die zwischen Tisch und Wand.
            Der Turtlebot könnte sich aber auch mittig von beiden Ecken positionieren, da sie so dich beieinander liegen.
            Wähle eine Koordinate in der Nähe der Ecke der Wände, die aber auch etwas weiter südlich liegt.
            (660,630) oder (660,620) wären gute Kandidaten.
            Wähle (660,625) genau dazwischen. Es handelt sich um eine Navigation und die Zielkoordinate befindet sich in der navigable_area mit area_index 33 
            """
        },
        {
            ### Relative und Relationale Navigation (F)
            # Beispiel 9
            "robot_position": (480, 80, 180),
            "prompt": "Fahr zwischen die Tische hinter dem Tisch rechts von dir.",
            "aktion": "Navigieren",
            "zielposition": {"x": 490, "y": 349, "z": 0},
            "explanation": "Fahre zwischen die 7 Tische und nördlich vom Tisch mit Pc rechts von mir.",
            "reasoning": """Es handelt sich um Befehlskategorie F und D, denn einmal ist die Relation 'hinter dem Tisch' angegeben mit der Richtung 'rechts' relativ zum Turtlebot und einmal ist die Relation 'zwischen die Tische' angegeben.
            Der Turtlebot schaut in die Richtung nach Westen und rechts neben ihm bedeutet nördlich von seiner Position.
            In der JSON der Roboterperspektive befindet sich Tisch 1 am nähsten und rechts mit einem relativen Winkel von ca. 260 Grad, was ziemlich eindeutig auf Tisch 1 bezogen ist.
            Tisch 6 befindet sich auch ziemlich genau rechts vom Turtlebot, aber die relative Distanz ist zu groß im Vergleich.
            Im Bild ist gut zu erkennen, dass Tosch 10, Tisch 6, Tisch 5, Tisch 4, Tisch 3, Tisch 1, Tisch 2 eine Art Kreis bilden.
            Tisch 9, TIsch 8, Tisch 7 bilden dagegen eher eine L-Form, die eine Ecke bilden.
            Zwischen die Tische fahren könnte ich die Ecke fahren oder in den Kreis fahren bedeuten.
            Zwischen die Tisch im Kreis zu fahren ergibt aber mehr Sinn und befindet sich unmittelbar nördlich von Tisch 1.
            An den Koordinatenachsen lässt sich der Punkt (480,360) gut ablesen, der sich in diesem Kreis befindet.
            zwischen die Tische könnte aber auch zwischen Tisch 10 und Tisch 6 bedeuten, da zwischen ihnen im Bild auch ein befahrbarer Bereich zu erkennen ist ebenso wie zwischen Tisch 1 und Tisch 10.
            nördlicher von Tisch 1 ist aber der Mittelpunkt des Kreises, in den der Turtlebot fahren könnte.
            Bezugspunkte sind alle Tische in dieser Kreiskonstellation.
            Der westlichste Tisch in der Konstellation ist Tisch 10 mit Zentrum bei (338,354).
            Am östlichsten in der Konstellation sind Tisch 4 und Tisch 3 mit Zentren bei (643,406) und (643,286).
            Am südlichsten sind Tisch 1 und Tisch 2 mit Zentren bei (498.5,186) und (624,186).
            Am nördlichsten sind Tisch 6 und 5 mit Zentren bei (496,512) und (622.5,512).
            Die mittigste y-Koordinate ist also (512+186)/2=349 und die mittigste x-Koordinate ist (338+643)/2=~490.
            "id_495_345" ist der nächste befahrbare Knoten und deutet auf die navigable_area mit area_index 32 in der Auch (490,349) liegt.
            (495,345), (490,349) und (480,360) sind alles potenzielle Zielkoordinaten, die die Anforderungen erfüllen würden.
            Wähle (490,349) als finale Zielkoordinate, weil sie am mittigsten liegt und befahrbar ist.
            """
        },
        {
            # Beispiel 10
            "robot_position": (330, 480, 315),
            "prompt": "Fahr zur Tür links vom Regal.",
            "aktion": "Navigieren",
            "zielposition": {"x": 250, "y": 210, "z": 0},
            "explanation": "",
            "reasoning": """Es handelt sich um Befehlskategorie B und F, weil ein direktes Ziel 'Tür' und eine Relation 'links vom Regal' angegeben ist.
            Es gibt 3 Türen im Raum und ein Regal.
            Der Turtlebot schaut in Richtung Südosten und das Regal befindet sich rechts von ihm, was Südwestlich bedeutet.
            Wenn sich das Regal südwestlich vom Turtlebot befindet, dann bedeutet 'links' vom Regal, dass die Tür sich Südöstlicher vom Regal befinden soll.
            Laut der JSOSN des Roboterperspektive befindet sich das Regal im "relative_angle": -78.9 und Tür 1 in "relative_angle": -112.3 und Tür 2 in "relative_angle": -88.0 und Tür 3 in "relative_angle": -60.1.
            Das bedeutet Tür 3 befindet sich weiter links, Tür 1 weiter rechts und Tür 2 weiter rechts vom Regal.
            Dementsprechend ist Tür 3 das Ziel. 
            Tür 3 hat die nördlichen befahrbaren Nachbarn "id_210_210", "id_225_210", "id_240_210", "id_255_210", "id_270_210", "id_285_210", "id_300_210", "id_315_210" und "id_330_210"
            Tür 3 hat die Geometrie "from": [189,182], "to": [310,182]. ein befahrbarer Node, der sich mittig der Tür befinden würde wäre also (250,210), der sich in der navigable_area mit area_index 12 befindet.
            Wähle (250,210) und die Aktion ist eine Navigation.
            """
        },
        {
            ### Mehrschrittbefehle und Pfadverfolgung (G)
            # Beispiel 11
            "robot_position": (115, 585, 0),
            "prompt": "Fahr geradeaus, biege dann rechts ab und fahre am neben den runden Tisch.",
            "actions": [
                {
                    "aktion": "Navigieren",
                    "zielposition": {"x": 210, "y": 585, "z": 0}
                },
                {
                    "aktion": "Navigieren", 
                    "zielposition": {"x": 225, "y": 465, "z": 0}
                },
                {
                    "aktion": "Navigieren",
                    "zielposition": {"x": 265, "y": 320, "z": 0}
                }
            ],
            "explanation": "Fahre geradeaus zu Pepper, biege dann hinter dem Tisch mit den Kartons rechts ab und fahre anschließend rechts neben den runden Tisch, weil ich so die Fahrt nach Süden fortführen kann nach dem Abbiegen.",
            "reasoning": """Es handelt sich um Befehlskategorie G, denn es wird ein Pfad beschrieben.
            Zuerst soll geradeaus gefahren werden, was eine Richtung relativ zum Roboter beschreibt und Befehlskategorie D entspricht.
            Danach soll rechts abgebogen werden, was ebenfalls eine Richtung relativ zum Roboter entspricht und damit unter Befehlskategorie D fällt.
            Anschließend soll er neben den runden Tisch fahren, was Befehlskategorie F entspricht, da eine Relation zu einem Objekt angegeben ist - nämlich 'neben'.
            Der Turtlebot befindet sich dem Bild zufolge in der nordwestlichen Ecke des Raumes.
            Er schaut in Richtung Osten, deshalb bedeutet 'geradeaus' aus seiner Perspektive, dass er weiter östlich von seiner Position fahren soll.
            Der JSON der Roboterperspektive zufolge befinden sich vor dem Turtlebot die Kommode und Pepper.
            Der nächste befahrbare Node ist "id_120_585" und der nächste befahrbare Nachbarknoten im Osten dazu ist "id_135_585", der in der navigable_area mit area_index 10 liegt.
            area_index 10 hat die Geometrie "bottom_left": [105,585],"width": 115, "height": 5.
            Das bedeutet der Turtlebot könnte garantiert bis an die Position (220,585) geradeaus fahren, nämlich 105 Zentimeter östlich.
            Der nächste befahrbare Node dort ist "id_210_585" und hat Pepper als nördlichen Nachbarn. Der Turtlebot könnte geradeaus ca. einen Meter nach Osten fahren, um sich südlich von Pepper zu positionieren.
            Der Turtlebot soll anschließend rechts abbiegen, was bedeutet, dass er nach Süden abbiegen soll.
            Der Turtlebot soll an eine Position geradeaus fahren, an der er rechts abbiegen kann.
            rechts, also südlich vom Turtlebot, befindet sich laut JSON der Roboterperspektive Tisch 7, Karton 2, Karton 3 ganz in der Nähe.
            Auch weiter weg und rechts vom Turtlebot also weiter südlich befindet sich der runde Tisch 10, neben dem sich der Turtlebot vermutlich später positionieren sollte.
            Der Turtlebot soll vermutlich geradeus fahren, sodass er im Anschluss bei Tisch 7 nach Süden abbiegen kann, um sich westlich von Tisch 7 zu positionieren.
            Tisch 7 hat Karton 2 und Karton 3 als südliche Nachbarn im topologischen Graphen, daher kann bei ihnen schlecht abgebogen werden.
            Auch rechts vom Turtlebot befindet sich das Regal, aber das ist über 3 Meter entfernt.
            Tisch 7 hat die östlich befahrbaren Nachbarn "id_210_555", "id_225_435", "id_225_450", "id_225_465", "id_225_480", "id_225_495", "id_225_510" und "id_225_525"
            "id_210_555" befindet sich sogar direkt südlich von "id_210_585" 
            Tisch 7 hat das Zentrum bei (141,491). Deshalb liegt "id_225_465" westlich und mittiger bzw. mehr in der Nähe vom Zentrum von Tisch 7 aus gesehen und wäre vermutlich im Anschluss besser, um abzubiegen.
            Der Turtlebot könnte geradeaus zu "id_210_585" fahren und anschließend rechts abbiegen zu "id_225_465".
            Wenn der Turtlebot das tun würde, dann würde er sich an der Position "id_225_465" befinden und nach Süden schauen, da er nach Süden fahren musste. Erst geradeaus und dann südlich.
            Wenn der Turtlebot sich an der Position (225,465) befinden würde und nach Süden schaut, dann wären In seinem Sichtfeld Tisch 10 und Tisch 1.
            Von allen Tischen ist aber Tisch 10 der einzige der rund ist.
            Tisch 10 befindet sich vom Zentrum her bei (338,354). 
            Der Pfad des Turtlebots ist momentan durch (115,585) -> (210,585) -> (225,465) und würde sich somit immer näher an Tisch 10 bewegen, was ein gutes Zeichen ist, dass der Pfad passt.
            Was bedeutet 'neben' dem Tisch 10, wenn sich der Turtlebot an der Position (225,465) befindet und nach Süden schaut?
            Die Position (225,465) befindet sich vom Tisch 10, der sich bei (338,354) befindet, 113 Zentimeter westlich und 111 Zentimeter nördlich von dessen Zentrum.
            Der Turtlebot würde sich an der Position (225,465) nordwestlich von Tisch 10 befinden.
            'neben' den Tisch 10 fahren ist mehrdeutig, denn es ist nicht angegeben, wo sich neben dem Tisch 10 befindet.
            Der Turtlebot befindet sich bei (225,465) nordwestlich von Tisch 10 und schaut Richtung Süden, was bedeutet, dass sich der Tisch 10 südöstlich vom Turtlebot befindet.
            Wenn sich der Tisch 10 südöstlich vom Turtlebot befindet, dann bedeutet 'neben' entweder links neben oder rechts neben, was aus Perspektive des Turtlebots entweder nordöstlich oder südwestlich von Tisch 10 bedeutet.
            Der Turtlebot soll sich nordöstlich oder südwestlich neben Tisch 10 positionieren.
            Da sich der Turtlebot nordwestlich von Tisch 10 befindet, muss er sich nach Süden bewegen, um sich südwestlich von Tisch 10 zu positionieren.
            Da sich der Turtlebot nordwestlich von Tisch 10 befindet, muss er sich nach Osten bewegen, um sich nordöstlich von Tisch 10 zu positionieren.
            Der Turtlebot fährt momentan den Pfad (115,585) -> (210,585) -> (225,465), was bedeutet, dass er nach Osten und anschließend nach Süden fährt.
            Der Turtlebot könnte seine Fahrt nach Süden fortsetzen, um sich südwestlich von Tisch 10 zu positionieren, was sich aus Sicht der Turtlebots rechts neben Tisch 10 befindet.
            Der Turtlebot soll sich südwestlich von Tisch 10 positionieren.
            Tisch 10 hat die südlichen befahrbaren Nachbarknoten "id_285_270" und "id_390_270" und die westlich befahrbaren Nachbarknoten "id_255_300" und "id_255_405".
            Stuhl 4 befindet sich westlich von Tisch 10 und Stuhl 1 befindet sich südlich von Tisch 10.
            Stuhl 4 hat keine  südlichen befahrbaren Nachbarknoten und Stuhl 1 hat keine westlich befahrbaren Nachbarknoten.
            (285,270) befindet sich südwestlich von Tisch 10 genauso wie (255,300).
            "id_285_270 befindet sich in der navigable_area mit area_index 7 und der Geometrie "bottom_left": [85,265],"width": 225,"height": 20
            "id_255_300 befindet sich in der navigable_area mit area_index 0 und der Geometrie "bottom_left": [20,295], "width": 250, "height": 30
            (310,285) und (270,325) befinden sich nordöstlich der beiden navigable areas.
            Wähle (265,320) als potenzielle Zielkoordinate, um Tisch 10 und Stuhl 4 nicht zu nahe zu kommen, aber sich noch südwestlich von Tisch 10 positionieren zu können.
            Die Zielkoordinate ist befahrbar und liegt in der navigable_area mit area_index 0.
            Der Pfad ergibt (115,585) -> (210,585) -> (225,465) -> (265,320).
            Es handelt sich um 3 Aktionen und alle 3 sind Navigationen.
            """
        },
        {
            ### Korrekturbefehle (J)
            # Beispiel 12
            "robot_position": (250, 210, 270),
            "prompt": "Oh, ich meinte das andere links.",
            "aktion": "Navigieren",
            "zielposition": {"x": 52, "y": 210, "z": 0},
            "old_prompt": "Fahr zur Tür links vom Regal.",
            "old_position": (330, 480, 315),
            "old_reasoning": """Es handelt sich um Befehlskategorie B und F, weil ein direktes Ziel 'Tür' und eine Relation 'links vom Regal' angegeben ist.
            Es gibt 3 Türen im Raum und ein Regal.
            Der Turtlebot schaut in Richtung Südosten und das Regal befindet sich rechts von ihm, was Südwestlich bedeutet.
            Wenn sich das Regal südwestlich vom Turtlebot befindet, dann bedeutet 'links' vom Regal, dass die Tür sich Südöstlicher vom Regal befinden soll.
            Laut der JSOSN des Roboterperspektive befindet sich das Regal im "relative_angle": -78.9 und Tür 1 in "relative_angle": -112.3 und Tür 2 in "relative_angle": -88.0 und Tür 3 in "relative_angle": -60.1.
            Das bedeutet Tür 3 befindet sich weiter links, Tür 1 weiter rechts und Tür 2 weiter rechts vom Regal.
            Dementsprechend ist Tür 3 das Ziel. 
            Tür 3 hat die nördlichen befahrbaren Nachbarn "id_210_210", "id_225_210", "id_240_210", "id_255_210", "id_270_210", "id_285_210", "id_300_210", "id_315_210" und "id_330_210"
            Tür 3 hat die Geometrie "from": [189,182], "to": [310,182]. ein befahrbarer Node, der sich mittig der Tür befinden würde wäre also (250,210), der sich in der navigable_area mit area_index 12 befindet.
            Wähle (250,210) und die Aktion ist eine Navigation.
            """,
            "explanation": "Ich werde die letzte Aktion korrigieren und stattdessen zur Tür rechts vom Regal fahren.",
            "reasoning": """Es handelt sich um Befehlskategorie J, denn der Mensch hat etwas anderes gemeint und möchte sich korrigieren.
            Im letzten Befehls sollte der Turtlebot zur Tür links vom Regal fahren.
            Tür 3 war links neben dem Regal und Tür 2 und Tür 1 waren rechts vom Regal.
            Der Turtlebot ist zur Tür 3 gefahren, weil sie links vom Regal ist.
            Der Mensch wollte etwas anderes. 'Oh, ich meinte das andere links.' bedeutet, dass der Mensch sich vertan hat.
            Das andere links bedeutet, dass der Mensch eigentlich rechts sagen wollte statt links.
            Der Mensch wollte eigentlich, dass der Turtlebot rechts neben das Regal fährt und nicht links.
            Das Ziel Tür ist weiterhin richtig, nur die Relation zum Regal muss geändert werden.
            Der Mensch möchte, dass der Turtlebot zur Tür rechts neben dem Regal fährt.
            Rechts neben dem Regal befinden sich Tür 2 und Tür 1.
            Tür 2 ist näher am Regal, weil der relative Winkel bezüglich Tür 2 und Regal ähnlicher war als zwischen Tür 3 und Regal.
            Wähle Tür 2 als neues Ziel.
            Tür 2 hat die nördlichen Nachbarn "id_30_210", "id_45_210", "id_60_210" und "id_75_210".
            Diese befinden sich alle in der navigable_area mit area_index 2.
            Tür 2 hat die Geometrie "from": [5,182], "to": [99,182].
            Die Zielkoordinate (52,210) befindet sich ebenfalls in der navigable_area und ist genau mittig über der Tür 2.
            Wähle (52,210) Als Zielkoordinate. Sie ist befahrbar, denn sie liegt in area_index 2. Die Aktion ist eine Navigation.
            """
        }
    ]
    
    # Lade Room Layout für automatische Berechnungen
    try:
        room_layout = load_room_layout()
        print("Room Layout erfolgreich geladen.")
    except FileNotFoundError as e:
        print(f"Fehler beim Laden des Room Layouts: {e}")
        exit(1)
    
    # Erstelle alle 16 Sample-Bilder und JSON-Dateien
    for i, sample_def in enumerate(sample_definitions, 1):
        robot_x, robot_y, robot_heading = sample_def["robot_position"]
        print(f"Erstelle Sample {i}: Position ({robot_x}, {robot_y}), Richtung {robot_heading}°")
        # Bestimme Aktion-Info für Ausgabe
        if "actions" in sample_def:
            action_info = f"Multi-Action ({len(sample_def['actions'])} Aktionen)"
        else:
            action_info = sample_def['aktion']
        
        print(f"Prompt: '{sample_def['prompt']}', Aktion: {action_info}")
        
        # Turtlebot JSON-Konfiguration ausgeben
        print_turtlebot_json(robot_x, robot_y, robot_heading)
        
        # Perspective Taker Analyse - Objekte relativ zum Turtlebot
        print("\n" + "="*60)
        print(f"PERSPECTIVE TAKER ANALYSE - SAMPLE {i}")
        print("="*60)
        
        try:
            perspective_analysis = analyze_objects_around_turtlebot(robot_x, robot_y, robot_heading)
            
            # Turtlebot Information
            turtlebot_info = perspective_analysis["turtlebot"]
            print(f"Turtlebot Position: ({turtlebot_info['position']['x']}, {turtlebot_info['position']['y']})")
            print(f"Turtlebot Orientierung: {turtlebot_info['orientation']['angle_degrees']}° ({turtlebot_info['orientation']['compass_direction']})")
            print()
            
            # Objekte nach Richtung
            directions = perspective_analysis["object_analysis"]["directions"]
            for direction, objects in directions.items():
                if objects:  # Nur Richtungen mit Objekten anzeigen
                    print(f"=== {direction.upper()} ({len(objects)} Objekt{'e' if len(objects) > 1 else ''}) ===")
                    for obj in objects:
                        print(f"  • ID: {obj['id']}")
                        print(f"    Distanz: {obj['distance_cm']} cm, Winkel: {obj['relative_angle']}°")
                        print()
            
            # Zusammenfassung
            summary = perspective_analysis["summary"]
            print(f"ZUSAMMENFASSUNG SAMPLE {i}:")
            print(f"Gesamt-Objekte: {summary['total_objects']}")
            for direction, count in summary['objects_per_direction'].items():
                if count > 0:
                    print(f"  {direction}: {count} Objekt{'e' if count > 1 else ''}")
            
            # Speichere auch die JSON-Analyse für dieses Sample
            import os
            home_dir = os.path.expanduser('~')
            output_dir = os.path.join(home_dir, 'ros2_ws', 'src', 'prompt', 'prompt', 'fewshots')
            json_filename = os.path.join(output_dir, f'sample{i}_perspective.json')
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(perspective_analysis, f, indent=2, ensure_ascii=False)
            print(f"Perspective Analyse gespeichert: {json_filename}")
            
        except Exception as e:
            print(f"Fehler bei Perspective Taker Analyse für Sample {i}: {e}")
        
        print("="*60)
        
        # Raumplan erstellen
        fig, ax = create_room_plan(robot_x, robot_y, robot_heading, show_fov=True)
        
        # Bild speichern (hochauflösend)
        import os
        home_dir = os.path.expanduser('~')
        output_dir = os.path.join(home_dir, 'ros2_ws', 'src', 'prompt', 'prompt', 'fewshots')
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, f'sample{i}.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()  # Schließe die Figur um Speicher zu sparen
        
        print(f"Sample {i} gespeichert als: {filename}")
        print()  # Leerzeile für bessere Lesbarkeit
    
    # Generiere samples.json mit allen EXAMPLE_PROMPTS, EXAMPLE_OUTPUTS und EXAMPLE_POSES
    print("\n" + "="*60)
    print("GENERIERE SAMPLES.JSON")
    print("="*60)
    
    try:
        samples_data = generate_samples_json(sample_definitions, room_layout)
        
        # Speichere samples.json
        home_dir = os.path.expanduser('~')
        output_dir = os.path.join(home_dir, 'ros2_ws', 'src', 'prompt', 'prompt', 'fewshots')
        samples_json_path = os.path.join(output_dir, 'samples.json')
        
        with open(samples_json_path, 'w', encoding='utf-8') as f:
            json.dump(samples_data, f, indent=2, ensure_ascii=False)
        
        print(f"samples.json erfolgreich erstellt: {samples_json_path}")
        print(f"- {len(samples_data['EXAMPLE_PROMPTS'])} EXAMPLE_PROMPTS")
        print(f"- {len(samples_data['EXAMPLE_OUTPUTS'])} EXAMPLE_OUTPUTS")
        print(f"- {len(samples_data['EXAMPLE_POSES'])} EXAMPLE_POSES")
        
    except Exception as e:
        print(f"Fehler beim Erstellen der samples.json: {e}")
    
    print(f"\nAlle 15 Sample-Bilder und samples.json wurden erfolgreich erstellt!")
    print("Dateien: sample1.png bis sample15.png und samples.json im Verzeichnis ~/ros2_ws/src/prompt/prompt/fewshots/")
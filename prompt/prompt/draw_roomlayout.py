"""
Modul zur Erstellung der roomlayout.json und topologischen Graphen.
Ausgelagert aus draw.py für bessere Codeorganisation.
"""

import json
import os
import math
import numpy as np
from shapely.geometry import Polygon


def write_room_layout_to_json():
    """
    Erstellt das ROOM_LAYOUT Dictionary basierend auf den Raumdaten und schreibt es in die roomlayout.json Datei.
    Die JSON-Datei wird im gleichen Verzeichnis wie dieses Skript erstellt.
    """
    
    # ROOM_LAYOUT Dictionary basierend auf den vorhandenen Raumdaten erstellen
    ROOM_LAYOUT = {
        "walls": {
            "points": [
                [315, 0], [689, 0], [689, 654], [0, 654], [0, 389],
                [-29, 389], [-29, 270], [0, 270], [0, 182], [315, 182], [315, 0]
            ]
        },
        "doors": [
            {
                "name": "Tür 1 (Flur)",
                "from": [-29, 275],
                "to": [-29, 384]
            },
            {
                "name": "Tür 2 (Serverraum)", 
                "from": [5, 182],
                "to": [99, 182]
            },
            {
                "name": "Tür 3 (Serverraum)",
                "from": [189, 182],
                "to": [310, 182]
            }
        ],
        "windows": [
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
        ],
        "whiteboards": [
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
        # HINWEIS: navigable_areas werden jetzt direkt in der topology gespeichert
    }
    
    # Zusätzlich erstellen wir hier die Objekt-Daten für den topologischen Graphen
    # Diese werden später nur in der Topologie gespeichert, nicht in der Hauptstruktur
    OBJECTS_FOR_TOPOLOGY = {
        "tables": [
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
        ],
        "cartons": [
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
        ],
        "cabinets": [
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
        ],
        "shelf": {
            "name": "Regal",
            "center": [144, 203],
            "width": 80,
            "height": 42
        },
        "dresser": {
            "name": "Kommode",
            "center": [190, 632],
            "width": 80,
            "height": 44,
            "description": "mit Telefon"
        },
        "pepper": {
            "name": "Pepper",
            "center": [260, 624],
            "width": 40,
            "height": 40,
            "description": "ist ein Roboter"
        },
        "trashcan": {
            "name": "Mülleimer",
            "center": [35, 420],
            "diameter": 30
        },
        "chairs": [
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
    }
    
    # Aktuelles Verzeichnis der draw_roomlayout.py Datei
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'roomlayout.json')
    
    # Füge ALLE Objekte aus OBJECTS_FOR_TOPOLOGY zu ROOM_LAYOUT hinzu
    ROOM_LAYOUT["tables"] = OBJECTS_FOR_TOPOLOGY["tables"]
    ROOM_LAYOUT["cabinets"] = OBJECTS_FOR_TOPOLOGY["cabinets"] 
    ROOM_LAYOUT["shelf"] = OBJECTS_FOR_TOPOLOGY["shelf"]
    ROOM_LAYOUT["cartons"] = OBJECTS_FOR_TOPOLOGY["cartons"]
    ROOM_LAYOUT["dresser"] = OBJECTS_FOR_TOPOLOGY["dresser"]
    ROOM_LAYOUT["pepper"] = OBJECTS_FOR_TOPOLOGY["pepper"] 
    ROOM_LAYOUT["trashcan"] = OBJECTS_FOR_TOPOLOGY["trashcan"]
    ROOM_LAYOUT["chairs"] = OBJECTS_FOR_TOPOLOGY["chairs"]
    
    try:
        # ROOM_LAYOUT in JSON-Format schreiben
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ROOM_LAYOUT, f, indent=4, ensure_ascii=False)
        
        print(f"✅ ROOM_LAYOUT erfolgreich geschrieben nach: {json_path}")
        return True, ROOM_LAYOUT, OBJECTS_FOR_TOPOLOGY
        
    except Exception as e:
        print(f"❌ Fehler beim Schreiben der roomlayout.json: {e}")
        return False, None, None


def create_topological_graph(ROOM_LAYOUT, OBJECTS_FOR_TOPOLOGY, navigable_areas):
    """
    Erstellt einen topologischen Graphen basierend auf dem ROOM_LAYOUT und den navigable_areas.
    
    Args:
        ROOM_LAYOUT: Das ROOM_LAYOUT Dictionary
        OBJECTS_FOR_TOPOLOGY: Dictionary mit allen Objektdaten für die Topologie
        navigable_areas: Liste der befahrbaren Bereiche
    
    Returns:
        dict: Topologischer Graph mit Nodes, navigable_areas und deren Nachbarn
    """
    # Konvertiere navigable_areas für die Topologie mit area_index
    formatted_nav_areas = []
    for area_idx, area in enumerate(navigable_areas):
        if 'x' in area and 'y' in area:
            x, y, w, h = area['x'], area['y'], area['width'], area['height']
        else:
            x, y = area['bottom_left']
            w, h = area['width'], area['height']
        
        center_x = x + w/2
        center_y = y + h/2
        
        formatted_nav_areas.append({
            "area_index": area_idx,
            "bottom_left": [x, y],
            "width": w,
            "height": h,
            "center": [center_x, center_y]
        })
    
    topology = {
        "navigable_areas": formatted_nav_areas,
        "nodes": {}
    }
    
    # === 1. NAVIGABLE NODES ERSTELLEN (25cm Raster) ===
    grid_step = 25  # 25cm Abstände zwischen Nodes
    
    # Erstelle Nodes für jeden befahrbaren Bereich
    for area_idx, area in enumerate(formatted_nav_areas):
        # Nutze die bereits formatierten navigable_areas aus der topology
        x_start = area['bottom_left'][0]
        y_start = area['bottom_left'][1]
        width = area['width']
        height = area['height']
        
        # Finde den nächsten Vielfachen von 25 für start-Koordinaten
        x_start_aligned = ((int(x_start) + 24) // 25) * 25  # Aufrunden auf nächstes Vielfaches von 25
        y_start_aligned = ((int(y_start) + 24) // 25) * 25  # Aufrunden auf nächstes Vielfaches von 25
        
        # Erstelle 25cm Raster innerhalb des befahrbaren Bereichs
        # Stelle sicher, dass alle Koordinaten Vielfache von 25 sind
        for x in range(x_start_aligned, int(x_start + width), grid_step):
            for y in range(y_start_aligned, int(y_start + height), grid_step):
                # Doppelt prüfen, dass x und y Vielfache von 25 sind
                if x % 25 == 0 and y % 25 == 0:
                    node_id = f"id_{x}_{y}"
                    
                    topology["nodes"][node_id] = {
                        "id": node_id,
                        "x": x,
                        "y": y,
                        "type": "navigable",
                        "navigable_area": {
                            "bottom_left": [x_start, y_start],
                            "width": width,
                            "height": height,
                            "area_index": area_idx
                        },
                        "neighbours": {
                            "north": None,
                            "south": None,
                            "east": None,
                            "west": None
                        }
                    }
    
    # === 2. HINDERNIS-NODES ERSTELLEN ===
    
    # Wände als Nodes hinzufügen
    wall_segments = [
        {"name": "Wand Süd", "from": [315, 0], "to": [689, 0]},
        {"name": "Wand Ost", "from": [689, 0], "to": [689, 654]},
        {"name": "Wand Nord", "from": [689, 654], "to": [0, 654]},
        {"name": "Wand West Oben", "from": [0, 654], "to": [0, 389]},
        {"name": "Wand West Eingang", "from": [0, 389], "to": [-29, 389]},
        {"name": "Wand Flur", "from": [-29, 389], "to": [-29, 270]},
        {"name": "Wand West Unten", "from": [-29, 270], "to": [0, 270]},
        {"name": "Wand Innen", "from": [0, 270], "to": [0, 182]},
        {"name": "Wand Süd Innen", "from": [0, 182], "to": [315, 182]},
        {"name": "Wand Vertikal", "from": [315, 182], "to": [315, 0]}
    ]
    
    for wall in wall_segments:
        node_id = wall["name"]
        # Berechne Mittelpunkt des Wandsegments
        x1, y1 = wall["from"]
        x2, y2 = wall["to"]
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        topology["nodes"][node_id] = {
            "id": node_id,
            "x": center_x,
            "y": center_y,
            "type": "obstacle",
            "obstacle_type": "wall",
            "from": wall["from"],
            "to": wall["to"],
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
    
    # Türen als Nodes hinzufügen
    for door in ROOM_LAYOUT["doors"]:
        node_id = door["name"]
        # Berechne Mittelpunkt der Tür
        x1, y1 = door["from"]
        x2, y2 = door["to"]
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        topology["nodes"][node_id] = {
            "id": node_id,
            "x": center_x,
            "y": center_y,
            "type": "obstacle",
            "obstacle_type": "door",
            "from": door["from"],
            "to": door["to"],
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
    
    # Fenster als Nodes hinzufügen
    for window in ROOM_LAYOUT["windows"]:
        node_id = window["name"]
        # Berechne Mittelpunkt des Fensters
        x1, y1 = window["from"]
        x2, y2 = window["to"]
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        topology["nodes"][node_id] = {
            "id": node_id,
            "x": center_x,
            "y": center_y,
            "type": "obstacle",
            "obstacle_type": "window",
            "from": window["from"],
            "to": window["to"],
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
    
    # Whiteboards als Nodes hinzufügen
    for whiteboard in ROOM_LAYOUT["whiteboards"]:
        node_id = whiteboard["name"]
        # Berechne Mittelpunkt des Whiteboards
        x1, y1 = whiteboard["from"]
        x2, y2 = whiteboard["to"]
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        topology["nodes"][node_id] = {
            "id": node_id,
            "x": center_x,
            "y": center_y,
            "type": "obstacle",
            "obstacle_type": "whiteboard",
            "from": whiteboard["from"],
            "to": whiteboard["to"],
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
    
    # Tische
    for table in OBJECTS_FOR_TOPOLOGY["tables"]:
        node_id = table["name"]
        center = table["center"]
        
        table_node = {
            "id": node_id,
            "x": center[0],
            "y": center[1],
            "type": "obstacle",
            "obstacle_type": "table",
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        # Füge alle zusätzlichen Eigenschaften hinzu
        for key, value in table.items():
            if key not in ["name", "center"]:
                table_node[key] = value
        
        topology["nodes"][node_id] = table_node
    
    # Schränke  
    for cabinet in OBJECTS_FOR_TOPOLOGY["cabinets"]:
        node_id = cabinet["name"]
        center = cabinet["center"]
        
        cabinet_node = {
            "id": node_id,
            "x": center[0],
            "y": center[1],
            "type": "obstacle",
            "obstacle_type": "cabinet",
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        # Füge alle zusätzlichen Eigenschaften hinzu
        for key, value in cabinet.items():
            if key not in ["name", "center"]:
                cabinet_node[key] = value
        
        topology["nodes"][node_id] = cabinet_node
    
    # Regal
    if "shelf" in OBJECTS_FOR_TOPOLOGY:
        shelf = OBJECTS_FOR_TOPOLOGY["shelf"]
        node_id = shelf["name"]
        center = shelf["center"]
        
        shelf_node = {
            "id": node_id,
            "x": center[0],
            "y": center[1],
            "type": "obstacle",
            "obstacle_type": "shelf",
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        # Füge alle zusätzlichen Eigenschaften hinzu
        for key, value in shelf.items():
            if key not in ["name", "center"]:
                shelf_node[key] = value
        
        topology["nodes"][node_id] = shelf_node
    
    # Kommode
    if "dresser" in OBJECTS_FOR_TOPOLOGY:
        dresser = OBJECTS_FOR_TOPOLOGY["dresser"]
        node_id = dresser["name"]
        center = dresser["center"]
        
        dresser_node = {
            "id": node_id,
            "x": center[0],
            "y": center[1],
            "type": "obstacle",
            "obstacle_type": "dresser",
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        # Füge alle zusätzlichen Eigenschaften hinzu
        for key, value in dresser.items():
            if key not in ["name", "center"]:
                dresser_node[key] = value
        
        topology["nodes"][node_id] = dresser_node
    
    # Pepper
    if "pepper" in OBJECTS_FOR_TOPOLOGY:
        pepper = OBJECTS_FOR_TOPOLOGY["pepper"]
        node_id = pepper["name"]
        center = pepper["center"]
        
        pepper_node = {
            "id": node_id,
            "x": center[0],
            "y": center[1],
            "type": "obstacle",
            "obstacle_type": "robot",
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        # Füge alle zusätzlichen Eigenschaften hinzu
        for key, value in pepper.items():
            if key not in ["name", "center"]:
                pepper_node[key] = value
        
        topology["nodes"][node_id] = pepper_node
    
    # Mülleimer
    if "trashcan" in OBJECTS_FOR_TOPOLOGY:
        trashcan = OBJECTS_FOR_TOPOLOGY["trashcan"]
        node_id = trashcan["name"]
        center = trashcan["center"]
        
        trashcan_node = {
            "id": node_id,
            "x": center[0],
            "y": center[1],
            "type": "obstacle", 
            "obstacle_type": "trashcan",
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        # Füge alle zusätzlichen Eigenschaften hinzu
        for key, value in trashcan.items():
            if key not in ["name", "center"]:
                trashcan_node[key] = value
        
        topology["nodes"][node_id] = trashcan_node
    
    # Kartons
    for carton in OBJECTS_FOR_TOPOLOGY["cartons"]:
        node_id = carton["name"]
        center = carton["center"]
        
        carton_node = {
            "id": node_id,
            "x": center[0],
            "y": center[1],
            "type": "obstacle",
            "obstacle_type": "carton",
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        # Füge alle zusätzlichen Eigenschaften hinzu
        for key, value in carton.items():
            if key not in ["name", "center"]:
                carton_node[key] = value
        
        topology["nodes"][node_id] = carton_node
    
    # Stühle
    for chair in OBJECTS_FOR_TOPOLOGY["chairs"]:
        node_id = chair["name"]
        center = chair["center"]
        
        chair_node = {
            "id": node_id,
            "x": center[0],
            "y": center[1],
            "type": "obstacle",
            "obstacle_type": "chair",
            "neighbours": {
                "north": [],
                "south": [],
                "east": [],
                "west": []
            }
        }
        
        # Füge alle zusätzlichen Eigenschaften hinzu
        for key, value in chair.items():
            if key not in ["name", "center"]:
                chair_node[key] = value
        
        topology["nodes"][node_id] = chair_node
    
    # === 3. NACHBARN FÜR NAVIGABLE NODES BERECHNEN ===
    
    navigable_nodes = {k: v for k, v in topology["nodes"].items() if v["type"] == "navigable"}
    
    def find_nearest_neighbor_in_direction(start_x, start_y, direction, max_distance=50):
        """
        Findet den nächsten navigable node in einer bestimmten Himmelsrichtung.
        Nur EXAKT orthogonale Verbindungen sind erlaubt (keine schrägen Verbindungen).
        
        Args:
            start_x, start_y: Startposition
            direction: 'north', 'south', 'east', 'west'
            max_distance: Maximale Suchentfernung in cm
        
        Returns:
            node_id oder None
        """
        best_node = None
        best_distance = float('inf')
        
        for node_id, node in navigable_nodes.items():
            node_x, node_y = node["x"], node["y"]
            
            # Prüfe EXAKT orthogonale Verbindungen (keine schrägen Verbindungen erlaubt)
            if direction == 'north':
                # Für Norden: gleiche x-Koordinate, größere y-Koordinate
                if node_x == start_x and node_y > start_y:
                    distance = node_y - start_y
                    if distance <= max_distance and distance < best_distance:
                        best_distance = distance
                        best_node = node_id
            elif direction == 'south':
                # Für Süden: gleiche x-Koordinate, kleinere y-Koordinate
                if node_x == start_x and node_y < start_y:
                    distance = start_y - node_y
                    if distance <= max_distance and distance < best_distance:
                        best_distance = distance
                        best_node = node_id
            elif direction == 'east':
                # Für Osten: gleiche y-Koordinate, größere x-Koordinate
                if node_y == start_y and node_x > start_x:
                    distance = node_x - start_x
                    if distance <= max_distance and distance < best_distance:
                        best_distance = distance
                        best_node = node_id
            elif direction == 'west':
                # Für Westen: gleiche y-Koordinate, kleinere x-Koordinate
                if node_y == start_y and node_x < start_x:
                    distance = start_x - node_x
                    if distance <= max_distance and distance < best_distance:
                        best_distance = distance
                        best_node = node_id
        
        return best_node
    
    for node_id, node in navigable_nodes.items():
        x, y = node["x"], node["y"]
        
        # Finde nächste Nachbarn in alle 4 Richtungen
        node["neighbours"]["north"] = find_nearest_neighbor_in_direction(x, y, 'north')
        node["neighbours"]["south"] = find_nearest_neighbor_in_direction(x, y, 'south')
        node["neighbours"]["east"] = find_nearest_neighbor_in_direction(x, y, 'east')
        node["neighbours"]["west"] = find_nearest_neighbor_in_direction(x, y, 'west')
    
    # === 4. NACHBARN FÜR HINDERNIS-NODES BERECHNEN (VEREINFACHT) ===
    
    obstacle_nodes = {k: v for k, v in topology["nodes"].items() if v["type"] == "obstacle"}
    
    def get_obstacle_bounds(obs_node):
        """
        Bestimmt die Grenzen eines Hindernisses basierend auf seinem Typ.
        Verwendet die exakten Dimensionen aus dem ROOM_LAYOUT.
        """
        obs_x, obs_y = obs_node["x"], obs_node["y"]
        obstacle_type = obs_node.get("obstacle_type", "unknown")
        obs_name = obs_node["id"]
        
        # Suche nach exakten Dimensionen in OBJECTS_FOR_TOPOLOGY
        if obstacle_type == "table":
            for table in OBJECTS_FOR_TOPOLOGY.get("tables", []):
                if table["name"] == obs_name:
                    if "width" in table and "height" in table:
                        w, h = table["width"], table["height"]
                    elif "diameter" in table:
                        w = h = table["diameter"]
                    else:
                        w, h = 120, 80
                    return {
                        'min_x': obs_x - w/2, 'max_x': obs_x + w/2,
                        'min_y': obs_y - h/2, 'max_y': obs_y + h/2,
                        'width': w, 'height': h
                    }
        elif obstacle_type == "cabinet":
            for cabinet in OBJECTS_FOR_TOPOLOGY.get("cabinets", []):
                if cabinet["name"] == obs_name:
                    w, h = cabinet["width"], cabinet["height"]
                    return {
                        'min_x': obs_x - w/2, 'max_x': obs_x + w/2,
                        'min_y': obs_y - h/2, 'max_y': obs_y + h/2,
                        'width': w, 'height': h
                    }
        elif obstacle_type == "shelf":
            if "shelf" in OBJECTS_FOR_TOPOLOGY and OBJECTS_FOR_TOPOLOGY["shelf"]["name"] == obs_name:
                w, h = OBJECTS_FOR_TOPOLOGY["shelf"]["width"], OBJECTS_FOR_TOPOLOGY["shelf"]["height"]
                return {
                    'min_x': obs_x - w/2, 'max_x': obs_x + w/2,
                    'min_y': obs_y - h/2, 'max_y': obs_y + h/2,
                    'width': w, 'height': h
                }
        elif obstacle_type == "dresser":
            if "dresser" in OBJECTS_FOR_TOPOLOGY and OBJECTS_FOR_TOPOLOGY["dresser"]["name"] == obs_name:
                w, h = OBJECTS_FOR_TOPOLOGY["dresser"]["width"], OBJECTS_FOR_TOPOLOGY["dresser"]["height"]
                return {
                    'min_x': obs_x - w/2, 'max_x': obs_x + w/2,
                    'min_y': obs_y - h/2, 'max_y': obs_y + h/2,
                    'width': w, 'height': h
                }
        elif obstacle_type == "carton":
            for carton in OBJECTS_FOR_TOPOLOGY.get("cartons", []):
                if carton["name"] == obs_name:
                    w, h = carton["width"], carton["height"]
                    return {
                        'min_x': obs_x - w/2, 'max_x': obs_x + w/2,
                        'min_y': obs_y - h/2, 'max_y': obs_y + h/2,
                        'width': w, 'height': h
                    }
        elif obstacle_type == "chair":
            for chair in OBJECTS_FOR_TOPOLOGY.get("chairs", []):
                if chair["name"] == obs_name:
                    w, h = chair["width"], chair["height"]
                    return {
                        'min_x': obs_x - w/2, 'max_x': obs_x + w/2,
                        'min_y': obs_y - h/2, 'max_y': obs_y + h/2,
                        'width': w, 'height': h
                    }
        elif obstacle_type == "whiteboard":
            # Whiteboards haben from/to Koordinaten anstatt center + width/height
            if "from" in obs_node and "to" in obs_node:
                from_x, from_y = obs_node["from"]
                to_x, to_y = obs_node["to"]
                return {
                    'min_x': min(from_x, to_x), 'max_x': max(from_x, to_x),
                    'min_y': min(from_y, to_y), 'max_y': max(from_y, to_y),
                    'width': abs(to_x - from_x), 'height': abs(to_y - from_y)
                }
        elif obstacle_type in ["wall", "door", "window"]:
            # Ähnlich wie Whiteboards - haben from/to Koordinaten
            if "from" in obs_node and "to" in obs_node:
                from_x, from_y = obs_node["from"]
                to_x, to_y = obs_node["to"]
                return {
                    'min_x': min(from_x, to_x), 'max_x': max(from_x, to_x),
                    'min_y': min(from_y, to_y), 'max_y': max(from_y, to_y),
                    'width': abs(to_x - from_x), 'height': abs(to_y - from_y)
                }
        
        # Standard-Fallback-Dimensionen
        fallback_dimensions = {
            "robot": (40, 40),
            "trashcan": (30, 30),
            "chair": (20, 20),
            "table": (120, 80),
            "cabinet": (80, 40),
            "carton": (40, 30)
        }
        w, h = fallback_dimensions.get(obstacle_type, (40, 40))
        
        return {
            'min_x': obs_x - w/2, 'max_x': obs_x + w/2,
            'min_y': obs_y - h/2, 'max_y': obs_y + h/2,
            'width': w, 'height': h
        }
    
    def find_closest_navigable_neighbor_in_direction(obs_node, direction, max_distance=40):
        """
        Findet den einen nächsten navigable node in einer bestimmten Richtung von einem Hindernis.
        Strenge Kriterien für "direkt benachbart".
        
        Args:
            obs_node: Das Hindernis-Node
            direction: Richtung ('north', 'south', 'east', 'west')
            max_distance: Maximale Entfernung für Nachbarsuche (reduziert auf 40cm)
            
        Returns:
            node_id oder None (nur ein Nachbar pro Richtung)
        """
        obs_x, obs_y = obs_node["x"], obs_node["y"]
        obs_bounds = get_obstacle_bounds(obs_node)
        
        best_neighbor = None
        best_distance = float('inf')
        
        for nav_id, nav_node in navigable_nodes.items():
            nav_x, nav_y = nav_node["x"], nav_node["y"]
            
            # Berechne Entfernung zur entsprechenden Kante des Hindernisses
            edge_distance = None
            is_in_correct_direction = False
            
            if direction == 'north':
                # Node muss nördlich (oberhalb) des Hindernisses sein
                if nav_y > obs_bounds['max_y']:
                    edge_distance = nav_y - obs_bounds['max_y']
                    # Node muss horizontal innerhalb der Hindernis-Breite + kleine Toleranz liegen
                    if (obs_bounds['min_x'] - 20 <= nav_x <= obs_bounds['max_x'] + 20):
                        is_in_correct_direction = True
            elif direction == 'south':
                # Node muss südlich (unterhalb) des Hindernisses sein
                if nav_y < obs_bounds['min_y']:
                    edge_distance = obs_bounds['min_y'] - nav_y
                    # Node muss horizontal innerhalb der Hindernis-Breite + kleine Toleranz liegen
                    if (obs_bounds['min_x'] - 20 <= nav_x <= obs_bounds['max_x'] + 20):
                        is_in_correct_direction = True
            elif direction == 'east':
                # Node muss östlich (rechts) des Hindernisses sein
                if nav_x > obs_bounds['max_x']:
                    edge_distance = nav_x - obs_bounds['max_x']
                    # Node muss vertikal innerhalb der Hindernis-Höhe + kleine Toleranz liegen
                    if (obs_bounds['min_y'] - 20 <= nav_y <= obs_bounds['max_y'] + 20):
                        is_in_correct_direction = True
            elif direction == 'west':
                # Node muss westlich (links) des Hindernisses sein
                if nav_x < obs_bounds['min_x']:
                    edge_distance = obs_bounds['min_x'] - nav_x
                    # Node muss vertikal innerhalb der Hindernis-Höhe + kleine Toleranz liegen
                    if (obs_bounds['min_y'] - 20 <= nav_y <= obs_bounds['max_y'] + 20):
                        is_in_correct_direction = True
            
            # Prüfe ob dieser Node ein gültiger Kandidat ist
            if (is_in_correct_direction and 
                edge_distance is not None and 
                edge_distance <= max_distance and 
                edge_distance < best_distance):
                best_distance = edge_distance
                best_neighbor = nav_id
        
        return best_neighbor
    
    # === 5. SYMMETRISCHE NACHBARSCHAFTEN UND EINDEUTIGKEIT SICHERSTELLEN ===
    
    def ensure_symmetric_neighbors():
        """
        Neue Implementierung: Stellt symmetrische Nachbarschaften sicher.
        - Navigable Nodes: Ein Nachbar pro Richtung (wie bisher)
        - Hindernisse: Listen von Nachbarn pro Richtung 
        - Alle navigable→hindernis Beziehungen werden zu hindernis→[navigable] Listen
        - Priorität: Türen/Fenster werden gegenüber Wänden bevorzugt
        """
        
        # Definiere Prioritäten für verschiedene Hindernistypen
        priority_order = {
            "door": 1,      # Höchste Priorität
            "window": 1,    # Höchste Priorität  
            "table": 1,     # Höchste Priorität
            "chair": 1,     # Höchste Priorität
            "cabinet": 1,   # Höchste Priorität
            "shelf": 1,     # Höchste Priorität
            "carton": 1,    # Höchste Priorität
            "dresser": 1,   # Höchste Priorität
            "robot": 1,     # Höchste Priorität
            "trashcan": 1,  # Höchste Priorität
            "whiteboard": 1, # Höchste Priorität
            "wall": 12      # Niedrigste Priorität - nur als letzter Ausweg
        }
        
        # Schritt 1: Lösche alle Hindernis-Nachbarschaften (navigable bleiben unverändert)
        for node_id, node in topology["nodes"].items():
            if node["type"] == "obstacle":
                node["neighbours"] = {
                    "north": [],
                    "south": [],
                    "east": [],
                    "west": []
                }
        
        # Schritt 2: Für jede navigable→obstacle Beziehung erstelle obstacle→navigable Listen
        for nav_id, nav_node in navigable_nodes.items():
            nav_x, nav_y = nav_node["x"], nav_node["y"]
            
            for direction, neighbor_id in nav_node["neighbours"].items():
                if neighbor_id and neighbor_id in obstacle_nodes:
                    # Navigable Node hat ein Hindernis als Nachbarn
                    obs_node = obstacle_nodes[neighbor_id]
                    
                    # Bestimme umgekehrte Richtung (vom Hindernis zum navigable Node)
                    opposite_direction = {
                        "north": "south", 
                        "south": "north", 
                        "east": "west", 
                        "west": "east"
                    }[direction]
                    
                    # Füge navigable Node zur Nachbarliste des Hindernisses hinzu
                    if nav_id not in obs_node["neighbours"][opposite_direction]:
                        obs_node["neighbours"][opposite_direction].append(nav_id)
        
        # Schritt 3: Verbinde navigable Nodes mit Hindernissen mit Prioritätssystem
        for nav_id, nav_node in navigable_nodes.items():
            nav_x, nav_y = nav_node["x"], nav_node["y"]
            
            for direction in ["north", "south", "east", "west"]:
                # Nur wenn dieser navigable node noch keinen Nachbarn in dieser Richtung hat
                if nav_node["neighbours"][direction] is None:
                    best_obstacle = None
                    best_distance = float('inf')
                    best_priority = float('inf')
                    
                    # Suche das beste Hindernis in dieser Richtung (mit Prioritätssystem)
                    for obs_id, obs_node in obstacle_nodes.items():
                        obs_x, obs_y = obs_node["x"], obs_node["y"]
                        obs_bounds = get_obstacle_bounds(obs_node)
                        obstacle_type = obs_node.get("obstacle_type", "unknown")
                        obstacle_priority = priority_order.get(obstacle_type, 99)
                        
                        # Berechne Entfernung zur entsprechenden Kante des Hindernisses
                        edge_distance = None
                        is_in_correct_direction = False
                        
                        if direction == 'north':
                            # Node sucht nördlich (oberhalb), Hindernis muss nördlich sein
                            if nav_y < obs_bounds['min_y']:  # navigable node ist südlich des Hindernisses
                                edge_distance = obs_bounds['min_y'] - nav_y
                                # Node muss horizontal innerhalb der Hindernis-Breite + Toleranz liegen
                                if (obs_bounds['min_x'] - 30 <= nav_x <= obs_bounds['max_x'] + 30):
                                    is_in_correct_direction = True
                        elif direction == 'south':
                            # Node sucht südlich (unterhalb), Hindernis muss südlich sein
                            if nav_y > obs_bounds['max_y']:  # navigable node ist nördlich des Hindernisses
                                edge_distance = nav_y - obs_bounds['max_y']
                                # Node muss horizontal innerhalb der Hindernis-Breite + Toleranz liegen
                                if (obs_bounds['min_x'] - 30 <= nav_x <= obs_bounds['max_x'] + 30):
                                    is_in_correct_direction = True
                        elif direction == 'east':
                            # Node sucht östlich (rechts), Hindernis muss östlich sein
                            if nav_x < obs_bounds['min_x']:  # navigable node ist westlich des Hindernisses
                                edge_distance = obs_bounds['min_x'] - nav_x
                                # Node muss vertikal innerhalb der Hindernis-Höhe + Toleranz liegen
                                if (obs_bounds['min_y'] - 30 <= nav_y <= obs_bounds['max_y'] + 30):
                                    is_in_correct_direction = True
                        elif direction == 'west':
                            # Node sucht westlich (links), Hindernis muss westlich sein
                            if nav_x > obs_bounds['max_x']:  # navigable node ist östlich des Hindernisses
                                edge_distance = nav_x - obs_bounds['max_x']
                                # Node muss vertikal innerhalb der Hindernis-Höhe + Toleranz liegen
                                if (obs_bounds['min_y'] - 30 <= nav_y <= obs_bounds['max_y'] + 30):
                                    is_in_correct_direction = True
                        
                        # Prüfe ob dieses Hindernis ein gültiger Kandidat ist
                        if (is_in_correct_direction and 
                            edge_distance is not None and 
                            edge_distance <= 100):  # Max 100cm Entfernung
                            
                            # NEUE REGEL: Prüfe ob ein anderer navigable node zwischen diesem node und dem hindernis liegt
                            has_navigable_between = False
                            
                            # Prüfe alle anderen navigable nodes, ob sie zwischen nav_node und obs_node liegen
                            for other_nav_id, other_nav_node in navigable_nodes.items():
                                if other_nav_id == nav_id:  # Skip sich selbst
                                    continue
                                    
                                other_x, other_y = other_nav_node["x"], other_nav_node["y"]
                                
                                # Prüfe ob other_nav_node zwischen nav_node und obs_node liegt
                                if direction == 'north':
                                    # nav_node sucht nördlich, other_node darf nicht zwischen liegen
                                    if (nav_y < other_y < obs_bounds['min_y'] and 
                                        abs(other_x - nav_x) <= 15):  # Gleiche x-Linie (±15cm Toleranz)
                                        has_navigable_between = True
                                        break
                                elif direction == 'south':
                                    # nav_node sucht südlich, other_node darf nicht zwischen liegen
                                    if (obs_bounds['max_y'] < other_y < nav_y and 
                                        abs(other_x - nav_x) <= 15):  # Gleiche x-Linie (±15cm Toleranz)
                                        has_navigable_between = True
                                        break
                                elif direction == 'east':
                                    # nav_node sucht östlich, other_node darf nicht zwischen liegen
                                    if (nav_x < other_x < obs_bounds['min_x'] and 
                                        abs(other_y - nav_y) <= 15):  # Gleiche y-Linie (±15cm Toleranz)
                                        has_navigable_between = True
                                        break
                                elif direction == 'west':
                                    # nav_node sucht westlich, other_node darf nicht zwischen liegen
                                    if (obs_bounds['max_x'] < other_x < nav_x and 
                                        abs(other_y - nav_y) <= 15):  # Gleiche y-Linie (±15cm Toleranz)
                                        has_navigable_between = True
                                        break
                            
                            # Nur wenn kein navigable node dazwischen liegt
                            if not has_navigable_between:
                                # Wähle basierend auf Priorität und Entfernung
                                # Türen/Fenster haben Vorrang, auch wenn sie etwas weiter entfernt sind
                                is_better = False
                                if obstacle_priority < best_priority:
                                    # Bessere Priorität
                                    is_better = True
                                elif obstacle_priority == best_priority and edge_distance < best_distance:
                                    # Gleiche Priorität, aber näher
                                    is_better = True
                                
                                if is_better:
                                    best_distance = edge_distance
                                    best_priority = obstacle_priority
                                    best_obstacle = obs_id
                    
                    # Setze Verbindung zum besten Hindernis
                    if best_obstacle:
                        nav_node["neighbours"][direction] = best_obstacle
                        # Setze auch symmetrische Verbindung vom Hindernis zum navigable node
                        opposite_direction = {
                            "north": "south", "south": "north", 
                            "east": "west", "west": "east"
                        }[direction]
                        obs_node = obstacle_nodes[best_obstacle]
                        if nav_id not in obs_node["neighbours"][opposite_direction]:
                            obs_node["neighbours"][opposite_direction].append(nav_id)
        
        # Schritt 4: Sammle ALLE symmetrischen Beziehungen für Türen, Fenster und alle Hindernisse
        # Durchlaufe alle navigable→obstacle Beziehungen und stelle sicher, dass sie symmetrisch sind
        for nav_id, nav_node in navigable_nodes.items():
            nav_x, nav_y = nav_node["x"], nav_node["y"]
            
            for direction, neighbor_id in nav_node["neighbours"].items():
                if neighbor_id and neighbor_id in obstacle_nodes:
                    # Navigable Node hat ein Hindernis als Nachbarn
                    obs_node = obstacle_nodes[neighbor_id]
                    
                    # Bestimme umgekehrte Richtung (vom Hindernis zum navigable Node)
                    opposite_direction = {
                        "north": "south", 
                        "south": "north", 
                        "east": "west", 
                        "west": "east"
                    }[direction]
                    
                    # Füge navigable Node zur Nachbarliste des Hindernisses hinzu, falls noch nicht vorhanden
                    if nav_id not in obs_node["neighbours"][opposite_direction]:
                        obs_node["neighbours"][opposite_direction].append(nav_id)
    
    # Führe Nachbarschafts-Bereinigung durch
    ensure_symmetric_neighbors()
    
    # === SPEZIELLE NACHBARSCHAFTSBEHANDLUNG (NACH BEREINIGUNG) ===
    
    # Spezielle Behandlung für Whiteboard 2 und Wand Nord
    for obs_id, obs_node in obstacle_nodes.items():
        # Whiteboard 2: Verbinde mit Nodes x=315-600, y=630
        if (obs_node.get("obstacle_type") == "whiteboard" and 
            "Whiteboard 2" in obs_node.get("id", "")):
            
            # Finde alle passenden Nachbarn im Süden (y=630, x zwischen 315 und 600)
            whiteboard_neighbors = []
            for nav_id, nav_node in navigable_nodes.items():
                nav_x, nav_y = nav_node["x"], nav_node["y"]
                if (nav_y == 630 and 315 <= nav_x <= 600):
                    whiteboard_neighbors.append(nav_id)
            
            # Setze symmetrische Verbindungen für alle gefundenen Nachbarn
            for nav_id in whiteboard_neighbors:
                nav_node = navigable_nodes[nav_id]
                nav_node["neighbours"]["north"] = obs_id
                # Füge zur Liste hinzu (statt zu überschreiben)
                if nav_id not in obs_node["neighbours"]["south"]:
                    obs_node["neighbours"]["south"].append(nav_id)
        
        # Wand Nord: Verbinde nur mit Nodes x=615-660, y=630
        elif (obs_node.get("obstacle_type") == "wall" and 
              "Wand Nord" in obs_node.get("id", "")):
            
            # Finde passende Nachbarn im Süden (y=630, x zwischen 615 und 660)
            wall_neighbors = []
            for nav_id, nav_node in navigable_nodes.items():
                nav_x, nav_y = nav_node["x"], nav_node["y"]
                if (nav_y == 630 and 615 <= nav_x <= 660):
                    wall_neighbors.append(nav_id)
            
            # Setze symmetrische Verbindungen für passende Nachbarn
            for nav_id in wall_neighbors:
                nav_node = navigable_nodes[nav_id]
                nav_node["neighbours"]["north"] = obs_id
                # Füge zur Liste hinzu (statt zu überschreiben)
                if nav_id not in obs_node["neighbours"]["south"]:
                    obs_node["neighbours"]["south"].append(nav_id)
            
            # Entferne falsche Verbindungen zu Nodes außerhalb des Bereichs x=615-660
            for nav_id, nav_node in navigable_nodes.items():
                nav_x, nav_y = nav_node["x"], nav_node["y"]
                if (nav_y == 630 and not (615 <= nav_x <= 660)):
                    # Entferne Verbindung zur Wand Nord, falls vorhanden
                    if nav_node["neighbours"]["north"] == obs_id:
                        nav_node["neighbours"]["north"] = None
    
    # === 6. NACHBARN ZWISCHEN HINDERNIS-NODES BERECHNEN (VEREINFACHT) ===
    
    def find_closest_obstacle_neighbor_in_direction(obs_node1, direction, max_distance=80):
        """
        Findet das nächste Hindernis in einer bestimmten Richtung.
        
        Returns:
            obstacle_id oder None
        """
        obs1_x, obs1_y = obs_node1["x"], obs_node1["y"]
        best_obstacle = None
        best_distance = float('inf')
        
        for obs_id2, obs_node2 in obstacle_nodes.items():
            if obs_id2 == obs_node1["id"]:
                continue
                
            obs2_x, obs2_y = obs_node2["x"], obs_node2["y"]
            
            # Prüfe Richtung
            dx = obs2_x - obs1_x
            dy = obs2_y - obs1_y
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance > max_distance:
                continue
            
            # Prüfe ob in der gewünschten Richtung
            is_in_direction = False
            if direction == 'north' and dy > 0 and abs(dy) >= abs(dx):
                is_in_direction = True
            elif direction == 'south' and dy < 0 and abs(dy) >= abs(dx):
                is_in_direction = True
            elif direction == 'east' and dx > 0 and abs(dx) >= abs(dy):
                is_in_direction = True
            elif direction == 'west' and dx < 0 and abs(dx) >= abs(dy):
                is_in_direction = True
            
            if is_in_direction and distance < best_distance:
                best_distance = distance
                best_obstacle = obs_id2
        
        return best_obstacle
    
    # Berechne Hindernis-zu-Hindernis Nachbarschaften (füge zu Listen hinzu)
    for obs_id1, obs_node1 in obstacle_nodes.items():
        for direction in ["north", "south", "east", "west"]:
            # Finde das nächste Hindernis in dieser Richtung
            closest_obstacle = find_closest_obstacle_neighbor_in_direction(obs_node1, direction)
            if closest_obstacle and closest_obstacle not in obs_node1["neighbours"][direction]:
                obs_node1["neighbours"][direction].append(closest_obstacle)
    
    # === 7. SPEZIELLE NACHBARSCHAFTSREGELN FÜR BENACHBARTE TISCHE UND OBJEKTE ===
    
    def add_special_table_neighbors():
        """
        Fügt spezielle Nachbarschaftsregeln für benachbarte Tische und Objekte hinzu.
        Diese Regeln ergänzen die automatische Nachbarschaftsberechnung.
        """
        
        # Definiere spezielle Nachbarschaftsregeln
        # Format: (object1, direction_from_obj1, object2)
        special_relationships = [
            # Tisch-zu-Tisch Nachbarschaften
            ("Tisch 1 (PC)", "east", "Tisch 2 (mit Telefon)"),
            ("Tisch 2 (mit Telefon)", "north", "Tisch 3"),
            ("Tisch 3", "north", "Tisch 4"),
            ("Tisch 4", "north", "Tisch 5 (PC)"),
            ("Tisch 5 (PC)", "west", "Tisch 6"),
            ("Tisch 7 (Kartons)", "west", "Tisch 8"),
            ("Tisch 8", "north", "Tisch 9"),
            
            # Tisch-zu-Karton Nachbarschaften
            ("Tisch 7 (Kartons)", "south", "Karton 3"),
            ("Tisch 4", "west", "Karton 1")
        ]
        
        # Richtungsumkehr-Mapping
        opposite_directions = {
            "north": "south",
            "south": "north", 
            "east": "west",
            "west": "east"
        }
        
        print("🔗 Füge spezielle Nachbarschaftsregeln hinzu...")
        
        for obj1_name, direction, obj2_name in special_relationships:
            # Prüfe ob beide Objekte existieren
            if obj1_name in topology["nodes"] and obj2_name in topology["nodes"]:
                obj1_node = topology["nodes"][obj1_name]
                obj2_node = topology["nodes"][obj2_name]
                
                # Füge obj2 zu obj1's Nachbarliste in der angegebenen Richtung hinzu
                if obj2_name not in obj1_node["neighbours"][direction]:
                    obj1_node["neighbours"][direction].append(obj2_name)
                    print(f"  ✅ {obj1_name} -> {direction}: {obj2_name}")
                
                # Füge obj1 zu obj2's Nachbarliste in der umgekehrten Richtung hinzu
                opposite_dir = opposite_directions[direction]
                if obj1_name not in obj2_node["neighbours"][opposite_dir]:
                    obj2_node["neighbours"][opposite_dir].append(obj1_name)
                    print(f"  ✅ {obj2_name} -> {opposite_dir}: {obj1_name}")
            else:
                print(f"  ❌ Warnung: Objekt '{obj1_name}' oder '{obj2_name}' nicht gefunden")
    
    # Führe spezielle Nachbarschaftsregeln durch
    add_special_table_neighbors()
    
    # === 8. NACHBARSCHAFTEN ZWISCHEN NAVIGABLE_AREAS BERECHNEN ===
    
    def add_navigable_area_neighbors():
        """
        Fügt Nachbarschaftsbeziehungen zwischen angrenzenden navigable_areas hinzu.
        Navigable_areas sind benachbart, wenn sie sich berühren oder sehr nah beieinander liegen.
        """
        print("🔗 Berechne Nachbarschaften zwischen navigable_areas...")
        
        # Füge neighbors Feld zu jeder navigable_area hinzu, falls nicht vorhanden
        for area in topology["navigable_areas"]:
            if "neighbors" not in area:
                area["neighbors"] = {
                    "north": [],
                    "south": [],
                    "east": [],
                    "west": []
                }
        
        def areas_are_adjacent(area1, area2, direction, tolerance=5):
            """
            Prüft, ob zwei navigable_areas in einer bestimmten Richtung angrenzend sind.
            
            Args:
                area1: Erste area (Referenz)
                area2: Zweite area (zu prüfende)
                direction: Richtung von area1 zu area2 ('north', 'south', 'east', 'west')
                tolerance: Toleranz in cm für "berührende" Bereiche
            
            Returns:
                bool: True wenn angrenzend
            """
            x1, y1, w1, h1 = area1['bottom_left'][0], area1['bottom_left'][1], area1['width'], area1['height']
            x2, y2, w2, h2 = area2['bottom_left'][0], area2['bottom_left'][1], area2['width'], area2['height']
            
            if direction == 'north':
                # area2 muss nördlich (oberhalb) von area1 sein
                # y2 sollte ungefähr bei y1 + h1 liegen
                vertical_adjacent = abs((y1 + h1) - y2) <= tolerance
                # Die Bereiche müssen sich horizontal überschneiden
                horizontal_overlap = not (x1 + w1 < x2 or x2 + w2 < x1)
                return vertical_adjacent and horizontal_overlap
                
            elif direction == 'south':
                # area2 muss südlich (unterhalb) von area1 sein
                # y1 sollte ungefähr bei y2 + h2 liegen
                vertical_adjacent = abs((y2 + h2) - y1) <= tolerance
                # Die Bereiche müssen sich horizontal überschneiden
                horizontal_overlap = not (x1 + w1 < x2 or x2 + w2 < x1)
                return vertical_adjacent and horizontal_overlap
                
            elif direction == 'east':
                # area2 muss östlich (rechts) von area1 sein
                # x2 sollte ungefähr bei x1 + w1 liegen
                horizontal_adjacent = abs((x1 + w1) - x2) <= tolerance
                # Die Bereiche müssen sich vertikal überschneiden
                vertical_overlap = not (y1 + h1 < y2 or y2 + h2 < y1)
                return horizontal_adjacent and vertical_overlap
                
            elif direction == 'west':
                # area2 muss westlich (links) von area1 sein
                # x1 sollte ungefähr bei x2 + w2 liegen
                horizontal_adjacent = abs((x2 + w2) - x1) <= tolerance
                # Die Bereiche müssen sich vertikal überschneiden
                vertical_overlap = not (y1 + h1 < y2 or y2 + h2 < y1)
                return horizontal_adjacent and vertical_overlap
            
            return False
        
        # Berechne Nachbarschaften zwischen allen navigable_areas
        for i, area1 in enumerate(topology["navigable_areas"]):
            for j, area2 in enumerate(topology["navigable_areas"]):
                if i == j:  # Gleiche Area
                    continue
                
                # Prüfe alle vier Richtungen
                for direction in ["north", "south", "east", "west"]:
                    if areas_are_adjacent(area1, area2, direction):
                        # Füge area2 als Nachbar von area1 in der entsprechenden Richtung hinzu
                        if j not in area1["neighbors"][direction]:
                            area1["neighbors"][direction].append(j)
                            print(f"  ✅ Area {i} -> {direction}: Area {j}")
        
        # Zähle gefundene Nachbarschaften
        total_neighbors = 0
        for area in topology["navigable_areas"]:
            for direction, neighbors in area["neighbors"].items():
                total_neighbors += len(neighbors)
        
        print(f"✅ {total_neighbors} Nachbarschaften zwischen navigable_areas gefunden")
    
    # Führe navigable_area Nachbarschaftsberechnung durch
    add_navigable_area_neighbors()
    
    # Erstelle connections Liste basierend auf den Nachbarschaften
    connections = []
    processed_pairs = set()  # Verhindert doppelte Verbindungen
    
    for node_id, node in topology["nodes"].items():
        for direction, neighbors in node["neighbours"].items():
            # Behandle sowohl Listen (Hindernisse) als auch einzelne IDs (navigable)
            if neighbors is not None:
                if isinstance(neighbors, list):
                    # Hindernis mit Liste von Nachbarn
                    for neighbor_id in neighbors:
                        if neighbor_id is not None:
                            # Sorge für eindeutige Paare (kleinere ID zuerst)
                            pair = tuple(sorted([node_id, neighbor_id]))
                            if pair not in processed_pairs:
                                processed_pairs.add(pair)
                                
                                # Berechne Entfernung zwischen den Knoten
                                node1 = topology["nodes"][pair[0]]
                                node2 = topology["nodes"][pair[1]]
                                distance = math.sqrt((node1["x"] - node2["x"])**2 + (node1["y"] - node2["y"])**2)
                                
                                connections.append({
                                    "node1": pair[0],
                                    "node2": pair[1],
                                    "distance": round(distance, 1)
                                })
                else:
                    # Navigable Node mit einzelnem Nachbarn
                    neighbor_id = neighbors
                    if neighbor_id is not None:
                        # Sorge für eindeutige Paare (kleinere ID zuerst)
                        pair = tuple(sorted([node_id, neighbor_id]))
                        if pair not in processed_pairs:
                            processed_pairs.add(pair)
                            
                            # Berechne Entfernung zwischen den Knoten
                            node1 = topology["nodes"][pair[0]]
                            node2 = topology["nodes"][pair[1]]
                            distance = math.sqrt((node1["x"] - node2["x"])**2 + (node1["y"] - node2["y"])**2)
                            
                            connections.append({
                                "node1": pair[0],
                                "node2": pair[1],
                                "distance": round(distance, 1)
                            })
    
    # Füge connections zur Topologie hinzu
    topology["connections"] = connections
    
    print(f"✅ Topologie erstellt: {len(topology['nodes'])} Knoten, {len(connections)} Verbindungen")
    
    # TEST: Zeige einige Beispiele der neuen Nachbarschaftslogik
    print("\n=== TEST: NACHBARSCHAFTSLOGIK ===")
    
    # Finde ein Hindernis und zeige seine Nachbarn
    for node_id, node in topology["nodes"].items():
        if node["type"] == "obstacle" and "Tisch" in node_id:
            print(f"Hindernis: {node_id}")
            for direction, neighbors in node["neighbours"].items():
                if neighbors:  # Listen sind nie None, aber können leer sein
                    print(f"  {direction}: {neighbors}")
            break
    
    # Finde einige navigable Nodes und zeige ihre Hindernisse als Nachbarn
    obstacle_connections = 0
    for node_id, node in topology["nodes"].items():
        if node["type"] == "navigable" and obstacle_connections < 3:
            for direction, neighbor_id in node["neighbours"].items():
                if neighbor_id and neighbor_id in obstacle_nodes:
                    print(f"Navigable {node_id} -> {direction}: {neighbor_id}")
                    obstacle_connections += 1
                    break
    
    print("=== ENDE TEST ===\n")
    
    return topology


def update_room_layout_with_navigable_areas(navigable_areas):
    """
    Aktualisiert die roomlayout.json mit den berechneten navigable_areas und topologischem Graph.
    Die navigable_areas werden jetzt direkt in die topology integriert.
    """
    
    # Erstelle das komplette ROOM_LAYOUT (ohne navigable_areas auf oberster Ebene)
    success, ROOM_LAYOUT, OBJECTS_FOR_TOPOLOGY = write_room_layout_to_json()
    
    if success and ROOM_LAYOUT and OBJECTS_FOR_TOPOLOGY:
        # === TOPOLOGISCHEN GRAPH ERSTELLEN (mit integrierten navigable_areas) ===
        print("🔄 Erstelle topologischen Graph mit integrierten navigable_areas...")
        topology = create_topological_graph(ROOM_LAYOUT, OBJECTS_FOR_TOPOLOGY, navigable_areas)
        ROOM_LAYOUT["topology"] = topology
        
        # Entferne navigable_areas aus der Hauptstruktur, da sie jetzt in topology sind
        if "navigable_areas" in ROOM_LAYOUT:
            del ROOM_LAYOUT["navigable_areas"]
        
        # Schreibe die aktualisierte JSON-Datei
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'roomlayout.json')
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(ROOM_LAYOUT, f, indent=4, ensure_ascii=False)
            
            # Statistiken ausgeben
            total_nodes = len(topology["nodes"])
            navigable_nodes = len([n for n in topology["nodes"].values() if n["type"] == "navigable"])
            obstacle_nodes = len([n for n in topology["nodes"].values() if n["type"] == "obstacle"])
            
            print(f"✅ ROOM_LAYOUT mit topologischem Graph aktualisiert: {json_path}")
            print(f"   📊 Gesamt Nodes: {total_nodes}")
            print(f"   🟢 Befahrbare Nodes: {navigable_nodes}")
            print(f"   🔴 Hindernis Nodes: {obstacle_nodes}")
            print(f"   📐 Navigable Areas: {len(topology['navigable_areas'])}")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Aktualisieren der roomlayout.json: {e}")
            return False
    
    return False


if __name__ == "__main__":
    # Test der Funktionalität
    print("🔄 Teste draw_roomlayout.py Funktionen...")
    success, room_layout, objects = write_room_layout_to_json()
    if success:
        print("✅ write_room_layout_to_json() funktioniert korrekt")
    else:
        print("❌ Fehler bei write_room_layout_to_json()")

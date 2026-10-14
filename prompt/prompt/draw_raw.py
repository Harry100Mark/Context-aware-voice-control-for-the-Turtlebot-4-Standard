import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import shapely.affinity
import json

# Import handling für sowohl direktes Ausführen als auch Modul-Import
try:
    from .perspectiveTaker import analyze_objects_around_turtlebot
    from .draw_roomlayout import write_room_layout_to_json, create_topological_graph, update_room_layout_with_navigable_areas
except ImportError:
    from perspectiveTaker import analyze_objects_around_turtlebot
    from draw_roomlayout import write_room_layout_to_json, create_topological_graph, update_room_layout_with_navigable_areas

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

def create_room_plan(robot_x=500, robot_y=390, robot_heading=180, show_fov=False):
    """
    Erstellt einen detaillierten Raumplan ohne Roboter.
    Args:
        robot_x, robot_y: Nicht verwendet (für Kompatibilität beibehalten)
        robot_heading: Nicht verwendet (für Kompatibilität beibehalten)
        show_fov: Nicht verwendet (für Kompatibilität beibehalten)
    """
    
    # Lade Objektdaten für die Visualisierung
    success, ROOM_LAYOUT, OBJECTS_FOR_TOPOLOGY = write_room_layout_to_json()
    if not success:
        print("❌ Fehler beim Laden der Raumdaten")
        return None, None, None
    
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
    tables_rect = {}
    for table in OBJECTS_FOR_TOPOLOGY["tables"]:
        if "width" in table and "height" in table:
            tables_rect[table["name"]] = {
                'pos': tuple(table["center"]), 
                'size': (table["width"], table["height"])
            }
    for data in tables_rect.values():
        x, y = data['pos']
        w, h = data['size']
        table_poly = Polygon([(x-w/2, y-h/2), (x+w/2, y-h/2),
                              (x+w/2, y+h/2), (x-w/2, y+h/2)])
        obstacles.append(table_poly)
    # Runder Tisch (korrigiert)
    round_table = None
    for table in OBJECTS_FOR_TOPOLOGY["tables"]:
        if "diameter" in table:
            round_table = table
            break
    
    if round_table:
        circle_points = []
        center_x, center_y = round_table["center"]
        radius = round_table["diameter"] / 2
        for angle in np.linspace(0, 2*np.pi, 32):
            circle_points.append((center_x + radius*np.cos(angle), center_y + radius*np.sin(angle)))
        obstacles.append(Polygon(circle_points))
    
    # Stühle um den runden Tisch
    round_table_chairs = []
    if round_table:
        center_x, center_y = round_table["center"]
        round_table_chairs = [(center_x, center_y-60), (center_x+60, center_y), (center_x, center_y+60), (center_x-60, center_y)]
    
    for x, y in round_table_chairs:
        chair_poly = Polygon([(x-10, y-10), (x+10, y-10), (x+10, y+10), (x-10, y+10)])
        obstacles.append(chair_poly)
    
    # Schränke
    schrank_obstacles = []
    for cabinet in OBJECTS_FOR_TOPOLOGY["cabinets"]:
        x, y = cabinet["center"]
        w, h = cabinet["width"], cabinet["height"]
        cabinet_poly = Polygon([(x-w/2, y-h/2), (x+w/2, y-h/2), (x+w/2, y+h/2), (x-w/2, y+h/2)])
        obstacles.append(cabinet_poly)
    
    # Regal
    if "shelf" in OBJECTS_FOR_TOPOLOGY:
        shelf = OBJECTS_FOR_TOPOLOGY["shelf"]
        x, y = shelf["center"]
        w, h = shelf["width"], shelf["height"]
        regal = Polygon([(x-w/2, y-h/2), (x+w/2, y-h/2), (x+w/2, y+h/2), (x-w/2, y+h/2)])
        obstacles.append(regal)
    
    # Kommode
    if "dresser" in OBJECTS_FOR_TOPOLOGY:
        dresser = OBJECTS_FOR_TOPOLOGY["dresser"]
        x, y = dresser["center"]
        w, h = dresser["width"], dresser["height"]
        kommode = Polygon([(x-w/2, y-h/2), (x+w/2, y-h/2), (x+w/2, y+h/2), (x-w/2, y+h/2)])
        obstacles.append(kommode)
    
    # Kartons
    for carton in OBJECTS_FOR_TOPOLOGY["cartons"]:
        x, y = carton["center"]
        w, h = carton["width"], carton["height"]
        karton_poly = Polygon([(x-w/2, y-h/2), (x+w/2, y-h/2), (x+w/2, y+h/2), (x-w/2, y+h/2)])
        obstacles.append(karton_poly)
    
    # Pepper Roboter (als Rechteck)
    if "pepper" in OBJECTS_FOR_TOPOLOGY:
        pepper = OBJECTS_FOR_TOPOLOGY["pepper"]
        x, y = pepper["center"]
        w, h = pepper["width"], pepper["height"]
        pepper_poly = Polygon([(x-w/2, y-h/2), (x+w/2, y-h/2), (x+w/2, y+h/2), (x-w/2, y+h/2)])
        obstacles.append(pepper_poly)
    
    # Mülleimer (als Kreis)
    if "trashcan" in OBJECTS_FOR_TOPOLOGY:
        trashcan = OBJECTS_FOR_TOPOLOGY["trashcan"]
        x, y = trashcan["center"]
        radius = trashcan["diameter"] / 2
        muelleimer_points = []
        for angle in np.linspace(0, 2*np.pi, 16):
            muelleimer_points.append((x + radius*np.cos(angle), y + radius*np.sin(angle)))
        obstacles.append(Polygon(muelleimer_points))
    
    # Übrige Stühle
    other_chairs = []
    for chair in OBJECTS_FOR_TOPOLOGY["chairs"]:
        chair_center = tuple(chair["center"])
        # Prüfe ob dieser Stuhl nicht bereits als round_table_chair hinzugefügt wurde
        if chair_center not in round_table_chairs:
            other_chairs.append(chair_center)
    
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

    print(merged_navigable_areas)
    
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
    ax.text(52, 170, 'Tür 2 (Serverraum)', fontsize=8, ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='wheat', alpha=0.7))
    # Tür 3
    ax.plot([189, 310], [182, 182], 'brown', linewidth=8, alpha=0.8)
    ax.text(249, 170, 'Tür 3 (Serverraum)', fontsize=8, ha='center', va='center',
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
    round_table = None
    for table in OBJECTS_FOR_TOPOLOGY["tables"]:
        if "diameter" in table:
            round_table = table
            break
    
    if round_table:
        center_x, center_y = round_table["center"]
        radius = round_table["diameter"] / 2
        circle = patches.Circle((center_x, center_y), radius, facecolor='saddlebrown',
                                edgecolor='black', linewidth=1.5)
        ax.add_patch(circle)
        ax.text(center_x, center_y, round_table["name"], fontsize=8, ha='center', va='center',
                color='white', weight='bold')
    
    # === SCHRÄNKE ===
    for cabinet in OBJECTS_FOR_TOPOLOGY["cabinets"]:
        x, y = cabinet["center"]
        w, h = cabinet["width"], cabinet["height"]
        schrank = patches.Rectangle((x-w/2, y-h/2), w, h,
                                   facecolor='darkslategray', edgecolor='black', linewidth=1.5)
        ax.add_patch(schrank)
        ax.text(x, y, cabinet["name"], fontsize=7, ha='center', va='center', color='white')
    
    # === REGAL ===
    if "shelf" in OBJECTS_FOR_TOPOLOGY:
        shelf = OBJECTS_FOR_TOPOLOGY["shelf"]
        x, y = shelf["center"]
        w, h = shelf["width"], shelf["height"]
        regal = patches.Rectangle((x-w/2, y-h/2), w, h,
                                  facecolor='darkgoldenrod', edgecolor='black', linewidth=1.5)
        ax.add_patch(regal)
        ax.text(x, y, shelf["name"], fontsize=8, ha='center', va='center', color='white')
    
    # === KOMMODE ===
    if "dresser" in OBJECTS_FOR_TOPOLOGY:
        dresser = OBJECTS_FOR_TOPOLOGY["dresser"]
        x, y = dresser["center"]
        w, h = dresser["width"], dresser["height"]
        kommode = patches.Rectangle((x-w/2, y-h/2), w, h,
                                    facecolor='darkgoldenrod', edgecolor='black', linewidth=1.5)
        ax.add_patch(kommode)
        description = dresser.get("description", "")
        display_name = f"{dresser['name']}\n({description})" if description else dresser["name"]
        ax.text(x, y, display_name, fontsize=8, ha='center', va='center', color='white')
    
    # === KARTONS ===
    for i, carton in enumerate(OBJECTS_FOR_TOPOLOGY["cartons"], 1):
        x, y = carton["center"]
        w, h = carton["width"], carton["height"]
        rect = patches.Rectangle((x-w/2, y-h/2), w, h,
                                 facecolor='burlywood', edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text(x, y, f'K{i}', fontsize=7, ha='center', va='center')
    
    # === ROBOTER PEPPER ===
    if "pepper" in OBJECTS_FOR_TOPOLOGY:
        pepper = OBJECTS_FOR_TOPOLOGY["pepper"]
        x, y = pepper["center"]
        w, h = pepper["width"], pepper["height"]
        pepper_patch = patches.Rectangle((x-w/2, y-h/2), w, h, facecolor='lightcoral',
                                       edgecolor='darkred', linewidth=2)
        ax.add_patch(pepper_patch)
        ax.text(x, y, pepper["name"], fontsize=8, ha='center', va='center',
                color='white', weight='bold')
    
    # === MÜLLEIMER ===
    if "trashcan" in OBJECTS_FOR_TOPOLOGY:
        trashcan = OBJECTS_FOR_TOPOLOGY["trashcan"]
        x, y = trashcan["center"]
        radius = trashcan["diameter"] / 2
        muelleimer = patches.Circle((x, y), radius, facecolor='gray',
                                    edgecolor='black', linewidth=1.5)
        ax.add_patch(muelleimer)
        ax.text(x, y, 'M', fontsize=8, ha='center', va='center',
                color='white', weight='bold')
    
    # === STÜHLE (mit Farben und Beschriftung) ===
    # Farbmapping für bessere Sichtbarkeit
    color_map = {
        'blue': 'royalblue',
        'blau': 'royalblue',
        'gray': 'lightgray',
        'grau': 'lightgray',
        'black': 'black',
        'schwarz': 'black'
    }
    
    for i, chair in enumerate(OBJECTS_FOR_TOPOLOGY["chairs"], 1):
        x, y = chair["center"]
        w, h = chair["width"], chair["height"]
        color = color_map.get(chair.get("color", "gray"), "lightgray")
        
        # Stuhl als Rechteck
        rect = patches.Rectangle((x-w/2, y-h/2), w, h, facecolor=color,
                                edgecolor='darkgray', linewidth=1.5)
        ax.add_patch(rect)
        
        # Beschriftung neben Stuhl (für KI-Interpretation)
        text_color = 'white' if color == 'black' else 'black'
        chair_label = f"S{i} ({chair.get('color', 'grau')})"
        ax.text(x, y-16, chair_label, fontsize=6, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
    
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
    fig.suptitle('Raumplan',
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
        patches.Patch(color='lightcoral', label='Pepper (Roboter)'),
        patches.Patch(color='gray', label='Mülleimer'),
        patches.Patch(color='royalblue', label='Stühle (blau)'),
        patches.Patch(color='lightgray', label='Stühle (grau)'),
        patches.Patch(color='black', label='Stühle (schwarz)')
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)
    # Ausgabe der Eckpunkte NACH dem Zeichnen
    print("\n" + "="*50)
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

    # Anpassung der Margen, um Platz für Labels und Titel zu schaffen
    plt.subplots_adjust(left=0.1, right=0.8, top=0.95, bottom=0.1)
    return fig, ax, merged_navigable_areas

# === VERWENDUNG ===
if __name__ == "__main__":
    # ROOM_LAYOUT automatisch in JSON schreiben
    print("🔄 Erstelle ROOM_LAYOUT und schreibe in roomlayout.json...")
    write_room_layout_to_json()
    
    # Standard-Roboterposition (einfach anpassbar)
    robot_x, robot_y = 480, 625
    robot_heading = 270 # Blickrichtung (wird zu Himmelsrichtung quantisiert)
    
    # Raumplan erstellen (ohne Roboter)
    result = create_room_plan(robot_x, robot_y, robot_heading)
    if result is None or result[0] is None:
        print("❌ Fehler beim Erstellen des Raumplans")
        exit(1)
        
    fig, ax, navigable_areas = result
    
    # Aktualisiere roomlayout.json mit den berechneten navigable_areas und topologischem Graph
    print("🔄 Aktualisiere roomlayout.json mit berechneten navigable_areas und topologischem Graph...")
    update_room_layout_with_navigable_areas(navigable_areas)
    
    # Bild für KI-Analyse speichern (hochauflösend)
    import os
    home_dir = os.path.expanduser('~')
    output_path = os.path.join(home_dir, 'ros2_ws', 'src', 'prompt', 'prompt', 'fewshots', 'room_raw.png')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Raumplan (ohne Roboter) gespeichert: {output_path}")
    
    # Perspective Taker Analyse wird übersprungen (kein Roboter)
    print("\n" + "="*60)
    print("RAUMPLAN OHNE ROBOTER ERSTELLT")
    print("="*60)
    
    # === TOPOLOGIE DEMO ===
    print("\n" + "="*60)
    print("TOPOLOGISCHER GRAPH - BEISPIELE")
    print("="*60)
    
    # Lade die aktualisierte roomlayout.json um Topologie zu demonstrieren
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'roomlayout.json')
        
        with open(json_path, 'r', encoding='utf-8') as f:
            room_layout_with_topology = json.load(f)
        
        topology = room_layout_with_topology.get("topology", {})
        nodes = topology.get("nodes", {})
        
        # Zeige Beispiel-Nodes
        print(f"📊 Topologie erstellt mit {len(nodes)} Nodes")
        
        # Beispiel: Befahrbare Nodes
        navigable_examples = [node_id for node_id, node in nodes.items() if node["type"] == "navigable"]
        if navigable_examples:
            example_nav = navigable_examples[0]
            node = nodes[example_nav]
            print(f"\n🟢 Beispiel Befahrbarer Node: {example_nav}")
            print(f"   Position: ({node['x']}, {node['y']})")
            print(f"   Nachbarn: N={node['neighbours']['north']}, S={node['neighbours']['south']}, E={node['neighbours']['east']}, W={node['neighbours']['west']}")
        
        # Beispiel: Hindernis-Nodes
        obstacle_examples = [node_id for node_id, node in nodes.items() if node["type"] == "obstacle"]
        if obstacle_examples:
            example_obs = obstacle_examples[0]
            node = nodes[example_obs]
            print(f"\n🔴 Beispiel Hindernis Node: {example_obs}")
            print(f"   Position: ({node['x']}, {node['y']})")
            print(f"   Typ: {node.get('obstacle_type', 'unknown')}")
            for direction, neighbors in node['neighbours'].items():
                if neighbors:
                    print(f"   {direction.capitalize()}: {len(neighbors)} Nachbarn {neighbors[:3]}{'...' if len(neighbors) > 3 else ''}")
        
        print("\n✅ Topologischer Graph erfolgreich erstellt und in roomlayout.json gespeichert!")
        
    except Exception as e:
        print(f"❌ Fehler beim Laden der Topologie: {e}")
    
    print("="*60)
    
    plt.show()
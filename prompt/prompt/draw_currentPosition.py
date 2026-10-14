import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import shapely.affinity
import os

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
    # Berechnung der Eckpunkte NACH dem Zeichnen (ohne Print-Ausgabe)
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

    # Anpassung der Margen, um Platz für Labels und Titel zu schaffen
    plt.subplots_adjust(left=0.1, right=0.8, top=0.95, bottom=0.1)
    return fig, ax

def meter_to_pixel_affine(x_m: float, y_m: float):
    """Map-Frame (Meter) -> Pixelkoordinaten relativ zum Raster, via Invertierung von T_FWD."""
    a, b, tx = T_FWD[0]
    c, d, ty = T_FWD[1]
    det = a * d - b * c
    if abs(det) < 1e-9:
        return float(RASTER_ORIGIN_X), float(RASTER_ORIGIN_Y)
    inv_a = d / det
    inv_b = -b / det
    inv_c = -c / det
    inv_d = a / det
    X = x_m - tx
    Y = y_m - ty
    u_rel = inv_a * X + inv_b * Y
    v_rel = inv_c * X + inv_d * Y
    u = u_rel + RASTER_ORIGIN_X
    v = v_rel + RASTER_ORIGIN_Y
    return u, v


def pixel_to_raster_cm(u: float, v: float):
    """Pixelkoordinaten -> Raster in cm (so wie create_room_plan es erwartet)."""
    x_cm = (u - RASTER_ORIGIN_X) * SCALE_X_UNITS_PER_PIXEL
    y_cm = (v - RASTER_ORIGIN_Y) * SCALE_Y_UNITS_PER_PIXEL
    return x_cm, y_cm


# Repliziere Raster-/Transformationskonstanten aus chat.py
RASTER_ORIGIN_X = 230
RASTER_ORIGIN_Y = 83
_DX_PIXELS = 900 - RASTER_ORIGIN_X  # entspricht 689 cm
_DY_PIXELS = 720 - RASTER_ORIGIN_Y  # entspricht 654 cm
SCALE_X_UNITS_PER_PIXEL = 689 / _DX_PIXELS
SCALE_Y_UNITS_PER_PIXEL = 654 / _DY_PIXELS

# Pixel -> Meter affine forward transform (aus chat.py)
T_FWD = [
    [-0.00415100004612316,  0.00913128097842589, -0.842668969097485],
    [ 0.00944119084993447,  0.00441552477005685, -5.89657886945609],
]


def generate_current_pose_image(x_cm: int, y_cm: int, yaw_img_deg: float, out_path: str | None = None):
    """Erzeugt draw_currentPosition.png in ~/ros2_ws/src/map mit den übergebenen Koordinaten.

    Args:
        x_cm, y_cm: Pose in cm (wie von chat.py Terminal-Eingabe)
        yaw_img_deg: Blickrichtung in Grad (0°=Osten/rechts, 90°=Norden/oben, gegen den Uhrzeigersinn)
        out_path: Optionaler Zielpfad; default ist ~/ros2_ws/src/map/draw_currentPosition.png
    """
    home = os.path.expanduser('~')
    default_dir = os.path.join(home, 'ros2_ws', 'src', 'map')
    os.makedirs(default_dir, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(default_dir, 'draw_currentPosition.png')

    # Direkte Verwendung der cm-Werte ohne unnötige Konvertierung
    robot_x_cm = int(x_cm)
    robot_y_cm = int(y_cm)

    # Blickrichtung direkt im gleichen CCW-System wie create_room_plan erwartet
    robot_heading_deg = float(yaw_img_deg) % 360.0

    # Zeichnen wie in draw.py/few_shot.py
    fig, ax = create_room_plan(robot_x=robot_x_cm, robot_y=robot_y_cm, robot_heading=robot_heading_deg, show_fov=True)

    plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
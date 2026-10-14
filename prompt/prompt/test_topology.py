import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import json
import os

def load_room_layout():
    """
    Lädt das ROOM_LAYOUT aus der roomlayout.json Datei.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'roomlayout.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            room_layout = json.load(f)
        print(f"✅ ROOM_LAYOUT erfolgreich geladen aus: {json_path}")
        return room_layout
    except Exception as e:
        print(f"❌ Fehler beim Laden der roomlayout.json: {e}")
        return None

def create_room_plan_with_topology():
    """
    Erstellt einen Raumplan und visualisiert die Topologie-Nodes aus der roomlayout.json.
    """
    # Lade Room Layout aus JSON
    room_layout = load_room_layout()
    if not room_layout:
        print("❌ Konnte roomlayout.json nicht laden!")
        return None, None
    
    fig, ax = plt.subplots(1, 1, figsize=(16, 14))
    
    # === WÄNDE ===
    wall_points = room_layout["walls"]["points"]
    wall_x = [p[0] for p in wall_points]
    wall_y = [p[1] for p in wall_points]
    ax.plot(wall_x, wall_y, 'k-', linewidth=3)
    
    # === TÜREN ===
    for door in room_layout["doors"]:
        from_point = door["from"]
        to_point = door["to"]
        ax.plot([from_point[0], to_point[0]], [from_point[1], to_point[1]], 
                'brown', linewidth=8, alpha=0.8)
        # Label hinzufügen
        mid_x = (from_point[0] + to_point[0]) / 2
        mid_y = (from_point[1] + to_point[1]) / 2
        ax.text(mid_x, mid_y - 15, door["name"], fontsize=8, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='wheat', alpha=0.7))
    
    # === FENSTER ===
    for i, window in enumerate(room_layout["windows"]):
        from_point = window["from"]
        to_point = window["to"]
        ax.plot([from_point[0], to_point[0]], [from_point[1], to_point[1]], 
                'lightblue', linewidth=8, alpha=0.7)
        # Label hinzufügen
        mid_x = (from_point[0] + to_point[0]) / 2
        mid_y = (from_point[1] + to_point[1]) / 2
        ax.text(mid_x + 15, mid_y, f'F{i+1}', fontsize=8, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='lightblue', alpha=0.8))
    
    # === WHITEBOARDS ===
    for whiteboard in room_layout["whiteboards"]:
        from_point = whiteboard["from"]
        to_point = whiteboard["to"]
        ax.plot([from_point[0], to_point[0]], [from_point[1], to_point[1]], 
                'white', linewidth=8, alpha=1.0)
        ax.plot([from_point[0], to_point[0]], [from_point[1], to_point[1]], 
                'black', linewidth=2)
        # Label hinzufügen
        mid_x = (from_point[0] + to_point[0]) / 2
        mid_y = (from_point[1] + to_point[1]) / 2
        ax.text(mid_x, mid_y - 12, whiteboard["name"], fontsize=8, ha='center', va='center')
    
    # === OBJEKTE AUS TOPOLOGIE VISUALISIEREN ===
    if "topology" in room_layout and "nodes" in room_layout["topology"]:
        nodes = room_layout["topology"]["nodes"]
        
        # Farbmapping für Stühle
        color_map = {
            'blau': 'royalblue',
            'grau': 'lightgray',
            'schwarz': 'black'
        }
        
        # Zeichne alle Objekte aus der Topologie
        for node_id, node in nodes.items():
            if node.get("type") == "obstacle":
                obstacle_type = node.get("obstacle_type", "unknown")
                center_x, center_y = node["x"], node["y"]
                
                if obstacle_type == "table":
                    if "diameter" in node:  # Runder Tisch
                        circle = patches.Circle((center_x, center_y), node["diameter"]/2, 
                                                facecolor='saddlebrown', edgecolor='black', linewidth=1.5)
                        ax.add_patch(circle)
                    else:  # Rechteckiger Tisch
                        width = node.get("width", 120)
                        height = node.get("height", 80)
                        rect = patches.Rectangle((center_x-width/2, center_y-height/2), width, height,
                                                 facecolor='saddlebrown', edgecolor='black', linewidth=1.5)
                        ax.add_patch(rect)
                    ax.text(center_x, center_y, node_id, fontsize=7, ha='center', va='center',
                            color='white', weight='bold')
                
                elif obstacle_type == "cabinet":
                    width = node.get("width", 80)
                    height = node.get("height", 40)
                    rect = patches.Rectangle((center_x-width/2, center_y-height/2), width, height,
                                             facecolor='darkslategray', edgecolor='black', linewidth=1.5)
                    ax.add_patch(rect)
                    ax.text(center_x, center_y, node_id, fontsize=7, ha='center', va='center', color='white')
                
                elif obstacle_type == "shelf":
                    width = node.get("width", 80)
                    height = node.get("height", 42)
                    rect = patches.Rectangle((center_x-width/2, center_y-height/2), width, height,
                                             facecolor='darkgoldenrod', edgecolor='black', linewidth=1.5)
                    ax.add_patch(rect)
                    ax.text(center_x, center_y, node_id, fontsize=8, ha='center', va='center', color='white')
                
                elif obstacle_type == "dresser":
                    width = node.get("width", 80)
                    height = node.get("height", 44)
                    rect = patches.Rectangle((center_x-width/2, center_y-height/2), width, height,
                                             facecolor='darkgoldenrod', edgecolor='black', linewidth=1.5)
                    ax.add_patch(rect)
                    description = node.get("description", "")
                    display_name = f"{node_id}\n({description})" if description else node_id
                    ax.text(center_x, center_y, display_name, fontsize=8, ha='center', va='center', color='white')
                
                elif obstacle_type == "carton":
                    width = node.get("width", 40)
                    height = node.get("height", 30)
                    rect = patches.Rectangle((center_x-width/2, center_y-height/2), width, height,
                                             facecolor='burlywood', edgecolor='black', linewidth=1)
                    ax.add_patch(rect)
                    ax.text(center_x, center_y, node_id, fontsize=7, ha='center', va='center')
                
                elif obstacle_type == "robot":
                    width = node.get("width", 40)
                    height = node.get("height", 40)
                    rect = patches.Rectangle((center_x-width/2, center_y-height/2), width, height, 
                                             facecolor='lightcoral', edgecolor='darkred', linewidth=2)
                    ax.add_patch(rect)
                    ax.text(center_x, center_y, node_id, fontsize=8, ha='center', va='center',
                            color='white', weight='bold')
                
                elif obstacle_type == "trashcan":
                    diameter = node.get("diameter", 30)
                    circle = patches.Circle((center_x, center_y), diameter/2, facecolor='gray',
                                            edgecolor='black', linewidth=1.5)
                    ax.add_patch(circle)
                    ax.text(center_x, center_y, 'M', fontsize=8, ha='center', va='center',
                            color='white', weight='bold')
                
                elif obstacle_type == "chair":
                    width = node.get("width", 20)
                    height = node.get("height", 20)
                    color = color_map.get(node.get("color", "grau"), "lightgray")
                    
                    rect = patches.Rectangle((center_x-width/2, center_y-height/2), width, height, 
                                             facecolor=color, edgecolor='darkgray', linewidth=1.5)
                    ax.add_patch(rect)
                    
                    # Beschriftung neben Stuhl
                    chair_color = node.get("color", "grau")
                    ax.text(center_x, center_y-16, f'{node_id} ({chair_color})', 
                            fontsize=6, ha='center', va='center',
                            bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
    
    # === NAVIGABLE AREAS ALS BEREICHE VISUALISIEREN ===
    if "topology" in room_layout and "navigable_areas" in room_layout["topology"]:
        navigable_areas = room_layout["topology"]["navigable_areas"]
        
        for i, area in enumerate(navigable_areas):
            x, y = area["bottom_left"]
            width = area["width"]
            height = area["height"]
            
            # Zeichne navigable_area als halbtransparenten Bereich
            rect = patches.Rectangle((x, y), width, height,
                                     facecolor='lightgreen', alpha=0.2,
                                     edgecolor='green', linewidth=1.5,
                                     label='Navigable Areas' if i == 0 else None)
            ax.add_patch(rect)
            
            # Area-Index in der Mitte
            center_x = x + width/2
            center_y = y + height/2
            ax.text(center_x, center_y, f'A{i}', fontsize=8, ha='center', va='center',
                    bbox=dict(boxstyle="round,pad=0.2", facecolor='lightgreen', alpha=0.9),
                    weight='bold', color='darkgreen')
    
    # === TOPOLOGISCHE KNOTEN ===
    if "topology" in room_layout and "nodes" in room_layout["topology"]:
        nodes = room_layout["topology"]["nodes"]
        
        first_navigable = True
        first_bbox = True
        
        for node_id, node in nodes.items():
            x, y = node["x"], node["y"]
            
            if node.get("type") == "navigable":
                # Navigierbare Knoten in grün (ohne ID-Text)
                circle = patches.Circle((x, y), 3, facecolor='lime', edgecolor='green', linewidth=1,
                                       label='Befahrbare Knotenpunkte' if first_navigable else None)
                ax.add_patch(circle)
                first_navigable = False
            
            elif node.get("type") == "obstacle":
                # Hindernis-Knoten in rot (nur ID bei wichtigen Objekten)
                circle = patches.Circle((x, y), 4, facecolor='red', edgecolor='darkred', linewidth=1.5)
                ax.add_patch(circle)
                
                # ID nur bei größeren Objekten anzeigen
                obstacle_type = node.get("obstacle_type", "unknown")
                if obstacle_type in ["table", "cabinet", "shelf", "dresser", "robot"]:
                    ax.text(x+8, y+8, node_id, fontsize=5, color='darkred', weight='bold')
                
                # BOUNDING BOX FÜR HINDERNISSE IN DUNKEL ORANGE
                if obstacle_type in ["table", "cabinet", "shelf", "dresser", "carton", "robot", "chair"]:
                    # Prüfe zuerst, ob es ein runder Tisch ist
                    if obstacle_type == "table" and "diameter" in node:
                        # Kreisförmige Bounding Box für runde Tische
                        diameter = node["diameter"]
                        bbox_circle = patches.Circle((x, y), diameter/2,
                                                     facecolor='none', edgecolor='darkorange',
                                                     linewidth=2, linestyle='--', alpha=0.8,
                                                     label='Bounding-Boxen' if first_bbox else None)
                        ax.add_patch(bbox_circle)
                        first_bbox = False
                    else:
                        # Rechteckige Bounding Box für alle anderen
                        width = node.get("width", 40)
                        height = node.get("height", 40)
                        bbox_rect = patches.Rectangle((x - width/2, y - height/2), width, height,
                                                      facecolor='none', edgecolor='darkorange', 
                                                      linewidth=2, linestyle='--', alpha=0.8,
                                                      label='Bounding-Boxen' if first_bbox else None)
                        ax.add_patch(bbox_rect)
                        first_bbox = False
                
                elif obstacle_type == "trashcan" and "diameter" in node:
                    # Kreisförmige Bounding Box
                    diameter = node["diameter"]
                    bbox_circle = patches.Circle((x, y), diameter/2,
                                                 facecolor='none', edgecolor='darkorange',
                                                 linewidth=2, linestyle='--', alpha=0.8,
                                                 label='Bounding-Boxen' if first_bbox else None)
                    ax.add_patch(bbox_circle)
                    first_bbox = False
                
                elif obstacle_type in ["wall", "door", "window", "whiteboard"]:
                    # Spezielle Behandlung für Raum-Elemente
                    if "width" in node and "height" in node:
                        width = node["width"]
                        height = node["height"]
                        bbox_rect = patches.Rectangle((x - width/2, y - height/2), width, height,
                                                      facecolor='none', edgecolor='darkorange',
                                                      linewidth=2, linestyle='--', alpha=0.8,
                                                      label='Bounding-Boxen' if first_bbox else None)
                        ax.add_patch(bbox_rect)
                        first_bbox = False
    
    # === VERBINDUNGEN ZWISCHEN NODES ===
    if "topology" in room_layout and "connections" in room_layout["topology"]:
        connections = room_layout["topology"]["connections"]
        nodes = room_layout["topology"]["nodes"]
        
        for i, connection in enumerate(connections):
            node1_id = connection["node1"]
            node2_id = connection["node2"]
            
            if node1_id in nodes and node2_id in nodes:
                x1, y1 = nodes[node1_id]["x"], nodes[node1_id]["y"]
                x2, y2 = nodes[node2_id]["x"], nodes[node2_id]["y"]
                
                # Verbindung als Linie zeichnen
                ax.plot([x1, x2], [y1, y2], 'b-', linewidth=0.8, alpha=0.6, 
                       label='Topologie Nachbarschaften' if i == 0 else None)
    
    # === NAVIGABLE AREA NACHBARSCHAFTEN ===
    if "topology" in room_layout and "navigable_areas" in room_layout["topology"]:
        navigable_areas = room_layout["topology"]["navigable_areas"]
        
        # Zeichne Verbindungen zwischen benachbarten navigable_areas in lila
        for area_idx, area in enumerate(navigable_areas):
            if "neighbors" in area:
                # Berechne Mittelpunkt der aktuellen Area
                area_center_x = area["center"][0]
                area_center_y = area["center"][1]
                
                # Durchlaufe alle Nachbarn in allen Richtungen
                for direction, neighbor_indices in area["neighbors"].items():
                    for neighbor_idx in neighbor_indices:
                        # Verhindere doppelte Linien (nur zeichnen wenn area_idx < neighbor_idx)
                        if area_idx < neighbor_idx and neighbor_idx < len(navigable_areas):
                            neighbor_area = navigable_areas[neighbor_idx]
                            neighbor_center_x = neighbor_area["center"][0]
                            neighbor_center_y = neighbor_area["center"][1]
                            
                            # Zeichne Verbindung in lila/violett
                            ax.plot([area_center_x, neighbor_center_x], 
                                   [area_center_y, neighbor_center_y], 
                                   color='magenta', linewidth=2.5, alpha=0.8,
                                   label='Navigable Area Nachbarschaften' if area_idx == 0 and direction == list(area["neighbors"].keys())[0] and neighbor_indices and neighbor_indices[0] == neighbor_idx else None)
    
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
    ax.set_ylim(-60, 720)
    ax.set_aspect('equal')
    ax.set_xlabel('x [cm]', fontsize=12, weight='bold')
    ax.set_ylabel('y [cm]', fontsize=12, weight='bold')
    ax.set_title('Raumplan mit Topologie-Visualisierung', fontsize=14, weight='bold')
    
    # Legende mit benutzerdefinierten Handles
    from matplotlib.lines import Line2D
    
    # Sammle automatisch generierte Legend-Handles
    handles, labels = ax.get_legend_handles_labels()
    
    # Erstelle benutzerdefinierten Handle für befahrbare Knotenpunkte als Kreis
    navigable_circle = Line2D([0], [0], marker='o', color='w', 
                              markerfacecolor='lime', markeredgecolor='green',
                              markersize=6, linewidth=0, markeredgewidth=1,
                              label='Befahrbare Knotenpunkte')
    
    # Entferne den automatisch generierten "Befahrbare Knotenpunkte" Eintrag und ersetze ihn
    new_handles = []
    new_labels = []
    for handle, label in zip(handles, labels):
        if label != 'Befahrbare Knotenpunkte':
            new_handles.append(handle)
            new_labels.append(label)
        else:
            new_handles.append(navigable_circle)
            new_labels.append('Befahrbare Knotenpunkte')
    
    ax.legend(new_handles, new_labels, loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)
    
    # Anpassung der Margen
    plt.subplots_adjust(left=0.1, right=0.8, top=0.95, bottom=0.1)
    
    return fig, ax

# === VERWENDUNG ===
if __name__ == "__main__":
    print("🔄 Lade roomlayout.json und visualisiere Topologie...")
    
    # Erstelle Raumplan mit Topologie-Visualisierung
    fig, ax = create_room_plan_with_topology()
    
    if fig and ax:
        print("✅ Raumplan mit Topologie erfolgreich erstellt!")
        
        # Bild speichern
        plt.savefig('room_plan_with_topology_and_bounding_boxes.png', dpi=300, bbox_inches='tight')
        print(f"✅ Raumplan mit Topologie und Bounding Boxes gespeichert als: room_plan_with_topology_and_bounding_boxes.png")
        
        plt.show()
    else:
        print("❌ Fehler beim Erstellen des Raumplans!")
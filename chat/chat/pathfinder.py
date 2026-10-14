"""
Pathfinder Module - Berechnet A* Pfade durch die Topologie und bestimmt Orientierungen.
"""

import math
import json
import os
from typing import List, Tuple, Optional, Dict, Any
import heapq


def load_topology() -> Optional[Dict[str, Any]]:
    """
    Lädt die Topologie-Daten aus der roomlayout.json Datei.
    
    Returns:
        dict: Topologie-Dictionary oder None bei Fehler
    """
    try:
        prompt_dir = os.path.join(os.path.expanduser('~'), 'ros2_ws', 'src', 'prompt', 'prompt')
        roomlayout_json_path = os.path.join(prompt_dir, 'roomlayout.json')
        
        if os.path.exists(roomlayout_json_path):
            with open(roomlayout_json_path, 'r', encoding='utf-8') as f:
                room_layout = json.load(f)
                return room_layout.get("topology", {}).get("nodes", {})
        else:
            print(f"❌ Topology file not found: {roomlayout_json_path}")
            return None
    except Exception as e:
        print(f"❌ Error loading topology: {e}")
        return None


def find_nearest_navigable_node(x: float, y: float, topology: Dict[str, Any]) -> Optional[str]:
    """
    Findet den nächsten befahrbaren Node in der Topologie zu einer gegebenen Position.
    
    Args:
        x, y: Zielposition in cm
        topology: Topologie-Dictionary
        
    Returns:
        str: Node-ID des nächsten befahrbaren Nodes oder None
    """
    if not topology:
        return None
        
    min_distance = float('inf')
    nearest_node_id = None
    
    for node_id, node_data in topology.items():
        if node_data.get("type") == "navigable":
            node_x = node_data.get("x", 0)
            node_y = node_data.get("y", 0)
            
            # Berechne euklidische Distanz
            distance = math.sqrt((x - node_x)**2 + (y - node_y)**2)
            
            if distance < min_distance:
                min_distance = distance
                nearest_node_id = node_id
                
    return nearest_node_id


def get_node_neighbors(node_id: str, topology: Dict[str, Any]) -> List[str]:
    """
    Gibt alle befahrbaren Nachbarn eines Nodes zurück, inklusive diagonaler Verbindungen.
    
    Args:
        node_id: ID des Nodes
        topology: Topologie-Dictionary
        
    Returns:
        list: Liste von Nachbar-Node-IDs
    """
    if node_id not in topology:
        return []
        
    neighbors = []
    node_data = topology[node_id]
    node_x = node_data.get("x", 0)
    node_y = node_data.get("y", 0)
    
    # Standardnachbarn (Norden, Süden, Osten, Westen)
    standard_neighbors = node_data.get("neighbours", {})
    for direction, neighbor_id in standard_neighbors.items():
        if neighbor_id in topology and topology[neighbor_id].get("type") == "navigable":
            neighbors.append(neighbor_id)
    
    # Suche nach diagonalen Nachbarn im 25cm Raster
    # Prüfe alle Nodes in der näheren Umgebung für diagonale Verbindungen
    for other_id, other_data in topology.items():
        if other_id == node_id or other_data.get("type") != "navigable":
            continue
            
        other_x = other_data.get("x", 0)
        other_y = other_data.get("y", 0)
        
        dx = abs(other_x - node_x)
        dy = abs(other_y - node_y)
        
        # Diagonale Nachbarn: 25cm in beide Richtungen (z.B. 25x25, 50x50, etc.)
        # Aber nicht weiter als ~35cm Luftlinie für direkte Verbindung
        if dx > 0 and dy > 0 and dx <= 25 and dy <= 25:
            distance = math.sqrt(dx**2 + dy**2)
            if distance <= 36:  # ~25*sqrt(2) für diagonale
                if other_id not in neighbors:
                    neighbors.append(other_id)
    
    return neighbors


def calculate_heuristic(node1_id: str, node2_id: str, topology: Dict[str, Any]) -> float:
    """
    Berechnet die heuristische Distanz (euklidisch) zwischen zwei Nodes.
    
    Args:
        node1_id, node2_id: Node-IDs
        topology: Topologie-Dictionary
        
    Returns:
        float: Heuristische Distanz
    """
    if node1_id not in topology or node2_id not in topology:
        return float('inf')
        
    node1 = topology[node1_id]
    node2 = topology[node2_id]
    
    x1, y1 = node1.get("x", 0), node1.get("y", 0)
    x2, y2 = node2.get("x", 0), node2.get("y", 0)
    
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def calculate_movement_cost(node1_id: str, node2_id: str, topology: Dict[str, Any]) -> float:
    """
    Berechnet die tatsächlichen Bewegungskosten zwischen zwei Nodes.
    
    Args:
        node1_id, node2_id: Node-IDs
        topology: Topologie-Dictionary
        
    Returns:
        float: Bewegungskosten (Distanz)
    """
    return calculate_heuristic(node1_id, node2_id, topology)


def a_star_pathfinding(start_node_id: str, goal_node_id: str, topology: Dict[str, Any]) -> List[str]:
    """
    Führt A* Pathfinding durch die Topologie aus.
    
    Args:
        start_node_id: Start-Node-ID
        goal_node_id: Ziel-Node-ID
        topology: Topologie-Dictionary
        
    Returns:
        list: Liste von Node-IDs, die den Pfad vom Start zum Ziel darstellen
    """
    if not topology or start_node_id not in topology or goal_node_id not in topology:
        return []
    
    # A* Datenstrukturen
    open_set = []
    heapq.heappush(open_set, (0, start_node_id))
    
    came_from = {}
    g_score = {start_node_id: 0}
    f_score = {start_node_id: calculate_heuristic(start_node_id, goal_node_id, topology)}
    
    while open_set:
        current_f, current_node = heapq.heappop(open_set)
        
        if current_node == goal_node_id:
            # Pfad rekonstruieren
            path = []
            while current_node in came_from:
                path.append(current_node)
                current_node = came_from[current_node]
            path.append(start_node_id)
            path.reverse()
            return path
        
        # Nachbarn durchsuchen
        neighbors = get_node_neighbors(current_node, topology)
        for neighbor in neighbors:
            tentative_g_score = g_score[current_node] + calculate_movement_cost(current_node, neighbor, topology)
            
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current_node
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + calculate_heuristic(neighbor, goal_node_id, topology)
                
                # Füge zu open_set hinzu, wenn nicht bereits enthalten
                if not any(neighbor == item[1] for item in open_set):
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
    
    # Kein Pfad gefunden
    return []


def calculate_orientation_from_movement(from_node_id: str, to_node_id: str, topology: Dict[str, Any]) -> float:
    """
    Berechnet die Orientierung basierend auf der Bewegung zwischen zwei Nodes.
    
    Args:
        from_node_id: Start-Node-ID
        to_node_id: Ziel-Node-ID
        topology: Topologie-Dictionary
        
    Returns:
        float: Orientierung in Grad (0-359)
    """
    if from_node_id not in topology or to_node_id not in topology:
        return 0.0
    
    from_node = topology[from_node_id]
    to_node = topology[to_node_id]
    
    from_x, from_y = from_node.get("x", 0), from_node.get("y", 0)
    to_x, to_y = to_node.get("x", 0), to_node.get("y", 0)
    
    # Berechne Richtungsvektor
    dx = to_x - from_x
    dy = to_y - from_y
    
    if dx == 0 and dy == 0:
        return 0.0  # Keine Bewegung
    
    # Berechne Winkel in Radiant, dann in Grad
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    
    # Normalisiere auf 0-359 Grad
    angle_deg = angle_deg % 360
    
    return angle_deg


def calculate_target_orientation(robot_x: float, robot_y: float, target_x: float, target_y: float) -> Tuple[float, float]:
    """
    Berechnet die Zielorientierung basierend auf dem A*-Pfad durch die Topologie.
    
    Args:
        robot_x, robot_y: Aktuelle Roboter-Position in cm
        target_x, target_y: Ziel-Position in cm
        
    Returns:
        tuple: (new_orientation_deg, path_length) oder (0.0, 0.0) bei Fehler
    """
    try:
        # 1. Lade Topologie
        topology = load_topology()
        if not topology:
            print("❌ Konnte Topologie nicht laden")
            return 0.0, 0.0
        
        # 2. Finde nächste Nodes
        robot_node_id = find_nearest_navigable_node(robot_x, robot_y, topology)
        target_node_id = find_nearest_navigable_node(target_x, target_y, topology)
        
        if not robot_node_id or not target_node_id:
            print(f"❌ Konnte keine navigierbaren Nodes finden: robot={robot_node_id}, target={target_node_id}")
            return 0.0, 0.0
        
        print(f"🤖 Roboter-Node: {robot_node_id} (nächster zu {robot_x}, {robot_y})")
        print(f"🎯 Ziel-Node: {target_node_id} (nächster zu {target_x}, {target_y})")
        
        # 3. Berechne A*-Pfad
        path = a_star_pathfinding(robot_node_id, target_node_id, topology)
        
        if len(path) < 2:
            print(f"❌ Kein gültiger Pfad gefunden oder zu kurz: {path}")
            return 0.0, 0.0
        
        print(f"🗺️ A*-Pfad: {' -> '.join(path)}")
        
        # 4. Berechne Orientierung aus letztem Schritt
        last_from_node = path[-2]  # Vorletzter Node
        last_to_node = path[-1]    # Letzter Node (Ziel)
        
        orientation = calculate_orientation_from_movement(last_from_node, last_to_node, topology)
        
        # 5. Berechne Pfadlänge
        path_length = 0.0
        for i in range(len(path) - 1):
            path_length += calculate_movement_cost(path[i], path[i + 1], topology)
        
        print(f"🧭 Berechnete Orientierung: {orientation:.1f}° (letzter Schritt: {last_from_node} -> {last_to_node})")
        print(f"📏 Pfadlänge: {path_length:.1f}cm")
        
        return orientation, path_length
        
    except Exception as e:
        print(f"❌ Fehler bei Orientierungsberechnung: {e}")
        return 0.0, 0.0


def debug_topology_nodes(x: float, y: float, radius: float = 100.0) -> None:
    """
    Debug-Funktion: Zeigt alle Nodes in einem Radius um eine Position an.
    
    Args:
        x, y: Position
        radius: Suchradius in cm
    """
    topology = load_topology()
    if not topology:
        return
    
    print(f"\n🔍 Nodes im Radius {radius}cm um Position ({x}, {y}):")
    found_nodes = []
    
    for node_id, node_data in topology.items():
        if node_data.get("type") == "navigable":
            node_x = node_data.get("x", 0)
            node_y = node_data.get("y", 0)
            distance = math.sqrt((x - node_x)**2 + (y - node_y)**2)
            
            if distance <= radius:
                found_nodes.append((distance, node_id, node_x, node_y))
    
    # Sortiere nach Distanz
    found_nodes.sort()
    
    for distance, node_id, node_x, node_y in found_nodes:
        print(f"  {node_id}: ({node_x}, {node_y}) - Distanz: {distance:.1f}cm")
    
    if not found_nodes:
        print(f"  Keine Nodes gefunden im Radius {radius}cm")

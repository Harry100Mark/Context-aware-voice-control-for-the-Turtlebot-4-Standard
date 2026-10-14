"""
Node Finder Modul - Findet den nächsten befahrbaren Node für eine gegebene Position.
"""

import json
import os
import math

def load_room_layout():
    """Lädt ROOM_LAYOUT aus roomlayout.json"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    roomlayout_json_path = os.path.join(current_dir, 'roomlayout.json')
    
    if os.path.exists(roomlayout_json_path):
        with open(roomlayout_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"roomlayout.json nicht gefunden in {roomlayout_json_path}")

def find_nearest_navigable_node(robot_x, robot_y, room_layout=None):
    """
    Findet den nächsten befahrbaren Node für eine Roboterposition.
    
    Args:
        robot_x (float): X-Koordinate des Roboters
        robot_y (float): Y-Koordinate des Roboters  
        room_layout (dict, optional): ROOM_LAYOUT Dictionary. Falls None, wird aus JSON geladen.
    
    Returns:
        dict: {
            "node_id": "id_x_y",
            "position": {"x": x, "y": y},
            "distance": distanz_in_cm
        }
        oder None falls kein Node gefunden
    """
    if room_layout is None:
        room_layout = load_room_layout()
    
    topology = room_layout.get("topology", {})
    nodes = topology.get("nodes", {})
    
    # Filtere nur navigable Nodes
    navigable_nodes = {
        node_id: node for node_id, node in nodes.items() 
        if node.get("type") == "navigable"
    }
    
    if not navigable_nodes:
        return None
    
    closest_node = None
    closest_distance = float('inf')
    
    # Finde den nächsten navigable Node
    for node_id, node in navigable_nodes.items():
        node_x = node["x"]
        node_y = node["y"]
        
        # Berechne euklidische Distanz
        distance = math.sqrt((robot_x - node_x)**2 + (robot_y - node_y)**2)
        
        if distance < closest_distance:
            closest_distance = distance
            closest_node = {
                "node_id": node_id,
                "position": {
                    "x": node_x,
                    "y": node_y
                },
                "distance": round(distance, 2)
            }
    
    return closest_node

def add_nearest_node_to_pose(pose_dict, room_layout=None):
    """
    Fügt einem Pose-Dictionary die Referenz zum nächsten navigable Node hinzu.
    
    Args:
        pose_dict (dict): Pose Dictionary mit position.x und position.y
        room_layout (dict, optional): ROOM_LAYOUT Dictionary
    
    Returns:
        dict: Erweiterte Pose mit "nearest_navigable_node" Feld
    """
    if "position" not in pose_dict:
        return pose_dict
    
    robot_x = pose_dict["position"]["x"]
    robot_y = pose_dict["position"]["y"]
    
    nearest_node = find_nearest_navigable_node(robot_x, robot_y, room_layout)
    
    if nearest_node:
        pose_dict["nearest_navigable_node"] = nearest_node
    
    return pose_dict

# Test der Funktionen
if __name__ == "__main__":
    # Test mit verschiedenen Positionen
    test_positions = [
        (600, 600),
        (500, 260),
        (100, 300),
        (400, 400)
    ]
    
    room_layout = load_room_layout()
    
    print("🔍 TESTE NODE FINDER")
    print("=" * 50)
    
    for x, y in test_positions:
        nearest = find_nearest_navigable_node(x, y, room_layout)
        if nearest:
            print(f"Position ({x}, {y}) -> Node {nearest['node_id']} bei ({nearest['position']['x']}, {nearest['position']['y']}) - Distanz: {nearest['distance']}cm")
        else:
            print(f"Position ({x}, {y}) -> Kein navigable Node gefunden")
    
    print("=" * 50)

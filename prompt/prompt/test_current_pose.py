#!/usr/bin/env python3
"""
Test-Skript für promptBuilder mit Node-Referenzen
"""

import sys
import os

# Füge das prompt Modul zum Path hinzu
sys.path.append('/home/harry/ros2_ws/src/prompt')

from prompt.fewshot import create_turtlebot_json

def test_current_pose():
    """Teste die aktuelle Pose mit Node-Referenz"""
    
    # Test-Positionen
    test_poses = [
        (600, 600, 180),  # Position auf einem Node
        (500, 260, 225),  # Position nahe einem Node  
        (100, 300, 45),   # Eine andere Position
        (480, 360, 0),    # Zentrale Position
    ]
    
    print("🔍 TESTE AKTUELLE POSE MIT NODE-REFERENZEN")
    print("=" * 60)
    
    for i, (x, y, heading) in enumerate(test_poses, 1):
        print(f"\n📍 TEST POSE {i}: Position ({x}, {y}), Richtung {heading}°")
        print("-" * 40)
        
        turtlebot_data = create_turtlebot_json(x, y, heading)
        
        print(f"Position: ({turtlebot_data['position']['x']}, {turtlebot_data['position']['y']})")
        print(f"Richtung: {turtlebot_data['orientation']['compass_direction']} ({turtlebot_data['orientation']['angle_degrees']}°)")
        
        if 'nearest_navigable_node' in turtlebot_data:
            node_info = turtlebot_data['nearest_navigable_node']
            print(f"✅ Nächster Node: {node_info['node_id']}")
            print(f"   Node Position: ({node_info['position']['x']}, {node_info['position']['y']})")
            print(f"   Distanz: {node_info['distance']}cm")
        else:
            print("❌ Kein nearest_navigable_node gefunden!")
        
        if turtlebot_data.get('current_navigable_area'):
            area = turtlebot_data['current_navigable_area']
            print(f"📍 Navigable Area: {area['bottom_left']} + {area['width']}x{area['height']}")
        else:
            print("📍 Nicht in navigable area")
    
    print("\n" + "=" * 60)
    print("✅ Test abgeschlossen!")

if __name__ == "__main__":
    test_current_pose()

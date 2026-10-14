#!/usr/bin/env python3
"""
Reset Script für vorherige Daten zwischen den Runden.
Löscht die previous_data.json Datei, so dass die nächste Runde
ohne vorherige Daten startet.
"""

import os

def reset_previous_data():
    """Löscht die previous_data.json Datei."""
    home = os.path.expanduser('~')
    base_ws = os.path.join(home, 'ros2_ws')
    data_file = os.path.join(base_ws, 'src', 'prompt', 'previous_data.json')
    
    if os.path.exists(data_file):
        os.remove(data_file)
        print(f"✅ Previous data file deleted: {data_file}")
    else:
        print(f"ℹ️  Previous data file not found: {data_file}")

if __name__ == '__main__':
    reset_previous_data()
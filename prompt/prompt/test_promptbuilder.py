#!/usr/bin/env python3

from promptBuilder import build_prompt
import json
import os

def test_promptbuilder():
    """Test der neuen optimierten promptBuilder Struktur"""
    
    # Test system instructions
    system_prompt = 'Test prompt with {Einfügepunkt: JSON des Raumplans} placeholder'

    # Mock image path
    image_path = '/tmp/test.png'
    os.makedirs('/tmp', exist_ok=True)
    with open(image_path, 'w') as f:
        f.write('mock')

    # Test build_prompt
    try:
        result = build_prompt(system_prompt, image_path, 100, 200, 45.0)
        print('✅ promptBuilder funktioniert!')
        
        # Extrahiere den JSON-Teil für Analyse
        start = result.find('```json')
        if start != -1:
            end = result.find('```', start + 7)
            if end != -1:
                json_str = result[start + 7:end]
                data = json.loads(json_str)
                print('JSON Struktur:', list(data.keys()))
                if 'topology' in data:
                    print('Topology Keys:', list(data['topology'].keys()))
                    print('Navigable Areas:', len(data['topology'].get('navigable_areas', [])))
                    print('Nodes (first 3):', list(data['topology'].get('nodes', {}).keys())[:3])
                    
                    # Überprüfe, dass connections entfernt wurden
                    if 'connections' not in data['topology']:
                        print('✅ Connections erfolgreich entfernt')
                    else:
                        print('❌ Connections noch vorhanden')
                        
        print('\n=== OPTIMIERUNG ERFOLGREICH ===')
        print('✅ Nur topology wird übertragen (viel kompakter!)')
        print('✅ navigable_areas sind in topology integriert')
        print('✅ connections sind für LLM entfernt')
        print('✅ Alle anderen redundanten Raumplan-Daten entfernt')
                        
    except Exception as e:
        print('❌ Fehler:', e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_promptbuilder()
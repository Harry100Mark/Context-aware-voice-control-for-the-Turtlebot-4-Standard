"""
Prompt Builder Modul für die Erstellung von Gemini Prompts.
Ersetzt Platzhalter im System-Prompt mit aktuellen Daten und fügt eine kompakte Few-Shot Galerie ein.
"""

import json
import os
import time

# Import handling für perspectiveTaker
try:
    from . import perspectiveTaker
except ImportError:
    import perspectiveTaker

# Import handling für node_finder
try:
    from .node_finder import find_nearest_navigable_node, add_nearest_node_to_pose
except ImportError:
    from node_finder import find_nearest_navigable_node, add_nearest_node_to_pose

def _safe_json(obj):
    """Safely dumps JSON without ASCII escaping for readability."""
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"[Fehler beim JSON-Formatieren: {e}]"

def _to_top_level_schema(example_output):
    """Converts an example output with actions[] into the required top-level schema.
    Picks the first Navigieren or Keine action and maps fields accordingly.
    """
    try:
        explanation = example_output.get("explanation", "")
        reasoning = example_output.get("reasoning", explanation)
        actions = example_output.get("actions", [])
        if not actions:
            return {
                "Aktion": "Keine",
                "answer": "",
                "explanation": explanation,
                "reasoning": reasoning
            }
        first = actions[0]
        aktion = first.get("aktion", "Keine")
        if aktion == "Navigieren":
            params = first.get("parameters", {}).get("zielposition", {})
            verification = first.get("verification")
            return {
                "Aktion": "Navigieren",
                "Parameter": {
                    "Zielposition": {
                        "x": params.get("x", 0),
                        "y": params.get("y", 0),
                        "z": params.get("z", 0)
                    }
                },
                "Einheiten": {"Position": "Zentimeter"},
                "verification": verification,
                "explanation": explanation,
                "reasoning": reasoning
            }
        elif aktion == "Keine":
            return {
                "Aktion": "Keine",
                "answer": first.get("answer", ""),
                "explanation": explanation,
                "reasoning": reasoning
            }
        else:
            # For unsupported actions in curated set, fall back to Keine to avoid confusing the model
            return {
                "Aktion": "Keine",
                "answer": "(Beispiel-Aktion wird im System nicht unterstützt)",
                "explanation": explanation,
                "reasoning": reasoning
            }
    except Exception as e:
        return {
            "Aktion": "Keine",
            "answer": f"Fehler beim Transformieren eines Beispiels: {e}",
            "explanation": "",
            "reasoning": ""
        }

def load_samples_data():
    """Lädt EXAMPLE_PROMPTS, EXAMPLE_OUTPUTS, EXAMPLE_POSES, EXAMPLE_OLD_PROMPTS und EXAMPLE_OLD_POSITIONS aus samples.json"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_json_path = os.path.join(current_dir, 'fewshots', 'samples.json')
    
    if os.path.exists(samples_json_path):
        try:
            with open(samples_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return (
                    data.get('EXAMPLE_PROMPTS', []),
                    data.get('EXAMPLE_OUTPUTS', []),
                    data.get('EXAMPLE_POSES', []),
                    data.get('EXAMPLE_OLD_PROMPTS', []),
                    data.get('EXAMPLE_OLD_POSITIONS', [])
                )
        except Exception as e:
            print(f"Fehler beim Laden von samples.json: {e}")
            return [], [], [], [], []
    else:
        print(f"samples.json nicht gefunden in {samples_json_path}")
        return [], [], [], [], []

# Lade die Sample-Daten
EXAMPLE_PROMPTS, EXAMPLE_OUTPUTS, EXAMPLE_POSES, EXAMPLE_OLD_PROMPTS, EXAMPLE_OLD_POSITIONS = load_samples_data()

def load_room_layout():
    """Lädt ROOM_LAYOUT aus roomlayout.json"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    roomlayout_json_path = os.path.join(current_dir, 'roomlayout.json')
    
    if os.path.exists(roomlayout_json_path):
        try:
            with open(roomlayout_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warnung: Konnte roomlayout.json nicht laden: {e}")
            return None
    else:
        print(f"Warnung: roomlayout.json nicht gefunden: {roomlayout_json_path}")
        return None

def build_prompt(system_instructions, image_path, turtlebot_x=None, turtlebot_y=None, turtlebot_heading=None, 
                 previous_command=None, previous_pose=None, previous_reasoning=None):
    """
    Baut den finalen Prompt für Gemini 2.5 Flash zusammen.
    """

    # Warte auf Bild-Erstellung (robust gegen Timing)
    max_wait_time = 15
    wait_start = time.time()
    time.sleep(2.0)
    while not os.path.exists(image_path):
        if time.time() - wait_start > max_wait_time:
            raise FileNotFoundError(f"Bild {image_path} wurde nicht rechtzeitig erstellt")
        time.sleep(0.5)
    time.sleep(1.0)

    # 1) Image URL
    image_url = f"file://{os.path.abspath(image_path)}"

    # 2) Turtlebot JSON (optional)
    turtlebot_data = None
    if all(param is not None for param in [turtlebot_x, turtlebot_y, turtlebot_heading]):
        try:
            from .fewshot import create_turtlebot_json
            turtlebot_data = create_turtlebot_json(turtlebot_x, turtlebot_y, turtlebot_heading)
        except Exception as e:
            turtlebot_data = {"error": f"Fehler bei Turtlebot-Daten: {e}"}

    # 3) Raumlayout laden (nur Topology)
    ROOM_LAYOUT = load_room_layout()
    if ROOM_LAYOUT is None:
        ROOM_LAYOUT = {"error": "ROOM_LAYOUT konnte nicht geladen werden"}
    if isinstance(ROOM_LAYOUT, dict) and "topology" in ROOM_LAYOUT:
        topology_data = ROOM_LAYOUT["topology"].copy()
        if "connections" in topology_data:
            del topology_data["connections"]
    else:
        topology_data = {"error": "Topology nicht verfügbar"}
    combined_room_data = {
        "topology": topology_data,
        "turtlebot": turtlebot_data
    }
    room_layout_json = _safe_json(combined_room_data)

    # 4) Roboterperspektive-Analyse (optional)
    perspective_analysis_json = "Keine Roboterperspektive-Analyse verfügbar"
    if all(param is not None for param in [turtlebot_x, turtlebot_y, turtlebot_heading]):
        try:
            perspective_analysis = perspectiveTaker.analyze_objects_around_turtlebot(
                turtlebot_x=turtlebot_x,
                turtlebot_y=turtlebot_y,
                turtlebot_heading=turtlebot_heading
            )
            perspective_analysis_json = _safe_json(perspective_analysis)
        except Exception as e:
            perspective_analysis_json = f"Fehler bei Roboterperspektive-Analyse: {e}"

    # 5) Platzhalter im System-Prompt ersetzen
    final_prompt = system_instructions.replace(
        "{Einfügepunkt: Bild der jetzigen Pose}", f"Bild der aktuellen Roboterposition: {image_url}"
    )
    final_prompt = final_prompt.replace(
        "{Einfügepunkt: JSON des Raumplans}", f"JSON des Raumplans (nur Topology mit Roboterposition):\n```json\n{room_layout_json}\n```"
    )
    final_prompt = final_prompt.replace(
        "{Einfügepunkt: JSON der Roboterperspektive}", f"JSON der Roboterperspektive:\n```json\n{perspective_analysis_json}\n```"
    )

    # 6) Alte Daten einsetzen (falls vorhanden)
    if previous_command is not None and previous_pose is not None:
        old_pose_text = f"Alter Befehl: \"{previous_command}\"\nAlte Pose: x={previous_pose[0]}cm, y={previous_pose[1]}cm, alpha={previous_pose[2]}°"
        final_prompt = final_prompt.replace("{Einfügepunkt: Alter Befehl und alte Pose}", old_pose_text)
    else:
        final_prompt = final_prompt.replace(
            "{Einfügepunkt: Alter Befehl und alte Pose}",
            "Kein vorheriger Befehl und keine vorherige Pose verfügbar (erster Befehl der Runde)"
        )
    if previous_reasoning is not None:
        final_prompt = final_prompt.replace("{Einfügepunkt: Alter Reasoning Prozess}", f"```\n{previous_reasoning}\n```")
    else:
        final_prompt = final_prompt.replace(
            "{Einfügepunkt: Alter Reasoning Prozess}",
            "Kein vorheriger Reasoning-Prozess verfügbar (erster Befehl der Runde)"
        )

    # 7) Kompakte Few-Shot Galerie einfügen (ohne Bilder)
    curated_indices = []
    total = min(len(EXAMPLE_PROMPTS), len(EXAMPLE_OUTPUTS), len(EXAMPLE_POSES))
    candidates = [2, 4, 6, 8, 9]  # C+B, D, E, F, I
    for idx in candidates:
        if 0 <= idx < total:
            curated_indices.append(idx)
    examples_text_parts = ["\n\n# === FEW-SHOT BEISPIELE (kompakte Auswahl) ==="]
    for i, idx in enumerate(curated_indices, start=1):
        pose_json = _safe_json(EXAMPLE_POSES[idx])
        navigation_command = EXAMPLE_PROMPTS[idx]
        transformed_output = _to_top_level_schema(EXAMPLE_OUTPUTS[idx])
        output_json = _safe_json(transformed_output)
        old_cmd = EXAMPLE_OLD_PROMPTS[idx] if idx < len(EXAMPLE_OLD_PROMPTS) else None
        old_pos = EXAMPLE_OLD_POSITIONS[idx] if idx < len(EXAMPLE_OLD_POSITIONS) else None
        old_block = ""
        if old_cmd or old_pos:
            parts = []
            if old_cmd:
                parts.append(f'Alter Befehl: "{old_cmd}"')
            if old_pos:
                old_pose_json = _safe_json({
                    "position": {"x": old_pos[0], "y": old_pos[1]},
                    "orientation": {"angle_degrees": old_pos[2]}
                })
                parts.append(f"Alte Pose (JSON):\n```json\n{old_pose_json}\n```")
            old_block = "\n" + "\n".join(parts)
        example_block = f"""
### Beispiel {i}:
Roboterpose (JSON):
```json
{pose_json}
```
Befehl des Menschen: "{navigation_command}"{old_block}
Erwartete Ausgabe:
```json
{output_json}
```
"""
        examples_text_parts.append(example_block)
    examples_text_parts.append("# === ENDE DER FEW-SHOT BEISPIELE ===\n")
    curated_examples_block = "\n".join(examples_text_parts)

    if "{Einfügepunkt: Few-Shot Beispiele}" in final_prompt:
        final_prompt = final_prompt.replace("{Einfügepunkt: Few-Shot Beispiele}", curated_examples_block)
    else:
        final_prompt = final_prompt.replace("# Schritt 2:", curated_examples_block + "\n# Schritt 2:")

    # 8) Finale Kontextwiederholung (falls im Prompt vorgesehen)
    final_prompt = final_prompt.replace(
        "{Einfügepunkt: Finales Bild der jetzigen Pose}", f"Aktueller Raumplan: {image_url}"
    )
    final_prompt = final_prompt.replace(
        "{Einfügepunkt: Finales JSON des Raumplans}",
        f"Aktueller JSON-Raumplan (nur Topology mit Roboterposition):\n```json\n{room_layout_json}\n```"
    )
    final_prompt = final_prompt.replace(
        "{Einfügepunkt: Neuer Prompt des Menschen}",
        "[Hier wird der transkribierte Text des Menschen eingefügt]"
    )

    return final_prompt
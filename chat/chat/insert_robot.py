from PIL import Image, ImageDraw
import os

# Dateien
HOME = os.path.expanduser("~")
ROOM_PATH = os.path.join(HOME, "ros2_ws", "src", "map", "Raumplan.png")
ROBOT_PATH = os.path.join(HOME, "ros2_ws", "src", "map", "Turtlebot_robot_target_units.png")  # aus transparent.py erzeugt
#OUTPUT_PATH = os.path.join(HOME, "ros2_ws", "src", "map", "Raumplan_Roboter.png")
OUTPUT_PATH = os.path.join(HOME, "ros2_ws", "src", "map", "currentPosition.png")

# Skalierungs-Konstanten (angepasst an neues Koordinatensystem aus roomplan.py)
# Ursprüngliche Pixel-Position vor Koordinatensystem-Änderung
ORIGINAL_ORIGIN_PIXELS = (230, 83)  # (x,y)
_dx_pixels = 900 - 230  # 670
_dy_pixels = 720 - 83   # 637
SCALE_X_UNITS_PER_PIXEL = 689 / _dx_pixels  # ≈1.02836
SCALE_Y_UNITS_PER_PIXEL = 654 / _dy_pixels  # ≈1.02667

# Neuer Ursprung: wo vorher y=-654 war (identisch zu roomplan.py)
ox_original, oy_original = ORIGINAL_ORIGIN_PIXELS
new_origin_y = int(oy_original + 654 / SCALE_Y_UNITS_PER_PIXEL)
ORIGIN_PIXELS = (ox_original, new_origin_y)

def units_to_pixels_x(units: float) -> float:
	return units / SCALE_X_UNITS_PER_PIXEL

def units_to_pixels_y(units: float) -> float:
	return -units / SCALE_Y_UNITS_PER_PIXEL  # Negativ für umgekehrtes Y-System

# ======= Konfiguration: Ziel-Koordinaten in RASTER-EINHEITEN (nicht Pixel!) =======
# Beispiel: Roboter-MITTE bei (x_units, y_units)
X_UNITS = 300  # anpassen (Einheiten für Mittelpunkt)
Y_UNITS = 300  # anpassen (Einheiten für Mittelpunkt)

# Orientierung des Roboters in Grad (0 = nach rechts / +x, 90 = nach oben / +y)
ORIENTATION_DEGREES = 260  # anpassen
# Sichtfeld / Field-of-View (FOV) Overlay konfigurieren
SHOW_FOV = True           # Ein-/Ausschalten
FOV_DEGREES = 90          # Öffnungswinkel
FOV_RANGE_UNITS = 200.0   # Reichweite in Einheiten (Raster-Einheiten)
FOV_COLOR = (100, 180, 255, 80)  # RGBA (hellblau, transparent)
# =============================================================================

def draw_fov(image: Image.Image, center_x: float, center_y: float, heading_deg: float):
	"""Zeichnet ein FOV als Keil mit Zentrum (center_x, center_y) in Bildpixeln.

	heading_deg: 0° = rechts, 90° = oben (gegen den Uhrzeigersinn)
	Verwendet unterschiedliche Skalierungen x/y für Reichweite, sodass leichte Anisotropie ausgeglichen wird.
	"""
	if FOV_DEGREES <= 0 or FOV_RANGE_UNITS <= 0:
		return

	# Reichweite in Pixel (für x und y separat) -> ergibt leicht elliptischen Keil wenn Skalen differieren.
	range_px_x = units_to_pixels_x(FOV_RANGE_UNITS)
	range_px_y = units_to_pixels_y(FOV_RANGE_UNITS)

	half_angle = FOV_DEGREES / 2.0
	start_angle = heading_deg - half_angle
	end_angle = heading_deg + half_angle

	# Schrittweite für die Arc-Punkte (je kleiner desto glatter)
	step = max(2, int(FOV_DEGREES / 15))  # ca. 6 Punkte für 90°
	angles = [start_angle + i * (FOV_DEGREES / step) for i in range(step + 1)]

	import math
	points = [(center_x, center_y)]
	for a in angles:
		rad = math.radians(a)
		x = center_x + math.cos(rad) * range_px_x
		y = center_y + math.sin(rad) * range_px_y  # Positiv für Standard-Koordinatensystem (CCW)
		points.append((x, y))
	# Polygon zeichnen
	overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
	draw = ImageDraw.Draw(overlay)
	draw.polygon(points, fill=FOV_COLOR)
	image.alpha_composite(overlay)


def update_robot_position(x_units: float, y_units: float, alpha_deg: float = 0.0, target_area=None):
    """
    Aktualisiert die Position des Roboters im Bild.
    
    Args:
        x_units: X-Koordinate in Einheiten
        y_units: Y-Koordinate in Einheiten
        alpha_deg: Orientierung in Grad
        target_area: Tuple (target_x, target_y) für Zielbereich-Visualisierung
    """
    try:
        room = Image.open(ROOM_PATH).convert("RGBA")
        robot = Image.open(ROBOT_PATH).convert("RGBA")
        
        # Zielbereich zeichnen (falls angegeben)
        if target_area is not None:
            draw_target_area(room, target_area[0], target_area[1])

        ox, oy = ORIGIN_PIXELS
        # Umrechnung Einheiten -> Pixel Offset (Mittelpunkt des Roboters relativ zum Ursprung)
        center_offset_x = units_to_pixels_x(x_units)
        center_offset_y = units_to_pixels_y(y_units)

        # Mittelpunkt in Bild-Pixeln (angepasst an neues Koordinatensystem)
        center_x = ox + center_offset_x
        center_y = oy + center_offset_y  # oy ist jetzt der neue Ursprung

        # Top-Left berechnen, damit Mittelpunkt auf Ziel liegt
        # Orientierung anwenden:
        # Originalsprite schaut bei 0° nach UNTEN (+y). Benutzer-Definition: 0° = rechts (+x), 90° = oben (+y).
        # Benötigter CCW-Rotationswinkel = alpha_deg + 90.
        ccw_degrees = alpha_deg + 90.0
        if ccw_degrees % 360 != 0:
            # PIL.rotate(angle) rotiert CCW 
            robot_rot = robot.rotate(ccw_degrees, resample=Image.BICUBIC, expand=True)
        else:
            robot_rot = robot

        rw, rh = robot_rot.size
        x_pixel = int(round(center_x - rw / 2))
        y_pixel = int(round(center_y - rh / 2))

        # Sichtfeld zuerst (damit Roboter oben liegt)
        if SHOW_FOV:
            draw_fov(room, center_x, center_y, alpha_deg)

        # Einfügen (Top-Left Position) Roboter über FOV
        room.paste(robot_rot, (x_pixel, y_pixel), mask=robot_rot)
        room.save(OUTPUT_PATH)
        
        print(f"Roboterposition aktualisiert: ({x_units}, {y_units}, {alpha_deg}°)")
        return True
        
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Roboterposition: {e}")
        return False

def draw_target_area(image, target_x_units: float, target_y_units: float, width_units: float = 140, height_units: float = 140):
    """
    Zeichnet einen transparenten hellgrünen rechteckigen Zielbereich auf das Bild.
    
    Args:
        image: PIL Image Objekt
        target_x_units: X-Koordinate des Zielbereichs in Einheiten
        target_y_units: Y-Koordinate des Zielbereichs in Einheiten
        width_units: Breite des Zielbereichs in Einheiten (Standard: 140cm)
        height_units: Höhe des Zielbereichs in Einheiten (Standard: 140cm)
    """
    ox, oy = ORIGIN_PIXELS
    
    # Mittelpunkt des Zielbereichs in Pixeln
    center_offset_x = units_to_pixels_x(target_x_units)
    center_offset_y = units_to_pixels_y(target_y_units)
    center_x = ox + center_offset_x
    center_y = oy + center_offset_y
    
    # Halbe Breite und Höhe in Pixeln
    half_width_pixels = units_to_pixels_x(width_units / 2)
    half_height_pixels = abs(units_to_pixels_y(height_units / 2))  # abs() da Y-Koordinaten invertiert sind
    
    # Bounding Box für das Rechteck
    left = center_x - half_width_pixels
    right = center_x + half_width_pixels
    top = center_y - half_height_pixels
    bottom = center_y + half_height_pixels
    
    # Erstelle transparentes Overlay für den Zielbereich
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Hellgrüner transparenter Rechteck
    draw.rectangle([left, top, right, bottom], 
                  fill=(144, 238, 144, 80),   # Hellgrün mit mehr Transparenz
                  outline=(50, 205, 50, 200), # Grüner Rand weniger transparent
                  width=3)
    
    # Overlay mit dem Hauptbild kombinieren
    image.alpha_composite(overlay)


def main():
	room = Image.open(ROOM_PATH).convert("RGBA")
	robot = Image.open(ROBOT_PATH).convert("RGBA")

	ox, oy = ORIGIN_PIXELS
	# Umrechnung Einheiten -> Pixel Offset (Mittelpunkt des Roboters relativ zum Ursprung)
	center_offset_x = units_to_pixels_x(X_UNITS)
	center_offset_y = units_to_pixels_y(Y_UNITS)

	# Mittelpunkt in Bild-Pixeln (angepasst an neues Koordinatensystem)
	center_x = ox + center_offset_x
	center_y = oy + center_offset_y  # oy ist jetzt der neue Ursprung

	# Top-Left berechnen, damit Mittelpunkt auf Ziel liegt
	# Orientierung anwenden:
	# Originalsprite schaut bei 0° nach UNTEN (+y). Benutzer-Definition: 0° = rechts (+x), 90° = oben (+y).
	# Benötigter CCW-Rotationswinkel = ORIENTATION_DEGREES + 90.
	ccw_degrees = ORIENTATION_DEGREES + 90.0
	if ccw_degrees % 360 != 0:
		# PIL.rotate(angle) rotiert CCW
		robot_rot = robot.rotate(ccw_degrees, resample=Image.BICUBIC, expand=True)
	else:
		robot_rot = robot

	rw, rh = robot_rot.size
	x_pixel = int(round(center_x - rw / 2))
	y_pixel = int(round(center_y - rh / 2))

	# Optionales Clamping falls Randüberschreitung (hier nur Warnung)
	if x_pixel < 0 or y_pixel < 0 or x_pixel + rw > room.width or y_pixel + rh > room.height:
		print("Warnung: Roboter liegt teilweise außerhalb des Bildes. (Kein Clamping durchgeführt)")

	# Sichtfeld zuerst (damit Roboter oben liegt) oder danach je nach gewünschter Überdeckung.
	if SHOW_FOV:
		draw_fov(room, center_x, center_y, ORIENTATION_DEGREES)

	# Einfügen (Top-Left Position) Roboter über FOV
	room.paste(robot_rot, (x_pixel, y_pixel), mask=robot_rot)
	room.save(OUTPUT_PATH)

	print("Einsetzen abgeschlossen:")
	print(f" Ziel (Mittelpunkt) in Einheiten: ({X_UNITS}, {Y_UNITS})")
	print(f" Mittelpunkt Pixel: ({center_x:.2f}, {center_y:.2f})")
	print(f" Orientierung (Eingabe): {ORIENTATION_DEGREES}° (0=rechts, 90=oben)")
	print(f" Effektive CCW-Rotation angewendet: {(ccw_degrees % 360):.1f}°")
	print(f" Eingesetzte Top-Left Pixel: ({x_pixel}, {y_pixel}) Größe (nach Rotation): {rw}x{rh}")
	print(f" Ausgabe: {OUTPUT_PATH}")

if __name__ == "__main__":
	main()
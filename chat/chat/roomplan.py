import cv2
import matplotlib.pyplot as plt
import os

# Bildpfad und Laden (BGR)
home = os.path.expanduser("~")
input_path = os.path.join(home, "ros2_ws", "src", "map", "Raumplan.png")
img = cv2.imread(input_path)
if img is None:
    raise FileNotFoundError(f"Bild konnte nicht geladen werden: {input_path}")

# Rasterparameter & Skalierung
rows, cols = img.shape[:2]
grid_pixel_step = 50  # ursprünglicher Pixelabstand (nicht mehr für Linien verwendet)
origin = (230, 83)  # (x, y) korrigiert
ox, oy = origin

# Vorgaben für Skalierung: (ox,oy)->(0,0), (900,83)-> x=689, (537,720)-> y=654
ref_x_pixel = 900
ref_x_value = 689
ref_y_pixel = 720
ref_y_value = 654

# Neuer Ursprung: wo vorher (x=0, y=-654) war
# Das entspricht Pixel-Position (ox, oy + 654/scale_y_units_per_pixel)
# Aber wir berechnen erstmal die ursprüngliche Skalierung
dx_pixels = ref_x_pixel - ox
dy_pixels = ref_y_pixel - oy
if dx_pixels == 0 or dy_pixels == 0:
    raise ValueError("Referenzpunkte dürfen nicht auf gleicher x- oder y-Position wie der Ursprung liegen.")

scale_x_units_per_pixel = ref_x_value / dx_pixels
scale_y_units_per_pixel = ref_y_value / dy_pixels

# Neuer Ursprung berechnen: Punkt wo y=-654 war
# y=-654 entspricht Pixel-Position oy + 654/scale_y_units_per_pixel
new_origin_x = ox  # x bleibt gleich (bei x=0)
new_origin_y = int(oy + 654 / scale_y_units_per_pixel)
origin = (new_origin_x, new_origin_y)
ox, oy = origin

# Farben - Raster jetzt dunkelgrau/schwarz
dark_gray = (64, 64, 64)  # BGR-Format: Dunkelgrau
axis_color = (32, 32, 32)  # Noch dunkleres Grau für Achsen
origin_color = (0, 0, 255)

font = cv2.FONT_HERSHEY_SIMPLEX
text_color = (0, 0, 0)
font_scale = 0.5  # vorher 0.4
thickness = 1     # zurück auf Standarddicke

# Neues Einheiten-Raster: Start im Ursprung, Schritte in Einheiten (z.B. 60)
unit_step = 60  # gewünschter Schritt in Koordinaten-Einheiten
px_step_x = unit_step / scale_x_units_per_pixel
px_step_y = unit_step / scale_y_units_per_pixel

# Vertikale Linien ab Ursprung (nur positive Richtung)
k = 0
while True:
    x_f = ox + k * px_step_x
    if x_f >= cols:
        break
    x = int(round(x_f))
    value = k * unit_step
    is_axis = (k == 0)
    cv2.line(img, (x, 0), (x, rows), axis_color if is_axis else dark_gray, 2 if is_axis else 1)
    # Beschriftung (X)
    label_y = oy - 50 if oy - 50 > 10 else oy + 66
    cv2.putText(img, str(int(value)), (x + 1, label_y), font, font_scale, text_color, thickness)
    k += 1

# Horizontale Linien ab Ursprung (Y-Koordinaten nach oben steigend)
k = 0
while True:
    y_f = oy - k * px_step_y  # Minus für aufsteigende Y-Werte nach oben
    if y_f < 0:
        break
    y = int(round(y_f))
    value = k * unit_step
    is_axis = (k == 0)
    cv2.line(img, (0, y), (cols, y), axis_color if is_axis else dark_gray, 2 if is_axis else 1)
    # Beschriftung (Y)
    desired_x = ox - 240
    label_x = desired_x if desired_x > 2 else 2
    cv2.putText(img, str(int(value)), (label_x, y - 3), font, font_scale, text_color, thickness)
    k += 1

# Ursprung markieren
cv2.circle(img, origin, 5, origin_color, -1)
cv2.putText(img, "(0,0)", (ox + 6, oy - 8 if oy - 8 > 10 else oy + 16), font, 0.6, origin_color, 1)

# Zusatz: Achsenbeschriftungen an Raster-Koordinaten (750,0) und (0,690)
# Nun gleiche Strichstärke wie normale Beschriftungen und gleiche grüne Farbe wie das Raster
axis_label_thickness = thickness

def units_to_pixels_x(u):
    return ox + u / scale_x_units_per_pixel
def units_to_pixels_y(u):
    return oy - u / scale_y_units_per_pixel  # Minus für umgekehrtes Y-System

# Zielkoordinaten in Einheiten
x_label_units = (750, 0)  # (x,y) in Raster-Einheiten
y_label_units = (0, 690)

# Umrechnen in Pixel
x_lab_px = int(round(units_to_pixels_x(x_label_units[0])))
x_lab_py_axis = int(round(units_to_pixels_y(x_label_units[1])))
y_lab_px_axis = int(round(units_to_pixels_x(y_label_units[0])))
y_lab_py = int(round(units_to_pixels_y(y_label_units[1])))

# Offsets für bessere Lesbarkeit
# Zusätzliche Verschiebung: x-Label 5px nach links und 10px nach unten; y-Label weitere 30px nach links
x_label_pos = (
    min(max(x_lab_px - 20 - 5 - 2 - 1, 0), cols - 10),  # weitere -1 px links
    max(x_lab_py_axis - 55 + 25 + 10 + 4 + 4, 10)       # weitere +4 px nach unten
)
y_label_pos = (
    min(max(y_lab_px_axis + 6 - 25 - 30 - 15 + 5, 2), cols - 60),  # +5 px nach rechts (reduziert linken Offset)
    min(max(y_lab_py + 9, 10), rows - 10)                          # +9 px nach unten
)

cv2.putText(img, "x [cm]", x_label_pos, font, font_scale, axis_color, axis_label_thickness)
cv2.putText(img, "y [cm]", y_label_pos, font, font_scale, axis_color, axis_label_thickness)

# Skaleninfo unten links
#info_text = f"dx:1px={scale_x_units_per_pixel:.3f}u  dy:1px={scale_y_units_per_pixel:.3f}u"
#cv2.putText(img, info_text, (10, rows - 10), font, 0.5, (50, 50, 50), 1)

"""Rasterbild speichern unter RaumplanRaster.<ext> im gleichen Verzeichnis"""
dir_name = os.path.dirname(input_path)
ext = os.path.splitext(input_path)[1]
output_path = os.path.join(dir_name, f"Raumplan_grid{ext}")
cv2.imwrite(output_path, img)  # Speichern im BGR-Format

# Für Anzeige nach RGB konvertieren (nur falls Anzeige gewünscht)
# img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# Anzeige (deaktiviert wegen Qt-Problemen)
# plt.imshow(img_rgb)
# plt.axis('off')
# plt.show()

print(f"Gespeichert unter: {output_path}")
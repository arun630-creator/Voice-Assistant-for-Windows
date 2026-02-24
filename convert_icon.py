"""Convert Nova logo PNG to multi-size ICO and tray PNG."""
from PIL import Image
import os

logo = Image.open("assets/nova_logo.png").convert("RGBA")

# Multi-size ICO (16, 24, 32, 48, 64, 128, 256)
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
imgs = []
for s in sizes:
    r = logo.copy()
    r.thumbnail(s, Image.LANCZOS)
    canvas = Image.new("RGBA", s, (0, 0, 0, 0))
    ox = (s[0] - r.width) // 2
    oy = (s[1] - r.height) // 2
    canvas.paste(r, (ox, oy))
    imgs.append(canvas)

imgs[0].save("assets/nova.ico", format="ICO", sizes=sizes, append_images=imgs[1:])
print("ICO created:", os.path.getsize("assets/nova.ico"), "bytes")

# 64x64 tray PNG
tray = logo.copy()
tray.thumbnail((64, 64), Image.LANCZOS)
tray_canvas = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
ox = (64 - tray.width) // 2
oy = (64 - tray.height) // 2
tray_canvas.paste(tray, (ox, oy))
tray_canvas.save("assets/nova_tray.png")
print("Tray PNG created")

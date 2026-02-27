"""
Generate icon.ico for use in PyInstaller and the MSI installer.
Reuses make_icon() from monitor.py so the installer icon matches the tray icon.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor import make_icon
from PIL import Image

SIZES = [16, 32, 48, 64, 128, 256]

images = []
for size in SIZES:
    img = make_icon(75)                            # green battery ~75%
    img = img.resize((size, size), Image.LANCZOS)
    images.append(img)

out = Path(__file__).parent / "icon.ico"
images[0].save(
    out,
    format="ICO",
    sizes=[(s, s) for s in SIZES],
    append_images=images[1:],
)
print(f"icon.ico written to {out}")

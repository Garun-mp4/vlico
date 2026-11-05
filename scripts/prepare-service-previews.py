"""Regenerate small hover previews from the canonical service-page images."""
from pathlib import Path
import runpy
from PIL import Image, ImageOps

root = Path(__file__).resolve().parents[1]
assets = root / 'wireframe'
services = runpy.run_path(str(root/'backend/core/site_content.py'))['SERVICES']
for service in services:
    destination = assets/service['preview']
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(assets/service['image']) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
        image.thumbnail((720,720),Image.Resampling.LANCZOS)
        image.save(destination,'WEBP',quality=82,method=6)
    print(f"{service['slug']}: {destination.stat().st_size//1024} KB")

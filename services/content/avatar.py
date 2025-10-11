from PIL import Image
import io, hashlib, time


def prepare_avatar(file_bytes, prefer="WEBP", max_px=512):
    im = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    im.save(buf, format=prefer, optimize=True)  # or AVIF if you have plugin
    b = buf.getvalue()
    return {
        "content": b,
        "content_type": f"image/{prefer.lower()}",
        "size_bytes": len(b),
        "sha256": hashlib.sha256(b).hexdigest(),
        "width": im.width,
        "height": im.height,
    }
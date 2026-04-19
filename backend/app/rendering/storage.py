"""Local storage helpers for V2 artefacts.

MVP uses a local filesystem path mounted at /uploads/v2. A future R2/S3 adapter
can implement the same three helpers with no call-site change.
"""

from __future__ import annotations

import base64
import hashlib
import io
import mimetypes
from pathlib import Path
from typing import Optional

from app.config_v2 import get_v2_settings


def _ext_for(mime: str) -> str:
    return mimetypes.guess_extension(mime) or ".bin"


def put_bytes(subdir: str, name: str, data: bytes, mime: str = "application/octet-stream") -> str:
    """Write bytes to storage and return a publicly-reachable URL."""
    s = get_v2_settings()
    dest_dir = s.storage_root / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(data).hexdigest()[:16]
    ext = Path(name).suffix or _ext_for(mime)
    filename = f"{Path(name).stem}-{sha}{ext}"
    (dest_dir / filename).write_bytes(data)
    return f"{s.public_base_url}/{subdir}/{filename}"


def put_text(subdir: str, name: str, text: str) -> str:
    return put_bytes(subdir, name, text.encode("utf-8"), "text/plain")


def fetch_image_bytes(source: str) -> bytes:
    """Resolve a source URL, data-URL, or local path to bytes.

    Resolution order:
      1. ``data:`` URLs decoded inline.
      2. URLs that we own (match ``public_base_url``) → read from local disk.
         This is critical in tests where no HTTP server is running.
      3. Remote http(s) URLs → fetched with httpx.
      4. Everything else is treated as a filesystem path.
    """
    if source.startswith("data:"):
        _, _, payload = source.partition(",")
        return base64.b64decode(payload)

    local = local_path_for_url(source)
    if local is not None and local.exists():
        return local.read_bytes()

    if source.startswith("http://") or source.startswith("https://"):
        import httpx
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(source)
            resp.raise_for_status()
            return resp.content

    return Path(source).read_bytes()


def local_path_for_url(url: str) -> Optional[Path]:
    """Map a public URL back to a local path, if it originated here."""
    s = get_v2_settings()
    prefix = s.public_base_url.rstrip("/") + "/"
    if not url.startswith(prefix):
        return None
    rel = url[len(prefix):]
    return s.storage_root / rel


def save_pil(subdir: str, name: str, image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    return put_bytes(subdir, name, buf.getvalue(), mime=f"image/{fmt.lower()}")

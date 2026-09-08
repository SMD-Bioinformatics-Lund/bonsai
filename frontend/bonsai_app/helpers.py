"""Flask and jinja helper functions."""

import json
from pathlib import Path
from flask import current_app, url_for

_MANIFEST_CACHE = None
_MANIFEST_CACHE_KEY = None


def load_manifest():
    """Cache manifest content until the asset build changes."""
    global _MANIFEST_CACHE, _MANIFEST_CACHE_KEY

    manifest_path = Path(current_app.static_folder) / "build" / "manifest.json"
    try:
        stat = manifest_path.stat()
    except FileNotFoundError:
        _MANIFEST_CACHE = None
        _MANIFEST_CACHE_KEY = None
        return {}

    cache_key = (manifest_path, stat.st_mtime_ns, stat.st_size)
    if _MANIFEST_CACHE is None or _MANIFEST_CACHE_KEY != cache_key:
        with manifest_path.open(encoding="utf-8") as f:
            _MANIFEST_CACHE = json.load(f)
        _MANIFEST_CACHE_KEY = cache_key
    
    return _MANIFEST_CACHE


def asset_url(filename: str) -> str:
    """Get url to asset file."""

    manifest = load_manifest()

    # Lookup hashed filename
    hashed = manifest.get(filename)

    if hashed:
        return url_for("static", filename=f"build/{hashed}")
    
    # fallback if build is missing
    return url_for("static", filename=filename)

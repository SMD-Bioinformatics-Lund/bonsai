"""Flask and jinja helper functions."""

import json
from flask import current_app, url_for

_MANIFEST_CACHE = None


def load_manifest():
    """Cache manifest content."""
    global _MANIFEST_CACHE

    if _MANIFEST_CACHE is None:
        manifest_path = current_app.static_folder + "/build/manifest.json"

        try:
            with open(manifest_path, encoding="utf-8") as f:
                _MANIFEST_CACHE = json.load(f)
        except FileNotFoundError:
            _MANIFEST_CACHE = {}
    
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
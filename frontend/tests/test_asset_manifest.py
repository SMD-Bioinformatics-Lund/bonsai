"""Regression tests for asset rebuilds in a running Flask process."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from flask import Flask

from bonsai_app.helpers import load_manifest


class ManifestTests(unittest.TestCase):
    def test_rebuild_and_missing_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Flask(__name__, static_folder=directory)
            manifest = Path(directory) / "build" / "manifest.json"
            manifest.parent.mkdir()
            with app.app_context():
                self.assertEqual(load_manifest(), {})
                manifest.write_text(json.dumps({"group-view.js": "old.js"}))
                self.assertEqual(load_manifest()["group-view.js"], "old.js")
                timestamp = manifest.stat().st_mtime_ns
                manifest.write_text(json.dumps({"group-view.js": "new.js"}))
                os.utime(manifest, ns=(timestamp + 1_000_000, timestamp + 1_000_000))
                self.assertEqual(load_manifest()["group-view.js"], "new.js")
                manifest.unlink()
                self.assertEqual(load_manifest(), {})


if __name__ == "__main__":
    unittest.main()

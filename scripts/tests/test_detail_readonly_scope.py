"""The detail increment allows display-only filters and refuses record writes."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from detail_readonly_scope import ReadOnlyDetailScope
from bounded_scope import ScopeViolation


class ReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.scope = ReadOnlyDetailScope()

    def test_existing_record_and_export_reads(self):
        for path in ["/samples/existing", "/export/existing/lims?fmt=csv"]:
            self.scope.check("GET", path)
            self.scope.check("OPTIONS", path)
        self.scope.check_browser("GET", "/sample/existing/resistance/variants")

    def test_display_only_filter_is_allowed(self):
        self.scope.check_browser("POST", "/sample/existing/resistance/variants", "min-depth=10&depth-operator=gte")

    def test_curation_fields_are_rejected(self):
        for body in ["classify-variant=Confirm", "curations=%5B%5D", "verify-variant-btn=accept", "amrs=test"]:
            with self.subTest(body=body), self.assertRaises(ScopeViolation):
                self.scope.check_browser("POST", "/sample/existing/resistance/variants", body)

    def test_all_record_writes_are_rejected_even_for_owned_ids(self):
        self.scope.samples.add("owned")
        for method, path, data in [("DELETE", "/samples/", ["owned"]),
                                   ("POST", "/samples/owned/metadata", []),
                                   ("POST", "/analysis/owned/curations", {})]:
            with self.subTest(path=path), self.assertRaises(ScopeViolation):
                self.scope.check(method, path, data)

    def test_compute_and_other_forms_are_rejected(self):
        for method, path in [("POST", "/sample/existing/similar"), ("GET", "/samples/cluster/"),
                             ("POST", "/sample/existing/comment")]:
            with self.subTest(path=path), self.assertRaises(ScopeViolation):
                self.scope.check_browser(method, path)

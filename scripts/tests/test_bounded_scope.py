"""Prove the local harness refuses excluded work before issuing a request."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bounded_scope import BoundedScope, ScopeViolation


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.scope = BoundedScope()
        self.scope.samples.add("owned-record")
        self.scope.groups.add("owned-group")
        self.scope.users.add("bounded_user")

    def test_stored_record_reads_and_summary_are_allowed(self):
        for method, path in [("GET", "/samples/existing"), ("GET", "/groups/existing"),
                             ("GET", "/memberships?s=existing"), ("POST", "/samples/summary")]:
            with self.subTest(path=path):
                self.scope.check(method, path)

    def test_analysis_jobs_and_curation_are_rejected(self):
        for path in ["/analysis/", "/cluster/minhash", "/job/status/id",
                     "/samples/owned-record/similar", "/samples/owned-record/pipeline-runs",
                     "/samples/owned-record/resources", "/analysis/id/curations"]:
            for method in ["GET", "POST", "PUT", "DELETE"]:
                with self.subTest(path=path, method=method):
                    with self.assertRaises(ScopeViolation):
                        self.scope.check(method, path)

    def test_generic_metadata_and_owned_group_changes_are_allowed(self):
        self.scope.check("POST", "/samples/owned-record/metadata", [])
        self.scope.check("PUT", "/groups/owned-group/allowed_columns", {})
        self.scope.check("DELETE", "/samples/", ["owned-record"])

    def test_original_records_cannot_be_mutated(self):
        for method, path, data in [("POST", "/samples/existing/metadata", []),
                                   ("DELETE", "/samples/", ["owned-record", "existing"]),
                                   ("DELETE", "/groups/existing", None),
                                   ("PUT", "/groups/owned-group/samples?s=existing", None),
                                   ("POST", "/samples/", {"sample_id": "bounded_new", "groups": ["existing"]}),
                                   ("PUT", "/users/admin", {})]:
            with self.subTest(path=path):
                with self.assertRaises(ScopeViolation):
                    self.scope.check(method, path, data)

    def test_only_prefixed_disposable_objects_can_be_created(self):
        self.scope.check("POST", "/samples/", {"sample_id": "bounded_one"})
        with self.assertRaises(ScopeViolation):
            self.scope.check("POST", "/samples/", {"sample_id": "existing"})


if __name__ == "__main__":
    unittest.main()

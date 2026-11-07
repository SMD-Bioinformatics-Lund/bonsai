"""Account changes and both delete forms remain confined to disposable fixtures."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from account_scope import AccountScope
from bounded_scope import ScopeViolation


class AccountScopeTests(unittest.TestCase):
    def setUp(self):
        self.scope = AccountScope()
        self.scope.samples.add("owned")
        self.scope.users.add("bounded_session_operator")

    def test_both_delete_forms_only_allow_owned_records(self):
        self.scope.check("DELETE", "/samples/owned")
        self.scope.check("DELETE", "/samples/", ["owned"])
        with self.assertRaises(ScopeViolation):
            self.scope.check("DELETE", "/samples/original")

    def test_original_account_changes_are_refused(self):
        self.scope.check("PUT", "/users/bounded_session_operator", {})
        for name in ["admin", "user_one", "user_two", "uploader"]:
            with self.subTest(name=name), self.assertRaises(ScopeViolation):
                self.scope.check("PUT", "/users/" + name, {})

    def test_analysis_and_curation_remain_excluded(self):
        for path in ["/analysis/", "/samples/owned/similar", "/analysis/owned/curations"]:
            with self.subTest(path=path), self.assertRaises(ScopeViolation):
                self.scope.check("POST", path, {})

from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recovery_scope import RecoveryScope
from bounded_scope import ScopeViolation


class RecoveryScopeTests(unittest.TestCase):
    def test_failure_targets_cannot_mutate_original_data(self):
        scope=RecoveryScope();scope.samples.add('owned');scope.groups.add('owned-group')
        scope.check('POST','/samples/owned/comment',{})
        scope.check('PUT','/groups/owned-group',{})
        with self.assertRaises(ScopeViolation):scope.check('POST','/samples/original/comment',{})

    def test_only_saved_generic_reads_and_schemas_are_allowed(self):
        scope=RecoveryScope();scope.check('GET','/samples/summary/manifest')
        for path in ['/analysis/test/curations','/samples/test/resources','/samples/test/similar']:
            with self.subTest(path=path),self.assertRaises(ScopeViolation):scope.check('POST',path,{})

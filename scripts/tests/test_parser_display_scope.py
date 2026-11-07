from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parser_display_scope import ParserDisplayScope
from bounded_scope import ScopeViolation


class ParserDisplayScopeTests(unittest.TestCase):
    def test_only_stored_reads_are_available(self):
        scope = ParserDisplayScope()
        scope.check('GET', '/samples/frozen-record')
        scope.check('GET', '/samples/summary/manifest')
        scope.check('POST', '/samples/summary', {})
        for method, path in [('POST', '/analysis'), ('POST', '/samples/record/pipeline-runs'),
                             ('POST', '/samples/record/comment'), ('DELETE', '/samples/record')]:
            with self.subTest(path=path), self.assertRaises(ScopeViolation):
                scope.check(method, path, {})

    def test_browser_only_submits_login(self):
        scope = ParserDisplayScope()
        scope.check_browser('POST', '/login')
        for path in ['/sample/record/resistance/variants', '/sample/record/comment', '/analysis/result/curations']:
            with self.subTest(path=path), self.assertRaises(ScopeViolation):
                scope.check_browser('POST', path, '')

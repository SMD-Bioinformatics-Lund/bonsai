#!/usr/bin/env python3
"""Offline parser regression worker; no service calls or sequence tools."""
import argparse
import importlib.metadata
import inspect
import json
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', choices=['sdk', 'prp', 'contracts', 'files'])
    parser.add_argument('--phase', default='original')
    args = parser.parse_args()
    job = Path('/audit/run/jobs') / (args.job + '-' + args.phase)
    job.mkdir(parents=True, exist_ok=True)
    import bonsai_libs
    from bonsai_libs.parse.core.registry import run_parser
    environment = {'python': sys.version, 'sdk_module': bonsai_libs.__file__,
        'parser_module': inspect.getfile(run_parser),
        'dependencies': {name: importlib.metadata.version(name) for name in ['pydantic', 'PyYAML', 'pytest']}}
    (job / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    if args.job == 'files':
        sys.argv = ['/audit/code/check_saved_reports.py', '--phase', args.phase]
        runpy.run_path(sys.argv[0], run_name='__main__')
        return
    if args.job == 'contracts':
        sys.argv = ['/audit/harness/check_parser_contracts.py', '--fixtures', '/audit/fixtures',
            '--output', '/audit/run/contracts', '--phase', args.phase]
        runpy.run_path(sys.argv[0], run_name='__main__')
        result = json.loads((Path('/audit/run/contracts') / args.phase / 'results.json').read_text())
        sys.exit(1 if result['counts'].get('FAIL', 0) else 0)
    import pytest
    target = '/audit/sdk/tests/parse' if args.job == 'sdk' else '/audit/prp/tests'
    exit_code = pytest.main(['-q', '-o', 'addopts=', '--import-mode=importlib', '-p', 'no:cacheprovider',
        '--basetemp', str(job / 'tmp'), '--junitxml', str(job / 'junit.xml'), target])
    sys.exit(int(exit_code))


if __name__ == '__main__': main()

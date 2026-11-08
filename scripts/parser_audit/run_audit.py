#!/usr/bin/env python3
"""Run the pinned combined SDK/PRP regression in offline disposable containers."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
DATA = Path.home() / 'data/codex/bonsai'
JASEN = Path.home() / 'data/codex/jasen'
RUN = DATA / 'runs/2026-11-08-parser-fixture-audit'
ORIGINAL = DATA / 'runs/2026-11-06-species-ui/fixtures'
DERIVED = RUN / 'derived-fixtures'
HARNESS = REPO.parent / 'bonsai/scripts/check_parser_contracts.py'
PRP = JASEN / 'environments/prp-kleborate-companion/source'
SDK = JASEN / 'environments/bonsai-pilot-sdk-kleborate/source'


def now(): return datetime.now(timezone.utc).isoformat()
def digest(path): return sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
def git(path, *args): return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def prepare():
    RUN.mkdir(parents=True, exist_ok=True)
    image = subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}', 'bonsai-jasen-pilot-api-1'], text=True).strip()
    context = {'created_at_utc': now(), 'image_id': image,
        'sdk': {'path': str(SDK), 'head': git(SDK, 'rev-parse', 'HEAD')},
        'prp': {'path': str(PRP), 'head': git(PRP, 'rev-parse', 'HEAD')},
        'harness': {'path': str(HARNESS), 'sha256': digest(HARNESS), 'repository_head': git(HARNESS.parents[1], 'rev-parse', 'HEAD')},
        'original_fixtures': {'path': str(ORIGINAL), 'checksum_manifest_sha256': digest(ORIGINAL / 'checksums.sha256')},
        'network': 'none', 'database_access': False, 'sequence_processing': False,
        'scope': 'Saved report file formats, parser outputs, dispatch and generic upload orchestration; no biological interpretation'}
    for source in [SDK, PRP]:
        assert not git(source, 'status', '--porcelain'), 'Tested source must be clean'
    context_file = RUN / 'source-context.json'
    if context_file.exists():
        previous = json.loads(context_file.read_text())
        for key in ['image_id', 'sdk', 'prp', 'harness', 'original_fixtures']:
            assert previous[key] == context[key], 'Source context changed: ' + key
        return previous
    write(context_file, context)
    return context


def run_job(kind, phase, context):
    directory = RUN / 'jobs' / (kind + '-' + phase)
    status = directory / 'status.json'
    if status.exists() and json.loads(status.read_text()).get('finished_at_utc'):
        return json.loads(status.read_text())
    directory.mkdir(parents=True, exist_ok=True)
    fixtures = DERIVED if phase == 'corrected' else ORIGINAL
    command = ['docker', 'run', '--rm', '--network', 'none', '--user', f'{os.getuid()}:{os.getgid()}',
        '-v', f'{RUN}:/audit/run:rw', '-v', f'{SDK}:/audit/sdk:ro', '-v', f'{PRP}:/audit/prp:ro',
        '-v', f'{fixtures}:/audit/fixtures:ro', '-v', f'{HARNESS.parent}:/audit/harness:ro',
        '-v', f'{JASEN / "runs/2026-11-08-bonsai-reference-pilot/output/ecoli"}:/audit/native:ro',
        '-v', f'{REPO / "scripts/parser_audit"}:/audit/code:ro',
        '-v', f'{DATA / "environments/general-test-deps"}:/test-deps:ro',
        '-e', 'PYTHONPATH=/audit/sdk/src:/audit/prp:/test-deps', '-e', 'PYTHONDONTWRITEBYTECODE=1',
        '-e', f'TMPDIR=/audit/run/jobs/{kind}-{phase}',
        context['image_id'], 'python', '/audit/code/worker.py', kind, '--phase', phase]
    state = {'job': kind, 'phase': phase, 'started_at_utc': now(), 'command': command}
    write(status, state)
    with (directory / 'output.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    state.update(exit_code=result.returncode, finished_at_utc=now())
    file_result = RUN / ('saved-report-regression.json' if phase == 'original' else 'saved-report-regression-corrected.json')
    if kind == 'files' and file_result.exists():
        payload = json.loads(file_result.read_text())
        state['counts'] = payload['counts']
        state['failed_cases'] = [{'case': c['case'], 'check': c['check']} for c in payload['checks'] if c['status'] == 'FAIL']
        state['format_review_cases'] = [c['case'] for c in payload['review_cases']]
    elif kind == 'contracts' and (RUN / 'contracts' / phase / 'results.json').exists():
        payload = json.loads((RUN / 'contracts' / phase / 'results.json').read_text())
        state['counts'] = payload['counts']
        state['failure_categories'] = {}
        for row in payload['cases']:
            if row['status'] == 'FAIL':
                state['failure_categories'][row['case']] = state['failure_categories'].get(row['case'], 0) + 1
    elif (directory / 'junit.xml').exists():
        suites = ET.parse(directory / 'junit.xml').getroot()
        selected = [suites] if suites.tag == 'testsuite' else list(suites)
        state['counts'] = {k: sum(int(s.get(k, '0')) for s in selected) for k in ['tests', 'failures', 'errors', 'skipped']}
        state['failed_tests'] = [{'name': t.get('name'), 'class': t.get('classname'),
            'kind': 'failure' if t.find('failure') is not None else 'error'}
            for t in suites.iter('testcase') if t.find('failure') is not None or t.find('error') is not None]
    write(status, state)
    print(json.dumps({k: v for k, v in state.items() if k in ['job', 'phase', 'exit_code', 'counts', 'failure_categories', 'failed_tests']}), flush=True)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['original', 'corrected'], default='original')
    parser.add_argument('--saved-reports', action='store_true')
    args = parser.parse_args(); context = prepare()
    jobs = ['files'] if args.saved_reports else ['sdk', 'prp', 'contracts'] if args.phase == 'original' else ['contracts']
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = list(pool.map(lambda kind: run_job(kind, args.phase, context), jobs))
    name = ('saved-report-summary.json' if args.phase == 'original' else 'saved-report-corrected-summary.json') if args.saved_reports else args.phase + '-summary.json'
    write(RUN / name, {'recorded_at_utc': now(), 'source_context': str(RUN / 'source-context.json'), 'jobs': results})
    raise SystemExit(1 if any(result['exit_code'] for result in results) else 0)


if __name__ == '__main__': main()

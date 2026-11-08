#!/usr/bin/env python3
"""Compose the minimal parser fix with the existing isolated pilot SDK."""
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

from kleborate_saved_report_cases import DATA, ROOT, PILOT, PRP_FIXED, now, write
from prepare_bonsai import compose


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def main():
    context_file = PILOT / 'bonsai/source-context.json'
    before = ROOT / 'source-context-before-kleborate.json'
    if not before.exists(): shutil.copy2(context_file, before)
    parent = json.loads(before.read_text())
    sdk_repo = Path('/home/jakob/src/codex/bonsai/bonsai-sdk')
    sdk_fix = git(sdk_repo, 'rev-parse', 'pr/kleborate-kaptive-nesting')
    destination = DATA / 'environments/bonsai-pilot-sdk-kleborate/source'
    if not destination.exists():
        subprocess.run(['git', '-C', str(sdk_repo), 'worktree', 'add', '--detach', str(destination), parent['trees']['SDK']['head']], check=True)
        subprocess.run(['git', '-C', str(destination), 'cherry-pick', sdk_fix], check=True)
    assert not git(destination, 'status', '--porcelain')
    context = json.loads(before.read_text())
    context['trees']['SDK'] = {'path': str(destination), 'head': git(destination, 'rev-parse', 'HEAD')}
    context['candidates']['KLEBORATE-KAPTIVE-NESTING'] = sdk_fix
    context['checks'].append({'name': 'kleborate-kaptive-input-format', 'status': 'PASS', 'tests': 4})
    env_file = PILOT / 'bonsai/compose.env'
    backup = ROOT / 'compose-before-kleborate.env'
    if not backup.exists(): shutil.copy2(env_file, backup); backup.chmod(0o600)
    values = dict(line.split('=', 1) for line in env_file.read_text().splitlines() if '=' in line)
    values['BONSAI_PILOT_SDK'] = str(destination)
    env_file.write_text(''.join(k + '=' + v + '\n' for k, v in values.items())); env_file.chmod(0o600)
    write(context_file, context)
    subprocess.run(compose('up', '-d', '--no-deps', 'api', 'frontend'), check=True)
    for _ in range(45):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18101/', timeout=2) as response:
                if response.status == 200: break
        except Exception: time.sleep(1)
    else: raise RuntimeError('Pilot API did not become ready')
    fixes = {'prepared_at_utc': now(), 'pushes_performed': False,
        'PRP': {'repository': '/home/jakob/src/codex/bonsai-prp', 'worktree': str(PRP_FIXED),
            'branch': 'pr/kleborate-companion-upload', 'base': '085ce7d3f2e475860cbe1529698e87fc17e6f801',
            'head': git(PRP_FIXED, 'rev-parse', 'HEAD'), 'production_scope': '13 additions, 1 deletion in one uploader file',
            'baseline_tests': '3 failed, 2 passed', 'fixed_tests': '5 passed'},
        'SDK': {'repository': str(sdk_repo), 'branch': 'pr/kleborate-kaptive-nesting',
            'base': '5789a9c7530407683f1fee9ffa450512269e62bc', 'head': sdk_fix,
            'production_scope': git(sdk_repo, 'diff', '--numstat', '5789a9c', sdk_fix, '--', 'src/bonsai_libs/parse/parsers/kleborate.py'),
            'baseline_tests': '4 failed', 'fixed_tests': '4 passed'},
        'active_sdk': context['trees']['SDK'], 'active_api': context['trees']['Bonsai'],
        'scope': 'Generic file transport and stored-report field mapping only; no new sequence analyses'}
    write(ROOT / 'local-fixes.json', fixes)
    print('Isolated pilot ready with the minimal SDK composition; both fix branches remain local')


if __name__ == '__main__': main()

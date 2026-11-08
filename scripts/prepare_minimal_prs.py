#!/usr/bin/env python3
"""Create isolated local release-fix branches without switching the test checkout.

Git objects and refs are written locally. No push, remote PR creation, live API
request or database mutation is performed. Branch updates require the previous
generated head to match, so unrelated work is never replaced.
"""

import argparse
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile

from minimal_pr_fixes import Edits, apply


REPO = Path(__file__).resolve().parents[1]
DATA = Path.home() / 'data/codex/bonsai'
APP_BASE = '21eccf7075fb59a897cb2ae86b0d6cdb95d0089c'
SDK_BASE = '5789a9c7530407683f1fee9ffa450512269e62bc'
DEPENDENCIES = {
    'ANALYSIS-UPLOAD-ROLE-GATE': ['ACCOUNT-ROLE-PERMISSIONS'],
    'RECOVERY-METADATA-LOSS': ['METADATA-ADD-500'],
    'RECOVERY-COMMENT-RETRY': ['RECOVERY-COMMENT-IDENTITIES'],
}
TITLES = {
    'PRIVATE-RECORD-SCOPE': 'Reject unsupported private sample creation',
    'BASKET-UNDEFINED-ASSAY': 'Render basket sample names as literal text',
    'KLEBORATE-CLIENT-COMPANION': 'Forward the optional hAMRonization companion in SDK uploads',
}


def git(repo, *args, input=None, env=None):
    return subprocess.check_output(['git', '-C', str(repo), *args], input=input, text=True, env=env).strip()


def prepare(output, selected=None):
    output = output.resolve(); output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((REPO / 'docs/local-testing/development-review-content.json').read_text())
    issues = {i['id']: i for i in catalog['issues'] if i['priority'] in {'P0', 'P1'}}
    issues['KLEBORATE-CLIENT-COMPANION'] = {'id': 'KLEBORATE-CLIENT-COMPANION', 'priority': 'P1', 'title': TITLES['KLEBORATE-CLIENT-COMPANION']}
    previous_file = output / 'branches.json'
    previous = {i['id']: i for i in json.loads(previous_file.read_text())['candidates']} if previous_file.exists() else {}
    candidates, errors, visiting = {}, [], set()

    def one(fid):
        if fid in candidates:
            return candidates[fid]
        if fid in visiting:
            raise ValueError('Dependency cycle: ' + fid)
        visiting.add(fid)
        dependencies = [one(dep) for dep in DEPENDENCIES.get(fid, [])]
        sdk = fid.startswith('PARSER-') or fid == 'KLEBORATE-CLIENT-COMPANION'
        repo = REPO / 'bonsai-sdk' if sdk else REPO
        base = dependencies[-1]['head'] if dependencies else SDK_BASE if sdk else APP_BASE
        branch = 'pr/' + fid.lower()
        ref = 'refs/heads/' + branch
        found = subprocess.run(['git', '-C', str(repo), 'show-ref', '--verify', '--hash', ref], capture_output=True, text=True)
        old = found.stdout.strip() if found.returncode == 0 else None
        if old and (fid not in previous or old != previous[fid]['head']):
            raise ValueError('Existing branch contains unowned changes: ' + branch)
        edits = Edits(repo, base); apply(fid, edits)
        # Preserve exact file bytes, including files without a final newline.
        files = {}
        for path, text in edits.files.items():
            try:
                original = subprocess.check_output(['git', '-C', str(repo), 'show', f'{base}:{path}'], text=True, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                original = None
            if text != original:
                if path.endswith('.py'):
                    ast.parse(text, filename=path)
                files[path] = text
        if not files:
            raise ValueError('No production patch for ' + fid)
        fd, index = tempfile.mkstemp(prefix='pr-index-', dir=output)
        os.close(fd); os.unlink(index)
        env = dict(os.environ, GIT_INDEX_FILE=index)
        try:
            git(repo, 'read-tree', base, env=env)
            for path, text in files.items():
                blob = git(repo, 'hash-object', '-w', '--stdin', input=text)
                git(repo, 'update-index', '--add', '--cacheinfo', f'100644,{blob},{path}', env=env)
            tree = git(repo, 'write-tree', env=env)
        finally:
            if Path(index).exists(): Path(index).unlink()
        title = TITLES.get(fid, issues[fid]['title'])
        message = f'fix: {title}\n\nFinding: {fid}\nMinimal local candidate; no surrounding refactor.\n'
        if old and git(repo, 'rev-parse', old + '^{tree}') == tree and git(repo, 'rev-parse', old + '^') == base:
            head = old
        else:
            head = git(repo, 'commit-tree', tree, '-p', base, input=message)
            git(repo, 'update-ref', ref, head, old or '0'*40)
        stats = git(repo, 'diff', '--numstat', base, head)
        changed = []
        for row in stats.splitlines():
            added, removed, path = row.split('\t'); changed.append({'path': path, 'added': int(added), 'removed': int(removed)})
        result = {'id': fid, 'repository': 'SDK' if sdk else 'Bonsai', 'branch': branch, 'head': head,
                  'base_ref': dependencies[-1]['branch'] if dependencies else 'master' if sdk else 'development',
                  'base_commit': base, 'dependencies': DEPENDENCIES.get(fid, []), 'title': title,
                  'priority': issues[fid]['priority'], 'files': changed,
                  'production_added': sum(i['added'] for i in changed), 'production_removed': sum(i['removed'] for i in changed),
                  'validation': 'Pending isolated candidate checks',
                  'policy_condition': 'Public-only creation; does not add ACLs or migrate existing private-marked records' if fid == 'PRIVATE-RECORD-SCOPE' else None}
        candidates[fid] = result; visiting.remove(fid)
        print(f'{fid}: {branch} +{result["production_added"]}/-{result["production_removed"]} ({len(changed)} files)', flush=True)
        return result

    for fid in selected or issues:
        try:
            one(fid)
        except Exception as exc:
            errors.append({'id': fid, 'error': str(exc)})
            visiting.clear()
            print(f'{fid}: ERROR {exc}', flush=True)
    merged = {**previous, **candidates}
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(), 'application_base': APP_BASE, 'sdk_base': SDK_BASE,
                'scope': 'Actual isolated production fixes in local branches; validation pending where explicitly stated',
                'candidates': list(merged.values()), 'errors': errors, 'no_git_pushes': True}
    previous_file.write_text(json.dumps(manifest, indent=2) + '\n')
    if errors:
        raise SystemExit(f'{len(errors)} candidates require adjustment; prepared candidates were retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DATA / 'runs/2026-11-06-species-ui/minimal-prs/2026-11-08')
    parser.add_argument('--only', nargs='+')
    args = parser.parse_args(); prepare(args.output, args.only)

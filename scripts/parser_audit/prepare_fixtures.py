#!/usr/bin/env python3
"""Audit pinned format metadata and derive explicitly corrected test fixtures."""
import ast
import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import shutil
import tomllib
import urllib.request

from run_audit import DATA, JASEN, REPO, RUN, ORIGINAL, DERIVED, SDK, digest, now, write

UPSTREAM_PIN = 'abc82ebe1a4a10bf4dcf0805d84d35fd6a846d2c'
MODULE = 'klebsiella_pneumo_complex__kaptive'
PUBLISHER = RUN / 'evidence/publisher-format/kleborate-v3.2.4'


def verify_originals():
    failures = []
    for line in (ORIGINAL / 'checksums.sha256').read_text().splitlines():
        expected, relative = line.split('  ', 1)
        if digest(ORIGINAL / relative) != expected: failures.append(relative)
    assert not failures, 'Frozen source fixtures changed: ' + str(failures)


def publisher_evidence():
    paths = ['pyproject.toml', 'kleborate/__main__.py', f'kleborate/modules/{MODULE}/{MODULE}.py']
    files = []
    for relative in paths:
        url = f'https://raw.githubusercontent.com/klebgenomics/Kleborate/{UPSTREAM_PIN}/{relative}'
        target = PUBLISHER / relative; target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with urllib.request.urlopen(url, timeout=30) as response: target.write_bytes(response.read())
        files.append({'relative_path': relative, 'url': url, 'bytes': target.stat().st_size, 'sha256': digest(target)})
    assert tomllib.loads((PUBLISHER / 'pyproject.toml').read_text())['project']['version'] == '3.2.4'
    tree = ast.parse((PUBLISHER / paths[2]).read_text())
    headers_function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'get_headers')
    assignment = next(n for n in headers_function.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'full_headers' for t in n.targets))
    headers = ast.literal_eval(assignment.value)
    main_tree = ast.parse((PUBLISHER / 'kleborate/__main__.py').read_text())
    writer = next(n for n in main_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'get_headers')
    writer_source = ast.get_source_segment((PUBLISHER / 'kleborate/__main__.py').read_text(), writer)
    assert "f'{module_name}__{h}'" in writer_source
    expected = [MODULE + '__' + h for h in headers]
    reference = JASEN / 'datasets/github/bonsai-sdk-saved-reports/5789a9c7530407683f1fee9ffa450512269e62bc/raw/kpneumoniae/kleborate_v3_kpsc_output.txt'
    with reference.open() as handle: reference_columns = next(csv.reader(handle, delimiter='\t'))
    assert set(expected) <= set(reference_columns), 'Saved fixture does not match tagged header metadata'
    evidence = {'acquired_at_utc': now(), 'repository': 'https://github.com/klebgenomics/Kleborate',
        'tag': 'v3.2.4', 'commit': UPSTREAM_PIN, 'files': files, 'expected_columns': expected,
        'saved_fixture': str(reference), 'saved_fixture_sha256': digest(reference),
        'verification': 'Tag version and header names read statically with AST; publisher source was not imported or executed'}
    write(PUBLISHER / 'acquisition.json', evidence)
    return evidence


def corrected_copy(evidence):
    verify_originals()
    receipt = RUN / 'fixture-corrections.json'
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        for row in previous['changed_reports']: assert digest(DERIVED / row['path']) == row['corrected_sha256']
        return previous
    assert not DERIVED.exists(), 'Incomplete derived copy requires inspection'
    shutil.copytree(ORIGINAL, DERIVED)
    catalog = json.loads((ORIGINAL / 'expectations.json').read_text()); changed = []
    for case in catalog['samples']:
        if case['assay'] not in {'klebsiella', 'kpneumoniae'}: continue
        relative = f'samples/{case["sample_id"]}/kleborate.tsv'; target = DERIVED / relative
        with target.open() as handle:
            reader = csv.DictReader(handle, delimiter='\t'); columns = reader.fieldnames; source_rows = list(reader)
        rename = {'klebsiella_pneumo_complex__' + h: MODULE + '__' + h
            for h in [c.removeprefix(MODULE + '__') for c in evidence['expected_columns']]}
        assert set(rename) <= set(columns)
        corrected_columns = [rename.get(c, c) for c in columns]; corrected_rows = []
        for row in source_rows:
            corrected = {rename.get(k, k): v for k, v in row.items()}
            for letter in ['K', 'O']:
                field = MODULE + '__' + letter + '_locus_identity'
                fraction = Decimal(corrected[field]); assert 0 <= fraction <= 1
                corrected[field] = format(fraction * 100, 'f') + '%'
                assert Decimal(corrected[field].removesuffix('%')) / 100 == fraction
            corrected_rows.append(corrected)
        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=corrected_columns, delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerows(corrected_rows); target.write_text(output.getvalue())
        # Independent roundtrip check: every source value survives the representational correction.
        inverse = {v: k for k, v in rename.items()}
        for source, corrected in zip(source_rows, corrected_rows):
            restored = {inverse.get(k, k): v for k, v in corrected.items()}
            for letter in ['K', 'O']:
                field = 'klebsiella_pneumo_complex__' + letter + '_locus_identity'
                assert Decimal(restored[field].removesuffix('%')) / 100 == Decimal(source[field])
                restored[field] = source[field]
            assert restored == source
        changed.append({'path': relative, 'source_sha256': digest(ORIGINAL / relative), 'corrected_sha256': digest(target),
            'header_renames': rename, 'value_changes': 'Two identity fractions expressed as equivalent percentages; other values unchanged'})
    assert len(changed) == 20
    entries = []
    for line in (ORIGINAL / 'checksums.sha256').read_text().splitlines():
        _, relative = line.split('  ', 1); entries.append(digest(DERIVED / relative) + '  ' + relative)
    (DERIVED / 'checksums.sha256').write_text('\n'.join(entries) + '\n')
    verify_originals()
    result = {'created_at_utc': now(), 'original': str(ORIGINAL), 'derived': str(DERIVED),
        'original_checksum_manifest_sha256': digest(ORIGINAL / 'checksums.sha256'),
        'derived_checksum_manifest_sha256': digest(DERIVED / 'checksums.sha256'), 'publisher_commit': UPSTREAM_PIN,
        'changed_reports': changed, 'expectations_unchanged': digest(ORIGINAL / 'expectations.json') == digest(DERIVED / 'expectations.json'),
        'originals_verified_unchanged': True, 'scope': 'Synthetic report formatting only; no biological result values were recalculated'}
    write(receipt, result)
    return result


def main():
    evidence = publisher_evidence(); result = corrected_copy(evidence)
    print(json.dumps({'changed_reports': len(result['changed_reports']), 'originals_unchanged': result['originals_verified_unchanged'],
        'expectations_unchanged': result['expectations_unchanged'], 'publisher_tag': evidence['tag'], 'publisher_commit': UPSTREAM_PIN}))


if __name__ == '__main__': main()

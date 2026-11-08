#!/usr/bin/env python3
"""Offline file/stream and selected-result checks on existing saved reports."""
from collections import Counter
from contextlib import ExitStack
import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path

from bonsai_libs.parse import run_parser
from bonsai_libs.parse.models.enums import AnalysisType

ROOT = Path('/audit/run')


def results(bundle):
    return {str(k): {'status': str(v.status), 'value': v.model_dump(mode='json', exclude_none=True).get('value')}
        for k, v in bundle.results.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['original', 'corrected'], default='original')
    args = parser.parse_args()
    catalog_file = ROOT / 'saved-report-catalog.json'; catalog = json.loads(catalog_file.read_text())
    checks = []; cases = []
    def check(case, name, passed, details):
        checks.append({'case': case['case'], 'software': case['software'], 'check': name,
            'status': 'PASS' if passed else 'FAIL', 'details': details})
    for case in catalog['cases']:
        software, _, subcommand = case['software'].partition('.')
        path = Path(case['container_path']); version = case['version']; aux = {k: Path(v) for k, v in case['auxiliary'].items()}
        assert sha256(path.read_bytes()).hexdigest() == case['sha256'], 'Input bytes changed: ' + case['case']
        try:
            bundle = run_parser(software, version=version, subcommand=subcommand or None, data=path, **aux)
            full = results(bundle)
        except Exception as error:
            check(case, 'saved-report-parse', False, {'exception': type(error).__name__, 'message': str(error)})
            continue
        errors = [k for k, v in full.items() if v['status'] == 'error']
        check(case, 'saved-report-parse', not errors, {'error_result_types': errors})
        usable = [k for k, v in full.items() if v['status'] in {'parsed', 'empty'}]
        case_result = {'case': case['case'], 'software': case['software'], 'version': version,
            'parser_name': bundle.parser_name, 'parser_version': bundle.parser_version, 'source_sha256_verified': True,
            'origin': case['origin'], 'version_basis': case['version_basis'],
            'statuses': {k: v['status'] for k, v in full.items()}, 'requires_format_review': not usable,
            'output_sha256': sha256(json.dumps(full, sort_keys=True).encode()).hexdigest()}
        cases.append(case_result)
        try:
            # Both the primary and auxiliary inputs use the same stream interface as multipart upload.
            with ExitStack() as stack:
                streams = {k: stack.enter_context(p.open(encoding='utf-8')) for k, p in aux.items()}
                primary = stack.enter_context(path.open(encoding='utf-8'))
                streamed = run_parser(software, version=version, subcommand=subcommand or None, data=primary, **streams)
                actual = results(streamed)
            check(case, 'primary-and-auxiliary-stream-equivalence', actual == full,
                {'auxiliary_streams': sorted(aux), 'same_status_and_values': actual == full})
        except Exception as error:
            check(case, 'primary-and-auxiliary-stream-equivalence', False, {'exception': type(error).__name__, 'message': str(error)})
        for kind, envelope in bundle.results.items():
            if str(envelope.status) == 'skipped': continue
            try:
                selected = run_parser(software, version=version, subcommand=subcommand or None, data=path, want={kind}, **aux)
                actual = results(selected)
                passed = actual[str(kind)] == full[str(kind)] and all(v['status'] == 'skipped' for k, v in actual.items() if k != str(kind))
                check(case, 'selected-result-' + str(kind), passed, {'same_selected_value_and_status': actual.get(str(kind)) == full[str(kind)]})
            except Exception as error:
                check(case, 'selected-result-' + str(kind), False, {'exception': type(error).__name__, 'message': str(error)})
        if case['software'] == 'quast':
            with path.open() as handle: row = next(csv.DictReader(handle, delimiter='\t'))
            mapping = {'total_length': 'Total length', 'reference_length': 'Reference length', 'largest_contig': 'Largest contig',
                'n_contigs': '# contigs', 'n50': 'N50', 'ng50': 'NG50', 'assembly_gc': 'GC (%)',
                'reference_gc': 'Reference GC (%)', 'duplication_ratio': 'Duplication ratio'}
            expected = {field: float(row[source]) for field, source in mapping.items() if source in row and row[source] not in {'-', '', 'NA'}}
            stored = full['qc']['value']
            check(case, 'independent-qc-fields', all(float(stored[k]) == v for k, v in expected.items()), {'compared_fields': len(expected)})
        if case['software'] == 'hAMRonization':
            with path.open() as handle: count = sum(1 for _ in csv.DictReader(handle, delimiter='\t'))
            value = full['amr']['value'] or []
            check(case, 'independent-companion-row-count', len(value) == count, {'source_rows': count, 'parsed_rows': len(value)})
    counts = dict(Counter(c['status'] for c in checks))
    result = {'scope': 'Saved report parsing and generic format contracts only; no sequence analysis or biological interpretation',
        'input_catalog_sha256': sha256(catalog_file.read_bytes()).hexdigest(), 'counts': counts, 'cases': cases, 'checks': checks,
        'review_cases': [c for c in cases if c['requires_format_review']],
        'remaining_limitations': ['Exact producer versions are unverified where stated',
            'Path/stream and selected-result agreement do not independently establish every upstream field mapping',
            'This offline pass does not establish live API/storage/browser coverage for every format']}
    name = 'saved-report-regression.json' if args.phase == 'original' else 'saved-report-regression-corrected.json'
    (ROOT / name).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'saved_report_cases': len(cases), 'counts': counts, 'format_review_cases': len(result['review_cases'])}))
    raise SystemExit(1 if counts.get('FAIL') else 0)


if __name__ == '__main__': main()

#!/usr/bin/env python3
"""Close the audit with input-integrity receipts and inspectable result data."""
import json
from pathlib import Path
import urllib.request

from prepare_fixtures import verify_originals
from run_audit import DATA, REPO, RUN, digest, now, prepare, write


def load(relative): return json.loads((RUN / relative).read_text())


def main():
    context = prepare(); verify_originals()
    original = load('original-summary.json'); corrected = load('corrected-summary.json')
    saved = load('saved-report-regression-corrected.json'); catalog = load('saved-report-catalog.json')
    corrections = load('fixture-corrections.json')
    sdk = next(j for j in original['jobs'] if j['job'] == 'sdk')
    prp = next(j for j in original['jobs'] if j['job'] == 'prp')
    historical = next(j for j in original['jobs'] if j['job'] == 'contracts')
    contracts = corrected['jobs'][0]
    assert sdk['counts'] == {'tests': 196, 'failures': 0, 'errors': 0, 'skipped': 0}
    assert prp['counts'] == {'tests': 46, 'failures': 0, 'errors': 0, 'skipped': 0}
    assert historical['counts'] == {'PASS': 694, 'FAIL': 20}
    assert historical['failure_categories'] == {'literal-input-fields': 20}
    assert contracts['counts'] == {'PASS': 714} and contracts['exit_code'] == 0
    assert saved['counts'] == {'PASS': 180} and not saved['review_cases']
    assert len(saved['cases']) == 48 and len(catalog['parser_matrix']) == 22
    assert all(r['saved_report_cases'] for r in catalog['parser_matrix'])
    assert saved['input_catalog_sha256'] == digest(RUN / 'saved-report-catalog.json')
    for case in catalog['cases']: assert digest(Path(case['path'])) == case['sha256']
    unknown = [{'case': c['case'], 'dispatch_label': c['version'], 'basis': c['version_basis']}
        for c in catalog['cases'] if '+fixture.unknown' in c['version']]
    result = {'completed_at_utc': now(), 'status': 'PASS_WITH_DERIVED_FIXTURE_CORRECTIONS',
        'scope': 'Offline saved-report formats, literal fixture fields, dispatch, result selection and upload orchestration',
        'production_parser_code_changed_in_this_increment': False, 'database_mutations': 0, 'new_sequence_analyses': 0,
        'source_context': context,
        'combined_regression': {'sdk_parser_tests': sdk['counts'], 'prp_tests': prp['counts'],
            'corrected_contract_checks': contracts['counts'], 'saved_report_checks': saved['counts']},
        'historical_fixture_run': {'counts': historical['counts'], 'failure_categories': historical['failure_categories'],
            'disposition': 'Twenty old synthetic reports omitted the publisher Kaptive module prefix; originals retained unchanged'},
        'fixture_corrections': {'reports': len(corrections['changed_reports']), 'originals_verified_unchanged': True,
            'expectations_unchanged': corrections['expectations_unchanged'], 'publisher_tag': 'v3.2.4',
            'publisher_commit': corrections['publisher_commit'],
            'publisher_header_definition': 'https://github.com/klebgenomics/Kleborate/blob/abc82ebe1a4a10bf4dcf0805d84d35fd6a846d2c/kleborate/modules/klebsiella_pneumo_complex__kaptive/klebsiella_pneumo_complex__kaptive.py',
            'value_preservation': 'Header nesting corrected and identity fractions expressed as equivalent percentages; other source values and expected results unchanged'},
        'saved_report_coverage': {'files': 48, 'registered_parser_keys_with_examples': 22,
            'reported_parser_names': len({c['parser_name'] for c in saved['cases']}),
            'primary_and_auxiliary_stream_cases': sum(c['check'] == 'primary-and-auxiliary-stream-equivalence' for c in saved['checks']),
            'explicit_unknown_version_labels': unknown},
        'fixture_metadata_findings': catalog['metadata_findings'],
        'remaining_validation_gaps': [
            'Exact historical producer releases remain unverified where only manifest or synthetic version labels exist',
            'Not every upstream field has an independent expected-value oracle',
            'Offline coverage does not establish live API, storage, export and browser behavior for every format',
            'Analysis reimport, overwrite, version replacement and failure recovery remain only partly covered'],
        'known_open_ui_issue': {'priority': 'P1', 'scope': 'Kleborate summary rendering',
            'report': 'http://100.90.51.21:8001/organisms/kleborate/', 'resolved_by_this_audit': False},
        'artifact_paths': {'run': str(RUN), 'catalog': str(REPO / 'datasets/bonsai_parser_fixture_audit.json'),
            'corrected_fixtures': corrections['derived'], 'correction_receipt': str(RUN / 'fixture-corrections.json')}}
    write(RUN / 'result.json', result)
    public = DATA / 'docs/development-findings/organisms/data'
    assert public.is_dir(), 'Existing findings server data directory is missing'
    write(public / 'parser-audit-results.json', result)
    write(public / 'parser-audit-matrix.json', {'recorded_at_utc': result['completed_at_utc'], 'parsers': catalog['parser_matrix']})
    url = 'http://127.0.0.1:8001/organisms/data/parser-audit-results.json'
    with urllib.request.urlopen(url, timeout=20) as response: published = json.load(response)
    assert published == result
    print(json.dumps({'status': result['status'], 'sdk_tests': 196, 'prp_tests': 46, 'contract_checks': 714,
        'saved_report_checks': 180, 'corrected_reports': 20, 'registered_parser_keys': 22,
        'originals_unchanged': True, 'published_result': 'http://100.90.51.21:8001/organisms/data/parser-audit-results.json'}))


if __name__ == '__main__': main()

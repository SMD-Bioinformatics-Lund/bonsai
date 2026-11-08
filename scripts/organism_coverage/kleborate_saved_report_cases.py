#!/usr/bin/env python3
"""Exercise saved-report companion transport; no sequence tools are invoked."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess

from coverage_common import DATA, HUB, PILOT, REPO, hashes, now, write
from run_saved_report_case import FIXTURE_PIN, FIXTURE_REPO

ROOT = HUB / 'cases/klebsiella/saved-report-ingestion'
RAW = DATA / 'datasets/github/bonsai-sdk-saved-reports' / FIXTURE_PIN / 'raw/kpneumoniae'
DERIVED = RAW.parent.parent / 'derived/kpneumoniae-software-controls'
PRP_BASE = DATA / 'environments/prp-2.0.0/source'
PRP_FIXED = DATA / 'environments/prp-kleborate-companion/source'
PRIMARY = 'kleborate_v3_kpsc_output.txt'
COMPANION = 'kleborate_v3_kpsc_hamronization_output.txt'
CASES = [{'key': alias + '-' + state, 'assay': alias, 'companion_state': state,
    'external_id': 'fixture_kleb_' + alias + '_' + state,
    'label': 'Saved Kleborate software fixture / ' + alias + ' / ' + state}
    for alias in ['klebsiella', 'kpneumoniae'] for state in ['provided', 'header-only']]


def prepare():
    rows = []
    for filename in [PRIMARY, COMPANION]:
        relative = 'tests/fixtures/kpneumoniae/' + filename
        original = subprocess.check_output(['git', '-C', str(FIXTURE_REPO), 'show', FIXTURE_PIN + ':' + relative])
        target = RAW / filename; target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == original, 'Preserved report changed'
        else:
            target.write_bytes(original)
        rows.append({'path': str(target.relative_to(DATA)), **hashes(target), 'git_object_verified': True,
            'upstream_url': f'https://github.com/SMD-Bioinformatics-Lund/bonsai-sdk/blob/{FIXTURE_PIN}/{relative}'})
    DERIVED.mkdir(parents=True, exist_ok=True)
    empty = DERIVED / 'header-only-companion.tsv'
    header = (RAW / COMPANION).read_bytes().splitlines(keepends=True)[0]
    if empty.exists():
        assert empty.read_bytes() == header
    else:
        empty.write_bytes(header)
    catalog_path = REPO / 'datasets/bonsai_kleborate_saved_report_cases.json'
    previous = json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
    catalog = {'acquired_at_utc': previous.get('acquired_at_utc', now()), 'fixture_commit': FIXTURE_PIN,
        'origin': 'One saved report/companion pair reused for software scenarios; not four biological samples',
        'scope': 'Report transport, parsing, persistence and literal browser display; no new sequence analysis or interpretation',
        'source_reports': rows, 'cases': CASES, 'sequence_processing_enabled': False,
        'header_only_control': {'path': str(empty.relative_to(DATA)), **hashes(empty),
            'parent': str((RAW / COMPANION).relative_to(DATA)), 'derivation': 'First header line only; synthetic empty-companion software control',
            'limitation': 'The primary report is unchanged; this is not a coherent biological no-findings sample'},
        'excluded': ['mislabelled Quast fixture', 'original inconsistent run metadata', 'raw reads', 'genomes', 'typing schemas', 'sequence indexes', 'variants']}
    if (ROOT / 'local-fixes.json').exists(): catalog['local_fixes'] = json.loads((ROOT / 'local-fixes.json').read_text())
    write(catalog_path, catalog); write(RAW.parent.parent / 'metadata/kpneumoniae-acquisition.json', catalog)
    for case in CASES:
        directory = ROOT / case['key']; directory.mkdir(parents=True, exist_ok=True)
        run_info = directory / 'fixture-import-metadata.json'
        if not run_info.exists():
            write(run_info, {'workflow_name': 'saved-kleborate-' + case['key'], 'assay': case['assay'],
                'pipeline': 'Bonsai saved-report companion test', 'version': 'fixture-sdk-5789a9c',
                'commit': FIXTURE_PIN, 'release_life_cycle': 'development', 'date': now(),
                'command': 'Saved result files imported; no producer run', 'analysis_profile': ['klebsiella'],
                'configuration_files': [], 'sequencing_run': 'fixture_no_new_sequencing', 'sequencing_platform': 'illumina', 'sequencing_type': 'PE'})
        companion = RAW / COMPANION if case['companion_state'] == 'provided' else empty
        write(directory / 'manifest.yml', {'sample_id': case['external_id'], 'sample_name': case['label'],
            'lims_id': 'FIXTURE-' + case['key'].upper(), 'groups': [case['assay']],
            'metadata': [{'fieldname': 'Test data origin', 'value': catalog['origin'], 'type': 'string', 'category': 'general'},
                {'fieldname': 'Test scope', 'value': catalog['scope'], 'type': 'string', 'category': 'general'},
                {'fieldname': 'Companion state', 'value': case['companion_state'], 'type': 'string', 'category': 'general'}],
            'nextflow_run_info': str(run_info), 'analysis_result': [
                {'software': 'kleborate', 'software_version': '3.2.4', 'uri': str(RAW / PRIMARY)},
                {'software': 'hAMRonization', 'software_version': '3.2.4', 'uri': str(companion)}]})
    print('Four software scenarios prepared from one pinned saved-report pair', flush=True)


def upload(baseline=False):
    from bonsai_libs.api_client.bonsai.models import CreateGroupInput
    from bonsai_libs.parse.core.registry import run_parser
    import bonsai_libs.parse.parsers  # register the installed parsers
    from prp.bonsai import BonsaiUploadService, make_bonsai_client
    from prp.bonsai.service import UploadStateStore
    from prp.io.manifest import read_manifest
    from prp.pipeline.loader import parse_manifest_for_upload

    def login(username, password):
        client = make_bonsai_client(base_url='http://api:8000'); client.timeout = 60
        assert client.authenticate_user(username=username, password=password), 'Authentication failed'
        return client
    values = dict(line.split('=', 1) for line in (PILOT / 'bonsai/compose.env').read_text().splitlines() if '=' in line)
    admin = login('pilot_admin', values['JASEN_PILOT_PASSWORD'])
    groups = {g.group_key for g in admin.get_groups()}
    for alias in ['klebsiella', 'kpneumoniae']:
        if alias not in groups:
            admin.create_group(CreateGroupInput(group_key=alias, display_name='Saved-report fixtures / ' + alias,
                description='Saved report transport and display tests; no new biological analysis'))
    account = json.loads((PILOT / 'bonsai/accounts.json').read_text())['pilot_uploader']
    client = login(account['username'], account['password'])
    outcomes = []
    for case in CASES[:1] if baseline else CASES:
        directory = ROOT / case['key']; status_file = directory / 'import-status.json'
        if not baseline and status_file.exists() and json.loads(status_file.read_text())['status'] == 'COMPLETE':
            outcomes.append(json.loads(status_file.read_text())); continue
        parsed = parse_manifest_for_upload(read_manifest(directory / 'manifest.yml'))
        service = BonsaiUploadService(client=client, state_store=UploadStateStore(root=directory / 'upload-state'),
            workflow_id='bonsai-saved-kleborate-' + case['key'], ignore_errors=False)
        try:
            result = service.upload_sample(parsed, force=False)
        except Exception as error:
            sample = client.get_sample_by_external_id(case['external_id'])
            descriptors = [r for k in ['typing_result', 'qc_result', 'element_type_result', 'species_prediction'] for r in sample.get(k, [])]
            if baseline:
                assert 'hAMRonization' in str(error) and not descriptors, 'Unexpected baseline failure'
                state = {'status': 'EXPECTED_BASELINE_FAILURE', 'checked_at_utc': now(), 'sample_id': sample['sample_id'],
                    'error': str(error), 'stored_view_descriptors': len(descriptors), 'partial_analysis_write': False,
                    'uploader_commit': '085ce7d3f2e475860cbe1529698e87fc17e6f801'}
                write(ROOT / 'baseline-result.json', state); print('Pinned PRP failure reproduced; rejected analysis left no view descriptors', flush=True)
                return
            write(status_file, {'status': 'FAILED', 'checked_at_utc': now(), 'error': str(error), 'sample_id': sample['sample_id']})
            raise
        assert not baseline, 'Baseline unexpectedly succeeded'
        sample = client.get_sample_by_id(result.sample_id)
        write(directory / 'sample-after-import.json', sample)
        companion = RAW / COMPANION if case['companion_state'] == 'provided' else DERIVED / 'header-only-companion.tsv'
        expected = run_parser('kleborate', version='3.2.4', data=RAW / PRIMARY, hamronization_source=companion)
        write(directory / 'expected-parser-output.json', expected.model_dump(mode='json', exclude_none=True))
        descriptors = [r for k in ['typing_result', 'qc_result', 'element_type_result', 'species_prediction'] for r in sample.get(k, [])]
        assert len({r['analysis_id'] for r in descriptors}) == 1 and len(descriptors) == len(expected.results)
        assert all(r['status'] != 'error' for r in descriptors)
        state = {'status': 'COMPLETE', 'finished_at_utc': now(), **case, 'sample_id': sample['sample_id'],
            'analysis_records': 1, 'view_descriptors': len(descriptors), 'descriptor_statuses': {r['analysis_type']: r['status'] for r in descriptors},
            'upload_result': asdict(result), 'sequence_processing_started': False}
        write(status_file, state); outcomes.append(state)
        print(case['key'] + ': imported one canonical analysis; ' + str(len(descriptors)) + ' descriptors', flush=True)
    write(ROOT / 'import-status.json', {'status': 'COMPLETE', 'finished_at_utc': now(), 'cases': outcomes})


def launch(baseline=False):
    from prepare_bonsai import compose
    if baseline and (ROOT / 'baseline-result.json').exists():
        print('Captured baseline failure preserved; no repeat upload requested', flush=True)
        return
    prepare(); source = PRP_BASE if baseline else PRP_FIXED
    assert source.is_dir(), 'Uploader source is not prepared'
    command = compose('run', '--rm', '--no-deps', '-T', '--user', f'{os.getuid()}:{os.getgid()}',
        '-v', f'{DATA}:{DATA}:ro', '-v', f'{ROOT}:{ROOT}:rw', '-v', f'{REPO}:{REPO}:ro',
        '-v', f'{source}:/pilot-prp:ro', '-e', 'PYTHONPATH=/pilot-prp:/app/api', '-e', 'JASEN_PILOT_DATA=' + str(DATA),
        'api', 'python', str(Path(__file__).resolve()), '--upload')
    if baseline: command.append('--baseline')
    name = 'baseline' if baseline else 'fixed'
    write(ROOT / (name + '-command.json'), {'command': command, 'created_at_utc': now()})
    with (ROOT / (name + '-import.log')).open('a') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upload', action='store_true'); parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    if args.upload: upload(args.baseline)
    else: launch(args.baseline)

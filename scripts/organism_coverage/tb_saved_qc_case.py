#!/usr/bin/env python3
"""One TB-profile software case using two existing numeric QC reports only."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess

from coverage_common import DATA, HUB, PILOT, REPO, hashes, now, write
from run_saved_report_case import FIXTURE_PIN, FIXTURE_REPO

CASE = HUB / 'cases/mtuberculosis/saved-qc-software-test'
RAW = DATA / 'datasets/github/bonsai-sdk-saved-reports' / FIXTURE_PIN / 'raw/mtuberculosis'
EXTERNAL = 'fixture_tb_sdk5789'
LABEL = 'TB-profile saved-QC software fixture'
LIMS = 'FIXTURE-TB-001'
REPORTS = [('quast.tsv', 'quast', '5.2.0'), ('bwa.qc', 'postalignqc', '0.0.0+fixture.unknown')]
ORIGIN = 'Existing repository QC reports; mixed fixtures, not a newly analysed TB isolate'
SCOPE = 'Numeric QC parsing, persistence and UI display only; no new sequence, resistance, virulence or lineage analysis'


def prepare():
    rows = []
    for filename, software, version in REPORTS:
        relative = 'tests/fixtures/mtuberculosis/' + filename
        original = subprocess.check_output(['git', '-C', str(FIXTURE_REPO), 'show', FIXTURE_PIN + ':' + relative])
        destination = RAW / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == original, 'Preserved fixture changed'
        else:
            destination.write_bytes(original)
        rows.append({'filename': filename, 'path': str(destination.relative_to(DATA)),
            'upstream_url': f'https://github.com/SMD-Bioinformatics-Lund/bonsai-sdk/blob/{FIXTURE_PIN}/{relative}',
            'git_object_verified': True, 'publisher_checksum_verified': False,
            **hashes(destination), 'software': software, 'software_version': version})
    catalog_path = REPO / 'datasets/bonsai_tb_saved_qc_case.json'
    previous = json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
    catalog = {'case': EXTERNAL, 'profile': 'mtuberculosis', 'source_commit': FIXTURE_PIN,
        'acquired_at_utc': previous.get('acquired_at_utc', now()), 'data_root': str(DATA),
        'origin': ORIGIN, 'scope': SCOPE, 'reports': rows, 'sequence_processing_enabled': False,
        'version_note': 'Legacy postalignqc producer version is absent from the source fixture; 0.0.0+fixture.unknown is a synthetic version placeholder required by the API',
        'excluded': ['raw reads', 'genomes', 'typing schemas', 'resistance/virulence/lineage reports', 'sequence indexes', 'variant files']}
    write(catalog_path, catalog)
    write(RAW.parent.parent / 'metadata/mtuberculosis-acquisition.json', catalog)
    CASE.mkdir(parents=True, exist_ok=True)
    run_info = CASE / 'fixture-import-metadata.json'
    if not run_info.exists():
        write(run_info, {'workflow_name': 'saved-qc-tb-20261108', 'assay': 'mtuberculosis',
            'pipeline': 'Bonsai saved-QC software test', 'version': 'fixture-sdk-5789a9c',
            'commit': FIXTURE_PIN, 'release_life_cycle': 'development', 'date': now(),
            'command': 'Two saved numeric QC reports imported; no producer run',
            'analysis_profile': ['mycobacterium_tuberculosis'], 'configuration_files': [],
            'sequencing_run': 'fixture_no_new_sequencing', 'sequencing_platform': 'illumina', 'sequencing_type': 'PE'})
    write(CASE / 'manifest.yml', {'sample_id': EXTERNAL, 'sample_name': LABEL, 'lims_id': LIMS,
        'groups': ['mtuberculosis'], 'metadata': [
            {'fieldname': 'Test data origin', 'value': ORIGIN, 'type': 'string', 'category': 'general'},
            {'fieldname': 'Test scope', 'value': SCOPE, 'type': 'string', 'category': 'general'}],
        'nextflow_run_info': str(run_info), 'analysis_result': [
            {'software': r['software'], 'software_version': r['software_version'], 'uri': str(DATA / r['path'])} for r in rows]})
    print('Two pinned numeric QC reports preserved; no sequence files selected', flush=True)


def upload():
    from bonsai_libs.api_client.bonsai.models import CreateGroupInput
    from prp.bonsai import BonsaiUploadService, make_bonsai_client
    from prp.bonsai.service import UploadStateStore
    from prp.io.manifest import read_manifest
    from prp.pipeline.loader import parse_manifest_for_upload

    status_file = CASE / 'import-status.json'
    if status_file.exists() and json.loads(status_file.read_text())['status'] == 'COMPLETE':
        print('Completed QC import preserved', flush=True)
        return
    def login(username, password):
        client = make_bonsai_client(base_url='http://api:8000'); client.timeout = 60
        assert client.authenticate_user(username=username, password=password), 'Authentication failed'
        return client
    values = dict(line.split('=', 1) for line in (PILOT / 'bonsai/compose.env').read_text().splitlines() if '=' in line)
    admin = login('pilot_admin', values['JASEN_PILOT_PASSWORD'])
    if not any(group.group_key == 'mtuberculosis' for group in admin.get_groups()):
        admin.create_group(CreateGroupInput(group_key='mtuberculosis', display_name='TB-profile software fixtures',
            description='Saved numeric QC reports only; no new sequence analysis'))
    account = json.loads((PILOT / 'bonsai/accounts.json').read_text())['pilot_uploader']
    client = login(account['username'], account['password'])
    parsed = parse_manifest_for_upload(read_manifest(CASE / 'manifest.yml'))
    assert parsed.reference_genome_accession is None and parsed.index_artifacts is None and not parsed.annotation_tracks
    assert {r.software for r in parsed.analysis_results} == {'quast', 'postalignqc'}
    state = {'status': 'RUNNING', 'started_at_utc': now(), 'account': account['username'],
        'origin': ORIGIN, 'scope': SCOPE, 'sequence_processing_started': False,
        'fixture_commit': FIXTURE_PIN, 'reports': 2, 'expected_analysis_records': 2}
    write(status_file, state)
    try:
        result = BonsaiUploadService(client=client, state_store=UploadStateStore(root=CASE / 'upload-state'),
            workflow_id='bonsai-saved-qc-tb-20261108', ignore_errors=False).upload_sample(parsed, force=False)
        sample = client.get_sample_by_id(result.sample_id)
        write(CASE / 'sample-after-import.json', sample)
        assert sample['external_sample_id'] == EXTERNAL and sample['sample_name'] == LABEL
        assert len(sample['qc_result']) == 2 and all(r['status'] == 'parsed' for r in sample['qc_result'])
        assert not any(sample.get(k) for k in ['typing_result', 'element_type_result', 'species_prediction'])
        state.update(status='COMPLETE', finished_at_utc=now(), sample_id=sample['sample_id'],
            analysis_records=2, view_descriptors=2, upload_result=asdict(result))
    except Exception as error:
        state.update(status='FAILED', finished_at_utc=now(), error=str(error)); write(status_file, state)
        raise
    write(status_file, state)
    print('TB-profile saved-QC import complete: two parsed analyses', flush=True)


def launch():
    from prepare_bonsai import compose
    prepare()
    command = compose('run', '--rm', '--no-deps', '-T', '--user', f'{os.getuid()}:{os.getgid()}',
        '-v', f'{DATA}:{DATA}:ro', '-v', f'{CASE}:{CASE}:rw', '-v', f'{REPO}:{REPO}:ro',
        '-v', str(DATA / 'environments/prp-2.0.0/source') + ':/pilot-prp:ro',
        '-e', 'PYTHONPATH=/pilot-prp:/app/api', '-e', 'JASEN_PILOT_DATA=' + str(DATA),
        'api', 'python', str(Path(__file__).resolve()), '--upload')
    write(CASE / 'import-command.json', {'command': command, 'created_at_utc': now()})
    with (CASE / 'import.log').open('a') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    print('Import evidence: ' + str(CASE), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upload', action='store_true', help='Container-only import step')
    if parser.parse_args().upload:
        upload()
    else:
        launch()

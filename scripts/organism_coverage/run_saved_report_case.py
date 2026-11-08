#!/usr/bin/env python3
"""Import one saved S. aureus SDK fixture bundle; never run a sequence tool."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess

from coverage_common import DATA, HUB, PILOT, REPO, hashes, now, write

FIXTURE_REPO = REPO.parent / 'bonsai/bonsai-sdk'
FIXTURE_PIN = '5789a9c7530407683f1fee9ffa450512269e62bc'
CASE = HUB / 'cases/saureus/saved-report-software-test'
EXTERNAL = 'fixture_saureus_sdk5789'
LABEL = 'S. aureus saved-report software fixture'
REPORTS = [
    ('spatyper.tsv', 'spatyper', None, '0.3.3'),
    ('quast.tsv', 'quast', None, '5.2.0'),
    ('samtools_coverage.txt', 'samtools', 'coverage', '1.17'),
    ('samtools_bedcov.txt', 'samtools', 'bedcov', '1.17'),
    ('samtools_stats.txt', 'samtools', 'stats', '1.17'),
]


def prepare():
    raw = DATA / 'datasets/github/bonsai-sdk-saved-reports' / FIXTURE_PIN / 'raw/saureus'
    rows = []
    for filename, software, subcommand, version in REPORTS:
        relative = 'tests/fixtures/saureus/' + filename
        original = subprocess.check_output(['git', '-C', str(FIXTURE_REPO), 'show', FIXTURE_PIN + ':' + relative])
        destination = raw / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == original, 'Preserved fixture changed'
        else:
            destination.write_bytes(original)
        rows.append({'filename': filename, 'path': str(destination.relative_to(DATA)),
            'upstream_url': f'https://github.com/SMD-Bioinformatics-Lund/bonsai-sdk/blob/{FIXTURE_PIN}/{relative}',
            'git_object_verified': True, 'publisher_checksum_verified': False,
            **hashes(destination), 'software': software, 'subcommand': subcommand, 'software_version': version})
    catalog_path = REPO / 'datasets/bonsai_saved_report_case.json'
    previous = json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
    catalog = {'case': EXTERNAL, 'profile': 'saureus', 'source_commit': FIXTURE_PIN,
        'acquired_at_utc': previous.get('acquired_at_utc', now()), 'data_root': str(DATA),
        'origin': 'Existing repository test reports; mixed fixtures, not a newly analysed isolate',
        'scope': 'Literal report parsing, persistence and UI display; no sequence processing or clinical interpretation',
        'reports': rows, 'sequence_processing_enabled': False,
        'excluded': ['raw reads', 'genomes', 'typing schemas', 'resistance/virulence reports', 'sequence indexes', 'variant files']}
    write(catalog_path, catalog)
    write(raw.parent.parent / 'metadata/acquisition.json', catalog)
    CASE.mkdir(parents=True, exist_ok=True)
    run_info = CASE / 'fixture-import-metadata.json'
    if not run_info.exists():
        write(run_info, {'workflow_name': 'saved-report-saureus-20261108', 'assay': 'saureus',
            'pipeline': 'Bonsai saved-report software test', 'version': 'fixture-sdk-5789a9c',
            'commit': FIXTURE_PIN, 'release_life_cycle': 'development', 'date': now(),
            'command': 'Saved repository reports imported; no producer run',
            'analysis_profile': ['staphylococcus_aureus'], 'configuration_files': [],
            'sequencing_run': 'fixture_no_new_sequencing', 'sequencing_platform': 'illumina',
            'sequencing_type': 'PE'})
    manifest = {'sample_id': EXTERNAL, 'sample_name': LABEL, 'lims_id': 'FIXTURE-SAUREUS-001',
        'groups': ['saureus'], 'metadata': [
            {'fieldname': 'Test data origin', 'value': catalog['origin'], 'type': 'string', 'category': 'general'},
            {'fieldname': 'Test scope', 'value': catalog['scope'], 'type': 'string', 'category': 'general'}],
        'nextflow_run_info': str(run_info), 'analysis_result': [
            {'software': r['software'], 'subcommand': r['subcommand'], 'software_version': r['software_version'],
             'uri': str(DATA / r['path'])} for r in rows]}
    write(CASE / 'manifest.yml', manifest)  # JSON is valid YAML; paths are explicit.
    print('Five pinned report files preserved; four canonical analyses expected (bedcov is auxiliary)', flush=True)


def upload():
    from bonsai_libs.api_client.bonsai.models import CreateGroupInput
    from prp.bonsai import BonsaiUploadService, make_bonsai_client
    from prp.bonsai.service import UploadStateStore
    from prp.io.manifest import read_manifest
    from prp.pipeline.loader import parse_manifest_for_upload

    status_file = CASE / 'import-status.json'
    if status_file.exists() and json.loads(status_file.read_text())['status'] == 'COMPLETE':
        print('Completed fixture import preserved', flush=True)
        return
    def login(username, password):
        client = make_bonsai_client(base_url='http://api:8000')
        client.timeout = 60
        assert client.authenticate_user(username=username, password=password), 'Authentication failed'
        return client
    values = dict(line.split('=', 1) for line in (PILOT / 'bonsai/compose.env').read_text().splitlines() if '=' in line)
    admin = login('pilot_admin', values['JASEN_PILOT_PASSWORD'])
    if not any(group.group_key == 'saureus' for group in admin.get_groups()):
        admin.create_group(CreateGroupInput(group_key='saureus', display_name='S. aureus software fixtures',
            description='Saved-report software test; no new sequence analysis'))
    account = json.loads((PILOT / 'bonsai/accounts.json').read_text())['pilot_uploader']
    client = login(account['username'], account['password'])
    parsed = parse_manifest_for_upload(read_manifest(CASE / 'manifest.yml'))
    assert parsed.reference_genome_accession is None and parsed.index_artifacts is None and not parsed.annotation_tracks
    state = {'status': 'RUNNING', 'started_at_utc': now(), 'account': account['username'],
        'origin': 'Saved SDK report fixtures; no new producer run', 'sequence_processing_started': False,
        'fixture_commit': FIXTURE_PIN, 'reports': len(parsed.analysis_results), 'expected_analysis_records': 4}
    write(status_file, state)
    try:
        service = BonsaiUploadService(client=client, state_store=UploadStateStore(root=CASE / 'upload-state'),
            workflow_id='bonsai-saved-report-saureus-20261108', ignore_errors=False)
        result = service.upload_sample(parsed, force=False)
        sample = client.get_sample_by_id(result.sample_id)
        write(CASE / 'sample-after-import.json', sample)
        descriptors = [r for field in ['qc_result', 'typing_result', 'element_type_result', 'species_prediction']
            for r in sample.get(field, [])]
        assert sample['external_sample_id'] == EXTERNAL and sample['sample_name'] == LABEL
        assert len({r['analysis_id'] for r in descriptors}) == 4 and len(descriptors) == 4
        assert all(r['status'] == 'parsed' for r in descriptors)
        state.update(status='COMPLETE', finished_at_utc=now(), sample_id=sample['sample_id'],
            analysis_records=4, view_descriptors=4, upload_result=asdict(result))
    except Exception as error:
        state.update(status='FAILED', finished_at_utc=now(), error=str(error))
        write(status_file, state)
        raise
    write(status_file, state)
    print('Saved-report import complete: four parsed analyses, no sequence processing', flush=True)


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
    print('Fixture import finished; evidence: ' + str(CASE), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upload', action='store_true', help='Container-only import step')
    if parser.parse_args().upload:
        upload()
    else:
        launch()

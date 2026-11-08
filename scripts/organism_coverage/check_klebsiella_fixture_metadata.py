#!/usr/bin/env python3
"""Check saved-fixture provenance and prior coverage without importing a record."""
import csv
from io import StringIO
import json
import subprocess

from coverage_common import DATA, HUB, now, write
from run_saved_report_case import FIXTURE_PIN, FIXTURE_REPO


def main():
    def source(relative):
        return subprocess.check_output(['git', '-C', str(FIXTURE_REPO), 'show', FIXTURE_PIN + ':' + relative])
    prefix = 'tests/fixtures/kpneumoniae/'
    metadata = json.loads(source(prefix + 'analysis_meta.json'))
    quast = source(prefix + 'quast.tsv')
    assembly = next(csv.DictReader(StringIO(quast.decode()), delimiter='\t'))['Assembly']
    coverage_path = DATA.parent / 'bonsai/runs/2026-11-06-species-ui/parser-display/2026-11-07/coverage.json'
    earlier = json.loads(coverage_path.read_text())
    aliases = [r for r in earlier['assays'] if r['assay'] in {'kpneumoniae', 'klebsiella'}]
    assert len(aliases) == 2 and all(r['offline_reports'] == r['offline_report_passes'] and
        r['records'] == r['browser_identity_passes'] for r in aliases)
    status = {'checked_at_utc': now(), 'status': 'DUPLICATE_QC_IMPORT_SKIPPED',
        'scope': 'Prior synthetic coverage and saved fixture metadata; no new biological analysis or record import',
        'fixture_commit': FIXTURE_PIN, 'earlier_coverage_source': str(coverage_path),
        'earlier_alias_coverage': aliases, 'new_record_imported': False,
        'observations': {'metadata_assay': metadata['assay'], 'qc_assembly_label': assembly,
            'qc_bytes_identical_to_ecoli_fixture': quast == source('tests/fixtures/ecoli/quast.tsv')},
        'fixture_urls': [f'https://github.com/SMD-Bioinformatics-Lund/bonsai-sdk/blob/{FIXTURE_PIN}/{prefix}{name}'
            for name in ['analysis_meta.json', 'quast.tsv']],
        'findings': [{'id': 'KLEBSIELLA-FIXTURE-PROVENANCE', 'priority': 'P2',
            'title': 'Klebsiella repository fixtures contain E. coli metadata and QC data',
            'observed': 'Run metadata declares ecoli; the QC assembly label is ecoli_test_1 and its bytes match the E. coli fixture.',
            'trigger_likelihood': 'Use of this repository fixture as a representative Klebsiella producer result; production frequency is not established',
            'fix_size': 'Small test-fixture metadata correction and an accurately labelled or replaced QC fixture; no production restructuring',
            'limitation': 'Generic parser coverage remains valid; representative Klebsiella producer coverage cannot be inferred',
            'production_code_changed': False}],
        'remaining_gap': 'Complete saved-report Kleborate ingestion and display with its companion file; the earlier offline passes and plumbing tests do not establish that integration'}
    assert status['observations']['metadata_assay'] == 'ecoli'
    assert status['observations']['qc_bytes_identical_to_ecoli_fixture']
    write(HUB / 'cases/klebsiella/fixture-preflight.json', status)
    print('Earlier coverage confirmed for both aliases; duplicate QC import skipped; fixture provenance issue recorded')


if __name__ == '__main__':
    main()

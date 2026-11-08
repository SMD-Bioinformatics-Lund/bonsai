#!/usr/bin/env python3
"""Catalog report schemas and declared versions without interpreting results."""
from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path

import yaml

from run_audit import DATA, JASEN, REPO, RUN, ORIGINAL, SDK, digest, now, write

NATIVE = JASEN / 'runs/2026-11-08-bonsai-reference-pilot/output/ecoli'
SDK_FIXTURES = SDK / 'tests/fixtures'


def schema(path, software):
    text = path.read_text()
    if path.suffix == '.json' or (path.name.endswith('.qc') and text.lstrip().startswith('{')):
        value = json.loads(text)
        first = value[0] if isinstance(value, list) and value else value
        keys = sorted(first) if isinstance(first, dict) else []
        import hashlib
        return {'format': 'json', 'root_type': type(value).__name__, 'top_level_fields': len(keys),
            'field_name_sha256': hashlib.sha256(json.dumps(keys).encode()).hexdigest()}
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines: return {'format': 'empty', 'line_count': 0}
    delimiter = ',' if path.suffix == '.csv' else '\t'
    if delimiter not in lines[0]: return {'format': 'text', 'line_count': len(lines)}
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter)); headers = rows[0]
    if software in {'kraken', 'emmtyper'}:
        return {'format': 'headerless-delimited', 'columns': len(headers), 'data_rows': len(rows),
            'header_note': 'The first row is data, not column names'}
    duplicates = {name: [i for i, col in enumerate(headers) if col == name] for name, n in Counter(headers).items() if n > 1}
    import hashlib
    return {'format': 'delimited', 'columns': len(headers), 'data_rows': max(0, len(rows)-1),
        'header_sha256': hashlib.sha256(json.dumps(headers).encode()).hexdigest(),
        'duplicate_headers': list(duplicates),
        'conflicting_duplicate_headers': [name for name, indices in duplicates.items()
            if any(len({row[i] for i in indices if i < len(row)}) > 1 for row in rows[1:])]}


def main():
    cases = []; metadata_findings = []
    def add(key, software, version, path, origin, version_basis, group=None, aux=None, role='primary'):
        assert path.is_file(), path
        if path.is_relative_to(SDK): container = '/audit/sdk/' + str(path.relative_to(SDK))
        elif path.is_relative_to(NATIVE): container = '/audit/native/' + str(path.relative_to(NATIVE))
        else: raise ValueError(path)
        cases.append({'case': key, 'software': software, 'version': str(version), 'path': str(path),
            'container_path': container, 'origin': origin, 'version_basis': version_basis, 'fixture_group': group,
            'role': role, 'sha256': digest(path), 'bytes': path.stat().st_size, 'schema': schema(path, software), 'auxiliary': aux or {}})
    for folder in sorted(SDK_FIXTURES.iterdir()):
        manifest = folder / 'sample_1.manifest.yml'
        if not manifest.exists(): continue
        payload = yaml.safe_load(manifest.read_text())
        reports = payload['analysis_result']; group = folder.name
        nextflow = folder / payload['nextflow_run_info']
        if nextflow.exists():
            run = json.loads(nextflow.read_text())
            aliases = {'kpneumoniae', 'klebsiella'} if group == 'kpneumoniae' else {group}
            if run.get('assay') not in aliases:
                metadata_findings.append({'type': 'fixture-assay-mismatch', 'fixture': group, 'declared_assay': run.get('assay'),
                    'manifest': str(manifest), 'scope': 'Repository fixture metadata, not a verified producer run'})
        for item in reports:
            software = item['software']; subcommand = item.get('subcommand')
            if software == 'samtools' and subcommand == 'bedcov': continue
            key = software + ('.' + subcommand if subcommand else '')
            path = (folder / item['uri']).absolute(); aux = {}
            if software == 'kleborate':
                companion = next(r for r in reports if r['software'] == 'hAMRonization')
                aux['hamronization_source'] = '/audit/sdk/' + str((folder / companion['uri']).relative_to(SDK))
            if key == 'samtools.stats':
                for command, field in [('coverage', 'coverage_path'), ('bedcov', 'bedcov_path')]:
                    selected = next((r for r in reports if r['software'] == 'samtools' and r.get('subcommand') == command), None)
                    if selected: aux[field] = '/audit/sdk/' + str((folder / selected['uri']).relative_to(SDK))
            add(group + '/' + key, key, item['software_version'], path, 'saved_repository_fixture',
                'Declared in repository manifest; producer execution/version not independently verified', group, aux,
                'companion' if key == 'hAMRonization' else 'primary')
    extra = [
        ('streptococcus/emmtyper.tsv', 'emmtyper', '0.0.0+fixture.unknown', 'Producer version absent; placeholder is a dispatch label'),
        ('streptococcus/kraken.report', 'kraken', '0.0.0+fixture.unknown', 'Producer version absent; placeholder is a dispatch label'),
        ('saureus/amrfinder.v3.tsv', 'amrfinder', '3.0.0+fixture.unknown', 'Legacy format family from fixture filename; exact producer version unverified'),
        ('ecoli/virulencefinder.v2.stx.json', 'virulencefinder', '2.0.0+fixture.unknown', 'Legacy format family from fixture filename; exact producer version unverified'),
        ('saureus/bwa.qc', 'postalignqc', '0.0.0+fixture.unknown', 'Legacy numeric QC fixture; exact producer version absent'),
        ('mtuberculosis/bwa.qc', 'postalignqc', '0.0.0+fixture.unknown', 'Legacy numeric QC fixture; exact producer version absent'),
    ]
    for relative, software, version, basis in extra:
        add('extra/' + relative, software, version, SDK_FIXTURES / relative, 'saved_repository_fixture', basis, relative.split('/')[0])
    manifest = NATIVE / 'analysis_yaml/pilot_k12_err022075.yaml'
    native = yaml.safe_load(manifest.read_text()); reports = native['analysis_result']
    for item in reports:
        software = item['software']; subcommand = item.get('subcommand')
        if software == 'samtools' and subcommand == 'bedcov': continue
        key = software + ('.' + subcommand if subcommand else ''); path = Path(item['uri']); aux = {}
        if key == 'samtools.stats':
            for command, field in [('coverage', 'coverage_path'), ('bedcov', 'bedcov_path')]:
                selected = next(r for r in reports if r['software'] == 'samtools' and r.get('subcommand') == command)
                aux[field] = '/audit/native/' + str(Path(selected['uri']).relative_to(NATIVE))
        add('native-ecoli/' + key, key, item['software_version'], path, 'completed_native_run_saved_report',
            'Recorded in pinned JASEN 1.4.1 run manifest; no new producer execution in this audit', 'ecoli', aux)
    # Known copied QC fixture: valid generic parser data, insufficient species provenance.
    if digest(SDK_FIXTURES / 'kpneumoniae/quast.tsv') == digest(SDK_FIXTURES / 'ecoli/quast.tsv'):
        metadata_findings.append({'type': 'shared-qc-fixture', 'fixtures': ['kpneumoniae/quast.tsv', 'ecoli/quast.tsv'],
            'scope': 'These bytes cannot establish independent Klebsiella producer coverage'})
    inventory = json.loads((RUN / 'contracts/original/inventory.json').read_text())['parsers']
    by_software = defaultdict(list)
    for row in cases: by_software[row['software']].append(row)
    matrix = []
    for registered in inventory:
        name = registered['parser']; observed = by_software[name]
        matrix.append({'parser': name, 'registered_ranges': registered['ranges'],
            'generated_fixture_versions': registered['fixture_versions'], 'saved_report_cases': len(observed),
            'saved_manifest_version_labels': sorted({r['version'] for r in observed}),
            'native_saved_report_cases': sum(r['origin'] == 'completed_native_run_saved_report' for r in observed),
            'exact_version_warning': 'File examples and registry dispatch do not certify every version in the registered range'})
    catalog = {'recorded_at_utc': now(), 'sdk_head': json.loads((RUN / 'source-context.json').read_text())['sdk']['head'],
        'scope': 'Existing report schemas and metadata only; no new biological analysis', 'cases': cases,
        'parser_matrix': matrix, 'metadata_findings': metadata_findings,
        'source_version_note': 'Unknown fixture versions are explicitly synthetic dispatch labels, not claims of producer execution'}
    write(RUN / 'saved-report-catalog.json', catalog)
    write(REPO / 'datasets/bonsai_parser_fixture_audit.json', catalog)
    print(json.dumps({'saved_report_cases': len(cases), 'registered_parser_keys': len(matrix),
        'keys_with_saved_examples': sum(bool(r['saved_report_cases']) for r in matrix), 'metadata_findings': metadata_findings}))


if __name__ == '__main__': main()

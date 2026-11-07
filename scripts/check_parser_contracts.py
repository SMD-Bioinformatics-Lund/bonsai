"""Offline fidelity checks of frozen reports; no analysis tools or uploads run."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import io
import json
from pathlib import Path

from bonsai_libs.parse import run_parser
from bonsai_libs.parse.core.registry import get_parser, registered_softwares, registered_version_ranges
from bonsai_libs.parse.exceptions import InvalidDataFormat, UnsupportedVersionError
from bonsai_libs.parse.models.enums import AnalysisType


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def at(value, path):
    for part in path:
        value = value[part]
    return value


def read_rows(path, delimiter='\t'):
    return list(csv.DictReader(io.StringIO(path.read_text()), delimiter=delimiter))


def input_facts(folder, case):
    """Read literal source fields with stdlib readers, independently of the SDK/API."""
    facts = []
    def add(software, kind, path, value, source, source_field):
        facts.append({'software': software, 'analysis_type': kind, 'path': path, 'expected': value,
                      'source': source, 'source_field': source_field})
    source = 'bracken.out'
    for index, row in enumerate(read_rows(folder/source)):
        for raw, field, convert in [('name','scientific_name',str), ('taxonomy_id','taxonomy_id',int),
                ('kraken_assigned_reads','kraken_assigned_reads',int), ('added_reads','added_reads',int),
                ('fraction_total_reads','fraction_total_reads',float)]:
            add('bracken','species_prediction',[index,field],convert(row[raw]),source,f'row {index+1}: {raw}')
    source = 'quast.tsv';row = read_rows(folder/source)[0]
    for raw, field, convert in [('Total length','total_length',int), ('# contigs','n_contigs',int),
            ('Largest contig','largest_contig',int),('N50','n50',int),('NG50','ng50',int),
            ('Reference length','reference_length',int),('GC (%)','assembly_gc',float),
            ('Reference GC (%)','reference_gc',float),('Duplication ratio','duplication_ratio',float)]:
        if raw in row:
            add('quast','qc',[field],convert(row[raw]),source,raw)
    source = 'mlst.json'
    if (folder/source).exists():
        row = json.loads((folder/source).read_text())[0]
        add('mlst','mlst',['scheme'],row['scheme'],source,'/0/scheme')
        add('mlst','mlst',['sequence_type'],int(row['sequence_type']),source,'/0/sequence_type')
        add('mlst','mlst',['alleles'],{k:int(v) for k,v in row['alleles'].items()},source,'/0/alleles')
    source = 'postalignqc.json'
    if (folder/source).exists():
        for key,value in json.loads((folder/source).read_text()).items():
            add('postalignqc','qc',[key],value,source,'/'+key)
    source = 'mykrobe.csv'
    if (folder/source).exists():
        row = read_rows(folder/source,',')[0]
        for raw,field,convert in [('species','scientific_name',lambda s:s.replace('_',' ')),
                ('species_per_covg','species_coverage',float),('phylo_group','phylogenetic_group',lambda s:s.replace('_',' ')),
                ('phylo_group_per_covg','phylogenetic_group_coverage',float)]:
            add('mykrobe','species_prediction',[0,field],convert(row[raw]),source,raw)
    source = 'emmtyper.tsv'
    if (folder/source).exists() and (folder/source).stat().st_size:
        row = next(csv.reader(io.StringIO((folder/source).read_text()),delimiter='\t'))
        for index,field,convert in [(1,'cluster_count',int),(2,'emmtype',str),(4,'emm_cluster',str)]:
            add('emmtyper','emm',[field],convert(row[index]),source,f'column {index+1}')
    # These expectations were frozen by the original fixture generator, independently of parsing.
    for software,kind,path,key in [('spatyper','spatype',['type'],'spa'),('sccmectyper','sccmec',[0,'type'],'sccmec'),
            ('serotypefinder','o_type',['sequence_name'],'o_type'),('serotypefinder','h_type',['sequence_name'],'h_type'),
            ('virulencefinder','stx',['gene_symbol'],'stx'),('kleborate','k_type',['type'],'k_type')]:
        if key in case and (software!='serotypefinder' or case['assay']=='ecoli'):
            value = case[key]
            if value is not None:
                add(software,kind,path,value,'expectations.json',key)
    if 'k_type' in case:
        add('kleborate','o_type',['type'],case['o_type'],'expectations.json','o_type')
        add('kleborate','virulence',['score'],case['virulence_score'],'expectations.json','virulence_score')
    return facts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',default='baseline')
    args=parser.parse_args();fixtures=args.fixtures.resolve();out=args.output.resolve()
    phase=out/args.phase
    phase.mkdir(parents=True,exist_ok=False)
    results=[];bundles={};facts={};catalog=json.loads((fixtures/'expectations.json').read_text())
    def log(case,ok,expected,observed,**identity):
        results.append({'phase':args.phase,'surface':'parser','case':case,'status':'PASS' if ok else 'FAIL',
                        'expected':expected,'observed':observed,**identity})
    checksum_failures=[]
    for line in (fixtures/'checksums.sha256').read_text().splitlines():
        expected,name=line.split('  ',1)
        if digest(fixtures/name)!=expected:checksum_failures.append(name)
    if checksum_failures:raise ValueError(('Frozen fixture checksums changed',checksum_failures))
    fixture_versions={}; representatives={}
    for case in catalog['samples']:
        sid=case['sample_id'];folder=fixtures/'samples'/sid
        manifest=json.loads((folder/(sid+'.manifest.yml')).read_text())
        records={}
        for item in manifest['analysis_result']+case['deferred_analyses']:
            kwargs={}
            if item.get('hamronization_source'):kwargs['hamronization_source']=folder/item['hamronization_source']
            identity={'sample':sid,'assay':case['assay'],'software':item['software'],'version':item['software_version'],
                      'source':str((folder/item['uri']).relative_to(fixtures)),'source_sha256':digest(folder/item['uri'])}
            fixture_versions.setdefault(item['software'],Counter())[item['software_version']]+=1
            try:
                bundle=run_parser(item['software'],version=item['software_version'],data=folder/item['uri'],**kwargs)
                value=bundle.model_dump(mode='json');records[item['software']]=value
                errors={str(k):str(v.reason) for k,v in bundle.results.items() if str(v.status)=='error'}
                log('frozen-report-parse',not errors,'No error envelope for a valid frozen report',{'errors':errors,'statuses':{str(k):str(v.status) for k,v in bundle.results.items()}},**identity)
                representatives.setdefault(item['software'],(item,folder,bundle,kwargs))
            except Exception as error:
                log('frozen-report-parse',False,'Valid frozen report parses',{'exception':type(error).__name__,'message':str(error)},**identity)
        bundles[sid]=records;facts[sid]=input_facts(folder,case)
        failures=[];compared=0
        for fact in facts[sid]:
            try:actual=at(records[fact['software']]['results'][fact['analysis_type']]['value'],fact['path'])
            except (KeyError,IndexError,TypeError):actual={'unavailable':True}
            compared+=1
            if actual!=fact['expected']:failures.append({**fact,'actual':actual})
        log('literal-input-fields',not failures,'Every selected literal source field reaches the parsed result',
            {'fields_compared':compared,'mismatches':failures},sample=sid,assay=case['assay'])
    # Dispatch tests exercise registry selection, not historical file-format compatibility.
    inventory=[]
    for name in sorted(registered_softwares()):
        software,_,subcommand=name.partition('.')
        ranges=registered_version_ranges(name)
        for span in ranges:
            for version in [str(span.min_version),str(span.max_version)]:
                ok=get_parser(software,version=version,subcommand=subcommand or None) is span.entry
                log('version-dispatch-boundary',ok,'The inclusive registered range selects its declared parser',{'selected':span.entry.__name__},software=name,version=version)
        inventory.append({'parser':name,'ranges':[{'min':str(s.min_version),'max':str(s.max_version),'entry':s.entry.__name__} for s in ranges],
            'fixture_versions':dict(fixture_versions.get(software,{})) if not subcommand else {},
            'fixture_format_covered':software in representatives and not subcommand})
        for version in ['not-a-version','999999.0.0']:
            try:get_parser(software,version=version,subcommand=subcommand or None);ok=False;error=None
            except (InvalidDataFormat,UnsupportedVersionError) as exc:ok=True;error=type(exc).__name__
            log('invalid-or-unsupported-version',ok,'Invalid or out-of-range versions are rejected explicitly',{'exception':error},software=name,version=version)
    for software,(item,folder,full,kwargs) in representatives.items():
        for kind,envelope in full.results.items():
            try:
                selected=run_parser(software,version=item['software_version'],data=folder/item['uri'],want={kind},**kwargs)
                actual=selected.results[kind].model_dump(mode='json')
                expected=envelope.model_dump(mode='json')
                skipped=all(str(v.status)=='skipped' for k,v in selected.results.items() if k!=kind)
                ok=actual['status']==expected['status'] and actual['value']==expected['value'] and skipped
                observed={'status':actual['status'],'same_value':actual['value']==expected['value'],'reason':actual.get('reason')}
            except Exception as error:ok=False;observed={'exception':type(error).__name__,'message':str(error)}
            log('selected-result-type',ok,'Requesting one existing result type preserves its full-parse value',observed,software=software,analysis_type=str(kind))
    def probe(name,software,version,text,expected_status,shape=None,want=None):
        path=phase/'format-inputs'/name;path.parent.mkdir(exist_ok=True);path.write_text(text)
        try:
            tool,_,subcommand=software.partition('.')
            b=run_parser(tool,version=version,data=path,subcommand=subcommand or None,**({'want':want} if want else {}))
            statuses={str(v.status) for v in b.results.values()}
            ok=bool(statuses) and statuses<={expected_status}
            if shape:ok=ok and shape(b)
            observed={'statuses':sorted(statuses),'reasons':{str(k):v.reason for k,v in b.results.items()},'values':{str(k):v.model_dump(mode='json')['value'] for k,v in b.results.items()}}
        except Exception as error:ok=False;observed={'exception':type(error).__name__,'message':str(error)}
        log('format-'+name,ok,'Expected '+expected_status+' with valid result shape',observed,software=software,version=version)
    bracken=(fixtures/'samples/synthetic_ec_001/bracken.out').read_text();header=bracken.splitlines()[0]
    probe('bracken-header-only.tsv','bracken','2.8.0',header+'\n','empty',lambda b:b.results[AnalysisType.SPECIES].value==[])
    probe('bracken-missing-column.tsv','bracken','2.8.0','name\ttaxonomy_id\nGeneric label\t1\n','error')
    probe('bracken-invalid-number.tsv','bracken','2.8.0',header+'\nGeneric label\t1\tS\t10\t0\t10\tinvalid\n','error')
    probe('bracken-zero.tsv','bracken','2.8.0',header+'\nGeneric label\t1\tS\t0\t0\t0\t0\n','parsed',lambda b:b.results[AnalysisType.SPECIES].value[0].fraction_total_reads==0)
    qheader='Assembly\t# contigs\tLargest contig\tTotal length\tGC (%)\tN50\n'
    probe('quast-no-reference.tsv','quast','5.2.0',qheader+'Generic\t1\t100\t100\t50\t100\n','parsed',lambda b:b.results[AnalysisType.QC].value.reference_length is None)
    probe('quast-zero-values.tsv','quast','5.2.0',qheader+'Generic\t0\t0\t0\t0\t0\n','parsed',lambda b:b.results[AnalysisType.QC].value.total_length==0)
    probe('quast-missing-required.tsv','quast','5.2.0','Assembly\tTotal length\nGeneric\t100\n','error')
    probe('quast-invalid-number.tsv','quast','5.2.0',qheader+'Generic\t1\t100\tinvalid\t50\t100\n','error')
    probe('quast-header-only.tsv','quast','5.2.0',qheader,'empty',lambda b:b.results[AnalysisType.QC].value is None)
    probe('postalign-zero.json','postalignqc','1.0.0','{"n_reads":0,"n_read_pairs":0,"n_dup_reads":0,"mean_cov":0,"median_cov":0}','parsed',lambda b:b.results[AnalysisType.QC].value.n_reads==0 and b.results[AnalysisType.QC].value.mean_cov==0)
    probe('postalign-missing-optional.json','postalignqc','1.0.0','{"n_reads":10,"n_read_pairs":5}','parsed')
    probe('postalign-invalid-json.json','postalignqc','1.0.0','{ invalid','error')
    probe('mlst-empty-list.json','mlst','2.23.0','[]','error')
    probe('mlst-missing-required.json','mlst','2.23.0','[{"scheme":"generic","sequence_type":"1"}]','error')
    # Small generic QC-format examples; they do not establish real producer/version compatibility.
    coverage='#rname\tstartpos\tendpos\tnumreads\tcovbases\tcoverage\tmeandepth\tmeanbaseq\tmeanmapq\nGeneric one\t1\t100\t0\t0\t0\t0\t0\t0\nGeneric two\t1\t100\t10\t50\t50\t5\t30\t60\n'
    probe('samtools-two-rows.tsv','samtools.coverage','1.0.0',coverage,'parsed',lambda b:len(b.results[AnalysisType.QC].value.contigs)==2 and b.results[AnalysisType.QC].value.contigs[0].n_reads==0)
    probe('samtools-zero.stats','samtools.stats','1.0.0','SN\traw total sequences:\t0\nSN\treads paired:\t0\nSN\treads mapped:\t0\nSN\treads duplicated:\t0\n','parsed',lambda b:b.results[AnalysisType.QC].value.n_reads==0)
    nano='General summary:\nMean read length: 100\nMean read quality: 20\nMedian read length: 100\nMedian read quality: 20\nNumber of reads: 10\nRead length N50: 100\nSTDEV read length: 0\nTotal bases: 1000\nNumber, percentage and megabases of reads above quality cutoffs:\n>Q10: 10 (100%)\n>Q15: 10 (100%)\n>Q20: 5 (50%)\n>Q25: 0 (0%)\n>Q30: 0 (0%)\nTop 5 highest mean basecall quality scores:\n1: 20\nTop 5 longest reads:\n1: 100\n'
    probe('nanoplot-generic.txt','nanoplot','1.0.0',nano,'parsed',lambda b:b.results[AnalysisType.QC].value.summary.n_reads==10 and b.results[AnalysisType.QC].value.qc_cutoff.q30==0)
    for software,(item,folder,full,kwargs) in representatives.items():
        try:
            stream=run_parser(software,version=item['software_version'],data=io.StringIO((folder/item['uri']).read_text()),**kwargs)
            expected={str(k):(str(v.status),v.model_dump(mode='json')['value']) for k,v in full.results.items()}
            actual={str(k):(str(v.status),v.model_dump(mode='json')['value']) for k,v in stream.results.items()}
            ok=actual==expected;observed={'same_status_and_values':ok}
        except Exception as error:ok=False;observed={'exception':type(error).__name__,'message':str(error)}
        log('path-stream-equivalence',ok,'Text-stream input preserves the frozen path-input result',observed,software=software)
    try:
        streamed=run_parser('samtools',version='1.0.0',subcommand='coverage',data=io.StringIO(coverage))
        n=len(streamed.results[AnalysisType.QC].value.contigs)
        log('samtools-stream-row-retention',n==2,'Both generic rows remain when the supported stream interface is used',{'rows':n},software='samtools.coverage')
    except Exception as error:
        log('samtools-stream-row-retention',False,'Both generic rows remain through stream input',{'exception':type(error).__name__,'message':str(error)},software='samtools.coverage')
    for item in inventory:
        item['generic_qc_contract_example']=item['parser'] in {'samtools.coverage','samtools.stats','nanoplot'}
    counts=dict(Counter(r['status'] for r in results))
    (phase/'results.json').write_text(json.dumps({'phase':args.phase,'counts':counts,'cases':results},indent=2)+'\n')
    (phase/'parsed.json').write_text(json.dumps(bundles,indent=2)+'\n')
    (phase/'input-facts.json').write_text(json.dumps(facts,indent=2)+'\n')
    (phase/'inventory.json').write_text(json.dumps({'parsers':inventory,'assays':dict(Counter(c['assay'] for c in catalog['samples'])),'report_count':sum(sum(c.values()) for c in fixture_versions.values()),'checksum_failures':checksum_failures},indent=2)+'\n')
    print(json.dumps({'counts':counts,'reports':479,'registered_parsers':len(inventory),'format_covered':sum(p['fixture_format_covered'] for p in inventory)}))
    for row in results:
        if row['status']=='FAIL':print(row['case'],row.get('sample',row.get('software')),json.dumps(row['observed'])[:900])


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Survey public metadata and HTTP headers; never download reads or run analyses."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
from common import DATA, REPO, SOURCE, ASSETS, PIN, now, write

SURVEY=DATA/'analyses/dataset-availability/2026-11-08-supported-species'
FIELDS='run_accession,study_accession,sample_accession,scientific_name,tax_id,strain,sample_alias,sample_title,experiment_title,library_strategy,library_source,library_layout,instrument_platform,instrument_model,read_count,base_count,fastq_ftp,fastq_md5,fastq_bytes'
PROFILES=[
    ('escherichia_coli','E. coli','tax_tree(562)',['MG1655','W3110','BW25113','DH10B']),
    ('staphylococcus_aureus','S. aureus','tax_tree(1280)',['25923','29213','8325']),
    ('streptococcus_pyogenes','S. pyogenes','tax_tree(1314)',['ATCC 19615','SF370']),
    ('klebsiella','Klebsiella','tax_tree(570)',['13883','700603']),
    ('staphylococcus','Other Staphylococcus','tax_tree(1279) AND NOT tax_tree(1280)',['TM300','RP62A','12228']),
    ('streptococcus','Other Streptococcus','tax_tree(1301) AND NOT tax_tree(1314)',['LMD-9','LMD9','ATCC 7073']),
    ('mycobacterium_tuberculosis','M. tuberculosis','tax_tree(1773)',['H37Ra']),
]
PLATFORMS={
    'illumina-paired':'instrument_platform="ILLUMINA" AND library_layout="PAIRED"',
    'nanopore':'instrument_platform="OXFORD_NANOPORE"',
    'iontorrent':'instrument_platform="ION_TORRENT"',
}


def metadata(name,endpoint,parameters):
    path=SURVEY/'metadata'/(name+'.json')
    receipt=path.with_name(path.stem+'.receipt.json')
    url='https://www.ebi.ac.uk/ena/portal/api/'+endpoint+'?'+urllib.parse.urlencode(parameters)
    if path.exists():
        record=json.loads(receipt.read_text())
        if record['url']==url:return json.loads(path.read_text()),url
        # Preserve the earlier response when the discovery query is refined.
        path=path.with_name(path.stem+'-'+sha256(url.encode()).hexdigest()[:12]+'.json')
        receipt=path.with_name(path.stem+'.receipt.json')
        if path.exists():
            assert json.loads(receipt.read_text())['url']==url
            return json.loads(path.read_text()),url
    with urllib.request.urlopen(url,timeout=40) as response:
        raw=response.read();headers=dict(response.headers);status=response.status
    parsed=json.loads(raw)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    write(receipt,{'url':url,'acquired_at_utc':now(),'status':status,'headers':headers,
        'bytes':len(raw),'sha256':sha256(raw).hexdigest(),'content':'Public archive metadata only'})
    return parsed,url


def candidate(row,platform,origin):
    # A broad label search can also return mixtures with several taxon IDs.
    if not re.fullmatch(r'\d+',row.get('tax_id','')):return None
    urls=[x for x in row.get('fastq_ftp','').split(';') if x]
    sums=row.get('fastq_md5','').split(';');sizes=row.get('fastq_bytes','').split(';')
    if not urls or len(urls)!=len(sums) or len(urls)!=len(sizes):return None
    if any(not re.fullmatch('[0-9a-f]{32}',x) for x in sums):return None
    if any(not x.isdigit() or int(x)<=0 for x in sizes):return None
    if platform=='illumina-paired' and (row['library_layout']!='PAIRED' or len(urls)!=2):return None
    return {'run':row['run_accession'],'study':row['study_accession'],'sample':row['sample_accession'],
        'organism':row['scientific_name'],'tax_id':int(row['tax_id']),'strain_label':row.get('strain',''),
        'sample_alias':row.get('sample_alias',''),'sample_title':row.get('sample_title',''),
        'experiment_title':row.get('experiment_title',''),'platform':row['instrument_platform'],
        'instrument_model':row['instrument_model'],'layout':row['library_layout'],
        'strategy':row['library_strategy'],'library_source':row['library_source'],
        'reads':int(row['read_count'] or 0),'bases':int(row['base_count'] or 0),
        'compressed_bytes':sum(map(int,sizes)),
        'files':[{'url':'https://'+u.removeprefix('ftp://').removeprefix('https://'),
            'bytes':int(n),'publisher_md5':h,'checksum_verified':False} for u,n,h in zip(urls,sizes,sums)],
        'metadata_origin':origin,'record_url':'https://www.ebi.ac.uk/ena/browser/view/'+row['run_accession'],
        'payload_downloaded_in_survey':False,'analysis_qualified':False}


def query_profile(item):
    profile,label,taxonomy,preferred=item;platforms={}
    for platform,restriction in PLATFORMS.items():
        query=f'({taxonomy}) AND library_strategy="WGS" AND library_source="GENOMIC" AND {restriction}'
        record={'query':query,'metadata_matches':None,'candidates':[]}
        try:
            count,url=metadata(profile+'--'+platform+'--count','count',{'result':'read_run','query':query,'format':'json'})
            record.update(metadata_matches=int(count['count']),count_url=url)
            params={'result':'read_run','query':query,'fields':FIELDS,'format':'json','limit':70}
            rows,url=metadata(profile+'--'+platform+'--search','search',params)
            valid=[c for row in rows if (c:=candidate(row,platform,'taxon search'))]
            record.update(metadata_rows_inspected=len(rows),valid_file_list_rows=len(valid),search_url=url,
                multi_taxon_rows_excluded=sum(not bool(re.fullmatch(r'\d+',r.get('tax_id',''))) for r in rows))
            if preferred:
                terms=' OR '.join(f'{field}="*{name}*"' for name in preferred
                    for field in ['strain','sample_title','sample_alias','experiment_title'])
                params['query']=query+' AND ('+terms+')';params['limit']=35
                extra,extra_url=metadata(profile+'--'+platform+'--reference-search','search',params)
                refs=[c for row in extra if (c:=candidate(row,platform,'Reference label matched; identity still needs qualification'))]
                record['reference_search_url']=extra_url
                record['reference_metadata_rows_inspected']=len(extra)
                record['reference_multi_taxon_rows_excluded']=sum(not bool(re.fullmatch(r'\d+',r.get('tax_id',''))) for r in extra)
            else:refs=[]
            selected=[];seen=set()
            for c in sorted(refs,key=lambda x:x['compressed_bytes'])[:3]+sorted(valid,key=lambda x:x['compressed_bytes'])[:3]:
                if c['run'] not in seen:selected.append(c);seen.add(c['run'])
            record['candidates']=selected
        except Exception as error:
            record['error']=str(error)
            write(SURVEY/'metadata'/(profile+'--'+platform+'--error.json'),{'observed_at_utc':now(),'query':query,'error':str(error)})
        platforms[platform]=record
    return {'profile':profile,'label':label,'taxonomy_scope':taxonomy,'platforms':platforms}


def profile_assets(profile):
    text=(SOURCE/'nextflow.config').read_text()
    match=re.search(r'^    '+re.escape(profile)+r' \{\n(.*?)^    \}',text,re.M|re.S)
    assert match,profile
    result=[]
    for key in ['reference_genome','reference_genome_fai','reference_genome_gff','chewbbaca_db','training_file','tbdb_bed']:
        setting=re.search(r'^        params\.'+key+r'\s*=\s*(.+?)\s*$',match[1],re.M)
        if not setting:continue
        expression=setting[1]
        if expression=='null':result.append({'parameter':key,'configured':None,'available_locally':None});continue
        value=expression.strip('"\'').replace('${params.assets_dir}',str(ASSETS))
        result.append({'parameter':key,'configured':expression,'available_locally':Path(value).exists() if '${' not in value else False})
    return result


def http_head(candidate_record):
    checks=[]
    for item in candidate_record['files']:
        try:
            request=urllib.request.Request(item['url'],method='HEAD')
            with urllib.request.urlopen(request,timeout=30) as response:
                length=response.headers.get('Content-Length')
                check={'url':item['url'],'status':response.status,'content_length':int(length) if length else None,
                    'length_matches_metadata':int(length)==item['bytes'] if length else None}
        except Exception as error:check={'url':item['url'],'error':str(error)}
        checks.append(check)
    return {'run':candidate_record['run'],'checked_at_utc':now(),'method':'HEAD; no read payload downloaded','files':checks}


def schema_sources():
    path=SURVEY/'schema-source-heads.json'
    if path.exists():heads=json.loads(path.read_text())
    else:
        urls={'saureus-configured-schema':'https://www.cgmlst.org/ncs/schema/141106/alleles',
            'spyogenes-configured-schema':'https://www.cgmlst.org/ncs/schema/30585223/alleles',
            'streptococcus-configured-schema-index':'https://enterobase.warwick.ac.uk/schemes/Streptococcus.cgMLSTv1/'}
        checks=[]
        for name,url in urls.items():
            row={'name':name,'url':url,'method':'HEAD; no schema payload downloaded'}
            try:
                with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=30) as response:
                    row.update(status=response.status,content_type=response.headers.get('Content-Type'))
            except Exception as error:row['error']=str(error)
            checks.append(row)
        heads={'observed_at_utc':now(),'checks':checks};write(path,heads)
    catalog=SURVEY/'metadata/chewie-ns-species-list.json'
    url='https://chewbbaca.online/NS/api/species/list'
    if catalog.exists():species=json.loads(catalog.read_text())
    else:
        with urllib.request.urlopen(url,timeout=30) as response:raw=response.read()
        species=json.loads(raw);catalog.write_bytes(raw)
        write(catalog.with_name(catalog.stem+'.receipt.json'),{'url':url,'acquired_at_utc':now(),
            'sha256':sha256(raw).hexdigest(),'content':'Public schema catalog metadata only'})
    wanted=['staphylococcus aureus','streptococcus pyogenes','escherichia coli','klebsiella pneumoniae']
    public=[{'name':row['name']['value'],'catalog_uri':row['species']['value']} for row in species
        if row['name']['value'].lower() in wanted]
    return {'configured_source_header_checks':heads,'public_catalog_url':url,'public_catalog_entries':public,
        'alternative_schema_caveat':'Catalog presence does not establish equivalence with the configured deployment schema',
        'klebsiella_configured_source':{'url':'https://bigsdb.pasteur.fr/api/db/pubmlst_klebsiella_seqdef/schemes/18',
            'credential_requirement':'Configured downloader requires BIGSdb Pasteur credentials; no credentials requested or tested',
            'evidence':'https://github.com/genomic-medicine-sweden/jasen/blob/'+PIN+'/docs/source/install.md'}}


def main():
    SURVEY.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:profiles=list(pool.map(query_profile,PROFILES))
    for item in profiles:item['required_asset_status']=profile_assets(item['profile'])
    params={'accession':'PRJEB90249','result':'read_run','fields':FIELDS,'format':'json'}
    benchmark,url=metadata('benchmark-PRJEB90249','filereport',params)
    benchmark_groups={}
    for row in benchmark:
        organism=row['scientific_name'].lower()
        selected=next((p[0] for p in PROFILES if
            (p[0]=='staphylococcus_aureus' and organism.startswith('staphylococcus aureus')) or
            (p[0]=='streptococcus_pyogenes' and organism.startswith('streptococcus pyogenes')) or
            (p[0]=='klebsiella' and organism.startswith('klebsiella ')) or
            (p[0]=='escherichia_coli' and organism.startswith('escherichia coli'))),None)
        if not selected:continue
        platform='illumina-paired' if row['instrument_platform']=='ILLUMINA' else 'nanopore' if row['instrument_platform']=='OXFORD_NANOPORE' else None
        if platform and (c:=candidate(row,platform,'Published benchmark PRJEB90249')):
            benchmark_groups.setdefault(selected,{}).setdefault(platform,[]).append(c)
    for p in profiles:
        p['benchmark_candidates']={key:sorted(rows,key=lambda x:x['compressed_bytes'])[:3]
            for key,rows in benchmark_groups.get(p['profile'],{}).items()}
    checks=[];seen=set()
    for p in profiles:
        for platform in ['illumina-paired','nanopore']:
            for group in [p['benchmark_candidates'].get(platform,[]),p['platforms'][platform]['candidates']]:
                if group and group[0]['run'] not in seen:checks.append(group[0]);seen.add(group[0]['run'])
    previous=SURVEY/'file-header-checks.json'
    cached={r['run']:r for r in json.loads(previous.read_text())} if previous.exists() else {}
    pending=[c for c in checks if c['run'] not in cached]
    with ThreadPoolExecutor(max_workers=4) as pool:new=list(pool.map(http_head,pending))
    cached.update({r['run']:r for r in new})
    headers=[cached[c['run']] for c in checks]
    write(SURVEY/'file-header-checks.json',headers)
    record={'observed_at_utc':now(),'source_commit':PIN,'jasen_version':'1.4.1',
        'scope':'Public dataset metadata and HTTP headers across pinned organism/platform profiles',
        'payload_downloads':0,'analyses_started':0,
        'count_caveat':'Counts are matching public metadata records, not a census of valid or reachable FASTQ pairs',
        'qualification_caveat':'Reference labels, file sizes and MD5 listings do not establish sample identity, read quality or pipeline compatibility',
        'metadata_directory':str(SURVEY/'metadata'),'profiles':profiles,
        'benchmark':{'study':'PRJEB90249','metadata_url':url,'records':len(benchmark),
            'platform_records':{p:sum(r['instrument_platform']==p for r in benchmark)
                for p in sorted({r['instrument_platform'] for r in benchmark})},
            'paper':'https://doi.org/10.1186/s12920-025-02305-2'},'file_header_checks':headers,
        'schema_source_availability':schema_sources(),
        'pinned_profile_caveats':{
            'staphylococcus':'The generic profile reuses the S. aureus reference and schema; suitability for other species is unqualified',
            'streptococcus':'The generic profile is reference-free and uses a genus schema; schema scope and preparation remain unqualified',
            'mycobacterium_tuberculosis':'A separate workflow and reference/catalog assets are configured; only availability metadata was checked',
            'all_profiles':'Live credentialed MLST snapshots are separate from the pinned container bundled database used by the pilot'},
        'pinned_ci_active_organism_profiles':['staphylococcus_aureus']}
    write(SURVEY/'availability.json',record)
    write(REPO/'datasets/jasen_species_availability.json',record)
    for p in profiles:
        values={k:{'metadata_matches':v['metadata_matches'],'candidates':len(v['candidates']),'error':v.get('error')}
            for k,v in p['platforms'].items()}
        print(p['profile']+' '+json.dumps(values),flush=True)
    print(f'Header checks saved for {len(headers)} runs; no read payloads downloaded or analyses started')


if __name__=='__main__':main()

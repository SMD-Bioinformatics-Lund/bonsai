#!/usr/bin/env python3
"""Compose the local production candidates in detached worktrees for build checks.

The running test checkout and its source mounts are not changed. No branch is
published. No live API, data processing or database write is performed.
"""
import argparse
import json
from pathlib import Path
import subprocess
from verify_minimal_prs import ROOT, REPO, DATA, CASES, prepare_checks


def compose(resume=False):
    manifest=json.loads((ROOT/'branches.json').read_text())
    directory=ROOT/'integration';directory.mkdir(exist_ok=True)
    report={'candidates':{x['id']:x['head'] for x in manifest['candidates']},'trees':{},'checks':[]}
    for label,repo,base in [('Bonsai',REPO,manifest['application_base']),('SDK',REPO/'bonsai-sdk',manifest['sdk_base'])]:
        tree=directory/label.lower()
        if tree.exists() and not resume:
            raise RuntimeError(f'Integration worktree already exists: {tree}; inspect it before starting another run')
        if not tree.exists():
            subprocess.run(['git','-C',str(repo),'worktree','add','--detach',str(tree),base],check=True,capture_output=True)
        if subprocess.check_output(['git','-C',str(tree),'status','--porcelain'],text=True).strip():
            raise RuntimeError('Resolve and commit the existing integration conflict first: '+str(tree))
        history=subprocess.check_output(['git','-C',str(tree),'log',base+'..HEAD','--format=%B'],text=True)
        for row in manifest['candidates']:
            if row['repository']!=label:continue
            if 'Finding: '+row['id']+'\n' in history:continue
            result=subprocess.run(['git','-C',str(tree),'cherry-pick',row['head']],capture_output=True,text=True)
            with (directory/'compose.log').open('a') as output:output.write(row['id']+'\n'+result.stdout+result.stderr)
            if result.returncode:
                (directory/'context.json').write_text(json.dumps(report,indent=2)+'\n')
                raise RuntimeError('Composition needs inspection: '+row['id'])
        head=subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()
        report['trees'][label]={'path':str(tree),'head':head}
    (directory/'context.json').write_text(json.dumps(report,indent=2)+'\n')
    print(directory/'context.json')


def validate(chosen=None):
    directory=ROOT/'integration';report=json.loads((directory/'context.json').read_text())
    app=Path(report['trees']['Bonsai']['path']);sdk=Path(report['trees']['SDK']['path'])
    jobs=[]
    node=['docker','run','--rm','--pull','never','--network','none','--user','1000:1000',
          '-v',f'{ROOT}:{ROOT}','-v',f'{app}/frontend/web:/app/frontend/web:ro',
          '-v',f'{app}/frontend/tsconfig.json:/app/frontend/tsconfig.json:ro',
          '-v',f'{app}/frontend/webpack.config.cjs:/app/frontend/webpack.config.cjs:ro',
          '-w','/app/frontend','--entrypoint','node','bonsai-general-node-tools']
    jobs.append(('typescript',node+['node_modules/typescript/bin/tsc','--noEmit']))
    jobs.append(('webpack',node+['node_modules/webpack-cli/bin/cli.js','--config','webpack.config.cjs','--mode','production','--output-path',str(directory/'frontend-build')]))
    for kind in ['api','frontend','sdk']:
        tests=prepare_checks(app,'PENDING-SAMPLE-500',kind)
        selected={}
        for entries in CASES.values():
            for surface,filename,pattern in entries:
                if surface==kind:selected.setdefault(filename,[]).append(pattern)
        files=[str(tests/name) for name in selected]
        selection=' or '.join('('+p+')' for patterns in selected.values() for p in patterns)
        image='bonsai-species-test-frontend' if kind=='frontend' else 'bonsai-species-test-api'
        cmd=['docker','run','--rm','--pull','never','--network','none','--user','1000:1000',
             '-v',f'{DATA}:{DATA}','-v',f'{app}/api/bonsai_api:/app/api/bonsai_api:ro',
             '-v',f'{app}/frontend/bonsai_app:/app/frontend/bonsai_app:ro',
             '-v',f'{sdk}/src/bonsai_libs:/usr/local/lib/python3.11/site-packages/bonsai_libs:ro',
             '-v',f'{DATA}/environments/general-test-deps:/test-deps:ro',
             '-e','PYTHONPATH=/test-deps:/app/api:/app/frontend','-e','SECRET_KEY=isolated-integration-check',
             '-e','TESTING=true','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',image,
             '-m','pytest','-q','-p','no:cacheprovider',*files,'-k',selection,'--confcutdir',str(tests)]
        jobs.append((kind,cmd))
    # All jobs are read-only with separate output files and can run independently.
    from concurrent.futures import ThreadPoolExecutor
    def one(job):
        name,cmd=job;result=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
        log=directory/(name+'.log');log.write_text(result.stdout+result.stderr)
        print(name+': '+('PASS' if result.returncode==0 else 'FAIL'),flush=True)
        return {'name':name,'status':'PASS' if result.returncode==0 else 'FAIL','command':cmd,'log':str(log.relative_to(ROOT))}
    if chosen:jobs=[job for job in jobs if job[0] in chosen]
    previous={x['name']:x for x in report.get('checks',[])}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(one,jobs):previous[result['name']]=result
    report['checks']=list(previous.values())
    (directory/'context.json').write_text(json.dumps(report,indent=2)+'\n')
    if any(x['status']=='FAIL' for x in report['checks']):raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',action='store_true');parser.add_argument('--validate',action='store_true')
    parser.add_argument('--checks',nargs='+')
    args=parser.parse_args()
    if args.validate:validate(args.checks)
    else:compose(args.resume)

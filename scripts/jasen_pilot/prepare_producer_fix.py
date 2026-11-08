#!/usr/bin/env python3
"""Keep the observed sample-name quoting fix on a separate local JASEN branch."""
import json
from pathlib import Path
import subprocess
from common import DATA, RUN, PIN, now, write


def main():
    repository=Path('/home/jakob/src/codex/jasen')
    branch='pr/quote-producer-sample-name'
    destination=DATA/'environments/jasen-quoted-sample-name/source'
    relative='modules/local/jasentool/main.nf'
    if not destination.exists():
        destination.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','-C',str(repository),'worktree','add','-b',branch,str(destination),PIN],check=True)
        path=destination/relative;text=path.read_text()
        marker='    def groups_arg                     ='
        assert text.count(marker)==1
        # One shell argument, including labels with spaces, quotes or brackets.
        line='    def sample_name_arg = "\'" + sample_name.replace("\'", "\'\\\"\'\\\"\'") + "\'"\n'
        text=text.replace(marker,line+marker)
        assert text.count('--sample-name ${sample_name}')==1
        path.write_text(text.replace('--sample-name ${sample_name}','--sample-name ${sample_name_arg}'))
        cdm=destination/'modules/local/cdm/main.nf';text=cdm.read_text()
        text=text.replace('    """\n    echo',line+'    """\n    echo',1)
        start=text.index('    echo ${sequencing_run}');end=text.index('    """',start)
        text=text[:start]+'''    cat <<'END_CDM' > ${output}
${sequencing_run} --sample-id ${sample_name_arg} --assay ${species} --qc ${params.outdir}/${params.species_dir}/${params.cdm_dir}/${qc} ${lims_id}
END_CDM
'''+text[end:]
        cdm.write_text(text)
        subprocess.run(['git','-C',str(destination),'add',relative,'modules/local/cdm/main.nf'],check=True)
        subprocess.run(['git','-C',str(destination),'commit','-m','fix: Quote sample names when producing upload manifests'],check=True)
    head=subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD'],text=True).strip()
    changes=subprocess.check_output(['git','-C',str(destination),'diff','--numstat',PIN,head],text=True).strip()
    record={'id':'JASEN-SAMPLE-NAME-QUOTING','apparent_priority':'P1','branch':branch,'head':head,
        'upstream_commit':PIN,'path':str(destination),'production_changes':changes,'prepared_at_utc':now(),
        'observed_failure':'Native create_yaml task exits 2 with a shell syntax error for Public reference MG1655 (ERR022075)',
        'normal_trigger':'Descriptive sample labels containing spaces or shell punctuation; less likely with identifier-only labels',
        'minimal_fix':'Shell-quote the existing sample-name argument in YAML and CDM output; no analysis or parser changes',
        'published':False}
    write(RUN/'deployment/source-context.json',record)
    print(branch+' '+head[:10]+' '+changes)


if __name__=='__main__':main()

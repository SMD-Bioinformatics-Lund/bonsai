BONSAI_USER=admin
BONSAI_PASSWD=admin

#agens=( "saureus" "ecoli" )
agens=( "ecoli" )
for spp in "${agens[@]}"; do
	echo $spp
	find "/fs1/results_dev/jasen/${spp}/analysis_result" -type f -ctime -2 | while read file; do
		#/data/bnf/scripts/jasen/upload_sample.sh --api http://mtlucmds2.lund.skane.se:8811 --group $spp -u $BONSAI_USER -p $BONSAI_PASSWD --input $file
		/data/bnf/scripts/jasen/upload_sample.sh --api http://mtlucmds1.lund.skane.se/staging/bonsai/api/v1 --group $spp -u $BONSAI_USER -p $BONSAI_PASSWD --input $file
		sleep 0.2
	done;
	break
done;

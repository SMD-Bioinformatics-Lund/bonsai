DIR="/fs1/results_dev/jasen/saureus/analysis_result/"
ls /fs1/results_dev/jasen/saureus/analysis_result/ | while read file; do 
	echo $(basename $file);
	echo $($file);
	bash ./scripts/upload_sample.sh --api http://mtlucmds2.lund.skane.se:8811 -u admin -p admin --input "${DIR}${file}" --group saureus;
	sleep 0.2;
done

parallel "bash ./scripts/upload_sample.sh --api http://mtlucmds2.lund.skane.se:8811 -u admin -p admin --input $1" ::: /fs1/results_dev/jasen/saureus/analysis_result/*.json
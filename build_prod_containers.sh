# build
docker build --no-cache -t clinicalgenomicslund/bonsai_app:0.10 frontend
docker push clinicalgenomicslund/bonsai_app:0.1.0
docker build --no-cache -t clinicalgenomicslund/bonsai_api:0.10 api
docker push clinicalgenomicslund/bonsai_api:0.1.0
docker build --no-cache -t clinicalgenomicslund/bonsai_minhash_service:0.1.0 minhash_service
docker push clinicalgenomicslund/bonsai_minhash_service:0.1.0
docker build --no-cache -t clinicalgenomicslund/bonsai_allele_cluster_service:0.1.0 allele_cluster_service
docker push clinicalgenomicslund/bonsai_allele_cluster_service:0.1.0
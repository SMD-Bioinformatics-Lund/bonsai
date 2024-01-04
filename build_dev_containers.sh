# build
docker build --no-cache -t clinicalgenomicslund/bonsai_app:latest frontend
docker push clinicalgenomicslund/bonsai_app:latest
docker build --no-cache -t clinicalgenomicslund/bonsai_api:latest api
docker push clinicalgenomicslund/bonsai_api:latest
docker build --no-cache -t clinicalgenomicslund/bonsai_minhash_service:latest minhash_service
docker push clinicalgenomicslund/bonsai_minhash_service:latest
docker build --no-cache -t clinicalgenomicslund/bonsai_allele_cluster_service:latest allele_cluster_service
docker push clinicalgenomicslund/bonsai_allele_cluster_service:latest
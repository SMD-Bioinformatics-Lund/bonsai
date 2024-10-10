#!/usr/bin/env bash
set -e

# bootstrap bonsai database
# =========================

# 1. create index and admin user
bonsai_api setup

# 2. create normal user
bonsai_api create-user -u user -p user -m user@mail.com -r user

# 3. create sample groups
bonsai_api create-group -i mtuberculosis -n "M. tuberculosis" -d "Tuberculosis test samples"
bonsai_api create-group -i saureus -n "S. aureus" -d "MRSA test samples" || exit 1
bonsai_api create-group -i ecoli -n "E. coli" -d "E. coli test samples" || exit 1

# 4. load test data

# M. tuberculosis
/home/worker/upload_sample.py --user admin \
                              --password admin \
                              --api http://api:8000/ \ 
                              -i /home/worker/fixtures/samples/tb_test_1_bonsai.yaml 

# S. aureus
/home/worker/upload_sample.py --user admin \
                              --password admin \
                              --api http://api:8000/ \ 
                              -i /home/worker/fixtures/samples/cmdtest1_240918_nb000000_0000_test_bonsai.yaml

# run commands given to container
# ===============================
echo "Executing command: ${@}"
exec "${@}"
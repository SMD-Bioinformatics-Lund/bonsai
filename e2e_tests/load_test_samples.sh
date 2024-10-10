#!/bin/bash

# Load test samples
# =================

# M. tuberculosis
/home/worker/upload_sample.py --user admin --password admin --api http://api:8000/ --input /home/worker/fixtures/samples/tb_test_1_bonsai.yaml 

# S. aureus
/home/worker/upload_sample.py --user admin --password admin --api http://api:8000/ --input /home/worker/fixtures/samples/cmdtest1_240918_nb000000_0000_test_bonsai.yaml
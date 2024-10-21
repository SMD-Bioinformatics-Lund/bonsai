#!/bin/bash

# Load test samples
# =================
find ~/fixtures/samples/ -name *yaml -exec ~/upload_sample.py --user admin --password admin --api http://api:8000/ --input {} \;
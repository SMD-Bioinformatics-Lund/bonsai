#!/bin/bash

# Load test samples
# =================
find /app/fixtures/samples/ -name *yaml -exec /app/upload_sample.py --user admin --password admin --api http://api:8000/ --input {} \;
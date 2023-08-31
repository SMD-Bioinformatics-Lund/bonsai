#!/bin/bash

# dont allow overwrite existing file, exit directly if pipeline fail
set -o errexit -o pipefail -o noclobber -o nounset

check_curl_status () {
  # check status of recent curl command
  # $1 is status code, response message is read from ./response.txt
  if ! [[ $1 == 200 || $1 == 201 ]]; then 
    echo "Upload error: ${PROCESS} status: ${1} - sample: $(basename $input_file); $(cat "${RESPONSE}" | jq .detail )"
    exit 3
  fi
}

# parse command line argument
d=n v=n user="${BONSAI_USER:=user}" password="${BONSAI_PASSWORD:=password}" 
group="" api_url="${BONSAI_API_URL:-}"
while [[ "$#" -gt 0 ]]; do
  case $1 in
    -d|--debug)
      d=y
      shift
      ;;
    -v|--verbose)
      v=y
      shift
      ;;
    -u|--user)
      user="$2"
      shift
      ;;
    -p|--password)
      password="$2"
      shift
      ;;
    -i|--input)
      input_file="$2"
      shift
      ;;
    -a|--api)
      api_url="$2"
      shift
      ;;
    -g|--group)
      group_name="$2"
      shift
      ;;
    *)
      echo "Unknown parameter passed: $1"
      exit 1
      ;;
  esac
  shift
done
# assert input_file exist
[[ ! -f "${input_file}" ]] && echo "Input file: '$input_file' not found" && exit 2

# assert api url is reachable
[[ ! $(curl -is "${api_url}" | head -n 1) ]] && echo "Error connecting to API URL: '${api_url}'" && exit 2

PROCESS='login'
echo login
# log in to Bonsai API and store access token
response=$(curl -s -X 'POST'                           \
  "${api_url}/token"                                   \
  -H 'accept: application/json'                        \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=${user}&password=${password}")
token=$(echo "${response}" | jq .access_token | sed 's/"//g')
[[ "${token}" == "null" ]] && echo "API authentication error" && exit 3

# uppload sample to Bonsai database
# read sample json to memory
sample=$(cat "${input_file}")
# parse sample id
sample_id=$(echo "${sample}" | jq .sample_id | sed "s/\"//g")
# stop execution if sample_id is empty
[[ -z "${sample_id}" ]] && echo "Empty sample_id in input file '${input_file}'" && exit 3

# upload sample
echo upload sample json
PROCESS='upload sample'
RESPONSE=$(tempfile -s .txt)
status=$(curl -X 'POST' -s            \
  "${api_url}/samples/"               \
  -H "Authorization: Bearer ${token}" \
  -H 'Content-Type: application/json' \
  -w %{http_code}                     \
  -o "${RESPONSE}"                    \
  -d "${sample}")

# check upload status
check_curl_status $status

# Upload genome signature to Bonsai
##
signature_fname=$(basename "${input_file}" | sed "s/_result.*/\.sig/")
signature_path="${input_file%/*/*}/sourmash/${signature_fname}"

# upload signature
echo upload sample signature
PROCESS='upload signature'
if [[ -f "${signature_path}" ]]; then
  # upload signature
  status=$(curl -X 'POST' -s                     \
    "${api_url}/samples/${sample_id}/signature"  \
    -H "Authorization: Bearer ${token}"          \
    -H 'Content-Type: multipart/form-data'       \
    -w %{http_code}                              \
    -F "signature=@${signature_path}"            \
    -o "${RESPONSE}")
fi
# check upload status
check_curl_status $status

# if group has been assign, add sample to group
if [[ ! -z "${group_name}" ]]; then
  echo adding group
  PROCESS='assign group'
  status=$(curl -X "PUT" -s "${api_url}/groups/${group_name}/sample" -G --data-urlencode "sample_id=${sample_id}" -H "Authorization: Bearer ${token}" -w %{http_code} -o "${RESPONSE}")
  check_curl_status $status
fi

echo "Sample $(basename "${input_file}") uploaded"
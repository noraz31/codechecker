#!/bin/bash

CC_URL="https://codechecker-demo.eastus.cloudapp.azure.com/codechecker"

if [ "$#" -ne 1 ]; then
    echo "<PR_NAME> is missing"
fi

./ci/github_analysis/pylint_analyze.sh
report-converter -c -t pylint -o ./reports-pylint ./pylint-reports.json
CodeChecker store -f ./reports-pylint --url "$CC_URL" --trim-path-prefix "$(pwd)" -n "$1"
CodeChecker cmd diff --url "$CC_URL" -b master -n "$1" --new
if [ "$?" -ne 0 ]; then
    echo "ERROR. YOUR PR FAILED GATING! Please check new reports at $CC_URL/reports?run=master&newcheck=$1"
    exit 1
else
    echo "Gating successful. No new report found. Your PR is ready to be merged."
fi
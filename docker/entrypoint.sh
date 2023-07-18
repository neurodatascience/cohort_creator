#!/usr/bin/env bash

# Used as the default entrypoint.sh that runs cohort_creator on startup.

set -e
export USER="${USER:=$(whoami)}"
if [ -n "$1" ]; then cohort_creator "$@"; else cohort_creator --help; fi

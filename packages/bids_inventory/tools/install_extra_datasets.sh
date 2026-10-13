#! /bin/bash

# Installs the BIDS datasets that are not on openneuro:
# - from the datalad superdataset: abide, abide2, adhd200, corr
# - from courtois-neuromod: cneuromod
#
# Usage:
#   install_extra_datasets.sh [target_dir]   (default: ./tmp)
#
# Then set 'local_paths.non_openneuro' to target_dir in your configuration
# and run: bids_inventory update --source non-openneuro

set -eux

target_dir=$(realpath "${1:-./tmp}")
mkdir -p "${target_dir}"

datalad install -s ///abide/RawDataBIDS/ "${target_dir}/abide"
datalad install -s ///abide2/RawData/ "${target_dir}/abide2"
datalad install -s ///adhd200/RawDataBIDS/ "${target_dir}/adhd200"
datalad install -s ///corr/RawDataBIDS/ "${target_dir}/corr"

for sds in abide abide2 adhd200 corr; do
    (cd "${target_dir}/${sds}" && datalad -f '{path}' subdatasets | xargs -n 1 -P 10 datalad install)
done

for sds in abide abide2 adhd200 corr; do
    for ds in "${target_dir}/${sds}"/*/; do
        (cd "${ds}" && datalad get ./*.tsv) || echo 'no tsv'
        (cd "${ds}" && datalad get ./*.json) || echo 'no json'
    done
done

# TODO get neuromod derivatives ?
datalad install -s https://github.com/courtois-neuromod/cneuromod.git "${target_dir}/cneuromod"
(cd "${target_dir}/cneuromod" && datalad -f '{path}' subdatasets | xargs -n 1 -P 2 datalad install)

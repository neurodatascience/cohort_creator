#! /bin/bash

# Installs:
# - BIDS datasets
#   - contained in datalad superdataset
#   - from courtois-neuromod

set -eux

# rm -fr ./tmp/ && mkdir ./tmp/

datalad install -s ///abide/RawDataBIDS/ ./tmp/abide
datalad install -s ///abide2/RawData/ ./tmp/abide2
datalad install -s ///adhd200/RawDataBIDS/ ./tmp/adhd200
datalad install -s ///corr/RawDataBIDS/ ./tmp/corr

for sds in $PWD/tmp/*; do
    cd "${sds}" && datalad -f '{path}' subdatasets | xargs -n 1 -P 10 datalad install
done

for sds in "$PWD"/tmp/*; do
    for ds in "${sds}"/*; do
        cd "${ds}" && datalad get ./*.tsv || echo 'no tsv'
        cd "${ds}" && datalad get ./*.json || echo 'no json'
    done
done

# TODO get neuromod derivatives ?
cd ../..
datalad install -s https://github.com/courtois-neuromod/cneuromod.git ./tmp/cneuromod
cd ./tmp/cneuromod && datalad -f '{path}' subdatasets | xargs -n 1 -P 2 datalad install
cd ../..

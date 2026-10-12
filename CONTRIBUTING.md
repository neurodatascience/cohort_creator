# Contributing guidelines

## How to contribute

### Fork the repository

### Clone your fork with all the submodules

```bash
git clone --recurse-submodules https://github.com/YOUR_GH_USERNAME/cohort_creator.git
```

### Repository layout

This repository contains 2 python packages:

- `packages/bids_inventory`: keeps the listing of known BIDS datasets up to date
- `packages/cohort_creator`: creates cohorts from the datasets in that listing

`cohort_creator` depends on `bids_inventory`.

### Install with all the dependencies in editable mode

```bash
pip install -e 'packages/bids_inventory[dev]' -e 'packages/cohort_creator[dev]'
```

### Install all openneuro datasets

In case you need to recreate the listing of datasets,
you may need to install all the openneuro datasets
contained in the datalad superdataset.

If so make sure to use the following command
to facilate installing datasets in parallel:

```bash
datalad -f '{path}' subdatasets | xargs -n 1 -P 10 datalad install
```

## Running the tests

Each package has its own tests, run them from the package folder:

```bash
cd packages/bids_inventory && pytest
cd packages/cohort_creator && pytest
```

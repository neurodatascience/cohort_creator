# Contributing guidelines

## How to contribute

### Fork the repository

### Clone your fork with all the submodules

```bash
git clone --recurse-submodules https://github.com/YOUR_GH_USERNAME/cohort_creator.git
```

### Repository layout

- `packages/cohort_creator`: creates cohorts from the datasets of the listing
- `packages/bids_inventory`: keeps the listing of known BIDS datasets up to date.
  It is a git submodule of the [bids_inventory](https://github.com/neurodatascience/bids_inventory) repository:
  contributions to it go to that repository.

`cohort_creator` depends on `bids_inventory`.

If you cloned the repository without its submodules:

```bash
git submodule update --init --recursive
```

### Install with all the dependencies in editable mode

```bash
pip install -e 'packages/bids_inventory[dev]' -e 'packages/cohort_creator[dev]'
```

## Running the tests

```bash
cd packages/cohort_creator && pytest
```

The tests of `bids_inventory` run in its own repository.

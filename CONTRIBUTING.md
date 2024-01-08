# Contributing guidelines

## How to contribute

### Fork the repository

### Clone your fork with all the submodules

```bash
git clone --recurse-submodules https://github.com/YOUR_GH_USERNAME/cohort_creator.git
```

### Install with all the dependencies in editable mode

```bash
pip install -e '.[dev]'
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

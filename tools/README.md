# Tools

This directory contains tools that are used to generate
the listing of openneuro and non-openneuro BIDS datasets.

## Requirements

Install the cohort_creator package with its development dependencies

```bash
pip install -e .[dev]
```

## Installing datasets

If you need to regenerate this listing from scratch
you may need to install all the openeuro datalad datasets.

Note that this may take some time.

```bash
datalad install ///openneuro --recursive -J 12
```

You can help the code track those folders
by modifying `local_paths.datalad` the `cohort_creator/data/config.yml`

For the non-openneuro datasets, you can use the `tools/install_extra_datasets.sh` script.

## Updating the list of datasets known to cohort_creator

If the listing must be regenerated from scratch (in case old entries need to be updated)
use `tools/list_openneuro.py`.

## Gihub API Tokens

To list the datasets on the openneuro organizations several calls need to be made to the github api.

The github api has a rate limit of the number of requests per hour.

To increase this limit you can create a github api token,
save it to a text file (not in the repository)
and add the path to it in the `cohort_creator/data/config.yml` file.

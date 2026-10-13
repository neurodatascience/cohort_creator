# Tools

This directory contains tools that are used to generate
the listing of openneuro and non-openneuro BIDS datasets.

## Requirements

Install the bids_inventory package with its development dependencies

```bash
pip install -e 'packages/bids_inventory[dev]'
```

## Configuration

The update needs a few local settings (where datasets are installed, a GitHub token...).

Do not edit `bids_inventory/data/config.yml`:
it only contains the default (empty) settings and documents each of them.
Instead create your own YAML file, outside of the repository,
with only the settings you need, for example:

```yaml
auth:
    # text file containing a GitHub token
    token_file: ~/tokens/github_token.txt
local_paths:
    datalad:
        # datasets in the datalad superdataset:
        # only needed to regenerate the listing from scratch
        OpenNeuroDatasets: ~/datalad/datasets.datalad.org/openneuro
        OpenNeuroDerivatives: ~/datalad/datasets.datalad.org/openneuro-derivatives
    openneuro:
        # where new openneuro datasets are installed during an update
        OpenNeuroDatasets: ~/openneuro
```

and pass it to the update:

```bash
bids_inventory update --config ~/bids_inventory_config.yml
```

or set the `BIDS_INVENTORY_CONFIG` environment variable to its path
(this also works for the scripts in this folder):

```bash
export BIDS_INVENTORY_CONFIG=~/bids_inventory_config.yml
```

If a setting needed by the update is missing,
the error message says which one.

## Installing datasets

If you need to regenerate this listing from scratch
you may need to install all the openeuro datalad datasets.

Note that this may take some time.

```bash
datalad install ///openneuro --recursive -J 12
```

and set `local_paths.datalad` in your configuration file to point to them.

For the non-openneuro datasets, you can use the `tools/install_extra_datasets.sh` script.

To update the listing with the new openneuro datasets, run `bids_inventory update`.

## Updating the list of known datasets

If the listing must be regenerated from scratch (in case old entries need to be updated)
use `tools/list_openneuro.py`.

## Skipping datasets

Datasets listed in `bids_inventory/data/skipped_datasets.csv` are never installed or indexed,
for example datasets deleted from OpenNeuro that are still mirrored on GitHub
(their file contents cannot be downloaded).
Each dataset is listed with the reason why it is skipped.

## GitHub API tokens

To list the datasets on the openneuro organizations several calls need to be made to the GitHub API.

The GitHub API has a rate limit of the number of requests per hour.

To increase this limit you can create a GitHub API token and either:

-   set the `GITHUB_TOKEN` environment variable (it takes precedence),
-   or save it to a text file (not in the repository)
    and set `auth.token_file` to its path in your configuration file.

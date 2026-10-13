# bids-inventory

Keeps an inventory of publicly available BIDS datasets
(OpenNeuro and a few other sources)
with information about their content (datatypes, tasks, sessions, number of participants, scan duration...).

The inventory is stored in `bids_inventory/data/` as [JSON lines](https://jsonlines.org/) files
(one dataset per line):

- `openneuro.jsonl`
- `non_openneuro.jsonl`

A description of each field is in `bids_inventory/data/columns_description.json`.
It is generated from the data model in `bids_inventory/models.py`:
after changing the model, regenerate it with `python -m bids_inventory.models`.

## Installation

```bash
pip install ./packages/bids_inventory
```

The base install is enough to load the listing.
The commands need optional dependencies:

- `bids-inventory[browse]`: `bids_inventory browse`, a dash app to browse and filter the listing
- `bids-inventory[update]`: `bids_inventory update`, to update the listing

## Usage

```python
from bids_inventory import filter_data, load_inventory

# listing with extra summary columns (has_fmriprep, nb_tasks, total_duration...)
df = load_inventory()
eeg_datasets = filter_data(df, config={"datatypes": ["eeg"]})
```

To browse the listing in a dash app:

```bash
pip install './packages/bids_inventory[browse]'
bids_inventory browse
```

## Updating the inventory

```bash
pip install -e './packages/bids_inventory[update]'
bids_inventory update
```

The listing is updated every week by the `update_listing.yml` GitHub workflow.

See `tools/README.md` to regenerate the listing from scratch.

## Running the update locally

### Install all OpenNeuro datasets

The datasets are installed with [datalad](https://www.datalad.org/)
from the datalad superdataset.
Only the git history and file names are downloaded (not the data),
but there are a lot of datasets, so this takes a while.

```bash
# where to install the superdataset, for example ~/datalad
cd ~/datalad
datalad install ///
cd datasets.datalad.org

# raw datasets: install all of them, 10 at a time
datalad install openneuro
cd openneuro
datalad -f '{path}' subdatasets | xargs -n 1 -P 10 datalad install
cd ..

# derivatives (fmriprep, mriqc...): same thing
datalad install openneuro-derivatives
cd openneuro-derivatives
datalad -f '{path}' subdatasets | xargs -n 1 -P 10 datalad install
```

### Configure and run the update

Tell the update where those datasets are
in a configuration file outside of the repository
(see `tools/README.md` for all the settings):

```yaml
# ~/bids_inventory_config.yml
local_paths:
    datalad:
        OpenNeuroDatasets: ~/datalad/datasets.datalad.org/openneuro
        OpenNeuroDerivatives: ~/datalad/datasets.datalad.org/openneuro-derivatives
    openneuro:
        # where new datasets (not yet in the listing) are installed
        OpenNeuroDatasets: ~/openneuro
```

```bash
pip install -e './packages/bids_inventory[update]'
export GITHUB_TOKEN=...  # optional, avoids GitHub API rate limits
bids_inventory update --config ~/bids_inventory_config.yml
```

Useful options (see `bids_inventory update --help`):

- `--jobs N`: number of datasets to install, and of NIfTI headers to read, in parallel (default: 4)
- `--reindex`: index again all the datasets, not only those missing from the listing,
  for example after new fields were added to the listing.
  Each entry is replaced in place, so the listing stays complete.
  If it is stopped, run the same command again to continue where it stopped.
- `--log-dir DIR`: where warnings and errors are saved, in 2 separate files (default: `logs`).
  Each warning and error mentions the dataset it comes from, for example `[ds004000 171/1380]`.

The listing is saved after each dataset is indexed:
if the update is stopped, run the same command again
and it continues with the datasets that are not in the listing yet.

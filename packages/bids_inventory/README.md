# bids-inventory

Keeps an inventory of publicly available BIDS datasets
(OpenNeuro and a few other sources)
with information about their content (datatypes, tasks, sessions, number of participants, scan duration...).

The inventory is stored in `bids_inventory/data/` as [JSON lines](https://jsonlines.org/) files
(one dataset per line):

- `openneuro.jsonl`
- `non_openneuro.jsonl`

A description of each field is in `bids_inventory/data/columns_description.json`.

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

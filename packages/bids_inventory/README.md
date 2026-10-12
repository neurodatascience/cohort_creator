# bids-inventory

Keeps an inventory of publicly available BIDS datasets
(OpenNeuro and a few other sources)
with information about their content (datatypes, tasks, sessions, number of participants, scan duration...).

The inventory is stored in `bids_inventory/data/` as [JSON lines](https://jsonlines.org/) files
(one dataset per line):

- `openneuro.jsonl`
- `non_openneuro.jsonl`

A description of each field is in `bids_inventory/data/columns_description.json`.

## Usage

```python
from bids_inventory.listing import known_datasets_df

df = known_datasets_df()
```

## Updating the inventory

```bash
pip install -e packages/bids_inventory
bids_inventory update
```

The listing is updated every week by the `update_listing.yml` GitHub workflow.

See `tools/README.md` to regenerate the listing from scratch.

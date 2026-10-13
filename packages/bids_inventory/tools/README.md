# Tools

Helpers that are not part of the `bids_inventory` command line.
To update the listing, use `bids_inventory update`: see the package README.

- `install_extra_datasets.sh [target_dir]`:
  installs the datasets that are not on OpenNeuro (ABIDE, ABIDE 2, ADHD-200, CoRR, CNeuroMod)
  in `target_dir` (default: `./tmp`).
  Then set `local_paths.non_openneuro` to `target_dir` in your configuration
  and run `bids_inventory update --source non-openneuro`.
- `localize_institutions.py` and `locations.tsv`:
  plot the locations of the institutions found in the listing.

# Frequently asked questions

## How to change which files are downloaded / copied?

This is uses a JSON bids-filter file to specify the files to be downloaded for
each dataset type.

The file is organized by dataset type and then list the "suffix groups" to be
downloaded / copied for each dataset.

```json
{
  "dataset_type": {
    "suffix_group": {
      "datatype": "func",
      "suffix": "bold",
      "ext": "nii*"
    }
  }
}
```

Each suffic group MUST have:

- `"datatype"`
- `"suffix"`
- `"ext"`

Those entries support typical glob pattern (like `*` or `?`...).

The default filter file is located at `cohort_creator/data/bids_filter.json`.

```{literalinclude} data/bids_filter.json
   :language: json
```

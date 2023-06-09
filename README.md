[![Test](https://github.com/neurodatascience/cohort_creator/actions/workflows/test.yml/badge.svg)](https://github.com/neurodatascience/cohort_creator/actions/workflows/test.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/neurodatascience/cohort_creator/main.svg)](https://results.pre-commit.ci/latest/github/neurodatascience/cohort_creator/main)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
![https://github.com/psf/black](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Sourcery](https://img.shields.io/badge/Sourcery-enabled-brightgreen)](https://sourcery.ai)
[![Documentation Status](https://readthedocs.org/projects/cohort-creator/badge/?version=latest)](https://cohort-creator.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/neurodatascience/cohort_creator/branch/main/graph/badge.svg?token=PMQYH0DIPX)](https://codecov.io/gh/neurodatascience/cohort_creator)

# Cohort creator

> **TL;DR**
>
> Creates a neuroimaging cohort by aggregating data across datasets.

Install a set of datalad datasets from openneuro and get the data for a set of
participants. Then copy the data to a new directory structure to create a
"cohort".

Takes 1 file as input that should list:

- subject in each dataset to be included in the cohort

For examples of of inputs TSV files see this
[page](https://github.com/neurobagel/documentation/wiki/Query-Tool#example-data)

## Requirements

### Operating system

It is recommended to use this package on a linux / Mac OS.

If you are on Windows, try using WSL (Windows Subsystem for Linux) to run this
package: windows does not handle symbolic links well, and this package relies on
symlinks. If you decided to go ahead anyway make sure you have got a LOT of disk
space available.

More information
[here](https://handbook.datalad.org/en/latest/intro/windows.html#ohnowindows)

### Python dependencies

Make sure you have the following installed:

- datalad and its dependencies:
  - if you are have anaconda / conda, it should be 'just' a matter of running
    ```
    conda install -c conda-forge datalad
    ```
  - But check the
    [installation instructions](https://handbook.datalad.org/en/latest/intro/installation.html#install)
    for more details.

Other dependencies are listed in the pyproject.toml file.

## Installation

```bash
git clone https://github.com/neurodatascience/cohort_creator.git
cd cohort_creator
pip install .
```

## Limitations

Cohorts can only be created by aggregating data from openneuro and openneuro
derivatives.

### Latest datasets

Currently this should allow you to access:

Number of datasets: 863 with 37441 subjects including:

- 692 datasets with MRI data
- with participants.tsv: 487
- with phenotype directory: 22
- with fmriprep: 90 (3937 subjects)
  - with participants.tsv: 74
  - with phenotype directory: 3
- with freesurfer: 36 (3322 subjects)
  - with participants.tsv: 34
  - with phenotype directory: 2
- with mriqc: 330 (14607 subjects)
  - with participants.tsv: 248
  - with phenotype directory: 18

It may be that very recent datasets are not available yet.

### Dataset types

Only possible to get data from:

- raw
- mriqc
- fmriprep

Not yet possible to get freesurfer data via the cohort creator, though the data
is available in the sourcedata folder of the fmriprep datasets.

### Blind spots

It may be possible that that some metadata files (JSON, TSV) are not accessed
over correctly if they are not in the root of the dataset or the same folder as
the data file.

**FIX** use pybids / ancpbids for data indexing and querying.

## Demo

To get from openneuro-derivatives for all T1w

- the MRIQC output for each file
- the corresponding T1W file

run the following command from within the cohort_creator folder:

```bash
cohort_creator install \
  --participant_listing inputs/participants_with_mriqc.tsv \
  --output_dir outputs \
  --dataset_types raw mriqc \
  --verbosity 3

cohort_creator get \
  --participant_listing inputs/participants_with_mriqc.tsv \
  --output_dir outputs \
  --dataset_types raw mriqc \
  --verbosity 3

cohort_creator copy \
  --participant_listing inputs/participants_with_mriqc.tsv \
  --output_dir outputs \
  --dataset_types raw mriqc \
  --verbosity 3
```

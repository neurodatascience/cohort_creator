[![Test](https://github.com/neurodatascience/cohort_creator/actions/workflows/test.yml/badge.svg)](https://github.com/neurodatascience/cohort_creator/actions/workflows/test.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/neurodatascience/cohort_creator/main.svg)](https://results.pre-commit.ci/latest/github/neurodatascience/cohort_creator/main)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
![https://github.com/psf/black](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Sourcery](https://img.shields.io/badge/Sourcery-enabled-brightgreen)](https://sourcery.ai)
[![Documentation Status](https://readthedocs.org/projects/cohort-creator/badge/?version=latest)](https://cohort-creator.readthedocs.io/en/latest/?badge=latest)
# Cohort creator

**TL;DR**

    Creates a neuroimaging cohort by aggregating data across datasets.

Install a set of datalad datasets from openneuro and get the data for a set of participants.
Then copy the data to a new directory structure to create a "cohort".

Takes 2 files as input that should list:
- source datasets
- subject in each dataset to be included in the cohort

For examples of 2 inputs TSV files see this [page](https://github.com/neurobagel/documentation/wiki/Query-Tool#example-data)

## Requirements

### Operating system

It is recommended to use this package on a linux / Mac OS.

If you are on Windows, try using WSL (Windows Subsystem for Linux) to run this package:
windows does not handle symbolic links well, and this package relies on symlinks.
If you decided to go ahead anyway make sure you have got a LOT of disk space available.

More information [here](https://handbook.datalad.org/en/latest/intro/windows.html#ohnowindows)

### Python dependencies

Make sure you have the following installed:

- datalad and its dependencies:
    - if you are have anaconda / conda, it should be 'just' a matter of running
      ```
      conda install -c conda-forge datalad
      ```
    - But check the [installation instructions](https://handbook.datalad.org/en/latest/intro/installation.html#install) for more details.

Other dependencies are listed in the pyproject.toml file.

## Installation

```bash
git clone https://github.com/neurodatascience/cohort_creator.git
cd cohort_creator
pip install .
```

## Output

At the moment everything is saved in the `outputs` folder.

It contains a sourcedata where all the datalad datasets are installed.

In the outputs folder itself is where the cohort is created:
relevant files are copied out of the sourcedata folder
and into a separate folder for each dataset.

```
outputs
├── ds000001
│   ├── dataset_description.json
│   ├── participants.tsv
│   ├── README
│   ├── sub-03
│   │   └── anat
│   │       └── sub-03_T1w.nii.gz
│   ├── sub-12
│   │   └── anat
│   │       └── sub-12_T1w.nii.gz
│   └── sub-13
│       └── anat
│           └── sub-13_T1w.nii.gz
├── ds000001-fmriprep
│   ├── dataset_description.json
│   ├── README.md
│   ├── sub-03
│   │   └── anat
│   │       ├── sub-03_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.json
│   │       └── sub-03_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz
│   ├── sub-12
│   │   └── anat
│   │       ├── sub-12_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.json
│   │       └── sub-12_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz
│   └── sub-13
│       └── anat
│           ├── sub-13_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.json
│           └── sub-13_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz
├── ds000001-mriqc
│   ├── dataset_description.json
│   ├── README.md
│   ├── sub-03
│   │   └── anat
│   │       └── sub-03_T1w.json
│   ├── sub-12
│   │   └── anat
│   │       └── sub-12_T1w.json
│   └── sub-13
│       └── anat
│           └── sub-13_T1w.json
├── ds000002
│   ├── sub-03
│   ├── sub-12
│   ├── sub-13
│   └── sub-17
├── ds000002-fmriprep
│   ├── sub-03
│   ├── sub-12
│   ├── sub-13
│   └── sub-17
├── ds000002-mriqc
│   ├── sub-03
│   ├── sub-12
│   ├── sub-13
│   └── sub-17
├── ds001226
│   ├── sub-CON03
│   ├── sub-CON04
│   ├── sub-CON07
│   └── sub-CON11
├── ds001226-fmriprep
│   ├── sub-CON03
│   ├── sub-CON04
│   ├── sub-CON07
│   └── sub-CON11
├── ds001226-mriqc
│   ├── sub-CON03
│   ├── sub-CON04
│   ├── sub-CON07
│   └── sub-CON11
└── sourcedata
    ├── ds000001
    ├── ds000001-fmriprep
    ├── ds000001-mriqc
    ├── ds000002
    ├── ds000002-fmriprep
    ├── ds000002-mriqc
    ├── ds001226
    ├── ds001226-fmriprep
    └── ds001226-mriqc
```

## Limitations

This package in part relies on the content of the datalad superdataset
to fetch datasets and data from openneuro.

So it may be that very recent datasets are not available yet.

## Demo

Get from openneuro derivatives for all T1w

- the MRIQC output for each file
- the corresponding T1W file

```bash
cohort_creator.py \
  inputs/datasets_with_mriqc.tsv \
  inputs/datasets_with_mriqc.tsv \
  outputs
```

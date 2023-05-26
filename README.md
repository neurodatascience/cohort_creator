# Cohort creator

**TL;DR**

    Creates a neuroimaging cohort by aggregating data across datasets.

Install a set of datalad datasets from openneuro and get the data for a set of participants.
Then copy the data to a new directory structure to create a "cohort".

Takes 2 files as input that should list:
- source datasets
- subject in each dataset to be included in the cohort

For examples of 2 inputs TSV files see: https://github.com/neurobagel/documentation/wiki/Query-Tool#example-data

## Requirements

It is recommended to use this package on a linux / Mac OS.

If you are on Windows, we suggest to use WSL (Windows Subsystem for Linux) to run this package:
windows does not handle symbolic links well, and this package relies on symlinks.
If you decided to go ahead anyway make sure you have got a LOT of disk space available.

More information here: https://handbook.datalad.org/en/latest/intro/windows.html#ohnowindows

Make sure you have the following installed:

- datalad:
    - if you are have anaconda / conda, it should be 'just' a matter of running
      ```
      conda install -c conda-forge datalad
      ```
    - But check the installation instructions for more details:
      https://handbook.datalad.org/en/latest/intro/installation.html#install

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
│   ├── dataset_description.json
│   ├── sub-03
│   │   └── anat
│   │       └── sub-03_T1w.nii.gz
│   ├── sub-12
│   │   └── anat
│   │       └── sub-12_T1w.nii.gz
│   └── sub-13
│       └── anat
│           └── sub-13_T1w.nii.gz
├── ds000001-fmriprep
│   ├── dataset_description.json
│   ├── sub-03
│   │   └── anat
│   │       ├── sub-03_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.json
│   │       └── sub-03_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz
│   ├── sub-12
│   │   └── anat
│   │       ├── sub-12_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.json
│   │       └── sub-12_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz
│   └── sub-13
│       └── anat
│           ├── sub-13_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.json
│           └── sub-13_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz
├── ds000001-mriqc
│   ├── dataset_description.json
│   ├── sub-03
│   │   └── anat
│   │       └── sub-03_T1w.json
│   ├── sub-12
│   │   └── anat
│   │       └── sub-12_T1w.json
│   └── sub-13
│       └── anat
│           └── sub-13_T1w.json
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
python cohort_creator.py \
  inputs/datasets_with_mriqc.tsv \
  inputs/datasets_with_mriqc.tsv \
  outputs
```

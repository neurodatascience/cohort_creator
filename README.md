# Cohort creator

Creates a cohort by grabbing specific subjects from opennneuro datasets.

Takes 2 files as inputthat should list:
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

- python3 >= 3.8
- datalad:
    - if you are have anaconda / conda, it should be 'just' a matter of running
      ```
      conda install -c conda-forge datalad
      ```
    - But check the installation instructions for more details:
      https://handbook.datalad.org/en/latest/intro/installation.html#install

## Installation

- fork the repo
- clone your fork
- otpional: create a virtual environment
- install the requirements: `pip install -r requirements.txt`

## Usage

Run:

```bash
python cohort_creator.py path_to_datasets_listing participants_listing output_dir
```

Maybe try on a subset of datasets / participants first to make sure things are OK.

```
usage: cohort_creator.py [-h] [-v] [--action {all,install,get,copy}] [--verbosity {0,1,2,3}] [--task TASK [TASK ...]]
                         [--space SPACE [SPACE ...]] [--dry_run] [--bids_filter_file BIDS_FILTER_FILE]
                         datasets_listing participants_listing output_dir

Creates a cohort by grabbing specific subjects from opennneuro datasets.

positional arguments:
  datasets_listing      Path to TSV file containing the list of datasets to install.
  participants_listing  Path to TSV file containing the list of participants to get.
  output_dir            Fullpath to the directory where the output files will be stored.

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  --action {all,install,get,copy}
                        Action to perform.
  --verbosity {0,1,2,3}
                        Verbosity level.
  --task TASK [TASK ...]
                        Tasks of the input data.
  --space SPACE [SPACE ...]
                        Space of the input data.
  --dry_run             When set to ``true`` this will generate and save the SPM batches, but not actually run them.
  --bids_filter_file BIDS_FILTER_FILE
                        Fullpath to a JSON file describing custom BIDS input filters.

For a more readable version of this help section, see the online doc https://github.com/neurodatascience/cohort_creator
```

<!--
Change the global variables at the top of the `src/cohort_creator.py` script
to match your input files.

Some of the other global variables can be changed but are not thourouhgly tested yet.
-->


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

# Outputs

The output layout tries to follow the layout recommended in the
[BIDS extension proposal 35](https://docs.google.com/document/d/1tFRNumQyIgjXBNC3brFDLO9FaikjL84noxK6Om-Ctik).

The output folder contains a `sourcedata` folder where all the datalad datasets
are installed.

The output folder itself is where the cohort is created: relevant files are
copied out of the `sourcedata` folder and into a separate folder for each
dataset.

```
outputs
├── sourcedata
│   ├── ds000001
│   ├── ds000001-fmriprep
│   ├── ds000001-mriqc
│   ├── ds000002
│   ├── ds000002-fmriprep
│   ├── ds000002-mriqc
│   ├── ds000200
│   ├── ds001226
│   ├── ds001226-fmriprep
│   └── ds001226-mriqc
│
├── study-ds000001
│   ├── derivatives
│   │   ├── fmriprep-21.0.1
│   │   │   ├── sub-03
│   │   │   │   └── anat
│   │   │   │       ├── sub-03_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.json
│   │   │   │       └── sub-03_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz
│   │   │   ├── dataset_description.json
│   │   │   └── README.md
│   │   └── mriqc-0.16.1
│   │       ├── sub-03
│   │       │   └── anat
│   │       │       └── sub-03_T1w.json
│   │       ├── dataset_description.json
│   │       └── README.md
│   ├── sub-03
│   │   └── anat
│   │       └── sub-03_T1w.nii.gz
│   ├── dataset_description.json
│   ├── participants.tsv
│   └── README
│
├── study-ds000002
│   ├── derivatives
│   ├── sub-12
│   ├── sub-13
│   ├── dataset_description.json
│   ├── participants.tsv
│   └── README
│
├── study-ds000200
│   ├── sub-2001
│   ├── dataset_description.json
│   ├── participants.tsv
│   └── README
│
├── study-ds001226
│   ├── derivatives
│   ├── sub-CON03
│   ├── sub-CON07
│   ├── dataset_description.json
│   ├── participants.tsv
│   └── README
│
├── dataset_description.json
├── README.md
├── studies.json
└── studies.tsv
```

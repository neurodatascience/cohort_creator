# Output

The output folder contains a `sourcedata` folder where all the datalad datasets are installed.

The output folder itself is where the cohort is created:
relevant files are copied out of the `sourcedata` folder
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

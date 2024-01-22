# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
### Added

### Changed

### Deprecated

### Removed


### Security
-->

## Unreleased

### Added

-   [ENH] Add non-openneuro datasets (ABIDE, CORR, ADHD200, Neuromod...). (#124 @Remi-Gau)
-   [ENH] Add Dash app to help browse and visualizse all known datasets.
-   [ENH] Improved listing of knonwn datasets to include:
    - "scan duration"
    - presence of `physio.tsv.gz` or `stim.tsv.gz` files
    - presence of a `stimuli` directory
    - numbers of the different file formats for EEG, MEG, iEEG
    - references and links associated to each dataset
    - dataset license

### Fixed

-   [FIX] Improve datasets listing for datasets with a mix of session level folders absent or present (for example: `sub-01/meg` and `sub-emptyroom/ses-20221212/meg`)
-   [FIX] Make datasets URI more generic. (#169 @Remi-Gau)
-   [FIX] handle datasets with fMRIPrep data in subfolders. (#173 @Remi-Gau)

## 0.2.0 - 2023-09-03

## Changed

-   Adapt to neurobagel query tools new outputs formats by using a participant
    and a dataset input files. #55 @Remi-Gau

### Added

-   [ENH] turns output into a yoda datalad dataset. #84 @Remi-Gau
-   [ENH] pass dataset listings as list of strings via the CLI. #82 @Remi-Gau
-   [ENH] Index dataset and return participant listing if not provided. #81 @Remi-Gau
-   [ENH] Skip mriqc if requested. #80 @Remi-Gau
-   [ENH] Add an "all" sub command that runs install, get and copy in sequence. #65 @Remi-Gau
-   [ENH] Add a dockerfile for the package. #64 @Remi-Gau
-   [ENH] Call MRIQC docker to regenerate group level plots after copying mriqc data. #32 @Remi-Gau
-   [ENH] Create a bagel.csv file for a new cohort to list
    what pipeline has been run on which subject / session pair. #29 @Remi-Gau
-   [ENH] Change output layout output to comply with recommendations
    from the "Mega" extension to BIDS. #24 @Remi-Gau
-   [ENH] Implement the usage of a "bids filter file" to define "suffix groups"
    with their own datatype, BIDS entities and suffix and extensions
    to flexibly allow to copy data from any datatype for each dataset type. #35 @Remi-Gau
-   [ENH] Allow to run without using any participant file.
    In this case all participants of each datasets are downloaded. #75 @Remi-Gau

### Removed

-   Only use the participants file and not the dataset listing file. #34 @Remi-Gau
-   Change output layout output to now comply with recommendations
    from the "Mega" extension to BIDS. #24 @Remi-Gau

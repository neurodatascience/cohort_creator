# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
- `Added` Added for new features.
- `Changed` Changed for changes in existing functionality.
- `Deprecated` Deprecated for soon-to-be removed features.
- `Removed` Removed for now removed features.
- `Fixed` Fixed for any bug fixes.
- `Security` Security in case of vulnerabilities.
-->

## [Unreleased]

### Added

- Call MRIQC docker to regenerate group level plots after copying mriqc data.
  #32
- Create a bagel.csv file for a new cohort to list what pipeline has been run on
  which subject / session pair. #29
- Change output layout output to comply with recommendations from the "Mega"
  extension to BIDS. #24
- Implement the usage of a "bids filter file" to define "suffix groups" with
  their own datatype, BIDS entities and suffix and extensions to flexibly allow
  to copy data from any datatype for each dataset type. #35

### Removed

- Only use the participants file and not the dataset listing file. #34
- Change output layout output to now comply with recommendations from the "Mega"
  extension to BIDS. #24

.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

clean:
	sudo rm -rf outputs

demo_install:
	cohort_creator install \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--verbosity 3

demo_anat_get: demo_install
	cohort_creator get \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--jobs 6 \
		--bids_filter_file cohort_creator/data/bids_filter.json \
		--verbosity 2

demo_anat: demo_anat_get
	cohort_creator copy \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--bids_filter_file cohort_creator/data/bids_filter.json \
		--verbosity 2

demo_func: demo_install
	cohort_creator get \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype func \
		--jobs 6 \
		--bids_filter_file cohort_creator/data/bids_filter.json \
		--verbosity 3
	cohort_creator copy \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype func \
		--bids_filter_file cohort_creator/data/bids_filter.json \
		--verbosity 3

demo_all: demo_install
	cohort_creator get \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat func \
		--space T1w MNI152NLin2009cAsym \
		--jobs 6 \
		--verbosity 3
	cohort_creator copy \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat func \
		--space T1w MNI152NLin2009cAsym \
		--verbosity 3

## DOC
.PHONY: docs

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/source/cohort_creator.rst
	rm -f docs/source/cohort_creator.rst
	sphinx-apidoc -o docs/source cohort_creator
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

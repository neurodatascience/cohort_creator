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

## MAINTENANCE

lint:
	black .
	mypy cohort_creator
	flake8 cohort_creator

## DEMOS
clean:
	sudo rm -rf outputs

demo_datasets_as-str:
	cohort_creator install -d ds000001 ds000002 -o outputs

demo_no_participant:
	cohort_creator install \
		-d tests/data/datasets.tsv \
		-o outputs \
		--datatype anat \
		--verbosity 1
	cohort_creator get \
		-d tests/data/datasets.tsv \
		-o outputs \
		--datatype anat \
		--jobs 6 \
		--verbosity 1
	cohort_creator copy \
		-d tests/data/datasets.tsv \
		-o outputs \
		--verbosity 2

demo_install:
	cohort_creator install \
		-d tests/data/datasets.tsv \
		-p tests/data/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--verbosity 3

demo_anat_get: demo_install
	cohort_creator get \
		-d tests/data/datasets.tsv \
		-p tests/data/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--jobs 6 \
		--bids_filter_file cohort_creator/data/bids_filter.json \
		--verbosity 2

demo_anat: demo_anat_get
	cohort_creator copy \
		-d tests/data/datasets.tsv \
		-p tests/data/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--bids_filter_file cohort_creator/data/bids_filter.json \
		--verbosity 2

demo_all:
	cohort_creator all \
		-d tests/data/datasets.tsv \
		-p tests/data/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat

demo_func: demo_install
	cohort_creator get \
		-d tests/data/datasets.tsv \
		-p tests/data/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype func \
		--jobs 6 \
		--bids_filter_file cohort_creator/data/bids_filter.json \
		--verbosity 3
	cohort_creator copy \
		-d tests/data/datasets.tsv \
		-p tests/data/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype func \
		--bids_filter_file cohort_creator/data/bids_filter.json \
		--verbosity 3

demo_func_and_anat: demo_install
	cohort_creator get \
		-p tests/data/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat func \
		--space T1w MNI152NLin2009cAsym \
		--jobs 6 \
		--verbosity 3
	cohort_creator copy \
		-p tests/data/participants.tsv \
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

## DOCKER
.PHONY: Dockerfile_wip
Dockerfile_wip:
	docker run --rm repronim/neurodocker:0.9.1 generate docker \
		--pkg-manager apt \
		--base-image bids/base_validator:1.11.0 \
		--install python3 python3-pip git-annex  \
		--run "pip install datalad==0.19.2" \
		--run "git config --global --add user.name 'Ford Escort' && git config --global --add user.email 42@H2G2.com"
		--run "mkdir /cohort_creator" \
		--copy "." "/cohort_creator" > Dockerfile_wip

Docker_build:
	docker build -t cohort_creator .

Docker_run_version:
	docker run -t --rm cohort_creator --version
	docker run -t --rm cohort_creator

Docker_demo:
	docker run -t --rm \
		-v $$PWD/tests/data:/data \
		-v $$PWD/outputs:/outputs \
			cohort_creator all \
				-d /data/datasets.tsv \
				-p /data/participants.tsv \
				-o /outputs

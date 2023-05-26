demo_anat:
	python src/cohort_creator.py \
		inputs/datasets.tsv \
		inputs/participants.tsv \
		outputs \
		--action all \
		--dataset_types raw mriqc fmriprep \
		--verbosity 3

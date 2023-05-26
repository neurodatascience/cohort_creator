demo_anat:
	cohort_creator \
		inputs/datasets.tsv \
		inputs/participants.tsv \
		outputs \
		--action all \
		--dataset_types raw mriqc fmriprep \
		--verbosity 3

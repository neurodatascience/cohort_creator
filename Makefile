clean:
	sudo rm -rf outputs
demo_anat:
	cohort_creator \
		inputs/datasets.tsv \
		inputs/participants.tsv \
		outputs \
		--action all \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--verbosity 3
demo_func:
	cohort_creator \
		inputs/datasets.tsv \
		inputs/participants.tsv \
		outputs \
		--action all \
		--dataset_types raw mriqc fmriprep \
		--datatype func \
		--verbosity 3
demo_all:
	cohort_creator \
		inputs/datasets.tsv \
		inputs/participants.tsv \
		outputs \
		--action all \
		--dataset_types raw mriqc fmriprep \
		--datatype anat func \
		--space T1w MNI152NLin2009cAsym \
		--verbosity 3

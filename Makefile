clean:
	sudo rm -rf outputs
demo_anat:
	cohort_creator install \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--verbosity 3
	cohort_creator get \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--jobs 6 \
		--verbosity 3
	cohort_creator copy \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--verbosity 3
demo_func:
	cohort_creator install \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--verbosity 3
	cohort_creator get \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--jobs 6 \
		--verbosity 3
	cohort_creator copy \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat \
		--verbosity 3
demo_all:
	cohort_creator install \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--verbosity 3
	cohort_creator get \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat func \
		--space T1w MNI152NLin2009cAsym \
		--jobs 6 \
		--verbosity 3
	cohort_creator copy \
		-d inputs/datasets.tsv \
		-p inputs/participants.tsv \
		-o outputs \
		--dataset_types raw mriqc fmriprep \
		--datatype anat func \
		--space T1w MNI152NLin2009cAsym \
		--verbosity 3

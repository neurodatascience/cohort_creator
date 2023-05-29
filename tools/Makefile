clean:
	rm -f *.tsv

OpenNeuroDerivatives.tsv:
	python list_derivatives.py

OpenNeuroDatasets.tsv:
	python install_missing_datasets.py

update: OpenNeuroDerivatives.tsv OpenNeuroDatasets.tsv
	python update_openneuro.py

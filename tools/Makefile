clean:
	rm -f *.tsv

OpenNeuroDerivatives.tsv:
	python list_derivatives.py

OpenNeuroDatasets.tsv:
	python install_missing_datasets.py

update: clean OpenNeuroDerivatives.tsv OpenNeuroDatasets.tsv

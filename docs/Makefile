# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python -m sphinx
SPHINXPROJ    = cohort_creator
SOURCEDIR     = source
BUILDDIR      = _build

clean:
	rm -rf $(BUILDDIR)/*

convert_to_csv:
	python convert_to_csv.py

html: convert_to_csv clean
	$(SPHINXBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

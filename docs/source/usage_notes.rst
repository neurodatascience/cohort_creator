.. _Usage :

Usage Notes
===========

Command-Line Arguments
----------------------
.. argparse::
   :prog: cohort_creator
   :module: cohort_creator._parsers
   :func: global_parser


Examples
--------

install
^^^^^^^

.. code-block:: bash

   cohort_creator install \
         --dataset_listing inputs/dataset-results.tsv \
         --participant_listing inputs/participant-results.tsv \
         --output_dir outputs \
         --dataset_types raw mriqc fmriprep \
         --verbosity 3

If no ``--participant_listing`` is provided,
a ``participants.tsv`` file will be generated
in ``output_dir/code`` that contains all participants
for all datasets in ``dataset_listing``.

Datasets listing can be passed directly as a list of datasets:

.. code-block:: bash

   cohort_creator install \
         --dataset_listing ds000001 ds000002 \
         --output_dir outputs \
         --dataset_types raw mriqc fmriprep \
         --verbosity 3

get
^^^

.. code-block:: bash

   cohort_creator get \
         --dataset_listing inputs/dataset-results.tsv \
         --participant_listing inputs/participant-results.tsv \
         --output_dir outputs \
         --dataset_types raw mriqc fmriprep \
         --datatype anat func \
         --space T1w MNI152NLin2009cAsym \
         --jobs 6 \
         --verbosity 3


copy
^^^^

.. code-block:: bash

   cohort_creator copy \
         --dataset_listing inputs/dataset-results.tsv \
         --participant_listing inputs/participant-results.tsv \
         --output_dir outputs \
         --dataset_types raw mriqc fmriprep \
         --datatype anat func \
         --space T1w MNI152NLin2009cAsym \
         --verbosity 3

all
^^^

.. code-block:: bash

   cohort_creator all \
         --dataset_listing inputs/dataset-results.tsv \
         --participant_listing inputs/participant-results.tsv \
         --output_dir outputs \
         --dataset_types raw mriqc fmriprep \
         --datatype anat func \
         --space T1w MNI152NLin2009cAsym \
         --verbosity 3

.. _Usage :

Usage Notes
===========

Command-Line Arguments
----------------------
.. argparse::
   :prog: cohort_creator
   :module: cohort_creator._parsers
   :func: global_parser


You can use the ``cohort_creator browse`` command to create a ``dataset-results.tsv``
to use for the next steps.

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

Python API
----------

.. code-block:: python

   from cohort_creator.data.utils import filter_data
   from cohort_creator.data.utils import known_datasets_df
   from cohort_creator.data.utils import save_dataset_listing
   from cohort_creator.data.utils import wrangle_data

   filter_config = {"task": "back", "datatypes": ["func"]}
   df = wrangle_data(known_datasets_df())
   df = filter_data(df, config=filter_config)
   save_dataset_listing(df)

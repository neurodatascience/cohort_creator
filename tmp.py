from pathlib import Path

from cohort_creator._cli import create_yoda
from cohort_creator._utils import sourcedata
from cohort_creator.copy_files import copy_this_subject
from cohort_creator.main import install_datasets

output_dir = Path.cwd() / "tmp"
create_yoda(output_dir)
dataset_types = ["raw"]
datatypes = ["anat"]
install_datasets(datasets=["ds000001"], output_dir=output_dir, dataset_types=dataset_types)
copy_this_subject(
    subject="sub-01",
    datatypes=datatypes,
    dataset_type=dataset_types[0],
    src_pth=sourcedata(output_dir) / "ds000001",
    target_pth=output_dir / "study-ds000001" / "bids",
)

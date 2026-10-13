import subprocess
import sys

import numpy as np
import pytest

from bids_inventory.listing import _data_dir

# needs the 'update' extra
nb = pytest.importorskip("nibabel")


@pytest.mark.parametrize("extension", [".nii", ".nii.gz"])
@pytest.mark.parametrize("image_class", ["Nifti1Image", "Nifti2Image"])
@pytest.mark.parametrize("header_extension", [False, True])
def test_read_nb_vols(tmp_path, extension, image_class, header_extension):
    """Only the beginning of the file is streamed to the script, compressed or not."""
    img = getattr(nb, image_class)(np.zeros((4, 4, 4, 7), dtype=np.int16), affine=np.eye(4))
    img.header.set_zooms((2.0, 2.0, 2.0, 1.5))
    if header_extension:
        # extensions longer than what is streamed must not prevent reading the header
        img.header.extensions.append(nb.nifti1.Nifti1Extension("comment", b"x" * 4000))
    filename = tmp_path / f"sub-01_task-rest_bold{extension}"
    nb.save(img, filename)

    result = subprocess.run(
        [sys.executable, str(_data_dir() / "read_nb_vols")],
        input=filename.read_bytes()[:1024],
        capture_output=True,
        check=True,
    )

    assert result.stdout.decode().split() == ["7", "1.5"]

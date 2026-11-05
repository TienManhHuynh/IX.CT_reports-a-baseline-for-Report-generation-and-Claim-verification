
from pathlib import Path
import tarfile
import shutil
import re

import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# 1. Tìm archive đã tải
archives = sorted((ROOT / "data/raw/mask_only").glob("*.tar.gz"))

if not archives:
    raise FileNotFoundError(
        "Chua tim thay archive trong data/raw/mask_only"
    )

archive_path = archives[0]
print("Archive:", archive_path.name)

# 2. Các loại mask tổn thương cần tìm
lesion_names = [
    "liver_lesion.nii.gz",
    "kidney_lesion.nii.gz",
    "pancreatic_lesion.nii.gz",
]

found = False

with tarfile.open(archive_path, "r:gz") as tar:
    members = [
        m for m in tar.getmembers()
        if m.isfile() and Path(m.name).name in lesion_names
    ]

    # Ưu tiên tổn thương gan
    members.sort(
        key=lambda m: (
            lesion_names.index(Path(m.name).name),
            m.name
        )
    )

    print("Candidate masks:", len(members))

    for member in members:
        match = re.search(r"BDMAP_\d+", member.name)
        if not match:
            continue

        case_id = match.group(0)
        filename = Path(member.name).name

        target = (
            ROOT / "data/sample"
            / case_id / "segmentations" / filename
        )
        target.parent.mkdir(parents=True, exist_ok=True)

        # Chỉ lấy file đang xét, không giải nén cả archive
        source = tar.extractfile(member)
        if source is None:
            continue

        with source, target.open("wb") as dest:
            shutil.copyfileobj(source, dest)

        # 3. Kiểm tra mask có voxel được đánh dấu không
        img = nib.load(str(target))
        mask = np.asanyarray(img.dataobj)

        count = int(np.count_nonzero(mask))

        if count == 0:
            target.unlink()
            continue

        print("\nFound positive lesion mask!")
        print("Case ID:", case_id)
        print("Mask:", filename)
        print("Shape:", mask.shape)
        print("Nonzero voxels:", count)
        print("Spatial unit:", img.header.get_xyzt_units()[0])

        found = True
        break

if not found:
    print("Khong tim thay mask co voxel duoc danh dau.")
    print("Hay kiem tra archive hoac thu archive khac.")

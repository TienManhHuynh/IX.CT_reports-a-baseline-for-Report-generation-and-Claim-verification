
from pathlib import Path
import json

import nibabel as nib
import numpy as np

# 1. Xác định thư mục gốc
ROOT = Path(__file__).resolve().parents[1]

# 2. Tìm mask tổn thương gan
mask_files = sorted(
    (ROOT / "data/sample").rglob("liver_lesion.nii.gz")
)

if not mask_files:
    raise FileNotFoundError("Cannot find liver lesion mask")

mask_path = mask_files[0]
case_id = mask_path.parent.parent.name

# 3. Đọc NIfTI
img = nib.load(str(mask_path))
mask = np.asanyarray(img.dataobj) > 0

if mask.ndim != 3:
    raise ValueError("Expected a 3D segmentation mask")

unit = img.header.get_xyzt_units()[0]

if unit != "mm":
    raise ValueError(f"Unsupported spatial unit: {unit}")

# 4. Trích xuất thuộc tính
voxel_count = int(np.count_nonzero(mask))
voxel_volume_mm3 = abs(np.linalg.det(img.affine[:3, :3]))

volume_cm3 = (
    voxel_count * voxel_volume_mm3 / 1000
)

# 5. Xác định bounding box trong tọa độ voxel
if voxel_count > 0:
    coords = np.argwhere(mask)

    bbox_min = coords.min(axis=0).tolist()
    bbox_max = coords.max(axis=0).tolist()

    # Chọn lát cắt có nhiều voxel được đánh dấu nhất
    slice_counts = mask.sum(axis=(0, 1))
    slice_index = int(np.argmax(slice_counts))
else:
    bbox_min = None
    bbox_max = None
    slice_index = None

# 6. Tạo structured report
features = {
    "organ": "liver",
    "annotated_lesion": voxel_count > 0,
    "voxel_count": voxel_count,
    "volume_cm3": round(float(volume_cm3), 3)
}

if voxel_count > 0:
    report_text = (
        "Liver lesion annotation is present. "
        f"Total segmented lesion volume: {volume_cm3:.3f} cm3."
    )
else:
    report_text = (
        "No liver lesion voxels are annotated "
        "in the supplied mask."
    )

# 7. Lưu bằng chứng grounding
evidence = {
    "mask_path": str(
        mask_path.relative_to(ROOT)
    ).replace("\\", "/"),
    "bbox_min": bbox_min,
    "bbox_max": bbox_max,
    "slice_axis": 2,
    "slice_index": slice_index
}

output = {
    "case_id": case_id,
    "features": features,
    "structured_report": report_text,
    "evidence": evidence
}

# 8. Lưu JSON
output_path = ROOT / "results" / "sample_report.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open("w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("Case ID:", case_id)
print("Structured report:", report_text)
print("Evidence:", evidence)
print("Saved:", output_path)

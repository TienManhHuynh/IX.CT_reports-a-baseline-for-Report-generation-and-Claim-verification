
from pathlib import Path

import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

# 1. Tìm mask mẫu
mask_files = list(
    (ROOT / "data/sample").rglob("*_lesion.nii.gz")
)

if not mask_files:
    raise FileNotFoundError("Chua co lesion mask mau.")

mask_path = mask_files[0]

# 2. Đọc file
img = nib.load(str(mask_path))
mask = np.asanyarray(img.dataobj) > 0

print("File:", mask_path.name)
print("Shape:", mask.shape)
print("Voxel count:", np.count_nonzero(mask))

# 3. Kiểm tra đơn vị
unit = img.header.get_xyzt_units()[0]

if unit != "mm":
    raise ValueError(
        f"Can kiem tra don vi NIfTI truoc khi tinh: {unit}"
    )

# 4. Tính thể tích dựa trên affine
voxel_volume_mm3 = abs(
    np.linalg.det(img.affine[:3, :3])
)

volume_cm3 = (
    np.count_nonzero(mask)
    * voxel_volume_mm3
    / 1000
)

print(f"Lesion volume: {volume_cm3:.4f} cm3")

# 5. Chọn lát cắt có nhiều voxel tổn thương nhất
slice_counts = mask.sum(axis=(0, 1))
slice_index = int(np.argmax(slice_counts))

plt.figure(figsize=(6, 6))
plt.imshow(
    mask[:, :, slice_index].T,
    cmap="gray",
    origin="lower"
)
plt.title(f"Lesion mask - slice {slice_index}")
plt.axis("off")

output = ROOT / "results/sample_mask.png"
output.parent.mkdir(exist_ok=True)

plt.savefig(output, dpi=150, bbox_inches="tight")
plt.show()

print("Saved visualization:", output)

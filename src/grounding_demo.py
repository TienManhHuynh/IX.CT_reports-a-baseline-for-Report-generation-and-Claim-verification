
import numpy as np

# 1. Giả lập một segmentation mask 3D
mask = np.zeros((10, 10, 10), dtype=bool)

# Đánh dấu một vùng tổn thương giả định
mask[2:5, 3:7, 4:6] = True

# 2. Tính thể tích
voxel_spacing_mm = (1.0, 1.0, 2.0)

voxel_volume_mm3 = np.prod(voxel_spacing_mm)
lesion_voxels = np.count_nonzero(mask)

volume_cm3 = lesion_voxels * voxel_volume_mm3 / 1000

print("Measured volume:", volume_cm3, "cm3")

# 3. Tạo structured report
report = f"Liver lesion volume: {volume_cm3:.3f} cm3."
print("Generated report:", report)

# 4. Kiểm tra các nhận định
def verify_volume(claimed_volume, measured_volume, tolerance=0.01):
    difference = abs(claimed_volume - measured_volume)

    if difference <= tolerance:
        return "SUPPORTED_BY_MASK"

    return "INCONSISTENT_WITH_MASK"


correct_claim = 0.048
incorrect_claim = 0.096

print("Correct claim:", verify_volume(correct_claim, volume_cm3))
print("Incorrect claim:", verify_volume(incorrect_claim, volume_cm3))

# 5. Giả lập segmentation bị thiếu một nửa
incomplete_mask = mask.copy()
incomplete_mask[:, :, 5] = False

incomplete_volume = (
    np.count_nonzero(incomplete_mask)
    * voxel_volume_mm3
    / 1000
)

print("Incomplete mask volume:", incomplete_volume)
print(
    "Original claim vs incomplete mask:",
    verify_volume(correct_claim, incomplete_volume)
)


from pathlib import Path
import json

import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# 1. Đọc kết quả Feature Extraction
report_path = ROOT / "results/sample_report.json"

with report_path.open("r", encoding="utf-8") as f:
    data = json.load(f)

measured_volume = data["features"]["volume_cm3"]

# 2. Hàm kiểm tra nhận định về thể tích
def verify_volume(claimed, measured, tolerance=0.01):
    if abs(claimed - measured) <= tolerance:
        return "SUPPORTED_BY_MASK"

    return "INCONSISTENT_WITH_MASK"


# 3. Hai claim để kiểm thử
correct_claim = measured_volume
wrong_claim = round(measured_volume * 2, 3)

print("=== CLAIM VERIFICATION ===")
print("Measured volume:", measured_volume)

print(
    "Correct claim:",
    verify_volume(correct_claim, measured_volume)
)

print(
    "Wrong claim:",
    verify_volume(wrong_claim, measured_volume)
)

# 4. Giả lập mask bị thiếu 50% voxel được đánh dấu
mask_path = ROOT / data["evidence"]["mask_path"]

img = nib.load(str(mask_path))
mask = np.asanyarray(img.dataobj) > 0

incomplete_mask = mask.copy()

# Cố ý xóa một nửa các voxel tổn thương
coords = np.argwhere(incomplete_mask)
remove_coords = coords[:len(coords) // 2]

incomplete_mask[tuple(remove_coords.T)] = False

# 5. Tính lại thể tích của mask bị thiếu
voxel_volume = abs(np.linalg.det(img.affine[:3, :3]))

incomplete_volume = (
    np.count_nonzero(incomplete_mask)
    * voxel_volume
    / 1000
)

print("\n=== INCOMPLETE MASK EXPERIMENT ===")
print("Original volume:", measured_volume)
print("Incomplete volume:", round(incomplete_volume, 3))

print(
    "Original claim vs incomplete mask:",
    verify_volume(correct_claim, incomplete_volume)
)

# 6. Lưu kết quả
results = {
    "case_id": data["case_id"],
    "original_volume_cm3": measured_volume,
    "incomplete_volume_cm3": round(
        float(incomplete_volume), 3
    ),
    "correct_claim_result": verify_volume(
        correct_claim, measured_volume
    ),
    "wrong_claim_result": verify_volume(
        wrong_claim, measured_volume
    ),
    "incomplete_mask_result": verify_volume(
        correct_claim, incomplete_volume
    )
}

result_path = ROOT / "results/verification_results.json"

with result_path.open("w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nSaved:", result_path)

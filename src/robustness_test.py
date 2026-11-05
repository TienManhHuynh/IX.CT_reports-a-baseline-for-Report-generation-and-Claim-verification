
from pathlib import Path
import json

import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

# Load structured report
with open(ROOT / "results/sample_report.json", encoding="utf-8") as f:
    report = json.load(f)

mask_path = ROOT / report["evidence"]["mask_path"]

img = nib.load(str(mask_path))
mask = np.asanyarray(img.dataobj) > 0

if img.header.get_xyzt_units()[0] != "mm":
    raise ValueError("NIfTI spatial unit must be mm")

voxel_volume = abs(np.linalg.det(img.affine[:3, :3]))

# Functions
def get_volume(m):
    return float(np.count_nonzero(m) * voxel_volume / 1000)


def verify_volume(claimed, measured, tolerance=0.01):
    if abs(claimed - measured) <= tolerance:
        return "SUPPORTED_BY_MASK"
    return "INCONSISTENT_WITH_MASK"


def dice_score(a, b):
    intersection = np.count_nonzero(a & b)
    denominator = np.count_nonzero(a) + np.count_nonzero(b)

    if denominator == 0:
        return 1.0

    return 2 * intersection / denominator


# Experiment 1: Original
original = mask.copy()

# Experiment 2: Remove 50% of annotated voxels
incomplete = mask.copy()
coords = np.argwhere(incomplete)
removed = coords[:len(coords) // 2]
incomplete[tuple(removed.T)] = False

# Experiment 3: Shift lesion mask along voxel axis 0
shift = 20
shifted = np.zeros_like(mask)

if coords[:, 0].max() + shift < mask.shape[0]:
    shifted[shift:, :, :] = mask[:-shift, :, :]
elif coords[:, 0].min() >= shift:
    shifted[:-shift, :, :] = mask[shift:, :, :]
else:
    raise ValueError("Not enough space to shift mask")

assert np.count_nonzero(shifted) == np.count_nonzero(mask)

# Use the rounded volume in the generated report
claimed_volume = report["features"]["volume_cm3"]

cases = {
    "Original": original,
    "Incomplete 50%": incomplete,
    "Shifted 20 voxels": shifted
}

print("=== ROBUSTNESS EXPERIMENT ===")
print("Claimed volume:", claimed_volume, "cm3")

results = []

for name, current_mask in cases.items():
    measured = get_volume(current_mask)
    status = verify_volume(claimed_volume, measured)
    dice = dice_score(original, current_mask)

    results.append({
        "condition": name,
        "volume_cm3": round(measured, 3),
        "volume_verification": status,
        "dice_vs_original": round(dice, 4)
    })

    print(f"\nCondition: {name}")
    print(f"Volume: {measured:.3f} cm3")
    print("Volume verification:", status)
    print(f"Dice vs original: {dice:.4f}")

# Save experimental results
output = ROOT / "results/robustness_results.json"

with output.open("w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nSaved:", output)

# Visualization: same voxel slice across conditions
z = report["evidence"]["slice_index"]

fig, axes = plt.subplots(1, 3, figsize=(12, 4))

for ax, (name, current_mask) in zip(axes, cases.items()):
    ax.imshow(
        current_mask[:, :, z].T,
        cmap="gray",
        origin="lower"
    )
    ax.set_title(name)
    ax.axis("off")

fig.suptitle(f"Segmentation perturbations - slice {z}")
fig.tight_layout()

image_path = ROOT / "results/robustness_visualization.png"
fig.savefig(image_path, dpi=150, bbox_inches="tight")
plt.show()

print("Saved visualization:", image_path)

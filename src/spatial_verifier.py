
from pathlib import Path
import json

import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

# Thresholds for experimental demonstration only
VOLUME_TOLERANCE_CM3 = 0.01
DICE_THRESHOLD = 0.50
MAX_CENTROID_DISTANCE_MM = 10.0

# 1. Load generated structured report
report_path = ROOT / "results/sample_report.json"

with report_path.open("r", encoding="utf-8") as f:
    report = json.load(f)

mask_path = ROOT / report["evidence"]["mask_path"]

img = nib.load(str(mask_path))

if img.header.get_xyzt_units()[0] != "mm":
    raise ValueError("Expected spatial unit: mm")

reference = np.asanyarray(img.dataobj) > 0
affine = img.affine

if not reference.any():
    raise ValueError("Reference mask is empty")

voxel_volume_mm3 = abs(np.linalg.det(affine[:3, :3]))

# The claim is anchored to the original annotation region
claimed_volume = float(report["features"]["volume_cm3"])


# 2. Volume measurement
def get_volume(mask):
    return (
        np.count_nonzero(mask)
        * voxel_volume_mm3
        / 1000.0
    )


def verify_volume(claimed, measured):
    return (
        "PASS"
        if abs(claimed - measured) <= VOLUME_TOLERANCE_CM3
        else "FAIL"
    )


# 3. Spatial measurements
def dice_score(a, b):
    intersection = np.count_nonzero(a & b)
    total = np.count_nonzero(a) + np.count_nonzero(b)

    if total == 0:
        return None

    return 2.0 * intersection / total


def centroid_world(mask):
    coords = np.argwhere(mask)

    if len(coords) == 0:
        return None

    # Centroid in voxel coordinates
    centroid_voxel = coords.mean(axis=0)

    # Convert to physical/world coordinates (mm)
    return nib.affines.apply_affine(
        affine, centroid_voxel
    )


def centroid_distance_mm(a, b):
    ca = centroid_world(a)
    cb = centroid_world(b)

    if ca is None or cb is None:
        return None

    return float(np.linalg.norm(ca - cb))


def verify_spatial(reference_mask, candidate_mask):
    dice = dice_score(reference_mask, candidate_mask)
    distance = centroid_distance_mm(
        reference_mask, candidate_mask
    )

    if dice is None or distance is None:
        status = "INSUFFICIENT_EVIDENCE"
    elif (
        dice >= DICE_THRESHOLD
        and distance <= MAX_CENTROID_DISTANCE_MM
    ):
        status = "PASS"
    else:
        status = "FAIL"

    return {
        "dice": dice,
        "centroid_distance_mm": distance,
        "status": status
    }


# 4. Create controlled perturbations

# A. Original mask
original = reference.copy()

# B. Remove approximately 50% of lesion voxels
incomplete = reference.copy()
coords = np.argwhere(incomplete)

remove_coords = coords[:len(coords) // 2]
incomplete[tuple(remove_coords.T)] = False

# C. Shift mask by 20 voxels along axis 0
shift = 20
shifted = np.zeros_like(reference)

if coords[:, 0].max() + shift < reference.shape[0]:
    shifted[shift:, :, :] = reference[:-shift, :, :]
elif coords[:, 0].min() >= shift:
    shifted[:-shift, :, :] = reference[shift:, :, :]
else:
    raise ValueError("Cannot shift without cropping")

assert shifted.sum() == reference.sum()

cases = {
    "Original": original,
    "Incomplete 50%": incomplete,
    "Shifted 20 voxels": shifted
}


# 5. Combined verification
results = []

print("=== SPATIAL VERIFICATION ===")
print("Case:", report["case_id"])
print("Claimed volume:", claimed_volume, "cm3")

for name, candidate in cases.items():

    measured_volume = get_volume(candidate)

    volume_status = verify_volume(
        claimed_volume, measured_volume
    )

    spatial = verify_spatial(
        reference, candidate
    )

    if spatial["status"] == "INSUFFICIENT_EVIDENCE":
        combined_status = "INSUFFICIENT_EVIDENCE"
    elif (
        volume_status == "PASS"
        and spatial["status"] == "PASS"
    ):
        combined_status = "PASS"
    else:
        combined_status = "FAIL"

    item = {
        "condition": name,
        "volume_cm3": round(measured_volume, 3),
        "volume_status": volume_status,
        "dice": (
            round(spatial["dice"], 4)
            if spatial["dice"] is not None else None
        ),
        "centroid_distance_mm": (
            round(spatial["centroid_distance_mm"], 3)
            if spatial["centroid_distance_mm"] is not None
            else None
        ),
        "spatial_status": spatial["status"],
        "combined_status": combined_status
    }

    results.append(item)

    print("\nCondition:", name)
    print("Volume:", item["volume_cm3"])
    print("Volume verification:", volume_status)
    print("Dice:", item["dice"])
    print(
        "Centroid distance (mm):",
        item["centroid_distance_mm"]
    )
    print("Spatial verification:", spatial["status"])
    print("Combined verification:", combined_status)


# 6. Save JSON results
output = ROOT / "results/spatial_verification_results.json"

with output.open("w", encoding="utf-8") as f:
    json.dump(
        {
            "case_id": report["case_id"],
            "reference": "original annotation mask",
            "thresholds": {
                "volume_tolerance_cm3": VOLUME_TOLERANCE_CM3,
                "dice_min": DICE_THRESHOLD,
                "centroid_distance_max_mm":
                    MAX_CENTROID_DISTANCE_MM
            },
            "results": results
        },
        f,
        indent=2
    )

print("\nSaved:", output)


# 7. Visualize reference vs candidate on same slice
z = report["evidence"]["slice_index"]

fig, axes = plt.subplots(1, 3, figsize=(12, 4))

for ax, (name, candidate) in zip(axes, cases.items()):
    ref_slice = reference[:, :, z].T
    cand_slice = candidate[:, :, z].T

    # Black background
    ax.imshow(
        np.zeros_like(ref_slice),
        cmap="gray",
        vmin=0,
        vmax=1,
        origin="lower"
    )

    # Red: original reference
    ax.imshow(
        np.ma.masked_where(~ref_slice, ref_slice),
        cmap="Reds",
        vmin=0,
        vmax=1,
        origin="lower",
        alpha=0.65
    )

    # Blue: candidate
    ax.imshow(
        np.ma.masked_where(~cand_slice, cand_slice),
        cmap="Blues",
        vmin=0,
        vmax=1,
        origin="lower",
        alpha=0.65
    )

    ax.set_title(name)
    ax.axis("off")

fig.suptitle(
    f"Spatial verification - Case {report['case_id']}"
)

fig.tight_layout()

image_path = ROOT / "results/spatial_verification.png"
fig.savefig(image_path, dpi=150, bbox_inches="tight")

print("Saved visualization:", image_path)

plt.show()

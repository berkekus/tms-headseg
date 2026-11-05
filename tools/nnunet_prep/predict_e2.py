"""Run the E2 nnU-Net model on one T1 MRI and save a prediction that MRI Workbench can open.

E2 was trained on images reoriented to RAS, so the T1 is reoriented first and the prediction is
saved on that RAS grid next to a copy of the reoriented T1 (`T1_ras.nii.gz`). Open the pair with
Workbench's "Open E1 segmentation..." (same label IDs: 1 skin, 2 skull, 3 CSF, 4 GM, 5 WM).

    python predict_e2.py --model <...__3d_fullres folder> --mri T1.nii.gz --out <new folder>
        [--charm-reference m2m_X/final_tissues.nii.gz] [--device cpu]
"""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from headmodel.labels import CHARM_TO_PROJECT  # noqa: E402

NAMES = {1: "skin", 2: "skull", 3: "csf", 4: "gray_matter", 5: "white_matter"}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def save_ras(src, dst):
    """Reorient to RAS and state mm units with qform = sform (the K3 coordinate contract)."""
    img = nib.as_closest_canonical(nib.load(src))
    out = nib.Nifti1Image(np.asarray(img.dataobj), img.affine)
    out.header.set_xyzt_units("mm")
    out.set_qform(img.affine, code=1)
    out.set_sform(img.affine, code=1)
    nib.save(out, dst)


def load_predictor(model, device):
    import torch
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
    from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
    from nnunetv2.utilities.label_handling.label_handling import determine_num_input_channels
    from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

    dataset_json = json.loads((model / "dataset.json").read_text())
    plans = PlansManager(json.loads((model / "plans.json").read_text()))
    # The checkpoint is a pickle: load only a model folder you trust (our own training run).
    checkpoint = torch.load(model / "fold_0" / "checkpoint_final.pth", map_location="cpu", weights_only=False)
    config = plans.get_configuration(checkpoint["init_args"]["configuration"])
    # The E2 trainer only changes the epoch count, so the standard trainer builds the same network.
    network = nnUNetTrainer.build_network_architecture(
        plans, config, determine_num_input_channels(plans, config, dataset_json),
        plans.get_label_manager(dataset_json).num_segmentation_heads, enable_deep_supervision=False)
    network.load_state_dict(checkpoint["network_weights"])
    predictor = nnUNetPredictor(device=torch.device(device), use_mirroring=True, verbose=False)
    predictor.manual_initialization(network, plans, config, [checkpoint["network_weights"]], dataset_json,
                                    checkpoint["trainer_name"], checkpoint.get("inference_allowed_mirroring_axes"))
    return predictor, plans


def dice_against_charm(prediction_path, charm_path):
    pred = nib.as_closest_canonical(nib.load(prediction_path))
    charm = nib.as_closest_canonical(nib.load(charm_path))
    if pred.shape != charm.shape[:3] or not np.allclose(pred.affine, charm.affine, atol=1e-3):
        return None
    p = np.asarray(pred.dataobj).astype(np.int64)
    ids = np.asarray(charm.dataobj).astype(np.int64).reshape(pred.shape)
    ref = np.zeros_like(ids)
    for charm_id, project_id in CHARM_TO_PROJECT.items():
        ref[ids == charm_id] = project_id
    return {name: round(float(2 * ((p == k) & (ref == k)).sum() / ((p == k).sum() + (ref == k).sum())), 3)
            for k, name in NAMES.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", type=Path, required=True, help="folder with plans.json, dataset.json, fold_0/")
    parser.add_argument("--mri", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new folder, outside Git")
    parser.add_argument("--charm-reference", type=Path, help="charm final_tissues.nii.gz of the same subject")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=False)
    t1_ras, prediction = args.out / "T1_ras.nii.gz", args.out / "prediction.nii.gz"
    save_ras(args.mri, t1_ras)

    start = time.perf_counter()
    predictor, plans = load_predictor(args.model, args.device)
    io = plans.image_reader_writer_class()
    image, properties = io.read_images([str(t1_ras)])
    seg = predictor.predict_single_npy_array(image, properties, None, None, False)
    io.write_seg(seg, str(prediction), properties)
    seconds = round(time.perf_counter() - start, 1)

    record = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mri": str(args.mri), "mri_sha256": sha256(args.mri),
        "checkpoint_sha256": sha256(args.model / "fold_0" / "checkpoint_final.pth"),
        "device": args.device, "mirroring": True, "seconds": seconds,
        "prediction": str(prediction),
        "voxels_ml": {name: round(float((seg == k).sum()) * float(np.prod(properties["spacing"])) / 1000, 1)
                      for k, name in NAMES.items()},
    }
    if args.charm_reference:
        record["charm_reference"] = str(args.charm_reference)
        record["dice_vs_charm"] = dice_against_charm(prediction, args.charm_reference)
    (args.out / "run.json").write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()

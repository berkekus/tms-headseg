# E2 training (Colab)

`E2_Colab.ipynb` trains the preliminary E2 model on K1's `handoff_k2_e2.zip` (`Dataset002_E2Charm`, charm 4.6.0 labels on IXI and MultiAxial). It follows the notebook that trained `E1_L4_001`: the same pinned environment (`tools/e1_training/requirements-colab.lock.txt`), seed 42, a checkpoint every epoch, an optional 5-epoch check, and a separate 100-epoch run. Only the data differ, so E1 and E2 can be compared.

## Use

1. In Drive, add a shortcut to the shared `handoff_k2_e2.zip` under **My Drive → `TMS_E2`** (right-click → Organize → Add shortcut), or copy it there. Shared folders are not visible under `MyDrive` in Colab.
2. Upload `E2_Colab.ipynb` to Colab and choose a GPU runtime (L4 was used for E1; at least 12 GiB VRAM).
3. Run the cells in order. After reviewing the preview and the data notes, set `ACKNOWLEDGE_E2_DATA = True`.
4. Optionally run the 5-epoch check (`RUN_5_EPOCH_PILOT`), then set `RUN_100_EPOCH_PRELIMINARY = True`. To continue an interrupted run, keep the same `EXPERIMENT_ID` and set `RESUME_PRELIMINARY = True`.

Results go to `MyDrive/TMS_E2/runs/E2_L4_001/`. Training flags are off by default, so Run All does not start paid training.

## What the notebook checks

- The archive's SHA-256 equals the value K1 published (`e2_contract.json`). Paths are checked for safety; Windows `\` separators are accepted.
- The split equals the one `tools/nnunet_prep/prepare_e2.plan_cases` computes from the shared assignments (67 train, 16 validation; IXI 23/6, MultiAxial 44/10), with no held-out subject. A test checks the contract against `prepare_e2` and `ixi_assignment.csv`.
- File names, image/label grids, integer labels 0–5, finite intensities, and the label contract in `dataset.json`.

## Axis order

`prepare_e2.py` keeps each scan in its stored order: IXI is PSR, MultiAxial is RAS. nnU-Net does not reorient, so the network would see two array layouts. With `CANONICALIZE_TO_RAS = True` (default) the notebook writes a copy in which every image and label is permuted and flipped to RAS, without interpolation and with each voxel's world position unchanged (the K3 coordinate contract, D-004). The per-case changes are saved with the run.

A model trained this way expects RAS-ordered input. The Workbench's **04 E1 / E2 segmentation** tab now applies K3's lossless preparation and source-grid restoration when E2 is selected. See [desktop inference](../mri_prototype/INFERENCE.md) for model and input requirements.

## Files

- `e2_helpers.py`: archive extraction, audit, RAS copy, preview, training command; also a small command line the notebook runs inside the training environment.
- `trainers_e2.py`: `nnUNetTrainer_E2Smoke` (5 epochs) and `nnUNetTrainer_E2Preliminary` (100 epochs), seed 42, checkpoint every epoch.
- `e2_contract.json`: archive checksum, labels, and the exact train/validation lists.
- `build_e2_notebook.py`: regenerates `E2_Colab.ipynb` from these files and the E1 helpers it reuses.

## Tests

```bash
python -m unittest discover -s tools/e2_training -v
```

The tests use small synthetic archives. They do not run nnU-Net, use a GPU, or open the real archive.

# E3 training: actual Dataset003 handoff

Use the revised **E3_Dataset003_Colab.ipynb** portable copy, or repository
[E3_Colab.ipynb](E3_Colab.ipynb). Both contain the same standalone notebook.
The earlier E2-based sampling-only proposal was superseded and backed up outside
Git. This revision targets the actual package supplied on 2026-11-06.

## What is fixed

- Archive: `handoff_e3.zip`, SHA-256
  `c12f5fb233d829d20bdcc112e412a1eb9fe17158a4a56377cec3e1951eba7698`.
- Dataset003_E3Face: 106 pairs, **90 training entries from 67 people + 16 validation
  people**. Training entries are 44 MultiAxial + 46 IXI (23 original IXI + 23 `w2`
  copies). The same underlying E2 people and fixed validation split are retained.
- **Uniform standard nnU-Net sampling.** The data already implements IXI weight 2;
  there is no additional weighted sampler.
- Training label **6 = ignore** on exactly-zero voxels connected to a volume border.
  Enclosed zero-valued components remain annotated. Validation labels remain 0–5.
  Ignore is skipped by loss; the network still predicts six channels (background
  and five tissues), not an additional ignore class.
- T1 input; lossless RAS preparation. The completed E2 plan is reused with only its
  `dataset_name` updated to Dataset003. Architecture, 1 mm spacing, patch
  160×128×112 and batch 2 remain fixed.
- Python 3.11, nnU-Net 2.8.1, torch 2.6.0+cu124, seed 42, 100 epochs, four
  augmentation workers, compile off, checkpoint every epoch. Start from random
  weights; no E1/E2 checkpoint is needed. The five-epoch pilot is a separate run.

E3 changes **two factors**: the annotation-ignore policy and source exposure. It
does not reconstruct a removed patient's actual face. Source weighting also changes
site/pathology exposure. Better facial accuracy is an experimental question.

## Start after the upload

1. Wait for these files to finish uploading:

   ```text
   My Drive/TMS_E3/handoff_e3.zip
   My Drive/TMS_E3/handoff_e3.zip.sha256
   ```

2. In Colab choose **File → Upload notebook** and select the revised Dataset003
   notebook. Select an NVIDIA L4 or A100 runtime. Uploading other code files is
   unnecessary: all helpers, plans and the reviewed contract are embedded.
3. Keep default `EXPERIMENT_ID = "E3_Dataset003_001"`. Mount the Drive account
   containing the uploads and run sections 1–3 in order. Setup checks the sidecar;
   data preparation copies the archive locally, checks the full ZIP hash and audits
   split identities, grids, ignore masks, copies and RAS values/coordinates.
4. Review the four training-case previews. In a **new code cell**, run:

   ```python
   ACKNOWLEDGE_E3_DATA = True
   ```

   Then run section 4 (fingerprint/integrity checks, frozen-plan preprocessing and
   split installation). Acknowledgement records willingness to proceed, not
   anatomical approval.
5. In a new code cell run:

   ```python
   RUN_5_EPOCH_PILOT = True
   ```

   Run the section 5 cell. Wait for all five epochs, `checkpoint_final.pth`, and
   final validation covering the exact 16 subjects. Check finite loss values.
   Section 6 estimates the main loop duration using the pilot; setup and final
   validation add time. The fresh main run is gated on this completed pilot.
6. In a new code cell run:

   ```python
   RUN_5_EPOCH_PILOT = False
   RUN_100_EPOCH_PRELIMINARY = True
   RESUME_PRELIMINARY = False
   RELEASE_RUNTIME_WHEN_DONE = True
   ```

   Run section 7. The 100-epoch model starts fresh, without pilot or E2 weights.
   Confirm the first completed epoch and a nonempty **main trainer**
   `checkpoint_latest.pth` in Drive before leaving the run.

Result root:

```text
My Drive/TMS_E3/runs/E3_Dataset003_001/
```

Main model:

```text
Dataset003_E3Face/nnUNetTrainer_E3Preliminary__nnUNetPlans__3d_fullres/fold_0/
```

All training/resume flags start False. Running the notebook cannot silently start
paid training. An allocated Colab GPU can still consume credits during setup/idle
time. Local Mac activity does not guarantee a Colab backend remains allocated.

## Resume and completion

### Recover an older section 4 missing-metadata error

An earlier notebook omitted `dataset.json` when installing the frozen plan. If
fingerprinting passed but preprocessing reports a missing
`nnUNet_preprocessed/Dataset003_E3Face/dataset.json`, run this in a new cell and
then rerun the failed section 4 cell. Keep the current runtime and dataset; no
re-upload or environment reset is needed.

```python
target = PREPROCESSED / DATASET
target.mkdir(parents=True, exist_ok=True)
shutil.copyfile(TRAIN_DATASET / "dataset.json", target / "dataset.json")
print("dataset.json ready:", (target / "dataset.json").is_file())
```

The revised notebook copies this metadata before launching preprocessing. The
five-epoch pilot starts only after section 4 completes.

After a runtime reset, keep the same experiment ID and unchanged files. Rerun
setup/audit/preprocessing to rebuild local VM data, acknowledge the data, then set:

```python
RUN_5_EPOCH_PILOT = False
RUN_100_EPOCH_PRELIMINARY = True
RESUME_PRELIMINARY = True
```

Run section 7. For an interrupted pilot, use `RESUME_PILOT = True` and section 5.
Missing/corrupt checkpoints, changed data/code/settings and existing fresh-run
folders fail visibly; none trigger a silent restart. A partial validation summary
requires inspection instead of automatic deletion.

Success requires final weights and the exact 16-case full-volume validation, then
`run_success.json`. `validation_subgroups.json` reports six IXI and ten MultiAxial
subjects separately. Epoch pseudo-Dice is a different metric. Runtime release is
requested only after checked success; actual release/billing still needs checking.

Preserve the **entire run folder**, including plans, dataset metadata, final/best
checkpoints, validation outputs, logs, environment records, notebook sources and
experiment contract. No raw MRI or model weights belong in Git.

## Comparison and inference boundary

Raw validation is left intact for comparison with E2's same references. Match
TTA and input processing. E3's subsequent inference needs explicit background
masking outside acquisition because ignore regions were not supervised. That
postprocessing is a separate recorded operation, not an extra anatomical output
class or a modification to raw validation here. Workbench E3 import will need a
completed model handoff; do not rename E3 weights/trainer to E2.

No test/calibration subjects enter training. IXI111's prior exploratory test
exposure remains recorded separately. Source subgroup Dice is not a facial-surface
accuracy score, and teacher agreement does not establish clinical utility.

## Verification

```bash
python tools/e3_training/build_e3_notebook.py
python -m unittest discover -s tools/e3_training -v
python -m unittest discover -s tools/e2_training -v
```

Local checks include the actual archive, all 106 RAS entries, source-person split
isolation, exact ignore masks and copies, real nnU-Net preprocessing of GU002 and
IXI037, standard-loader sampling, ignore-loss invariance/zero gradient and a
synthetic CPU U-Net update. Original archive/source bytes are hash-checked; prepared
RAS values/grid use a semantic hash to tolerate Mac/Linux gzip encoding differences.
The standalone notebook compiles. Colab/CUDA and multi-worker execution remain
unverified until the GPU pilot; a full E3 training result is not claimed.

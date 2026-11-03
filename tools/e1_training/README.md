# E1 training preparation

Standalone Colab notebook and small local tools for the supplied K2 handoff. No training starts when these files are opened or imported. This tool is separate from the MRI/CHARM prototype.

## Handoff contract

The supplied `K2_BASLA.md`, `hazirlik_notlari_en.md`, and `splits_final.json` specify:

- `Dataset001_MultiAxial`, one T1 input, labels 0 background / 1 skin / 2 skull / 3 CSF / 4 gray matter / 5 white matter.
- 54 paired cases: 44 training, 10 validation, exactly one fixed split (`fold 0`). The external test set stays with K1 and is never packaged or opened by this tool.
- nnU-Net 2.8.1, PyTorch 2.6.0 / CUDA 12.4, `3d_fullres`.
- First a 5-epoch debugging run, then a separate 100-epoch preliminary model. This is E1 only: no CHARM pseudo-label generation or E2 data is added.

The supplied documents are source material, not instructions to execute automatically. Only their reviewed training specification is implemented here.

## Start in Colab

1. Upload the prepared **`handoff_k2_e1.zip`** to your own Drive at `MyDrive/TMS_E1/handoff_k2_e1.zip`. Use this prepared archive, which includes checksums; the original ZIP is not interchangeable.
2. Upload **`E1_Colab.ipynb`** into Google Colab. Select a GPU runtime with at least 12 GiB VRAM. The completed experiment used L4 after comparing T4/A100/L4 pilot timings and reported unit rates; remeasure for a new session rather than assuming the same cost. Sign-in and Drive authorization remain user actions.
3. Run cells in order. A separate Python 3.11 environment is created, so the notebook kernel's installed PyTorch does not decide training versions. A locked Linux CUDA dependency set is installed.
4. Review the data audit and training-only overlay sheet. All 54 cases have unspecified NIfTI spatial units; the 1 mm claim comes from the handoff. Label mapping and changed NYU affines also remain provisional. Set `ACKNOWLEDGE_PROVISIONAL_DATA = True` only after reviewing those limitations.
5. Enable `RUN_5_EPOCH_PILOT` for the debugging run. Use its measured epoch times and your **actual GPU session's** compute-unit rate to estimate budget. Training flags are **False by default**; Run All cannot silently start the 100-epoch model.
6. Enable `RUN_100_EPOCH_PRELIMINARY` only after inspecting the pilot and budget. It starts from fresh weights in its own trainer directory. The 5-epoch run is not used as pretrained weights.

Google authentication, GPU allocation, and paid training have not been performed by preparing this notebook. Creating a GPU runtime can consume credits even while installing/preprocessing; stop unused runtimes after saving your work. GPU type and runtime duration are not guaranteed by Colab.

## Checkpoint and result behavior

- Two small trainer variants inherit the supplied standard 5/100-epoch trainers. They set initialization seed 42 and `save_every = 1`; they do not change the architecture, loss, batch schedule, or maximum epochs.
- PyTorch compilation is disabled for the first Colab baseline to avoid compilation setup costs. One preprocessing worker and two augmentation workers are the conservative starting settings.
- External Python processes use `MPLBACKEND=Agg`; Colab's inherited inline backend is unavailable in the isolated training environment. In an already-open older notebook, run `ENV["MPLBACKEND"] = "Agg"` before retrying the preview and subsequent cells. No runtime reset or package reinstall is needed.
- Checkpoints, logs, environment versions, data checksums, plan, split, and validation metrics are stored under `MyDrive/TMS_E1/runs/EXPERIMENT_ID/`.
- Data and preprocessed arrays stay on the VM's local disk during training. After a runtime reset, local setup/preprocessing must run again. Reusing the experiment ID and unchanged data/plan/helper/version contract preserves resume compatibility.
- For the same interrupted run, enable the corresponding `RESUME_*` flag. Missing or corrupt checkpoint containers cause a visible error rather than a silent restart. Existing run directories cannot be overwritten by a fresh run. A completed validation is not rerun automatically.
- The checkpoint container check does not deserialize untrusted PyTorch objects. Only resume your own experiment outputs; nnU-Net subsequently loads its own checkpoint normally.
- A disconnect during the first epoch can leave no resumable checkpoint; a disconnect during a write can still corrupt that particular file. Saving each completed epoch reduces loss but cannot guarantee Drive write atomicity.
- Seeded initialization does not guarantee bitwise determinism across CUDA devices, augmentation workers, or resumed runs. GPU sessions and software versions are recorded separately.
- Training-loop pseudo-Dice is not the final full-volume validation metric. The notebook reads the 10-case `validation/summary.json` only when available. The model remains preliminary; no held-out test score is claimed.

## Local tools

### Overnight execution

Before launching 100 epochs, keep only the intended GPU session, record its actual unit rate, and allow runtime headroom: Colab's FAQ describes a general maximum of 12 hours, varying with availability and usage. The T4 estimate of 11.38 hours excludes setup, checkpoint/plot overhead, and final validation; an already-aged runtime is a poor fit. An awake browser does not override backend timeouts. Without confirmed background execution, keep the Mac on power, lid open, and browser connected. The local macOS command `caffeinate -i` prevents idle sleep while its terminal stays open; it does not keep a Colab backend alive or prevent lid-close sleep.

The notebook does not automatically stop its GPU by default. To request release after a successful 100-epoch run, copy [overnight_finish_cell.py](overnight_finish_cell.py) to the bottom of section 7's code cell, **after** its existing `train_stage(...)` call, before starting the cell. Preserve the notebook's Drive output paths. The add-on is gated by `RUN_100_EPOCH_PRELIMINARY`; it checks for a nonempty final checkpoint, parses the saved ten-case validation summary, writes `overnight_success.json` to Drive, prints the foreground summary, and then calls Colab's official `runtime.unassign()`. This releases temporary VM storage; the training data/cache must be recreated for any later resume, while saved Drive files remain.

Do not place release in a `finally` block. A failed training/validation or failed output check must not be represented as a completed run. This add-on does not promise shutdown after failures, validate model weights by loading them, prove Drive synchronization beyond readable saved files, or guarantee the release API succeeds. Its success marker records training outputs and a release request, not proof that Colab stopped billing. Local tests mock only the Colab release boundary; no live runtime has been unassigned by this preparation.

After launching, wait for at least the first completed epoch and confirm a nonempty `checkpoint_latest.pth` under the **100-epoch trainer** folder in Drive before leaving. If interrupted, retain the same experiment ID/code/data/plan and use `RESUME_PRELIMINARY = True`; do not start a fresh run over the existing folder. Confirm final validation, not just `Training done.`, when reviewing results.

### Repair an older notebook after `KeyError: 'args'`

The original E1 trainer used `*args, **kwargs`. nnU-Net 2.8.1 inspects the subclass's initialization signature to record named checkpoint parameters, so this failed before the training loop. Both variants now use explicit `plans, configuration, fold, dataset_json, device` parameters. The regression reproduces the signature introspection rather than only checking inherited epoch counts.

For an already-running older Colab notebook, copy the contents of [repair_failed_init_colab.py](repair_failed_init_colab.py) into a new code cell immediately before section 5 and run it once. It patches only the known old trainer, updates its fingerprint, and selects a fresh experiment ID ending in `_initfix`; prior logs and experiment contracts remain untouched. The repair does not start training. Rerun section 4 to record the new contract and reuse existing preprocessing, then enable and run only the 5-epoch pilot. Do not rerun the old setup cells, which embed the incompatible trainer. After a later runtime reset, use the regenerated notebook and set `EXPERIMENT_ID` to the repaired ID before resuming that same experiment.

The repair records the previous results path in `repair_origin.json`; earlier audit/session metadata remains at that referenced path. No previous contract is rewritten and no checkpoint is deleted.

### Audit and packaging

Use an isolated Python environment with `requirements-audit.txt`. Training dependencies are not required for auditing, bundling, or synthetic tests. Overlay previews additionally need matplotlib.

```bash
python audit_handoff.py /path/to/handoff_k2 --out /outside/git/audit_report.json
python prepare_bundle.py /path/to/handoff_k2 --out /outside/git/e1-preparation
python preview_handoff.py /path/to/handoff_k2 --out /outside/git/label_review.png
python -m unittest discover -s tools/e1_training -v
```

Run the first three commands from this folder (or use their full paths); the test command is from the repository root.

`prepare_bundle.py` reads originals and never rewrites NIfTI headers or labels. It includes only audited train/validation data, dataset metadata, fixed split, and a checksum manifest. It refuses MRI archive destinations inside Git. Colab extraction rejects path traversal, links, duplicate entries, unexpected files, and mismatched hashes.

`handoff_contract.json` contains aggregate settings and data/split fingerprints, not scans or patient-level records. Full per-case audits, raw archives, and review images belong outside Git. New datasets require a new reviewed contract rather than silently reusing this E1 fingerprint.

## Notebook maintenance

`build_notebook.py` embeds reviewed helpers and the Linux dependency lock into the notebook. Regenerate with:

```bash
python tools/e1_training/build_notebook.py
```

Tests verify that the generated notebook matches its current sources, every code cell compiles, and training/acknowledgment flags default to False. `requirements-colab.lock.txt` was resolved for Linux x86-64, Python 3.11, CUDA 12.4; resolution is not evidence of a successful GPU installation or training run.

## Observed preparation evidence

On 2026-11-02, all 54 supplied image/label pairs passed the implemented technical checks: filenames, fixed split, finite data, permitted label IDs, paired shapes/affines, no current shear, and no identical image voxel arrays across subjects. All 54 cases had `unknown` header spatial units. Original files were kept byte-identical. Selected train-only voxel-plane overlays were rendered and inspected; anatomical/semantic approval remains unestablished.

Eighteen preparation checks passed for split errors, data/label defects, duplicate subjects, hold-out exclusion, archive round trips/traversal rejection, split/experiment overwrite protection, checkpoint gates, subprocess logging, trainer signature/epoch settings, notebook generation/defaults, a failed-init repair that preserves the previous experiment, successful-output gates before optional overnight release, and rendering a synthetic preview despite an invalid inherited matplotlib backend. The rendering check requires matplotlib. No nnU-Net training or CUDA execution has run on the local Mac. The completed user-side Colab training/validation and later local GU011 CPU inference are recorded separately in [EXP-003](../../knowledge/experiments/e1-preparation.md).

Sources: [nnU-Net 2.8.1 code](https://github.com/MIC-DKFZ/nnUNet/tree/v2.8.1), [training-length variants](https://github.com/MIC-DKFZ/nnUNet/blob/v2.8.1/nnunetv2/training/nnUNetTrainer/variants/training_length/nnUNetTrainer_Xepochs.py), [checkpoint defaults](https://github.com/MIC-DKFZ/nnUNet/blob/v2.8.1/nnunetv2/training/nnUNetTrainer/nnUNetTrainer.py), [Colab resource limits](https://research.google.com/colaboratory/faq.html).

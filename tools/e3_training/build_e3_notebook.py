"""Build the real Dataset003 E3 notebook from the E2 Colab workflow."""
import hashlib
import importlib.util
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent
E2 = ROOT.parent / "e2_training"


def build():
    spec = importlib.util.spec_from_file_location("e3_base_notebook", E2 / "build_e2_notebook.py")
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    notebook = module.build()
    sources = {name: p.read_text(encoding="utf-8") for name, p in module.EMBEDDED_FILES.items()
               if name not in ("trainers_e2.py", "e2_contract.json")}
    for name in ("e3_data.py", "e3_helpers.py", "trainers_e3.py", "e3_contract.json", "e3_plans.json"):
        sources[name] = (ROOT / name).read_text(encoding="utf-8")

    for cell in notebook["cells"]:
        s = cell["source"]
        if cell["cell_type"] == "markdown":
            continue
        s = s.replace("ACKNOWLEDGE_E2_DATA", "ACKNOWLEDGE_E3_DATA")
        s = s.replace("nnUNetTrainer_E2Smoke", "nnUNetTrainer_E3Smoke").replace("nnUNetTrainer_E2Preliminary", "nnUNetTrainer_E3Preliminary")
        s = s.replace("/content/e2_tools", "/content/e3_dataset003_tools")
        if "EXPERIMENT_ID = " in s:
            s = s.replace('ARCHIVE = Path("/content/drive/MyDrive/TMS_E2/handoff_k2_e2.zip")',
                          'ARCHIVE = Path("/content/drive/MyDrive/TMS_E3/handoff_e3.zip")\nARCHIVE_SHA256_FILE = Path(str(ARCHIVE) + ".sha256")')
            s = s.replace('"/content/drive/MyDrive/TMS_E2/runs"', '"/content/drive/MyDrive/TMS_E3/runs"')
            s = s.replace('"E2_L4_001"', '"E3_Dataset003_001"').replace('"/content/e2_work"', '"/content/e3_dataset003_work"')
            s = s.replace('"/content/e2-venv"', '"/content/e3-dataset003-venv"').replace('AUGMENTATION_WORKERS = 2', 'AUGMENTATION_WORKERS = 4')
            s += '\nassert CANONICALIZE_TO_RAS, "Keep E2-compatible RAS preparation enabled."\n'
        elif s.startswith('assert sys.platform'):
            s = s.replace('handoff_k2_e2.zip', 'handoff_e3.zip').replace('TMS_E2', 'TMS_E3')
            s += '\nassert ARCHIVE_SHA256_FILE.is_file(), "Wait for both ZIP and .sha256 to finish uploading."\n'
        elif s.startswith('# Gömülü, sürümlü yardımcılar.'):
            s = ("# Reviewed embedded sources; no archive file is executed.\n" + f"EMBEDDED = {sources!r}\n" + textwrap.dedent('''
                import hashlib
                for name, source in EMBEDDED.items():
                    (TOOLS / name).write_text(source, encoding="utf-8")
                sys.path.insert(0, str(TOOLS))
                for module_name in ("e3_data", "e3_helpers", "colab_helpers"):
                    sys.modules.pop(module_name, None)  # Reload this notebook's embedded helper versions.
                from e3_data import extract_handoff, install_split, require, sha256, verify_sidecar, DATASET, DATASET_ID
                from e3_helpers import training_command, validation_complete, subgroup_metrics
                from colab_helpers import record_run, run_logged
                CONTRACT = json.loads(EMBEDDED["e3_contract.json"])
                LOCK_SHA256 = sha256(TOOLS / "requirements-colab.lock.txt")
                TRAINER_SHA256 = sha256(TOOLS / "trainers_e3.py")
                CONTRACT_SHA256 = sha256(TOOLS / "e3_contract.json")
                require(LOCK_SHA256 == CONTRACT["lock_sha256"], "Pinned dependency lock changed.")
                verify_sidecar(ARCHIVE_SHA256_FILE, CONTRACT["archive_sha256"])
                print("Dataset003: 90 train entries / 67 people; 16 validation; ignore=6.")
                print("Uniform sampling: 23 IXI copies already implement weight 2. No extra sampler.")
            ''').lstrip())
        elif 'trainer_path = Path(' in s:
            start, end = s.index('trainer_path = Path('), s.index('ENV = os.environ.copy()')
            s = s[:start] + textwrap.dedent('''
                trainer_path = Path(subprocess.check_output([str(PYTHON), "-c",
                    "from pathlib import Path; import nnunetv2; print(Path(nnunetv2.__file__).parent / 'training/nnUNetTrainer/variants/training_length/nnUNetTrainer_E3.py')"], text=True).strip().splitlines()[-1])
                if trainer_path.exists():
                    require(trainer_path.read_text(encoding="utf-8") == EMBEDDED["trainers_e3.py"], "Installed trainer differs; use a fresh E3 environment.")
                else:
                    trainer_path.write_text(EMBEDDED["trainers_e3.py"], encoding="utf-8")
            ''').lstrip() + s[end:]
        elif s.startswith('layout = extract_handoff'):
            s = textwrap.dedent('''
                verify_sidecar(ARCHIVE_SHA256_FILE, CONTRACT["archive_sha256"])
                local_archive = WORK / CONTRACT["archive"]
                if not local_archive.is_file():
                    partial = local_archive.with_suffix(".partial")
                    print("Copying uploaded E3 archive to local Colab disk...", flush=True)
                    shutil.copyfile(ARCHIVE, partial)
                    require(sha256(partial) == CONTRACT["archive_sha256"], "Uploaded ZIP incomplete or different; checksum failed.")
                    partial.replace(local_archive)
                layout = extract_handoff(local_archive, DATA, CONTRACT["archive_sha256"])
                contract_path = TOOLS / "e3_contract.json"
                stamp = str(time.time_ns())
                run_logged([str(PYTHON), str(TOOLS / "e3_data.py"), "audit", str(layout["dataset"]), str(layout["splits"]),
                            str(contract_path), str(WORK / "audit_source.json")], RESULTS / "logs" / f"audit_source_{stamp}.log", ENV)
                source_report = json.loads((WORK / "audit_source.json").read_text())
                require(source_report["dataset_sha256"] == CONTRACT["source_dataset_sha256"], "Source E3 dataset fingerprint changed.")
                require(source_report["split_sha256"] == CONTRACT["split_sha256"], "Fixed E3 split changed.")
                shutil.copyfile(WORK / "audit_source.json", RESULTS / f"audit_source_{stamp}.json")
                if not (RAS_RAW / DATASET).exists():
                    run_logged([str(PYTHON), str(TOOLS / "e3_data.py"), "ras", str(layout["dataset"]), str(RAS_RAW),
                                str(WORK / "orientation_changes.json")], RESULTS / "logs" / f"ras_{stamp}.log", ENV)
                TRAIN_DATASET = RAS_RAW / DATASET
                shutil.copyfile(WORK / "orientation_changes.json", RESULTS / f"orientation_changes_{stamp}.json")
                run_logged([str(PYTHON), str(TOOLS / "e3_data.py"), "audit", str(TRAIN_DATASET), str(layout["splits"]),
                            str(contract_path), str(WORK / "audit_train.json")], RESULTS / "logs" / f"audit_train_{stamp}.log", ENV)
                report = json.loads((WORK / "audit_train.json").read_text())
                require(report["semantic_dataset_sha256"] == CONTRACT["ras_semantic_sha256"], "Prepared RAS values/grid differ from reviewed E3 data.")
                require(report["axis_codes"] == {"RAS": 106}, "Every E3 entry must be RAS.")
                shutil.copyfile(WORK / "audit_train.json", RESULTS / f"audit_train_{stamp}.json")
                print("All E3 entry/split/ignore/copy/grid checks passed:", report["axis_codes"])
            ''').lstrip()
        elif 'train_ids = CONTRACT["train"]' in s:
            s = s.replace('train_ids = CONTRACT["train"]', 'train_ids = CONTRACT["source_train"]')
            s = s.replace('"e2_label_review.png"', '"e3_label_review.png"').replace('"e2_helpers.py"', '"e3_data.py"')
        elif s.startswith('require(ACKNOWLEDGE_E3_DATA'):
            s = textwrap.dedent('''
                require(ACKNOWLEDGE_E3_DATA, "Review the source notes and preview, then set ACKNOWLEDGE_E3_DATA = True.")
                frozen_plan = TOOLS / "e3_plans.json"
                require(sha256(frozen_plan) == CONTRACT["plans_sha256"], "E3 plan hash changed.")
                marker = PREPROCESSED / ".e3_dataset003_input_sha256"
                preprocessing_key = hashlib.sha256((report["semantic_dataset_sha256"] + LOCK_SHA256 + sha256(frozen_plan)).encode()).hexdigest()
                plan_path = PREPROCESSED / DATASET / "nnUNetPlans.json"
                if marker.is_file():
                    require(marker.read_text().strip() == preprocessing_key and sha256(plan_path) == CONTRACT["plans_sha256"], "Cached preprocessing differs.")
                else:
                    run_logged([str(VENV / "bin/nnUNetv2_extract_fingerprint"), "-d", DATASET_ID, "--verify_dataset_integrity", "-np", "1"],
                               RESULTS / "logs" / f"fingerprint_{time.time_ns()}.log", ENV)
                    plan_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(TRAIN_DATASET / "dataset.json", plan_path.parent / "dataset.json")
                    shutil.copyfile(frozen_plan, plan_path)
                    run_logged([str(VENV / "bin/nnUNetv2_preprocess"), "-d", DATASET_ID, "-c", "3d_fullres", "-np", "1"],
                               RESULTS / "logs" / f"preprocess_{time.time_ns()}.log", ENV)
                    marker.write_text(preprocessing_key + "\\n")
                split_hash = install_split(layout["splits"], PREPROCESSED)
                require(split_hash == CONTRACT["split_sha256"], "Installed fixed split changed.")
                plans = json.loads(plan_path.read_text())
                print(json.dumps(plans["configurations"]["3d_fullres"], indent=2))
                contract = {"experiment": "E3", "dataset": DATASET, "initialization": "random_seed_42",
                    "archive_sha256": CONTRACT["archive_sha256"], "source_dataset_sha256": source_report["dataset_sha256"],
                    "dataset_sha256": report["semantic_dataset_sha256"], "fingerprint_kind": "decoded_values_and_grid",
                    "split_sha256": split_hash, "plans_sha256": sha256(plan_path),
                    "lock_sha256": LOCK_SHA256, "trainer_sha256": TRAINER_SHA256, "e3_contract_sha256": CONTRACT_SHA256,
                    "data_helpers_sha256": sha256(TOOLS / "e3_data.py"), "run_helpers_sha256": sha256(TOOLS / "e3_helpers.py"),
                    "base_helpers_sha256": sha256(TOOLS / "e2_helpers.py"), "sampling": "uniform_over_entries", "ignore_label": 6,
                    "train_entries": 90, "unique_train_subjects": 67, "validation_subjects": 16, "canonicalized_to_ras": True,
                    "configuration": "3d_fullres", "fold": 0, "nnunetv2": "2.8.1", "torch": "2.6.0+cu124", "seed": 42,
                    "augmentation_workers": AUGMENTATION_WORKERS, "torch_compile": False, "preliminary_only": True,
                    "test_accessed": False, "inference_outside_acquisition_mask_required": True}
                record_run(RESULTS / "experiment_contract.json", contract)
                for path in (plan_path, PREPROCESSED / DATASET / "dataset_fingerprint.json", TRAIN_DATASET / "dataset.json", layout["splits"],
                             layout["splits"].parent / "e3_manifest.csv", *[TOOLS / n for n in EMBEDDED]):
                    target = RESULTS / path.name
                    if target.exists():
                        require(sha256(target) == sha256(path), f"Saved evidence changed: {path.name}; use a new experiment ID.")
                    else:
                        shutil.copyfile(path, target)
            ''').lstrip()
        elif s.startswith('def train_stage'):
            anchor = '    record_run(RESULTS / "experiment_contract.json", contract)'
            require_count = s.count(anchor)
            if require_count != 1:raise ValueError("E2 stage changed; review pilot guard adapter.")
            s = s.replace(anchor, textwrap.indent(textwrap.dedent('''
                if trainer == "nnUNetTrainer_E3Preliminary" and not resume:
                    pilot = RESULTS / DATASET / "nnUNetTrainer_E3Smoke__nnUNetPlans__3d_fullres/fold_0"
                    require(validation_complete(pilot, CONTRACT["val"]) and (pilot / "checkpoint_final.pth").is_file(),
                            "Complete the E3 five-epoch pilot before the fresh 100-epoch run.")
                record_run(RESULTS / "experiment_contract.json", contract)
            ''').strip(), '    '))
        elif s.startswith('final_folder = train_stage'):
            s = textwrap.dedent('''
                final_folder = train_stage("nnUNetTrainer_E3Preliminary", RUN_100_EPOCH_PRELIMINARY, RESUME_PRELIMINARY)
                if final_folder is not None:
                    checkpoint = final_folder / "checkpoint_final.pth"
                    require(checkpoint.is_file() and checkpoint.stat().st_size > 0, "Final checkpoint missing; runtime left active.")
                    require(validation_complete(final_folder, CONTRACT["val"]), "Final validation identities/metrics incomplete; runtime left active.")
                    metrics = json.loads((final_folder / "validation/summary.json").read_text())
                    groups = subgroup_metrics(metrics, CONTRACT["val"])
                    (RESULTS / "validation_subgroups.json").write_text(json.dumps(groups, indent=2) + "\\n")
                    (RESULTS / "run_success.json").write_text(json.dumps({"experiment": "E3", "dataset": DATASET,
                        "checkpoint": str(checkpoint), "validation_cases": 16, "foreground_mean": metrics["foreground_mean"],
                        "runtime_release_requested": RELEASE_RUNTIME_WHEN_DONE}, indent=2) + "\\n")
                    print("Raw E3 validation saved:", metrics["foreground_mean"], groups, flush=True)
                    if RELEASE_RUNTIME_WHEN_DONE:
                        from google.colab import runtime
                        runtime.unassign()
            ''').lstrip()
        elif s.startswith('folder = RESULTS / DATASET'):
            s = s.replace('validation_complete(folder, 16)', 'validation_complete(folder, CONTRACT["val"])')
            s = s.replace('metrics = json.loads((folder / "validation/summary.json").read_text())',
                          'metrics = json.loads((folder / "validation/summary.json").read_text())\n    print(json.dumps(subgroup_metrics(metrics, CONTRACT["val"]), indent=2))')
        cell["source"] = s

    headings = {
        1: "Drive connection\n\nWait for both uploads, then mount the account containing `TMS_E3/handoff_e3.zip` and `.sha256`.",
        2: "Pinned training environment\n\nSame Python 3.11, nnU-Net 2.8.1 and torch 2.6.0+cu124 as E2. Embedded sources are reviewed code; archive contents are data only.",
        3: "Verify the actual E3 archive and prepare RAS\n\nChecks cover checksum, source-person split isolation, integer labels, aligned grids, all copy identities and exact border-connected ignore masks. The ZIP is copied locally before extraction. Every image and label is losslessly reoriented to RAS.",
        4: "Preprocess with the E2 architecture and fixed E3 split\n\nReview the preview and run `ACKNOWLEDGE_E3_DATA = True` first. The saved E2 plan is reused with only its dataset name changed to Dataset003: 1 mm, patch 160×128×112, batch 2. The provided 90/16 split is installed after preprocessing. Ignore 6 is excluded by standard nnU-Net loss; there are still six prediction channels including background.",
        5: "Required five-epoch GPU pilot\n\nSet `RUN_5_EPOCH_PILOT = True`, run the next cell and wait for all five epochs plus all 16 validation outputs. Check finite losses and a final checkpoint. This verifies the live CUDA/augmentation environment. Pilot weights do not initialize the main run.",
        6: "Pilot timing estimate\n\nThe median post-first-epoch time estimates the 100-epoch loop. Installation, preprocessing and final validation add time; GPU type and interruption overhead can change it.",
        7: "Main 100-epoch E3 run\n\nSet `RUN_5_EPOCH_PILOT = False`, `RUN_100_EPOCH_PRELIMINARY = True`, and run this cell after pilot completion. Optional `RELEASE_RUNTIME_WHEN_DONE = True` requests runtime release after verified success. A fresh run starts from random weights. For the same interrupted run, keep the experiment ID and set `RESUME_PRELIMINARY = True`.",
        8: "Final validation and delivery\n\nUse full-volume final Dice, not epoch pseudo-Dice. These are raw predictions against unchanged E2 validation labels. Compare the same TTA/preprocessing settings and report IXI/MultiAxial subgroups. Preserve the whole run folder, code, plans, logs and validation outputs. Future inference must clear boundary-connected zero-signal regions; that separate postprocessing is not applied to raw validation here. No independent face-surface accuracy is claimed.",
    }
    for cell in notebook["cells"]:
        if cell["cell_type"] != "markdown":continue
        s = cell["source"]
        if s.startswith('# E2'):
            s = """# E3 · Dataset003_E3Face / Colab training

**Use this revised Dataset003 notebook, not the superseded E2 sampling-only version.**

Data: `handoff_e3.zip`, 106 T1/label pairs: **90 training entries from 67 people + 16 validation people**.
23 IXI training cases have `w2` copies, so **standard uniform sampling already implements IXI weight 2**.
There is no additional weighted sampler. Training label **6 is ignore**, not another anatomical class.
Validation labels remain 0–5 and the same 16 E2 subjects. No test/calibration data is included.

Same E2 environment, architecture, seed 42, 100 epochs, batch 2, four augmentation workers,
checkpoint every epoch. E3 starts from random weights. **All training switches start off.**

1. Finish uploading ZIP + SHA to `My Drive/TMS_E3/`.
2. Upload this notebook to Colab, choose NVIDIA L4/A100 and run setup/audit/preview.
3. Acknowledge the data, preprocess, complete the five-epoch pilot, then enable the main run.
4. Results: `My Drive/TMS_E3/runs/E3_Dataset003_001/`.

This E3 changes both annotation-ignore policy and training-source exposure. Clinical or facial-surface
improvement has not been established. Colab setup/idle time also consumes GPU credits.
"""
        elif s.startswith('## '):
            section = int(s[3])
            s = f"## {section} · {headings[section]}\n"
        elif s.startswith('**Veri inceleme'):
            s = "**Data acknowledgement.** Training-only preview hides ignore voxels. References are CHARM-based with the existing E2 mapping/lesion rules, not independent manual truth. Inspect the notes and preview, then run `ACKNOWLEDGE_E3_DATA = True`. This does not constitute anatomical acceptance.\n"
        elif s.startswith('Kaynaklar:'):
            s = "Sources: E2 workflow `tools/e2_training`; Dataset003 handoff reviewed at upstream `bfbb98d`; generator `tools/e3_training/build_e3_notebook.py`.\n"
        cell["source"] = s
    notebook["metadata"]["colab"]["name"] = "E3_Dataset003_Colab.ipynb"
    notebook["metadata"].pop("e2_embedded_sha256", None)
    notebook["metadata"]["e3_embedded_sha256"] = {n: hashlib.sha256(s.encode()).hexdigest() for n, s in sources.items()}
    for i, cell in enumerate(notebook["cells"]):cell["id"] = f"e3-d003-{i:02d}"
    return notebook


if __name__ == "__main__":
    notebook = build()
    for c in notebook["cells"]:
        if c["cell_type"] == "code":compile(c["source"], c["id"], "exec")
    path = ROOT / "E3_Colab.ipynb"
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(path)

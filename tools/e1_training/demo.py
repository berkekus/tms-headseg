"""E1/E2 single-MRI inference and saved-result presentation. Never trains or rewrites inputs."""

import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import time
import zipfile

import nibabel as nib
import numpy as np

LABELS = {"background": 0, "skin": 1, "skull": 2, "csf": 3, "gray_matter": 4, "white_matter": 5}
TITLES = {1: "Deri", 2: "Kafatası", 3: "BOS / CSF", 4: "Gri cevher", 5: "Beyaz cevher"}
VALIDATION_CASES = ("GU011", "GU012", "GU018", "GU033", "GU041", "NC012", "NC019", "NC023", "NC029", "NYU005")
E2_VALIDATION_CASES = VALIDATION_CASES + ("IXI148", "IXI167", "IXI294", "IXI320", "IXI368", "IXI426")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_volume(path, labels=False):
    image = nib.load(str(path))
    require(image.ndim == 3 and 0 < np.prod(image.shape) <= 100_000_000, "Expected a bounded 3D NIfTI volume.")
    require(np.isfinite(image.affine).all() and abs(np.linalg.det(image.affine[:3, :3])) > 1e-10,
            "NIfTI affine is invalid.")
    array = image.get_fdata(dtype=np.float32, caching="unchanged")
    require(np.isfinite(array).all(), "Volume must contain finite values.")
    if labels:
        require(np.all(array == np.round(array)) and np.all((array >= 0) & (array <= 5)), "Expected integer labels 0–5.")
        array = array.astype(np.uint8)
        require(np.any(array), "Segmentation is empty.")
    else:
        require(np.ptp(array) > 0, "MRI is constant.")
    return image, array


def compare_volumes(mri, prediction, reference=None):
    paths = {"mri": Path(mri), "prediction": Path(prediction)}
    if reference is not None:
        paths["reference"] = Path(reference)
        require(paths["reference"].resolve() != paths["prediction"].resolve(), "Reference and prediction are the same file.")
    loaded = {role: read_volume(path, labels=role != "mri") for role, path in paths.items()}
    source = loaded["mri"][0]
    units = {role: image.header.get_xyzt_units()[0] for role, (image, _) in loaded.items()}
    known_units = set(units.values()) - {"unknown"}
    require(len(known_units) <= 1, "Known spatial units disagree; no automatic conversion is performed.")
    for image, _ in loaded.values():
        require(image.shape == source.shape and np.allclose(image.affine, source.affine, rtol=0, atol=1e-5),
                "Volume grid differs; no automatic resampling is performed.")
    warnings = ["Doku isimleri teslim paketindeki geçici eşlemeye dayanır; sonuçlar bağımsız test değildir."]
    if "unknown" in units.values():
        warnings.append("Kaynak fiziksel birimleri belirsiz. Bu karşılaştırma voksel düzlemindedir; mm doğruluğunu kanıtlamaz.")
    per_label = None
    macro = None
    if reference is not None:
        target, guess = loaded["reference"][1], loaded["prediction"][1]
        confusion = np.bincount((target.astype(np.int16) * 6 + guess).ravel(), minlength=36).reshape(6, 6)
        per_label = {}
        for label in range(1, 6):
            tp = int(confusion[label, label])
            n_ref, n_pred = int(confusion[label].sum()), int(confusion[:, label].sum())
            per_label[str(label)] = {"name": TITLES[label], "dice": 2 * tp / (n_ref + n_pred) if n_ref + n_pred else None,
                                     "reference_voxels": n_ref, "prediction_voxels": n_pred,
                                     "volume_bias_percent": 100 * (n_pred / n_ref - 1) if n_ref else None}
        valid = [m["dice"] for m in per_label.values() if m["dice"] is not None]
        macro = float(np.mean(valid)) if valid else None
    return {"case_mean_dice": macro, "per_label": per_label, "grid_shape": list(source.shape),
            "axis_codes": list(nib.aff2axcodes(source.affine)), "spatial_units": units, "warnings": warnings,
            "source_files": {role: {"path": str(path.resolve()), "sha256": sha256(path)} for role, path in paths.items()}}


def fresh_directory(path):
    path = Path(path).resolve()
    require(not path.exists(), f"Output already exists; choose a fresh directory: {path}")
    require(not any((parent / ".git").exists() for parent in (path, *path.parents)), "Keep MRI demo outputs outside Git.")
    path.mkdir(parents=True)
    return path


def render_comparison(mri, prediction, reference, destination, experiment="E1"):
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(Path(destination).parent / ".matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    _, image = read_volume(mri)
    _, guess = read_volume(prediction, labels=True)
    target = read_volume(reference, labels=True)[1] if reference else None
    focus = target if target is not None else guess
    coordinates = np.where(np.isin(focus, [3, 4, 5]))
    if not coordinates[0].size:
        coordinates = np.where(focus > 0)
    center = [int(np.median(c)) for c in coordinates]
    colors = [(0, 0, 0, 0), (.99, .65, .52, .5), (1, .9, .4, .55), (.25, .55, 1, .6),
              (.65, .25, .82, .6), (.93, .93, .93, .6)]
    foreground = image[image != 0]
    low, high = np.percentile(foreground, [.5, 99.5])
    columns = 4 if target is not None else 2
    fig, axes = plt.subplots(3, columns, figsize=(columns * 3.1, 9.2), squeeze=False)
    for row, (axis, title) in enumerate(((2, "Aksiyel"), (1, "Koronal"), (0, "Sagittal"))):
        plane = np.take(image, center[axis], axis).T
        masks = [None, np.take(guess, center[axis], axis).T]
        if target is not None:
            truth = np.take(target, center[axis], axis).T
            masks = [None, truth, masks[1], (truth != masks[1]).astype(np.uint8)]
        titles = ["MRI", "Model tahmini"] if target is None else ["MRI", "Referans etiket", "Model tahmini", "Etiket farkı"]
        for column, mask in enumerate(masks):
            ax = axes[row, column]
            ax.imshow(plane, cmap="gray", vmin=low, vmax=high, origin="lower", interpolation="nearest")
            if mask is not None:
                cmap = ListedColormap([(0, 0, 0, 0), (1, .45, 0, .85)]) if column == 3 else ListedColormap(colors)
                ax.imshow(mask, cmap=cmap, vmin=0, vmax=1 if column == 3 else 5, origin="lower", interpolation="nearest")
            ax.set_title(f"{title} · voksel {center[axis]}\n{titles[column]}", fontsize=10)
            ax.axis("off")
    fig.legend(handles=[Patch(color=colors[i][:3], label=TITLES[i]) for i in range(1, 6)], loc="lower center", ncol=5)
    fig.suptitle(f"{experiment} · MRI ve doku segmentasyonu\nAynı voksel ızgarası; sınırlı kesit incelemesi", fontsize=13)
    fig.tight_layout(rect=(0, .04, 1, .94))
    fig.savefig(destination, dpi=140)
    plt.close(fig)


def cohort_metrics(path, experiment="E1"):
    if path is None:
        return None
    data = json.loads(Path(path).read_text())
    rows = data["metric_per_case"]
    ids = [Path(row["reference_file"]).name.removesuffix(".nii.gz") for row in rows]
    expected = E2_VALIDATION_CASES if experiment == "E2" else VALIDATION_CASES
    require(len(ids) == len(expected) and set(ids) == set(expected), "Expected the fixed validation cases for this experiment.")
    means = {str(i): float(np.mean([row["metrics"][str(i)]["Dice"] for row in rows])) for i in range(1, 6)}
    require(all(np.isfinite(x) and 0 <= x <= 1 for x in means.values()), "Invalid validation Dice.")
    value = float(np.mean(list(means.values())))
    require(np.isclose(value, data["foreground_mean"]["Dice"], rtol=0, atol=1e-10), "Validation summary mean disagrees.")
    return {"validation_cases": len(ids), "mean_dice": value, "per_label_dice": means, "summary_sha256": sha256(path)}


def make_report(mri, prediction, output, reference=None, mode="recorded", timing=None, summary=None, model=None, experiment="E1"):
    require(experiment in ("E1", "E2"), "Choose E1 or E2.")
    require(mode in ("recorded", "inference"), "Unknown demo mode.")
    require(mode != "recorded" or timing is None, "Recorded predictions cannot claim live inference timing.")
    require(mode != "inference" or timing is not None, "New inference requires measured timing.")
    result = compare_volumes(mri, prediction, reference)
    result.update({"experiment": experiment, "mode": mode, "timing": timing, "cohort": cohort_metrics(summary, experiment), "model": model,
                   "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "held_out_test": False})
    folder = fresh_directory(output)
    render_comparison(mri, prediction, reference, folder / "comparison.png", experiment)
    from surface_view import make_view
    source, _ = read_volume(mri)
    _, labels = read_volume(prediction, labels=True)
    surface_html, surface_metadata = make_view(labels, source.affine, TITLES)
    result["surface_view"] = surface_metadata
    (folder / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    number = lambda value: "—" if value is None else f"{value:.4f}"
    rows = "".join(f"<tr><td>{html.escape(m['name'])}</td><td>{number(m['dice'])}</td></tr>" for m in (result["per_label"] or {}).values())
    cohort = result["cohort"]
    cohort_text = f"Eğitim sonunda kaydedilen {cohort['validation_cases']} vakalık doğrulama · ortalama Dice <strong>{cohort['mean_dice']:.4f}</strong>" if cohort else "Bu raporda kohort skoru sunulmuyor."
    score_table = (f"<table><tr><th>Doku</th><th>Bu vaka — Dice</th></tr>{rows}</table>"
                   if rows else "<p>Referans yok; bu MRI için Dice hesaplanmadı.</p>")
    difference_legend = "<p>Turuncu: referans ve tahminin farklı etiket verdiği vokseller.</p>" if reference else ""
    badge = "Kaydedilmiş tahmin · canlı çalıştırma değil" if mode == "recorded" else f"Yeni tahmin · {html.escape(timing['device'].upper())}"
    timing_text = "" if timing is None else (f"<p>Model yükleme: {timing['model_load_seconds']:.1f} sn · "
        f"Ön işleme + tahmin + NIfTI kaydı: {timing['prediction_seconds']:.1f} sn. "
        f"Ayna çevirmeli tahmin: {'açık' if timing['tta'] else 'kapalı'}.</p>")
    picture = base64.b64encode((folder / "comparison.png").read_bytes()).decode()
    notes = "".join(f"<li>{html.escape(note)}</li>" for note in result["warnings"])
    page = f'''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{experiment} · MRI doku segmentasyonu</title><style>
body{{font:17px/1.55 system-ui,sans-serif;color:#18232d;background:#f3f5f7;margin:0}}main{{max-width:1180px;margin:36px auto;padding:28px;background:white;border-radius:14px}}
h1{{font-size:32px;margin:10px 0}}.badge{{display:inline-block;background:#e7f0ff;color:#174b87;padding:6px 12px;border-radius:6px}}img{{width:100%;height:auto}}table{{border-collapse:collapse;min-width:320px}}td,th{{text-align:left;padding:9px 18px;border-bottom:1px solid #dde3e8}}small{{color:#53606c}}
</style><main><div class="badge">{badge}</div><h1>MRI → doku segmentasyonu</h1>
<p>{experiment} ön model · 100 epoch · fold 0</p><p>{cohort_text}</p>
<p>Seçilen vaka: <strong>{html.escape(Path(mri).name)}</strong> · vaka ortalama Dice: <strong>{number(result['case_mean_dice'])}</strong></p>
<p><small>Rapor kayıt zamanı: {result['created_utc']} (UTC). Bu dosyayı yeniden açmak yeni tahmin başlatmaz.</small></p>
{timing_text}{surface_html}{score_table}
<img alt="MRI, referans etiket ve model tahmininin eşleşen üç düzlemde karşılaştırması" src="data:image/png;base64,{picture}">
{difference_legend}<ul>{notes}</ul>
<small>Bu çıktı doku segmentasyonu ve gösterim yüzeyleridir; simülasyona hazır hacim mesh'i veya klinik doğrulama değildir. Kaydedilmiş rapor internet bağlantısı gerektirmez.</small></main></html>'''
    (folder / "report.html").write_text(page, encoding="utf-8")
    return folder / "report.html"


def validate_model(folder):
    folder = Path(folder)
    require((folder / "dataset.json").is_file(), "Model dataset.json is missing.")
    dataset = json.loads((folder / "dataset.json").read_text())
    require(dataset.get("labels") == LABELS, "Model labels differ from the project mapping.")
    require(dataset.get("channel_names") == {"0": "T1"} and dataset.get("file_ending") == ".nii.gz", "Expected a T1 model.")
    require((folder / "plans.json").is_file(), "Model plans.json is missing.")
    plans = json.loads((folder / "plans.json").read_text())
    require("3d_fullres" in plans.get("configurations", {}), "Model lacks 3d_fullres.")
    checkpoint = folder / "fold_0/checkpoint_final.pth"
    require(checkpoint.is_file() and zipfile.is_zipfile(checkpoint), "Final checkpoint is missing or incomplete.")
    with zipfile.ZipFile(checkpoint) as archive:
        require(archive.testzip() is None, "Final checkpoint integrity check failed.")
    return {"checkpoint_sha256": sha256(checkpoint), "plans_sha256": sha256(folder / "plans.json"),
            "dataset_sha256": sha256(folder / "dataset.json"), "fold": 0, "checkpoint": "checkpoint_final.pth"}


def register_trainer():
    import nnunetv2
    source = Path(__file__).with_name("trainers.py").read_text()
    target = Path(nnunetv2.__file__).parent / "training/nnUNetTrainer/variants/training_length/nnUNetTrainer_E1.py"
    if target.exists():
        require(target.read_text() == source, "Installed E1 trainer differs; use the reviewed isolated environment.")
    else:
        target.write_text(source)


def initialize_e2(predictor, model_folder):
    """Restore this E2 architecture from its plans without installing trainer code."""
    import torch
    import inspect
    from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
    from nnunetv2.utilities.plans_handling.plans_handler import PlansManager
    from nnunetv2.utilities.label_handling.label_handling import determine_num_input_channels

    folder = Path(model_folder)
    # NumPy 2 moved this callable; older checkpoints keep its NumPy 1 module path.
    with torch.serialization.safe_globals([np.core.multiarray.scalar,
                                           (np.core.multiarray.scalar, "numpy.core.multiarray.scalar"), np.dtype,
                                           type(np.dtype("float32")), type(np.dtype("float64"))]):
        checkpoint = torch.load(folder / "fold_0/checkpoint_final.pth", map_location="cpu", weights_only=True)
    require(checkpoint.get("trainer_name") == "nnUNetTrainer_E2Preliminary", "Expected the completed E2 model.")
    require(checkpoint.get("current_epoch") == 100, "Expected a completed 100-epoch E2 checkpoint.")
    plans_data = json.loads((folder / "plans.json").read_text())
    dataset = json.loads((folder / "dataset.json").read_text())
    require(checkpoint["init_args"]["plans"] == plans_data, "Checkpoint and model plans disagree.")
    require(checkpoint["init_args"]["configuration"] == "3d_fullres", "Expected E2 3d_fullres.")
    plans = PlansManager(plans_data)
    configuration = plans.get_configuration("3d_fullres")
    num_input = determine_num_input_channels(plans, configuration, dataset)
    num_output = plans.get_label_manager(dataset).num_segmentation_heads
    builder = nnUNetTrainer.build_network_architecture
    if "plans_manager" in inspect.signature(builder).parameters:
        network = builder(plans, configuration, num_input, num_output, enable_deep_supervision=False)
    else:
        network = builder(configuration.network_arch_class_name, configuration.network_arch_init_kwargs,
                          configuration.network_arch_init_kwargs_req_import,
                          num_input, num_output, enable_deep_supervision=False)
    weights = checkpoint["network_weights"]
    network.load_state_dict(weights, strict=True)
    predictor.manual_initialization(network, plans, configuration, [weights], dataset,
                                    checkpoint["trainer_name"], checkpoint.get("inference_allowed_mirroring_axes"))


def predict(model_folder, mri, output, reference=None, device="cpu", tta=True, summary=None, experiment="E1",
            head_crop=True):
    require(experiment in ("E1", "E2"), "Choose E1 or E2.")
    require(device in ("cpu", "cuda"), "Use cpu or cuda.")
    require(not Path(output).resolve().is_relative_to(Path(model_folder).resolve()),
            "Output must be outside the model directory.")
    read_volume(mri)
    model = validate_model(model_folder)
    model["experiment"] = experiment
    folder = fresh_directory(output)
    status = folder / "status.json"
    status.write_text(json.dumps({"state": "running", "mode": "inference"}) + "\n")
    try:
        import importlib.metadata
        import torch
        require(importlib.metadata.version("nnunetv2") == "2.8.1", "Use nnunetv2 2.8.1.")
        require(torch.__version__.split("+")[0] == "2.6.0", "Use torch 2.6.0.")
        require(device != "cuda" or torch.cuda.is_available(), "CUDA unavailable; select a GPU runtime.")
        os.environ["nnUNet_compile"] = "false"
        if experiment == "E1":
            register_trainer()
        from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
        sync = lambda: torch.cuda.synchronize() if device == "cuda" else None
        sync()
        start = time.perf_counter()
        predictor = nnUNetPredictor(tile_step_size=.5, use_gaussian=True, use_mirroring=tta,
                                   device=torch.device(device), perform_everything_on_device=device == "cuda",
                                   verbose=False, verbose_preprocessing=False, allow_tqdm=True)
        inference_mri = Path(mri).resolve()
        destination = folder / "prediction"
        crop = None
        if experiment == "E2":
            initialize_e2(predictor, model_folder)
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from headmodel.model_io import prepare, restore_labels
            from nnunet_prep.head_crop import crop_file, paste_file
            canonical = folder / "model_input_ras.nii.gz"
            prepare(mri, canonical, folder / "geometry.json")
            inference_mri = canonical
            if head_crop:  # E2 fails on neck and shoulders (EXP-008); the model sees the head only
                inference_mri = folder / "model_input_0000.nii.gz"
                crop = crop_file(canonical, inference_mri)
                (folder / "head_crop.json").write_text(json.dumps(crop, indent=2) + "\n")
            destination = folder / "prediction_model"
        else:
            predictor.initialize_from_trained_model_folder(str(model_folder), use_folds=(0,), checkpoint_name="checkpoint_final.pth")
            require(predictor.trainer_name == "nnUNetTrainer_E1Preliminary", "Expected the completed 100-epoch E1 model.")
        sync()
        loaded = time.perf_counter()
        predictor.predict_from_files([[str(inference_mri)]], [str(destination)], save_probabilities=False,
                                     overwrite=False, num_processes_preprocessing=1, num_processes_segmentation_export=1)
        if experiment == "E2":
            model_output = destination.with_suffix(".nii.gz")
            if crop is not None:
                model_output = folder / "prediction_model_full.nii.gz"
                paste_file(destination.with_suffix(".nii.gz"), canonical, crop, model_output)
            restore_labels(model_output, folder / "geometry.json", folder / "prediction.nii.gz")
            destination = folder / "prediction"
        sync()
        finished = time.perf_counter()
        timing = {"device": device, "model_load_seconds": loaded - start, "prediction_seconds": finished - loaded,
                  "tta": tta, "torch": torch.__version__, "nnunetv2": "2.8.1",
                  "hardware": torch.cuda.get_device_name(0) if device == "cuda" else __import__("platform").platform()}
        report = make_report(mri, destination.with_suffix(".nii.gz"), folder / "report", reference=reference,
                             mode="inference", timing=timing, summary=summary, model=model, experiment=experiment)
        status.write_text(json.dumps({"state": "completed", "report": str(report), "timing": timing}, indent=2) + "\n")
        return report
    except BaseException as error:
        status.write_text(json.dumps({"state": "failed", "error": str(error)}, indent=2) + "\n")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("report", "predict"):
        command = commands.add_parser(name)
        command.add_argument("--mri", type=Path, required=True)
        command.add_argument("--reference", type=Path)
        command.add_argument("--summary", type=Path)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--experiment", choices=("E1", "E2"), default="E1")
        if name == "report":
            command.add_argument("--recorded-prediction", type=Path, required=True)
        else:
            command.add_argument("--model", type=Path, required=True)
            command.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
            command.add_argument("--disable-tta", action="store_true")
            command.add_argument("--no-head-crop", action="store_true",
                                 help="E2: feed the whole field of view instead of the head crop")
    args = parser.parse_args()
    if args.command == "report":
        report = make_report(args.mri, args.recorded_prediction, args.out, reference=args.reference,
                             summary=args.summary, experiment=args.experiment)
    else:
        report = predict(args.model, args.mri, args.out, reference=args.reference, device=args.device,
                         tta=not args.disable_tta, summary=args.summary, experiment=args.experiment,
                         head_crop=not args.no_head_crop)
    print(f"Rapor hazır: {report}", flush=True)


if __name__ == "__main__":
    main()

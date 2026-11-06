"""Dataset003 E3 experiment guards; importing this never starts training."""

import json
import math
from pathlib import Path
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)




def training_command(executable, trainer, fold_directory, resume=False):
    require(trainer in ("nnUNetTrainer_E3Smoke", "nnUNetTrainer_E3Preliminary"), "Expected an E3 trainer.")
    folder = Path(fold_directory)
    if resume:
        checkpoint = next((folder / f"checkpoint_{name}.pth" for name in ("final", "latest", "best")
                           if (folder / f"checkpoint_{name}.pth").is_file()), None)
        require(checkpoint is not None, "No checkpoint to resume; refusing a silent fresh run.")
        require(not (folder / "validation/summary.json").exists(), "Validation already exists; inspect it before resuming.")
        require(zipfile.is_zipfile(checkpoint), "Checkpoint container is incomplete.")
        with zipfile.ZipFile(checkpoint) as archive:
            require(archive.testzip() is None, "Checkpoint CRC failed.")
    else:
        require(not folder.exists(), "Run folder exists; use resume or a new experiment ID.")
    return [str(executable), "3", "3d_fullres", "0", "-tr", trainer, "-device", "cuda"] + (["--c"] if resume else [])


def validation_rows(summary, expected_cases):
    rows = summary["metric_per_case"]
    cases = []
    for row in rows:
        names = [str(row[key]).replace("\\", "/").rsplit("/", 1)[-1] for key in ("prediction_file", "reference_file")]
        require(names[0] == names[1] and names[0].endswith(".nii.gz"), "Validation image identities differ.")
        cases.append(names[0][:-7])
    require(len(cases) == len(set(cases)) == len(expected_cases) and set(cases) == set(expected_cases),
            "Final validation must cover exactly the fixed E2/E3 validation subjects.")
    return list(zip(cases, rows))


def validation_complete(fold_directory, expected_cases):
    path = Path(fold_directory) / "validation/summary.json"
    if not path.is_file():
        return False
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
        validation_rows(summary, expected_cases)
        return math.isfinite(summary["foreground_mean"]["Dice"])
    except (ValueError, KeyError, TypeError):
        return False


def subgroup_metrics(summary, expected_cases):
    rows = validation_rows(summary, expected_cases)
    result = {}
    for group, is_ixi in (("IXI", True), ("MultiAxial", False)):
        selected = [row for case, row in rows if case.startswith("IXI") == is_ixi]
        require(selected, f"No {group} validation cases.")
        means = {}
        for label in range(1, 6):
            scores = [row["metrics"][str(label)]["Dice"] for row in selected]
            finite = [score for score in scores if isinstance(score, (float, int)) and math.isfinite(score)]
            require(finite, f"No finite {group} Dice for label {label}.")
            means[str(label)] = sum(finite) / len(finite)
        result[group] = {"cases": len(selected), "per_label_dice": means,
                         "mean_foreground_dice": sum(means.values()) / 5}
    return result




if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = subgroup_metrics(json.loads(args.summary.read_text()), json.loads(args.contract.read_text())["val"])
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))

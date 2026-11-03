"""Run once in an existing Colab cell after the E1 trainer's KeyError: 'args'."""

source = (TOOLS / "trainers.py").read_text()
require(source.count("def __init__(self, *args, **kwargs):") == 2
        and source.count("super().__init__(*args, **kwargs)") == 2,
        "This repair expects the original broken E1 trainer; it may already be repaired.")
require(trainer_path.read_text() == source, "Installed trainer differs from the embedded source; stop and inspect.")
repaired = source.replace("def __init__(self, *args, **kwargs):",
                          'def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):')
repaired = repaired.replace("super().__init__(*args, **kwargs)",
                            "super().__init__(plans, configuration, fold, dataset_json, device)")
old_results = RESULTS
repaired_id = EXPERIMENT_ID + "_initfix"
repaired_results = RESULTS_BASE / repaired_id
require(not repaired_results.exists(), "Repair output directory exists; do not overwrite it.")
repaired_results.mkdir(parents=True)
(TOOLS / "trainers.py").write_text(repaired)
trainer_path.write_text(repaired)
EMBEDDED["trainers.py"] = repaired
old_trainer_sha256 = TRAINER_SHA256
TRAINER_SHA256 = sha256(TOOLS / "trainers.py")
EXPERIMENT_ID, RESULTS = repaired_id, repaired_results
ENV.update({"nnUNet_results": str(RESULTS), "MPLBACKEND": "Agg"})
(RESULTS / "repair_origin.json").write_text(json.dumps({"reason": "E1 init signature KeyError: args",
    "previous_results": str(old_results), "previous_trainer_sha256": old_trainer_sha256,
    "trainer_sha256": TRAINER_SHA256}, indent=2))
RUN_5_EPOCH_PILOT, RUN_100_EPOCH_PRELIMINARY = False, False
RESUME_PILOT, RESUME_PRELIMINARY = False, False
print("Düzeltme uygulandı. Şimdi yalnız 4. bölümün hücresini yeniden çalıştır; kurulum hücrelerini çalıştırma.")
print("Yeni sonuç klasörü:", RESULTS)

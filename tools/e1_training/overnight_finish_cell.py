"""Append after the successful 100-epoch train_stage call in notebook section 7."""

if RUN_100_EPOCH_PRELIMINARY:
    from google.colab import runtime

    final_folder = RESULTS / DATASET / "nnUNetTrainer_E1Preliminary__nnUNetPlans__3d_fullres/fold_0"
    final_checkpoint = final_folder / "checkpoint_final.pth"
    assert final_checkpoint.is_file() and final_checkpoint.stat().st_size > 0, "Final checkpoint missing; runtime kept open."
    final_metrics = json.loads((final_folder / "validation/summary.json").read_text())
    assert len(final_metrics.get("metric_per_case", [])) == 10, "Ten-case validation incomplete; runtime kept open."
    (RESULTS / "overnight_success.json").write_text(json.dumps({
        "checkpoint": str(final_checkpoint), "validation_cases": 10,
        "foreground_mean": final_metrics["foreground_mean"], "shutdown_requested": True,
    }, indent=2) + "\n")
    print("Sonuçlar Drive'a kaydedildi:", final_metrics["foreground_mean"], flush=True)
    runtime.unassign()

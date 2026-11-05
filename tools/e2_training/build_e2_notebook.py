"""Generate the standalone E2 Colab notebook from the reviewed local files.

The flow follows the E1 notebook that trained E1_L4_001 (same pinned environment, seed, checkpoints
and 5/100-epoch trainers); the data checks and the dataset are E2's.
"""

import hashlib
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent
E1 = ROOT.parent / "e1_training"
EMBEDDED_FILES = {
    "e2_helpers.py": ROOT / "e2_helpers.py",
    "trainers_e2.py": ROOT / "trainers_e2.py",
    "e2_contract.json": ROOT / "e2_contract.json",
    "colab_helpers.py": E1 / "colab_helpers.py",
    "requirements-colab.lock.txt": E1 / "requirements-colab.lock.txt",
}


def build():
    cells = []
    contract = json.loads((ROOT / "e2_contract.json").read_text(encoding="utf-8"))
    sources = {name: path.read_text(encoding="utf-8") for name, path in EMBEDDED_FILES.items()}
    train_count, val_count = len(contract["train"]), len(contract["val"])

    def markdown(source):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": textwrap.dedent(source).strip() + "\n"})

    def code(source):
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                      "source": textwrap.dedent(source).strip() + "\n"})

    markdown(f"""
        # E2 · charm etiketleri / nnU-Net — Colab eğitimi

        **Veri:** K1'in `handoff_k2_e2.zip` paketi, `Dataset002_E2Charm`. Sabit **{train_count} eğitim + {val_count} doğrulama**
        (IXI {contract['sources']['IXI']['train']}/{contract['sources']['IXI']['val']},
        MultiAxial {contract['sources']['MultiAxial']['train']}/{contract['sources']['MultiAxial']['val']}), tek T1 kanalı,
        0–5 etiketleri, `3d_fullres`, yalnız **fold 0**. Test ve ayrılmış vakalar pakette yok; defter bunu da denetler.

        Ayarlar E1_L4_001 ile aynıdır: aynı sürümler, seed 42, her epoch checkpoint, 5 epoch kontrol ve 100 epoch ön model.
        Böylece E1 ile E2 arasındaki fark veriden gelir.

        1. Drive'da Berke'nin `TMS` klasöründeki `handoff_k2_e2.zip` dosyasına sağ tıkla → **Düzenle → Kısayol ekle** →
           **Drive'ım** altında `TMS_E2` adlı bir klasör oluşturup onu seç. (Kopyalamak da olur; kısayol kotanı harcamaz.)
        2. Colab'da bu defteri aç; çalışma zamanı olarak GPU seç (L4 önerilir; en az 12 GB VRAM).
        3. Hücreleri sırayla çalıştır. Önizlemeyi ve veri notlarını incelemeden eğitim açılmaz.

        **Varsayılan ayarlar eğitim başlatmaz.** GPU oturumu açık kaldığı sürece birim harcar.
        Sonuçlar/checkpoint'ler Drive'da, veri ve ön işleme Colab'ın yerel diskinde tutulur.
    """)
    code('''
        # Ayarlar. Devam ederken aynı deney kimliğini koru.
        from pathlib import Path
        import json, os, re, shutil, subprocess, sys, time

        ARCHIVE = Path("/content/drive/MyDrive/TMS_E2/handoff_k2_e2.zip")
        RESULTS_BASE = Path("/content/drive/MyDrive/TMS_E2/runs")
        EXPERIMENT_ID = "E2_L4_001"
        CANONICALIZE_TO_RAS = True  # IXI PSR saklanıyor, MultiAxial RAS; nnU-Net döndürmez. Açıklama 3. bölümde.
        ACKNOWLEDGE_E2_DATA = False  # Önizlemeyi ve veri notlarını inceledikten sonra True yap.
        RUN_5_EPOCH_PILOT = False
        RUN_100_EPOCH_PRELIMINARY = False
        RESUME_PILOT = False
        RESUME_PRELIMINARY = False
        RELEASE_RUNTIME_WHEN_DONE = False  # True: 100 epoch ve tam doğrulama bitince GPU oturumunu bırak.
        CU_PER_HOUR = 0.0  # Açık oturumun gösterilen birim/saat değeri; 0 = bilinmiyor.
        AVAILABLE_CU = 0.0
        AUGMENTATION_WORKERS = 2
        assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", EXPERIMENT_ID)
        assert 1 <= AUGMENTATION_WORKERS <= 4 and CU_PER_HOUR >= 0 and AVAILABLE_CU >= 0
        WORK = Path("/content/e2_work")
        TOOLS = Path("/content/e2_tools")
        VENV = Path("/content/e2-venv")
        PYTHON = VENV / "bin/python"
        DATA = WORK / "handoff"
        RAS_RAW = WORK / "raw_ras"
        PREPROCESSED = WORK / "nnUNet_preprocessed"
        RESULTS = RESULTS_BASE / EXPERIMENT_ID
    ''')
    markdown("""
        ## 1 · Drive bağlantısı
        Paylaşılan klasörler Colab'da `MyDrive` altında görünmez; bu yüzden 1. adımdaki kısayol gerekir.
    """)
    code('''
        assert sys.platform == "linux", "Bu defteri Google Colab'ın Linux oturumunda aç."
        from google.colab import drive
        drive.mount("/content/drive")
        assert os.path.ismount("/content/drive"), "Kalıcı Drive bağlantısı kurulamadı."
        assert ARCHIVE.is_file(), (f"Paket bulunamadı: {ARCHIVE}\\n"
            "Berke'nin TMS klasöründeki handoff_k2_e2.zip için Drive'ım/TMS_E2 altına kısayol ekle ya da yolu düzelt.")
        WORK.mkdir(parents=True, exist_ok=True)
        TOOLS.mkdir(parents=True, exist_ok=True)
        RESULTS.mkdir(parents=True, exist_ok=True)
        assert shutil.disk_usage("/content").free > 40 * 1024**3, "Kurulum, veri ve ön işleme için en az 40 GiB boş yer gerekli."
    ''')
    markdown("""
        ## 2 · Ayrı, sürümü sabitlenmiş eğitim ortamı
        E1 ile aynı kilitli bağımlılıklar (Python 3.11, nnU-Net 2.8.1, PyTorch 2.6.0 + CUDA 12.4).
        Gömülü yardımcılar proje deposundan üretilmiştir; ZIP içindeki hiçbir dosya kod olarak çalıştırılmaz.
    """)
    code("# Gömülü, sürümlü yardımcılar.\n"
         "EMBEDDED = " + repr(sources) + "\n"
         "import hashlib\n"
         "for name, source in EMBEDDED.items():\n"
         "    (TOOLS / name).write_text(source)\n"
         "sys.path.insert(0, str(TOOLS))\n"
         "from e2_helpers import (extract_handoff, install_split, training_command, validation_complete, require, sha256, DATASET, DATASET_ID)\n"
         "from colab_helpers import record_run, run_logged\n"
         "CONTRACT = json.loads(EMBEDDED['e2_contract.json'])\n"
         "LOCK_SHA256 = sha256(TOOLS / 'requirements-colab.lock.txt')\n"
         "TRAINER_SHA256 = sha256(TOOLS / 'trainers_e2.py')\n"
         "print(f\"Sözleşme: {len(CONTRACT['train'])} eğitim / {len(CONTRACT['val'])} doğrulama; arşiv {CONTRACT['archive_sha256'][:12]}…\")")
    code('''
        subprocess.run([sys.executable, "-m", "pip", "install", "uv==0.11.8"], check=True)
        uv = [sys.executable, "-m", "uv"]
        if not PYTHON.is_file():
            subprocess.run(uv + ["venv", str(VENV), "--python", "3.11"], check=True)
        subprocess.run(uv + ["pip", "install", "--python", str(PYTHON), "--torch-backend", "cu124",
                             "-r", str(TOOLS / "requirements-colab.lock.txt")], check=True)
        subprocess.run(uv + ["pip", "check", "--python", str(PYTHON)], check=True)
        trainer_path = Path(subprocess.check_output([str(PYTHON), "-c",
            "from pathlib import Path; import nnunetv2; print(Path(nnunetv2.__file__).parent / 'training/nnUNetTrainer/variants/training_length/nnUNetTrainer_E2.py')"], text=True).strip().splitlines()[-1])
        if trainer_path.exists():
            require(trainer_path.read_text() == EMBEDDED["trainers_e2.py"], "Eğitici kodu değişmiş; ortamı ve deney kimliğini kontrol et.")
        else:
            trainer_path.write_text(EMBEDDED["trainers_e2.py"])
        ENV = os.environ.copy()
        ENV.update({"nnUNet_raw": str(RAS_RAW if CANONICALIZE_TO_RAS else DATA), "nnUNet_preprocessed": str(PREPROCESSED),
                    "nnUNet_results": str(RESULTS), "nnUNet_n_proc_DA": str(AUGMENTATION_WORKERS),
                    "nnUNet_compile": "false", "PYTHONHASHSEED": "42", "MPLBACKEND": "Agg",
                    "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        require(subprocess.check_output([str(PYTHON), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], text=True).strip() == "3.11", "Python sürümü 3.11 olmalı.")
        gpu = json.loads(subprocess.check_output([str(PYTHON), "-c",
            "import sys,json; sys.path.insert(0, '/content/e2_tools'); from colab_helpers import gpu_probe; print(json.dumps(gpu_probe()))"], env=ENV, text=True))
        print(json.dumps(gpu, indent=2))
        session_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        (RESULTS / f"session_{session_id}.json").write_text(json.dumps({**gpu, "cu_per_hour": CU_PER_HOUR, "available_cu": AVAILABLE_CU}, indent=2))
        (RESULTS / f"environment_{session_id}.txt").write_text(subprocess.check_output(uv + ["pip", "freeze", "--python", str(PYTHON)], text=True))
    ''')
    markdown(f"""
        ## 3 · Paketi doğrula ve tek eksen sırasına getir
        Arşivin SHA-256 değeri K1'in yayımladığı değerle aynı olmalı. Sonra bölme K1'in atamasından hesaplanan
        {train_count}/{val_count} listesiyle, dosya adları, ızgaralar ve 0–5 etiketleri tek tek denetlenir.

        **Eksen sırası:** IXI görüntüleri PSR (sagital), MultiAxial görüntüleri RAS saklanıyor. nnU-Net görüntüyü
        döndürmez, yani ağ iki farklı dizi düzeni görür. `CANONICALIZE_TO_RAS = True` her vakayı RAS sırasına
        getirir: yalnız eksen değiştirme/çevirme, interpolasyon yok, her vokselin dünya konumu aynı kalır
        (K3 koordinat sözleşmesi, D-004). Bu modelle çıkarım yapılırken PSR girdiler de aynı şekilde RAS'a çevrilmelidir
        (`tools/headmodel/model_io.py prepare/restore`).
    """)
    code('''
        layout = extract_handoff(ARCHIVE, DATA, CONTRACT["archive_sha256"])
        contract_path = TOOLS / "e2_contract.json"
        stamp = str(time.time_ns())
        run_logged([str(PYTHON), str(TOOLS / "e2_helpers.py"), "audit", str(layout["dataset"]), str(layout["splits"]),
                    str(contract_path), str(WORK / "audit_source.json")], RESULTS / "logs" / f"audit_source_{stamp}.log", ENV)
        source_report = json.loads((WORK / "audit_source.json").read_text())
        shutil.copyfile(WORK / "audit_source.json", RESULTS / f"audit_source_{stamp}.json")
        for warning in source_report["warnings"]:
            print("UYARI:", warning)
        if CANONICALIZE_TO_RAS:
            if not (RAS_RAW / DATASET).exists():
                run_logged([str(PYTHON), str(TOOLS / "e2_helpers.py"), "ras", str(layout["dataset"]), str(RAS_RAW),
                            str(WORK / "orientation_changes.json")], RESULTS / "logs" / f"ras_{stamp}.log", ENV)
            shutil.copyfile(WORK / "orientation_changes.json", RESULTS / f"orientation_changes_{stamp}.json")
            TRAIN_DATASET = RAS_RAW / DATASET
        else:
            TRAIN_DATASET = layout["dataset"]
        run_logged([str(PYTHON), str(TOOLS / "e2_helpers.py"), "audit", str(TRAIN_DATASET), str(layout["splits"]),
                    str(contract_path), str(WORK / "audit_train.json")], RESULTS / "logs" / f"audit_train_{stamp}.log", ENV)
        report = json.loads((WORK / "audit_train.json").read_text())
        shutil.copyfile(WORK / "audit_train.json", RESULTS / f"audit_train_{stamp}.json")
        require(report["train_count"] == len(CONTRACT["train"]) and report["validation_count"] == len(CONTRACT["val"]), "Bölme değişmiş.")
        require(not CANONICALIZE_TO_RAS or report["axis_codes"] == {"RAS": len(CONTRACT["train"]) + len(CONTRACT["val"])},
                "RAS kopyasında RAS olmayan vaka kaldı.")
        print("Eğitimde kullanılacak eksen sıraları:", report["axis_codes"])
    ''')
    code('''
        # Yalnız eğitim vakaları; voksel düzleminde önizleme. Hepsi aynı yönde görünmeli.
        train_ids = CONTRACT["train"]
        shown = [c for c in train_ids if c.startswith("IXI")][:2] + [c for c in train_ids if not c.startswith("IXI")][:2]
        preview = RESULTS / "e2_label_review.png"
        subprocess.run([str(PYTHON), str(TOOLS / "e2_helpers.py"), "preview", str(TRAIN_DATASET), str(preview), *shown], check=True, env=ENV)
        from IPython.display import display, Image
        display(Image(filename=str(preview)))
    ''')
    markdown(f"""
        **Veri inceleme noktası.** Etiketler charm 4.6.0 çıktısıdır (elle çizilmiş referans değil); kan BOS'a,
        sıfır dolgu üzerindeki etiketler arka plana çevrildi; MultiAxial charm koşuları yalnız T1 ile yapıldı
        (kafatası T1+T2'ye göre zayıf olabilir); 19 MultiAxial vakada lezyon kuralı uygulandı (EXP-002 notu).
        Doğrulama Dice'ı charm etiketlerine göre hesaplanır; E1'in MultiAxial referansına göre Dice'ı ile doğrudan
        karşılaştırılamaz.

        Önizlemeyi ve bu notları inceleyip devam etmeyi seçersen ilk hücrede `ACKNOWLEDGE_E2_DATA = True` yap
        (ya da aşağıya `ACKNOWLEDGE_E2_DATA = True` yazıp çalıştır). Bu, anatomik onay anlamına gelmez.
    """)
    markdown("""
        ## 4 · Ön işleme ve sabit fold 0
        K1 masaüstündeki plan: 1 mm, patch 160×128×112, batch 2 (RAS'a çevirmeden önceki eksen sırasıyla).
        Burada bu ortamın ürettiği plan gösterilir. Colab yeniden başlarsa yerel ön işleme yeniden yapılır;
        Drive'daki ağırlıklar silinmez.
    """)
    code('''
        require(ACKNOWLEDGE_E2_DATA, "Önizlemeyi ve veri notlarını incele; sonra ACKNOWLEDGE_E2_DATA = True yap.")
        marker = PREPROCESSED / ".e2_input_sha256"
        preprocessing_key = hashlib.sha256((report["dataset_sha256"] + LOCK_SHA256 + str(CANONICALIZE_TO_RAS)).encode()).hexdigest()
        if marker.is_file():
            require(marker.read_text().strip() == preprocessing_key, "Ön işleme başka veri/sürüme ait; yeni yerel klasör kullan.")
        else:
            run_logged([str(VENV / "bin/nnUNetv2_plan_and_preprocess"), "-d", DATASET_ID, "-c", "3d_fullres",
                        "--verify_dataset_integrity", "-np", "1"], RESULTS / "logs" / f"preprocess_{time.time_ns()}.log", ENV)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(preprocessing_key + "\\n")
        split_hash = install_split(layout["splits"], PREPROCESSED)
        require(split_hash == report["split_sha256"], "Sabit bölme kopyası değişmiş.")
        plan_path = PREPROCESSED / DATASET / "nnUNetPlans.json"
        plans = json.loads(plan_path.read_text())
        require("3d_fullres" in plans["configurations"], "3d_fullres planı oluşmadı.")
        print(json.dumps(plans["configurations"]["3d_fullres"], indent=2))
        contract = {"experiment": "E2", "archive_sha256": CONTRACT["archive_sha256"],
                    "source_dataset_sha256": source_report["dataset_sha256"], "dataset_sha256": report["dataset_sha256"],
                    "canonicalized_to_ras": CANONICALIZE_TO_RAS, "split_sha256": split_hash, "plans_sha256": sha256(plan_path),
                    "lock_sha256": LOCK_SHA256, "trainer_sha256": TRAINER_SHA256, "configuration": "3d_fullres", "fold": 0,
                    "nnunetv2": "2.8.1", "torch": "2.6.0+cu124", "seed": 42, "augmentation_workers": AUGMENTATION_WORKERS,
                    "torch_compile": False, "preliminary_only": True, "test_accessed": False}
        record_run(RESULTS / "experiment_contract.json", contract)
        for path in (plan_path, PREPROCESSED / DATASET / "dataset_fingerprint.json", layout["splits"]):
            target = RESULTS / path.name
            if target.exists():
                require(sha256(target) == sha256(path), f"Kayıtlı {path.name} değişmiş; yeni deney kimliği kullan.")
            else:
                shutil.copyfile(path, target)
    ''')
    markdown("""
        ## 5 · İsteğe bağlı 5 epoch kontrol
        Mert'in notu: bu adım atlanabilir. Açarsan (`RUN_5_EPOCH_PILOT = True`) süreyi ölçer ve 6. bölümde 100 epoch tahmini verir.
        Her epoch'ta checkpoint alınır. Devam için aynı deney kimliği ve `RESUME_PILOT = True`.
    """)
    code('''
        def train_stage(trainer, enabled, resume):
            if not enabled:
                print(f"{trainer}: kapalı; eğitim başlatılmadı.")
                return None
            require(ACKNOWLEDGE_E2_DATA and (RESULTS / "experiment_contract.json").is_file(), "Veri/ön işleme adımları tamamlanmalı.")
            require(os.path.ismount("/content/drive"), "Checkpoint hedefi kalıcı Drive bağlantısında olmalı.")
            require(ENV["nnUNet_results"] == str(RESULTS) and ENV["nnUNet_n_proc_DA"] == str(AUGMENTATION_WORKERS),
                    "Ayarlar değişti; ortam/veri/ön işleme hücrelerini yeniden çalıştır.")
            record_run(RESULTS / "experiment_contract.json", contract)
            folder = RESULTS / DATASET / f"{trainer}__nnUNetPlans__3d_fullres" / "fold_0"
            command = training_command(VENV / "bin/nnUNetv2_train", trainer, folder, resume)
            log = RESULTS / "logs" / f"{trainer}_{time.time_ns()}.log"
            result = run_logged(command, log, ENV)
            (log.with_suffix(".json")).write_text(json.dumps(result, indent=2))
            print(f"Bitti: {result['elapsed_seconds']/60:.1f} dakika. Log: {log}")
            return folder
        train_stage("nnUNetTrainer_E2Smoke", RUN_5_EPOCH_PILOT, RESUME_PILOT)
    ''')
    markdown("""
        ## 6 · Süre/birim tahmini (5 epoch çalıştıysa)
        İlk epoch dışarıda bırakılıp sonraki epoch sürelerinin medyanı kullanılır. Kurulum, ön işleme ve son doğrulama dahil değildir.
    """)
    code('''
        logs = sorted((RESULTS / "logs").glob("nnUNetTrainer_E2Smoke_*.log"))
        epoch_seconds = []
        for log in logs:
            epoch_seconds.extend(float(value) for value in re.findall(r"Epoch time:\\s*([0-9.]+)", log.read_text()))
        if len(epoch_seconds) >= 2:
            import statistics
            hours = statistics.median(epoch_seconds[1:]) * 100 / 3600
            print(f"100 epoch eğitim döngüsü yaklaşık {hours:.2f} saat; ek aşamalar dahil değil.")
            if CU_PER_HOUR > 0:
                print(f"Girilen oranla yaklaşık {hours * CU_PER_HOUR:.1f} işlem birimi + ek aşamalar.")
        else:
            print("Tahmin için 5 epoch kontrolünden en az iki epoch süresi gerekli (adım atlandıysa normal).")
    ''')
    markdown("""
        ## 7 · 100 epoch E2 ön modeli — ana eğitim
        `RUN_100_EPOCH_PRELIMINARY = True` yap (ya da aşağıdaki hücrenin başına yaz) ve çalıştır. Sıfırdan başlar;
        5 epoch ağırlıklarını kullanmaz. Oturum koparsa aynı deney kimliğiyle `RESUME_PRELIMINARY = True` ver;
        son checkpoint'ten devam eder. `RELEASE_RUNTIME_WHEN_DONE = True` ise eğitim ve tam doğrulama bitince
        sonuç Drive'a yazılır ve GPU oturumu bırakılır.
    """)
    code(f'''
        final_folder = train_stage("nnUNetTrainer_E2Preliminary", RUN_100_EPOCH_PRELIMINARY, RESUME_PRELIMINARY)
        if final_folder is not None and RELEASE_RUNTIME_WHEN_DONE:
            checkpoint = final_folder / "checkpoint_final.pth"
            require(checkpoint.is_file() and checkpoint.stat().st_size > 0, "Son checkpoint yok; oturum açık bırakıldı.")
            require(validation_complete(final_folder, {val_count}), "Doğrulama {val_count} vakayı kapsamıyor; oturum açık bırakıldı.")
            metrics = json.loads((final_folder / "validation/summary.json").read_text())
            (RESULTS / "run_success.json").write_text(json.dumps({{"checkpoint": str(checkpoint), "validation_cases": {val_count},
                "foreground_mean": metrics["foreground_mean"], "runtime_release_requested": True}}, indent=2) + "\\n")
            print("Sonuçlar Drive'a kaydedildi:", metrics["foreground_mean"], flush=True)
            from google.colab import runtime
            runtime.unassign()
    ''')
    markdown(f"""
        ## 8 · Doğrulama çıktıları
        Epoch logundaki pseudo-Dice ile {val_count} doğrulama vakasının son segmentasyon Dice'ı farklıdır.
        Bu Dice charm etiketlerine göredir. Test kümesi bu defterde açılmaz.
    """)
    code(f'''
        folder = RESULTS / DATASET / "nnUNetTrainer_E2Preliminary__nnUNetPlans__3d_fullres/fold_0"
        if validation_complete(folder, {val_count}):
            metrics = json.loads((folder / "validation/summary.json").read_text())
            print("Yalnız {val_count} doğrulama vakası — ön sonuç (charm etiketlerine göre):")
            print(json.dumps({{"foreground_mean": metrics.get("foreground_mean"), "per_label_mean": metrics.get("mean")}}, indent=2))
        else:
            print("Tamamlanmış 100 epoch doğrulama özeti henüz yok.")
        print("Ara verirken checkpoint/logların Drive'da olduğunu kontrol et; kullanılmayan GPU oturumunu kapat.")
    ''')
    markdown("""
        Kaynaklar: [nnU-Net v2.8.1](https://github.com/MIC-DKFZ/nnUNet/tree/v2.8.1) ·
        E2 veri hazırlığı `tools/nnunet_prep/prepare_e2.py` · E1 akışı `tools/e1_training/build_notebook.py` ·
        bu defterin üreticisi `tools/e2_training/build_e2_notebook.py`.
    """)
    for index, cell in enumerate(cells):
        cell["id"] = f"e2-{index:02d}"
    return {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"colab": {"name": "E2_Colab.ipynb", "provenance": []},
                         "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}, "accelerator": "GPU",
                         "e2_embedded_sha256": {name: hashlib.sha256(text.encode()).hexdigest() for name, text in sources.items()}},
            "cells": cells}


if __name__ == "__main__":
    path = ROOT / "E2_Colab.ipynb"
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(path)

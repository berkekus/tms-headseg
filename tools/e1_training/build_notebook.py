"""Generate a standalone Colab notebook from the reviewed local helpers."""

import hashlib
import json
from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parent
HELPERS = ("audit_handoff.py", "colab_helpers.py", "preview_handoff.py", "trainers.py", "requirements-colab.lock.txt")


def build():
    cells = []
    handoff_contract = json.loads((ROOT / "handoff_contract.json").read_text())

    def markdown(source):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": textwrap.dedent(source).strip() + "\n"})

    def code(source):
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                      "source": textwrap.dedent(source).strip() + "\n"})

    markdown("""
        # E1 · MultiAxial / nnU-Net — Colab hazırlığı

        **Kaynak:** `handoff_k2/K2_BASLA.md`, `hazirlik_notlari_en.md`, `splits_final.json`.
        Sabit **44 eğitim + 10 doğrulama**, tek T1 kanalı, 0–5 etiketleri, `3d_fullres`, yalnız **fold 0**.
        Test verisi kullanılmaz. Bu defter CHARM çalıştırmaz, hazır ağ ağırlığı indirmez.

        1. Hazırlanan `handoff_k2_e1.zip` dosyasını kendi Drive'ında `TMS_E1/` klasörüne yükle.
        2. Colab'da bu defteri aç; GPU seç (en az 12 GB VRAM; tamamlanan deneyde L4 kullanıldı).
        3. Hücreleri sırayla çalıştır. Önizlemeleri ve veri notlarını incelemeden eğitim açılmaz.
        4. Önce 5 epoch kontrol; 100 epoch ön model ayrı, açık bir seçimdir.

        **Varsayılan ayarlar eğitim başlatmaz.** GPU oturumunu açık bırakmak yine de birim tüketebilir.
        Sonuçlar/checkpoint'ler Drive'da, eğitim verisi ve ön işleme Colab'ın yerel diskinde tutulur.
        Google hesabına giriş ve Drive erişim onayı sana aittir.
    """)
    code('''
        # Change paths if you uploaded the prepared archive elsewhere.
        from pathlib import Path
        import json, os, re, shutil, subprocess, sys, time

        ARCHIVE = Path("/content/drive/MyDrive/TMS_E1/handoff_k2_e1.zip")
        RESULTS_BASE = Path("/content/drive/MyDrive/TMS_E1/runs")
        EXPERIMENT_ID = "E1_baseline_001"  # Keep unchanged when resuming the SAME experiment.
        ACKNOWLEDGE_PROVISIONAL_DATA = False  # Review labels/units/NYU geometry caveats first.
        RUN_5_EPOCH_PILOT = False
        RUN_100_EPOCH_PRELIMINARY = False  # Enable only after reviewing pilot and budget.
        RESUME_PILOT = False
        RESUME_PRELIMINARY = False
        CU_PER_HOUR = 0.0  # Enter this GPU session's actual displayed rate; 0 means unknown.
        AVAILABLE_CU = 0.0  # Current ACCOUNT balance, not a sum of notebooks' balances.
        AUGMENTATION_WORKERS = 2
        assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", EXPERIMENT_ID)
        assert 1 <= AUGMENTATION_WORKERS <= 4
        assert CU_PER_HOUR >= 0 and AVAILABLE_CU >= 0
        WORK = Path("/content/e1_work")
        TOOLS = Path("/content/e1_tools")
        VENV = Path("/content/e1-venv")
        PYTHON = VENV / "bin/python"
        DATA = WORK / "handoff"
        PREPROCESSED = WORK / "nnUNet_preprocessed"
        RESULTS = RESULTS_BASE / EXPERIMENT_ID
    ''')
    code("# Fingerprints of the locally audited handoff; do not change for a resumed experiment.\n"
         f"EXPECTED_DATASET_SHA256 = {handoff_contract['dataset_sha256']!r}\n"
         f"EXPECTED_SPLIT_SHA256 = {handoff_contract['split_sha256']!r}")
    markdown("""
        ## 1 · Drive bağlantısı
        Yalnız kendi erişimin olan arşivi kullan. Drive'daki orijinal MRI dosyaları değiştirilmez.
    """)
    code('''
        assert sys.platform == "linux", "Bu defteri Google Colab'ın Linux oturumunda aç."
        from google.colab import drive
        drive.mount("/content/drive")
        assert os.path.ismount("/content/drive"), "Kalıcı Drive bağlantısı kurulamadı."
        assert ARCHIVE.is_file(), f"Hazırlanan ZIP bulunamadı: {ARCHIVE}"
        WORK.mkdir(parents=True, exist_ok=True)
        TOOLS.mkdir(parents=True, exist_ok=True)
        RESULTS.mkdir(parents=True, exist_ok=True)
        assert shutil.disk_usage("/content").free > 20 * 1024**3, "Kurulum/veri için en az 20 GiB boş yer ayır."
    ''')
    markdown("""
        ## 2 · Ayrı, sürümü sabitlenmiş eğitim ortamı
        Colab çekirdeğinin PyTorch'unu değiştirmek yerine Python 3.11 sanal ortamı kullanılır.
        Linux/CUDA bağımlılık çözümlemesi hazırlanmıştır; gerçek GPU çalışması aşağıda kontrol edilir.
        İlk kurulum birkaç GB indirebilir. Gömülü yardımcılar bu proje kaynaklarından üretilmiştir;
        ZIP'teki metinlerden veya başka depolardan kod çalıştırılmaz.
    """)
    sources = {name: (ROOT / name).read_text() for name in HELPERS}
    code("# Embedded, versioned helpers; no private repository authentication needed.\n"
         "EMBEDDED = " + repr(sources) + "\n"
         "import hashlib\n"
         "for name, source in EMBEDDED.items():\n"
         "    (TOOLS / name).write_text(source)\n"
         "sys.path.insert(0, str(TOOLS))\n"
         "from colab_helpers import (extract_handoff, verify_manifest, install_split, training_command, record_run, run_logged, require, sha256, DATASET)\n"
         "LOCK_SHA256 = sha256(TOOLS / 'requirements-colab.lock.txt')\n"
         "TRAINER_SHA256 = sha256(TOOLS / 'trainers.py')")
    code('''
        subprocess.run([sys.executable, "-m", "pip", "install", "uv==0.11.8"], check=True)
        uv = [sys.executable, "-m", "uv"]
        if not PYTHON.is_file():
            subprocess.run(uv + ["venv", str(VENV), "--python", "3.11"], check=True)
        subprocess.run(uv + ["pip", "install", "--python", str(PYTHON), "--torch-backend", "cu124",
                             "-r", str(TOOLS / "requirements-colab.lock.txt")], check=True)
        subprocess.run(uv + ["pip", "check", "--python", str(PYTHON)], check=True)
        trainer_path = Path(subprocess.check_output([str(PYTHON), "-c",
            "from pathlib import Path; import nnunetv2; print(Path(nnunetv2.__file__).parent / 'training/nnUNetTrainer/variants/training_length/nnUNetTrainer_E1.py')"], text=True).strip().splitlines()[-1])
        if trainer_path.exists():
            require(trainer_path.read_text() == EMBEDDED["trainers.py"], "Eğitici kodu değişmiş; ortamı ve deney kimliğini kontrol et.")
        else:
            trainer_path.write_text(EMBEDDED["trainers.py"])
        # Keep all nnU-Net commands in the same external Python environment.
        ENV = os.environ.copy()
        ENV.update({"nnUNet_raw": str(DATA / "nnUNet_raw"), "nnUNet_preprocessed": str(PREPROCESSED),
                    "nnUNet_results": str(RESULTS), "nnUNet_n_proc_DA": str(AUGMENTATION_WORKERS),
                    "nnUNet_compile": "false", "PYTHONHASHSEED": "42",
                    "MPLBACKEND": "Agg",  # External venv cannot use Colab's inline backend.
                    "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        require(subprocess.check_output([str(PYTHON), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], text=True).strip() == "3.11", "Python sürümü 3.11 olmalı.")
        gpu = json.loads(subprocess.check_output([str(PYTHON), "-c",
            "import sys,json; sys.path.insert(0, '/content/e1_tools'); from colab_helpers import gpu_probe; print(json.dumps(gpu_probe()))"], env=ENV, text=True))
        print(json.dumps(gpu, indent=2))
        session_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        (RESULTS / f"session_{session_id}.json").write_text(json.dumps({**gpu, "cu_per_hour": CU_PER_HOUR, "available_cu": AVAILABLE_CU}, indent=2))
        (RESULTS / f"environment_{session_id}.txt").write_text(subprocess.check_output(uv + ["pip", "freeze", "--python", str(PYTHON)], text=True))
    ''')
    markdown("""
        ## 3 · Arşiv ve 54 MRI/etiket çiftini doğrula
        Paket yalnız eğitim/doğrulama içerir; test klasörü kabul edilmez. Dosya sağlama toplamları,
        44/10 ayrımı, voxel değerleri, şekiller, affine eşleşmesi ve tam kopya görüntüler kontrol edilir.
        Bu teknik kontrol doku isimlerinin/anatomik etiketlerin uzman onayı değildir.
    """)
    code('''
        extract_handoff(ARCHIVE, DATA)
        stamp = str(time.time_ns())
        run_logged([str(PYTHON), str(TOOLS / "audit_handoff.py"), str(DATA), "--out", str(WORK / "audit_report.json")],
                   RESULTS / "logs" / f"audit_{stamp}.log", ENV)
        report = json.loads((WORK / "audit_report.json").read_text())
        verify_manifest(DATA, report)
        require(report["dataset_sha256"] == EXPECTED_DATASET_SHA256 and report["split_sha256"] == EXPECTED_SPLIT_SHA256,
                "Arşiv, yerelde kontrol edilen teslim paketiyle aynı değil.")
        require(report["train_count"] == 44 and report["validation_count"] == 10, "Bölme değişmiş.")
        shutil.copyfile(WORK / "audit_report.json", RESULTS / f"audit_{stamp}.json")
        unknown = sum("unknown" in case["header_spatial_units"] for case in report["cases"])
        print(f"54 çift kontrol edildi: 44 eğitim / 10 doğrulama. Birimi belirtilmemiş vaka: {unknown}")
        print("EĞİTİM ÖNCESİ NOTLAR:\\n" + "\\n".join(report["warnings"][:4]))
    ''')
    code('''
        # Uses training cases only; these are voxel-plane previews, not mm-space validation.
        preview = RESULTS / "label_review.png"
        subprocess.run([str(PYTHON), str(TOOLS / "preview_handoff.py"), str(DATA), "--out", str(preview)], check=True, env=ENV)
        from IPython.display import display, Image
        display(Image(filename=str(preview)))
    ''')
    markdown("""
        **Veri inceleme noktası:** teslim notuna göre etiket dönüşümü çıkarımla yapılmış;
        hava boşlukları arka plana birleştirilmiş; silinen yüz için `ignore` maskesi yok.
        Bazı NYU affine'leri değiştirilmiş ve özgün dönüşüm manifesti pakette yok.
        Başlıklarda fiziksel birim de belirtilmemiş. Bu çalışmadan hasta yüzü veya mm-doğruluğu iddiası üretme.

        Görüntüleri ve bu sınırlamaları inceleyip ön deneye devam etmeyi seçersen ilk hücrede
        `ACKNOWLEDGE_PROVISIONAL_DATA = True` yap. Bu, otomatik anatomik onay anlamına gelmez.
    """)
    markdown("""
        ## 4 · Ön işleme ve sabit fold 0
        Teslim edilen plan raporu: 1 mm, patch 128×160×112, batch 2. Burada kendi ortamımızın ürettiği plan gösterilir;
        farklıysa eğitime geçmeden incele. Colab yeniden başlarsa yerel ön işleme yeniden yapılır;
        Drive'daki öğrenilmiş ağırlıklar silinmez.
    """)
    code('''
        require(ACKNOWLEDGE_PROVISIONAL_DATA, "Önizlemeleri/veri notlarını incele; sonra veri inceleme seçimini aç.")
        marker = PREPROCESSED / ".e1_input_sha256"
        preprocessing_key = hashlib.sha256((report["dataset_sha256"] + LOCK_SHA256).encode()).hexdigest()
        if marker.is_file():
            require(marker.read_text().strip() == preprocessing_key, "Ön işleme başka veri/sürüme ait; yeni yerel klasör kullan.")
        else:
            run_logged([str(VENV / "bin/nnUNetv2_plan_and_preprocess"), "-d", "1", "-c", "3d_fullres",
                        "--verify_dataset_integrity", "-np", "1"], RESULTS / "logs" / f"preprocess_{time.time_ns()}.log", ENV)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(preprocessing_key + "\\n")
        split_hash = install_split(DATA, PREPROCESSED)
        require(split_hash == report["split_sha256"], "Sabit bölme kopyası değişmiş.")
        plan_path = PREPROCESSED / DATASET / "nnUNetPlans.json"
        plans = json.loads(plan_path.read_text())
        require("3d_fullres" in plans["configurations"], "3d_fullres planı oluşmadı.")
        print(json.dumps(plans["configurations"]["3d_fullres"], indent=2))
        contract = {"experiment": "E1", "dataset_sha256": report["dataset_sha256"],
                    "split_sha256": split_hash, "plans_sha256": sha256(plan_path), "lock_sha256": LOCK_SHA256,
                    "trainer_sha256": TRAINER_SHA256, "configuration": "3d_fullres", "fold": 0,
                    "nnunetv2": "2.8.1", "torch": "2.6.0+cu124", "seed": 42,
                    "augmentation_workers": AUGMENTATION_WORKERS, "torch_compile": False,
                    "preliminary_only": True, "test_accessed": False}
        record_run(RESULTS / "experiment_contract.json", contract)
        for path in (plan_path, PREPROCESSED / DATASET / "dataset_fingerprint.json", DATA / "splits_final.json"):
            target = RESULTS / path.name
            if target.exists():
                require(sha256(target) == sha256(path), f"Kayıtlı {path.name} değişmiş; yeni deney kimliği kullan.")
            else:
                shutil.copyfile(path, target)
    ''')
    markdown("""
        ## 5 · Yalnız 5 epoch kontrol çalışması
        `RUN_5_EPOCH_PILOT = True` seçimi ücretli GPU çalışmasını başlatır.
        Her tamamlanan epoch'ta checkpoint alınır. Bir epoch tamamlanmadan koparsa başlangıç ağırlıkları kaydedilmiş olmayabilir.
        Devam için aynı deney kimliği + `RESUME_PILOT = True`; checkpoint yoksa sessiz yeniden başlama yapılmaz.
        Başlangıç seed'i 42; CUDA/çok işçili artırmalar bit düzeyinde tekrarlanabilirlik garantisi vermez.
    """)
    code('''
        def train_stage(trainer, enabled, resume):
            if not enabled:
                print(f"{trainer}: kapalı; eğitim başlatılmadı.")
                return
            require(ACKNOWLEDGE_PROVISIONAL_DATA and (RESULTS / "experiment_contract.json").is_file(), "Veri/ön işleme adımları tamamlanmalı.")
            require(os.path.ismount("/content/drive"), "Checkpoint hedefi kalıcı Drive bağlantısında olmalı.")
            require(ENV["nnUNet_results"] == str(RESULTS) and ENV["nnUNet_raw"] == str(DATA / "nnUNet_raw")
                    and ENV["nnUNet_n_proc_DA"] == str(AUGMENTATION_WORKERS), "Ayarlar değişti; ortam/veri/ön işleme hücrelerini yeniden çalıştır.")
            record_run(RESULTS / "experiment_contract.json", contract)
            folder = RESULTS / DATASET / f"{trainer}__nnUNetPlans__3d_fullres" / "fold_0"
            command = training_command(VENV / "bin/nnUNetv2_train", trainer, folder, resume)
            log = RESULTS / "logs" / f"{trainer}_{time.time_ns()}.log"
            result = run_logged(command, log, ENV)
            (log.with_suffix(".json")).write_text(json.dumps(result, indent=2))
            print(f"Bitti: {result['elapsed_seconds']/60:.1f} dakika. Log: {log}")
        train_stage("nnUNetTrainer_E1Smoke", RUN_5_EPOCH_PILOT, RESUME_PILOT)
    ''')
    markdown("""
        ## 6 · Süre/birim tahmini
        İlk epoch'un başlangıç maliyetini dışarıda bırakıp sonraki epoch sürelerinin medyanı kullanılır.
        Hesap yalnız eğitim döngüsüne yaklaşır; kurulum, ön işleme, nihai doğrulama ve değişen hız için ek pay gerekir.
        1.23 birim/saat bilgisini başka GPU için kullanma; açık oturumun kendi oranını gir.
    """)
    code('''
        logs = sorted((RESULTS / "logs").glob("nnUNetTrainer_E1Smoke_*.log"))
        epoch_seconds = []
        for log in logs:
            epoch_seconds.extend(float(value) for value in re.findall(r"Epoch time:\\s*([0-9.]+)", log.read_text()))
        if len(epoch_seconds) >= 2:
            import statistics
            median = statistics.median(epoch_seconds[1:])
            hours = median * 100 / 3600
            print(f"100 epoch eğitim döngüsü yaklaşık {hours:.2f} saat; ek aşamalar dahil değil.")
            if CU_PER_HOUR > 0:
                units = hours * CU_PER_HOUR
                print(f"Girilen oranla yaklaşık {units:.1f} işlem birimi + ek aşamalar.")
                if AVAILABLE_CU > 0:
                    print(f"Girilen hesap bakiyesi: {AVAILABLE_CU:.1f}. Bu hesap yeterlilik garantisi değildir.")
        else:
            print("Tahmin için en az iki tamamlanmış epoch süresi gerekli.")
    ''')
    markdown("""
        ## 7 · Ayrı 100 epoch ön model — varsayılan kapalı
        Kontrol çalışmasının hızını, görüntülerini ve bütçeyi inceledikten sonra
        `RUN_100_EPOCH_PRELIMINARY = True` yap. Bu eğitici ayrı klasörde **sıfırdan** başlar;
        5 epoch ağırlıklarını otomatik aktarmaz. Kendi kesilmiş 100 epoch çalışmasına devam için
        `RESUME_PRELIMINARY = True` kullan. Mevcut sonuçların üzerine yeni eğitim yazılmaz.

        **100 epoch bir ön sonuçtur**, nihai proje tamamlanması/test başarısı değildir.
        Ücretli uzun çalıştırmayı burada otomatik açma.
    """)
    code('''
        train_stage("nnUNetTrainer_E1Preliminary", RUN_100_EPOCH_PRELIMINARY, RESUME_PRELIMINARY)
    ''')
    markdown("""
        ## 8 · Doğrulama çıktıları
        Epoch logundaki patch tabanlı pseudo-Dice ile tüm 10 doğrulama vakasının son segmentasyon Dice'ı farklıdır.
        Nihai doğrulama bitmediyse sonuç varmış gibi raporlanmaz. Test kümesi bu defterde açılmaz.
    """)
    code('''
        summary = RESULTS / DATASET / "nnUNetTrainer_E1Preliminary__nnUNetPlans__3d_fullres/fold_0/validation/summary.json"
        if summary.is_file():
            metrics = json.loads(summary.read_text())
            print("Yalnız 10 doğrulama vakası — ön sonuç:")
            print(json.dumps({"foreground_mean": metrics.get("foreground_mean"), "per_label_mean": metrics.get("mean")}, indent=2))
        else:
            print("Tamamlanmış 100 epoch doğrulama özeti henüz yok.")
        print("Ara verirken: checkpoint/logların Drive'da bulunduğunu kontrol et; kullanılmayan GPU oturumunu sonlandır.")
    ''')
    markdown("""
        Kaynaklar: [nnU-Net v2.8.1](https://github.com/MIC-DKFZ/nnUNet/tree/v2.8.1),
        [5/100 epoch eğiticileri](https://github.com/MIC-DKFZ/nnUNet/blob/v2.8.1/nnunetv2/training/nnUNetTrainer/variants/training_length/nnUNetTrainer_Xepochs.py),
        [Colab kaynak sınırları](https://research.google.com/colaboratory/faq.html).
        CHARM E2 için ayrı etiketleme aracı olabilir; bu E1 defteri yalnız teslim edilen MultiAxial verisini kullanır.
    """)
    for index, cell in enumerate(cells):
        cell["id"] = f"e1-{index:02d}"
    return {"nbformat": 4, "nbformat_minor": 5, "metadata": {"colab": {"name": "E1_Colab.ipynb", "provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"}, "accelerator": "GPU",
            "e1_helper_sha256": {name: hashlib.sha256(source.encode()).hexdigest() for name, source in sources.items()}}, "cells": cells}


if __name__ == "__main__":
    path = ROOT / "E1_Colab.ipynb"
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n")
    print(path)

"""Build the standalone, inference-only E1 Colab demonstration notebook."""

import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent
HELPERS = ("demo.py", "surface_view.py", "surface_controls.js", "trainers.py", "colab_helpers.py", "requirements-colab.lock.txt")


def build():
    cells = []
    contract = json.loads((ROOT / "handoff_contract.json").read_text())

    def markdown(source):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": textwrap.dedent(source).strip() + "\n"})

    def code(source):
        cells.append({"cell_type": "code", "metadata": {}, "source": textwrap.dedent(source).strip() + "\n",
                      "execution_count": None, "outputs": []})

    markdown('''
        # E1 · MRI → doku segmentasyonu — 3B sunum demosu

        **Tamamlanan çalışma:** 100 epoch, 44 eğitim / 10 doğrulama, yalnız fold 0.
        Bu defter eğitim başlatmaz. Önce gerçek, **önceden kaydedilmiş** doğrulama tahminini gösterir.
        İsteğe bağlı son adım, eğitilmiş modeli yükleyip **yeni tahmin** üretir.

        - Kayıtlı sonuç gösterimi için Colab'da **CPU** yeterli.
        - Canlı GPU tahmini için **L4** seç; ilk hücrede `RUN_LIVE = True` yap, ortam hücresini tekrar çalıştır.
        - Kaynak: kendi Drive'ındaki `TMS_E1/runs/E1_L4_001` ve hazırlanmış `handoff_k2_e1.zip`.
        - Çıktılar `TMS_E1/demos/` altında yeni klasörlere yazılır. Eğitim dosyaları değiştirilmez.

        Gösterilen vakalar doğrulama vakalarıdır; bağımsız test sonucu veya mesh üretimi değildir.
    ''')
    code('''
        from pathlib import Path
        import json, os, shutil, subprocess, sys, time

        EXPERIMENT_ID = "E1_L4_001"
        CASE_ID = "GU011"  # Other examples: GU041, NYU005. Validation cases only.
        RUN_LIVE = False
        DEVICE = "cuda"  # For explicitly enabled inference: "cuda" or "cpu".
        USE_TTA = True  # Matches validation; changing it changes the inference protocol.
        DRIVE = Path("/content/drive/MyDrive/TMS_E1")
        ARCHIVE = DRIVE / "handoff_k2_e1.zip"
        EXPERIMENT = DRIVE / "runs" / EXPERIMENT_ID
        DATASET = "Dataset001_MultiAxial"
        MODEL = EXPERIMENT / DATASET / "nnUNetTrainer_E1Preliminary__nnUNetPlans__3d_fullres"
        SAVED = MODEL / "fold_0/validation"
        SUMMARY = SAVED / "summary.json"
        WORK = Path("/content/e1_demo")
        TOOLS = WORK / "tools"
        DATA = WORK / "handoff"
        VENV = Path("/content/e1-demo-venv")
        PYTHON = VENV / "bin/python"
        OUTPUTS = DRIVE / "demos" / EXPERIMENT_ID
        assert DEVICE in ("cpu", "cuda")
        assert EXPERIMENT_ID.replace("_", "").replace("-", "").isalnum()
    ''')
    markdown('''
        ## 1 · Drive bağlantısı ve kaynaklar
        Aynı Google hesabını kullan. Burada yeni GPU tahsisi veya eğitim yapılmaz.
    ''')
    code('''
        from google.colab import drive
        drive.mount("/content/drive")
        assert os.path.ismount("/content/drive"), "Drive bağlı değil."
        assert ARCHIVE.is_file(), f"Hazırlanmış veri ZIP'i bulunamadı: {ARCHIVE}"
        assert MODEL.is_dir() and SUMMARY.is_file(), f"Tamamlanmış model/özet bulunamadı: {MODEL}"
        TOOLS.mkdir(parents=True, exist_ok=True)
    ''')
    markdown('''
        ## 2 · Demo ortamı
        Kayıtlı sonuç modu yalnız hafif görüntüleme paketlerini kurar. `RUN_LIVE = True` seçiliyse
        ayrıca eğitimle aynı nnU-Net/Torch sürümleri kurulur. İlk kurulum internet ister;
        üretilen HTML raporu sonradan internetsiz açılabilir.
    ''')
    sources = {name: (ROOT / name).read_text() for name in HELPERS}
    code("EMBEDDED = " + repr(sources) + "\n"
         "for name, source in EMBEDDED.items():\n    (TOOLS / name).write_text(source)\n"
         "sys.path.insert(0, str(TOOLS))\n"
         "from colab_helpers import extract_handoff, sha256, require, run_logged\n"
         f"EXPECTED_DATASET_SHA256 = {contract['dataset_sha256']!r}\n"
         f"EXPECTED_SPLIT_SHA256 = {contract['split_sha256']!r}\n"
         "EXPECTED_ARCHIVE_SHA256 = 'c580a1706a8242afc11b3e34c7b74586e759766e89fc4f3bd0c82cacb0be071a'\n"
         "EXPECTED_CHECKPOINT_SHA256 = '678867420134d54b31a9975f2c2d1a34b57b8369aef5692fa64f97a8980a531b'\n")
    code('''
        subprocess.run([sys.executable, "-m", "pip", "install", "uv==0.11.8"], check=True)
        uv = [sys.executable, "-m", "uv"]
        if not PYTHON.is_file():
            subprocess.run(uv + ["venv", str(VENV), "--python", "3.11"], check=True)
        if RUN_LIVE:
            subprocess.run(uv + ["pip", "install", "--python", str(PYTHON), "--torch-backend", "cu124",
                                 "-r", str(TOOLS / "requirements-colab.lock.txt")], check=True)
        else:
            subprocess.run(uv + ["pip", "install", "--python", str(PYTHON),
                                 "numpy==1.26.4", "nibabel==5.4.2", "matplotlib==3.11.2"], check=True)
        subprocess.run(uv + ["pip", "install", "--python", str(PYTHON),
                             "scikit-image==0.26.0", "plotly==7.1.0"], check=True)
        subprocess.run(uv + ["pip", "check", "--python", str(PYTHON)], check=True)
        ENV = os.environ.copy()
        ENV.update({"MPLBACKEND": "Agg", "MPLCONFIGDIR": str(WORK / "matplotlib"),
                    "PYTHONNOUSERSITE": "1", "nnUNet_compile": "false",
                    "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        print("Ortam hazır. Yeni tahmin seçimi:", RUN_LIVE)
    ''')
    markdown('''
        ## 3 · Deneyi değiştirmeden doğrulama vakasını seç
        Sabit veri paketinin sağlama toplamı kontrol edilir. Test kümesi açılmaz.
        Eğitim ön işlemesi yapılmaz; yeni tahminin kendi ön işlemesi tahmin adımındadır.
    ''')
    code('''
        require(sha256(ARCHIVE) == EXPECTED_ARCHIVE_SHA256, "ZIP, hazırlanan E1 arşiviyle aynı değil.")
        extract_handoff(ARCHIVE, DATA)
        require(sha256(DATA / "splits_final.json") == EXPECTED_SPLIT_SHA256, "Sabit ayrım değişmiş.")
        split = json.loads((DATA / "splits_final.json").read_text())[0]
        require(CASE_ID in split["val"] and CASE_ID not in split["train"], "Bir doğrulama vakası seç.")
        manifest = json.loads((DATA / "expected_files.json").read_text())
        require(manifest["dataset_sha256"] == EXPECTED_DATASET_SHA256, "Başka veri paketi seçilmiş.")
        MRI = DATA / "nnUNet_raw" / DATASET / "imagesTr" / f"{CASE_ID}_0000.nii.gz"
        REFERENCE = DATA / "nnUNet_raw" / DATASET / "labelsTr" / f"{CASE_ID}.nii.gz"
        for path in (MRI, REFERENCE):
            require(sha256(path) == manifest["files"][path.relative_to(DATA).as_posix()], "Vaka dosyası değişmiş.")
        RECORDED = SAVED / f"{CASE_ID}.nii.gz"
        require(RECORDED.is_file(), f"Kaydedilmiş doğrulama tahmini yok: {RECORDED}")
        print(f"Seçilen vaka: {CASE_ID} — doğrulama, bağımsız test değil.")
    ''')
    markdown('''
        ## 4 · Kaydedilmiş sonucu göster — GPU gerekmez
        Bu hücre yeni tahmin üretmez. Önceden hesaplanan segmentasyonu MRI ve referansla
        karşılaştırır; vaka Dice skorunu dosyalardan yeniden hesaplar.
        Raporun başında **döndürülebilir 3B yüzey görünümü** bulunur: dokuları seç,
        görünürlüklerini değiştir, Beyin/Kafa/Tümü görünümlerini dene. Altında 2B karşılaştırma korunur.
        Bu yüzeyler simülasyon için hazırlanmış SimNIBS mesh'i değildir.
    ''')
    code('''
        RECORDED_REPORT = OUTPUTS / f"{CASE_ID}_recorded_{time.time_ns()}"
        run_logged([str(PYTHON), str(TOOLS / "demo.py"), "report", "--mri", str(MRI),
                    "--reference", str(REFERENCE), "--recorded-prediction", str(RECORDED),
                    "--summary", str(SUMMARY), "--out", str(RECORDED_REPORT)],
                   WORK / f"report_{time.time_ns()}.log", ENV)
        from IPython.display import HTML, display
        display(HTML((RECORDED_REPORT / "report.html").read_text()))
        print("Sunum yedeği — internetsiz açılır:", RECORDED_REPORT / "report.html")
    ''')
    markdown('''
        ## 5 · Eğitilmiş modelle yeni tahmin — açık seçim
        İlk hücrede `RUN_LIVE = True` yapıp ortam hücresini yeniden çalıştır.
        GPU için çalışma zamanı türünü L4 seç; çalışma zamanı değişmişse 1–4'ü yeniden çalıştır.
        Ağırlıklar yalnız okunur. Eksik/yanlış checkpoint durumunda kayıtlı tahmin canlıymış gibi gösterilmez.
    ''')
    code('''
        if RUN_LIVE:
            require(sha256(MODEL / "fold_0/checkpoint_final.pth") == EXPECTED_CHECKPOINT_SHA256,
                    "Checkpoint, tamamlanan E1_L4_001 modelinden farklı.")
            LIVE_OUTPUT = OUTPUTS / f"{CASE_ID}_{DEVICE}_{time.time_ns()}"
            command = [str(PYTHON), str(TOOLS / "demo.py"), "predict", "--model", str(MODEL),
                       "--mri", str(MRI), "--reference", str(REFERENCE), "--summary", str(SUMMARY),
                       "--out", str(LIVE_OUTPUT), "--device", DEVICE]
            if not USE_TTA:
                command.append("--disable-tta")
            run_logged(command, WORK / f"inference_{time.time_ns()}.log", ENV)
            display(HTML((LIVE_OUTPUT / "report/report.html").read_text()))
            print("Yeni tahmin:", LIVE_OUTPUT / "prediction.nii.gz")
            print("Ölçülen süreler:", (LIVE_OUTPUT / "status.json").read_text())
        else:
            print("Yeni tahmin kapalı. 4. bölümdeki çıktı, kaydedilmiş doğrulama tahminidir.")
    ''')
    markdown('''
        ## Sunum sırası
        1. MRI girdisini ve renkli doku tahminini göster.
        2. Referans/tahmin farklarını ve seçilen vaka skorlarını açıkla.
        3. Kohort ortalamasının 10 doğrulama vakasına ait olduğunu belirt; test sonucu deme.
        4. Canlı tahmin yaptıysan ölçülen cihazı ve ayna çevirmeli tahmin seçimini söyle.
        5. Sonraki iş: etiket teyidi, diğer vakaların incelemesi, E2 verisi ve kontrollü karşılaştırmalar.

        Sunumdan önce `report.html` ve `report.json` dosyalarını indir. GPU oturumunu işin bitince sonlandır.
        Referans doku eşlemesi, yüzü silinmiş bölgeler ve fiziksel birim sınırlamaları geçerliliğini korur.
    ''')
    for index, cell in enumerate(cells):
        cell["id"] = f"e1-demo-{index:02d}"
    return {"cells": cells, "metadata": {"colab": {"name": "E1_Demo_3D.ipynb"},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


if __name__ == "__main__":
    destination = ROOT / "E1_Demo.ipynb"
    destination.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n")
    print(destination)

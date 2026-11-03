# E1 sunum demosu

Eğitilmiş E1 modelini gösterir. Döndürülebilir 3B gösterim yüzeyleri ve 2B kesit karşılaştırmaları içerir. Yeni eğitim, CHARM çalışması veya SimNIBS/FEM hacim mesh'i üretimi başlatmaz. MRI/CHARM masaüstü prototipini değiştirmez.

## Colab: en kısa yol

1. [E1_Demo.ipynb](E1_Demo.ipynb) dosyasını Colab'da aç.
2. **Kayıtlı sonuç gösterimi için CPU** seç. İlk hücrede `EXPERIMENT_ID = "E1_L4_001"`, `CASE_ID = "GU011"`, `RUN_LIVE = False` kalsın.
3. 1–4 bölümlerini sırayla çalıştır. Mevcut Drive modeli ve `TMS_E1/handoff_k2_e1.zip` kullanılır. Eğitim ön işlemesini tekrarlamaz.
4. Raporun başında **3B doku yüzeyleri** açılır. Fareyle döndür, tekerlekle yakınlaştır. Dokuları kutucuklarla aç/kapat; kaydırıcıda 0 tamamen saydam, 100 opaktır. **Beyin / Kafa / Tümü / Sıfırla** kontrolleri hazırdır. Altında üç düzlemde MRI, referans, tahmin ve farklar korunur. Vaka Dice'ı özgün hacimden yeniden hesaplanır; 10 vakalık ortalama mevcut doğrulama JSON'undan okunur.
5. **Yeni tahmin** göstermek için L4 çalışma zamanı seç; `RUN_LIVE = True`, `DEVICE = "cuda"`, `USE_TTA = True` yap. Ortam yenilendiyse 1–4'ü, ardından 5'i çalıştır. Tek MRI için tahmin alınır; ağırlıklar değişmez.
6. Sunum öncesi raporu indir. `report.html` tek dosyadır, internet veya GPU olmadan açılır. Kaydedilmiş tahmin olduğunu açıkça belirtir.

Bu bölüm numaraları **E1_Demo.ipynb** içindir. Tamamlanmış modeli göstermek için eğitim notebook'unu yeniden çalıştırmak gerekmez.

Önceki 2B sürümü açtıysan **güncellenmiş notebook'u yeniden yükle**; eski notebook kendi gömülü kodunu kullanır ve kendiliğinden güncellenmez. Yeni sürümün 2. bölümünü de çalıştır: 3B için `scikit-image==0.26.0` ve `plotly==7.1.0` kurulur. Yeni model, veri ZIP'i veya GPU gerekmez. Tarayıcıda JavaScript/WebGL desteği gerekir; 2B karşılaştırma aynı raporda kalır.

3B yüzeyler kaynak affine ile yerleştirilir. Tarayıcıyı zorlamamak için gösterim geometrisi yaklaşık örneklenir; kullanılan adım raporda belirtilir. Bu işlem kaynak etiketleri veya skorları değiştirmez. Doku yüzeyleri SimNIBS'e hazır tetrahedral hacim mesh'i değildir; fiziksel ölçek ve anatomik doğruluk bu görünümle doğrulanmış sayılmaz. Plotly JavaScript'i HTML içine gömülüdür; HTML indirildikten sonra çevrimdışı çalışır.

`CASE_ID` sabit doğrulama ayrımındaki bir vaka olmalıdır. Önerilen örnekler: GU011 (düşük skor), GU041 (yüksek skor), NYU005 (farklı merkez). Bunlar bağımsız test değildir.

## Gerekli model dosyaları

Drive'da şu yapı korunmalı:

```text
TMS_E1/runs/E1_L4_001/
└── Dataset001_MultiAxial/
    └── nnUNetTrainer_E1Preliminary__nnUNetPlans__3d_fullres/
        ├── plans.json
        ├── dataset.json
        └── fold_0/
            ├── checkpoint_final.pth
            └── validation/
                ├── summary.json
                └── GU011.nii.gz
```

Diğer doğrulama tahminleri de aynı `validation` klasöründedir. Notebook, bu tamamlanmış modelin kontrol edilen checkpoint SHA-256 değerini doğrular. Başka model seçmek yeni bir inceleme ve demo kaydı gerektirir.

Ekip tesliminde **E1_L4_001 klasörünün tamamını** koru. Ayrıca [trainers.py](trainers.py), [requirements-colab.lock.txt](requirements-colab.lock.txt), bu kılavuz ve demo kodu/notebook'u ver. Trainer kurulumu ve dosya düzeni [teslim kılavuzunda](HANDOFF.md). Özel `nnUNetTrainer_E1Preliminary` sınıfı ağırlıkların yüklenmesi için gereklidir. Bu deney yalnız fold 0 içerir; fold 1–4 eğitilmedi.

## Yerel kullanım

Kayıtlı rapor için NumPy, nibabel, matplotlib, scikit-image 0.26.0 ve plotly 7.1.0 gerekir. Model tahmini için **ayrı Python 3.11 ortamında** nnunetv2 2.8.1, torch 2.6.0 ve uyumlu bağımlılıkları kur; mevcut SimNIBS ortamına kurulum yapma. Colab CUDA bağımlılık kilidi Linux içindir; macOS'a uygulanmaz. Yalnız kendi eğittiğin checkpoint'i kullan.

Repo kökünden:

Araç ZIP'ini ayrı klasöre açtıysan aşağıdaki komutlarda `tools/e1_training/demo.py` yerine `demo.py` kullan.

```bash
python tools/e1_training/demo.py report \
  --mri /outside/git/GU011_0000.nii.gz \
  --reference /outside/git/GU011_reference.nii.gz \
  --recorded-prediction /outside/git/GU011_prediction.nii.gz \
  --summary /outside/git/summary.json \
  --out /outside/git/fresh_recorded_report

python tools/e1_training/demo.py predict \
  --model /outside/git/model_folder \
  --mri /outside/git/GU011_0000.nii.gz \
  --reference /outside/git/GU011_reference.nii.gz \
  --out /outside/git/fresh_live_run --device cpu --disable-tta
```

`--reference` ve `--summary` isteğe bağlıdır. Referans olmadan Dice gösterilmez. CPU örneğinde hız için ayna çevirmeli tahmin kapalıdır; bu, eğitim sonundaki TTA-açık doğrulamayla aynı protokol değildir. Colab'da varsayılan TTA açıktır. Ölçümler model yüklemesini ve ön işleme/tahmin/NIfTI kaydını ayrı verir; saf GPU çekirdek süresi veya bütün CHARM hattının süresi değildir.

Her çıktı yeni klasöre yazılır. Başarısız tahmin `status.json` içinde `failed` olur; kayıtlı sonuçla sessizce değiştirilmez. Kaynak NIfTI başlıkları değiştirilmez. Şekil/affine uyumsuzluğu reddedilir; fiziksel birimi bilinmeyen kaynaklar açık notla yalnız voksel düzleminde karşılaştırılır. MRI içeren çıktılar ve ağırlıklar Git dışında tutulur.

## Kontroller

```bash
python -m unittest discover -s tools/e1_training -q
python tools/e1_training/build_demo_notebook.py
```

Sentetik testler gerçek model başarısını kanıtlamaz. Gerçek ağırlıkla yürütme ve sunum provası ayrıca [EXP-003](../../knowledge/experiments/e1-preparation.md) içinde kaydedilir.

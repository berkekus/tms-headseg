# charm toplu çalıştırma (E2 etiketleri)

E2 eğitimi için IXI kişilerinin charm etiketleri iki makinede üretilir: K1 ve K2. İki makinede de **aynı araç, aynı komut ve aynı ayarlar** kullanılır. Böylece etiketler kimin makinesinde üretildiğine göre değişmez.

## Kim hangi kişileri çalıştırıyor

Atama dosyası: [ixi_assignment.csv](ixi_assignment.csv). [make_assignment.py](make_assignment.py) bu dosyayı sabit bir tohumla (`20261103`) üretir; elle değiştirme.

| Grup | Sayı | Kim | Not |
|---|---|---|---|
| `train`, K2 | 15 | **K2** | IXI037, 054, 062, 070, 078, 148, 167, 185, 239, 329, 368, 377, 393, 426, 442 |
| `train`, K1 | 14 | K1 | 3 pilot (IXI045, 095, 294) dahil |
| `test_face` | 10 | K1 | Yüz testi için ayrıldı. **Eğitime asla girmez.** |
| `calibration` | 5 | K1 | Eşik ayarı için ayrıldı. **Eğitime asla girmez.** |
| `excluded_d05` | 6 | kimse | D05 test setiyle çakışıyor. Hiçbir yerde kullanılmaz. |

IXI045 ve IXI294 pilotları bu araçtan önce, aynı charm sürümüyle ama iş parçacığı sınırı olmadan elle çalıştırıldı. IXI095 ve K1'in kalan vakaları bu araçla çalışıyor.

İki kişi de üç siteden (Guys, HH, IOP) vaka alır. Test ve kalibrasyon kişileri yalnızca yüzü ve kafa tepesi görüntüye tam giren kişilerden seçildi. Bu ayrım **geçicidir** ve K1 (test sorumlusu) tarafından onaylanınca kesinleşir.

## Gerekenler

1. **SimNIBS 4.6.0.** Sürüm birebir aynı olmalı. Araç sürümü log'dan okur ve başka bir sürümde vakayı başarısız sayar.
2. **D06 IXI verisi.** Ekip Drive'ındaki D06 klasöründen indirilip açılır (yaklaşık 0,75 GB). Araç dosyaları `DATA/IXI037/IXI037-Guys-0704-T1.nii.gz` düzeninde de, hepsi tek klasörde olacak şekilde de bulur.
3. **Disk alanı.** Kişi başına yaklaşık 0,25 GB, 15 kişi için yaklaşık 4 GB.
4. **Hafıza.** En az 16 GB RAM. **Aynı anda tek charm** çalıştır; araç vakaları zaten sırayla işler.
5. **Bu repo.** `git pull` ile güncel olmalı.

Çıktı klasörü Git deposunun **dışında** olmalı; araç repo içine yazmayı reddeder.

## Çalıştırma

Araç SimNIBS'in kendi Python'uyla çalışır (`simnibs_python`, SimNIBS'le birlikte kurulur ve nibabel içerir). Komutları repo kökünden çalıştır.

**Windows (PowerShell):**

```powershell
& "$env:USERPROFILE\SimNIBS-4.6\bin\simnibs_python.cmd" tools/charm_batch/run_charm_batch.py `
    --owner K2 --data C:\veri\D06 --out C:\veri\charm_K2 `
    --charm "$env:USERPROFILE\SimNIBS-4.6\bin\charm.cmd" --dry-run
```

**macOS / Linux:**

```bash
~/Applications/SimNIBS-4.6/bin/simnibs_python tools/charm_batch/run_charm_batch.py \
    --owner K2 --data ~/veri/D06 --out ~/veri/charm_K2 \
    --charm ~/Applications/SimNIBS-4.6/bin/charm --dry-run
```

SimNIBS başka bir klasöre kurulduysa yolları ona göre değiştir.

1. Önce komutu `--dry-run` ile çalıştır. 15 satır görmelisin; bazılarında `--forceqform` yazacak (aşağıya bak). Hata çıkarsa K1'e yaz.
2. Sonra **aynı komutu `--dry-run` olmadan** çalıştır.
3. **Süre:** Kişi başına yaklaşık 40–70 dakika; 15 kişi için 12–16 saat. Geceye bırakılabilir. Bilgisayarın uyku moduna geçmesini kapat.
4. **Durursa:** Aynı komutu tekrar çalıştır. Biten kişiler atlanır, yarım kalan kişi baştan başlar. Yarım kalanın eski klasörü `m2m_<ID>_attempt_<zaman>` adıyla saklanır.
5. **Tek kişi denemek için:** komutun sonuna `--only IXI037` ekle.

## Aracın senin yerine yaptıkları

Bunları elle yapma ya da değiştirme. K1'in makinesinde de birebir aynı adımlar uygulanıyor.

- **qform/sform kontrolü.**
  - IXI dosyalarının bir kısmında iki konum kaydı arasında 0,00001 mm düzeyinde yuvarlama farkı var. charm bu durumda durur.
  - Araç, charm'ın kendi kontrolünü önceden yapar. Fark yuvarlama düzeyindeyse `--forceqform` ekler (K2'nin 15 kişisinin 12'sinde gerekiyor).
  - Fark 0,001 mm'den büyükse vakayı **atlar** ve K1'e sor der.
- **İş parçacığı sınırları.** Matematik kütüphanelerinin iş parçacığı sayısını 1'e sabitler (`OPENBLAS_NUM_THREADS`, `OPENBLAS_DEFAULT_NUM_THREADS`, `OMP_NUM_THREADS`). Bu, Windows'ta görülen OpenBLAS çökmesini önleyen ayar (EXP-002); MRI Workbench'teki charm başlatıcısı da aynısını yapıyor.
- **Kayıt.** Her kişi için `runs/<ID>.json` yazar: başlangıç ve bitiş zamanı, süre, çıkış kodu, SimNIBS sürümü, `--forceqform` kullanılıp kullanılmadığı, işletim sistemi. charm'ın tüm çıktısı `logs/<ID>.log` dosyasına gider.
- **Doğrulama.** `final_tissues.nii.gz`, `final_tissues_LUT.txt` ve `charm_report.html` yoksa ya da sürüm 4.6.0 değilse vakayı başarısız sayar.
- **Teslim paketi.** Başarılı her kişi için `deliver_K2/<ID>/` klasörünü hazırlar. İçinde etiketler, LUT, rapor, log, ayarlar, `run.json` ve `SHA256SUMS.txt` bulunur.

Araç etiketleri **dönüştürmez**: ham charm etiketleri (0–12) teslim edilir. Proje etiketlerine çevirme (eşleme, Q-05) K1'de merkezi olarak yapılır, çünkü eşleme hâlâ değişiyor (örneğin kan → BOS önerisi).

## Kalite kontrolü (senin işin)

Araç `qc_K2.csv` dosyasını oluşturur. Biten her kişi için `m2m_<ID>/charm_report.html` dosyasını aç ve bak:

- Kafatası, BOS, gri madde, beyaz madde ve deri sınırları MR'daki gerçek sınırları izliyor mu?
- Büyük bir doku eksik mi, ya da kafa dışına taşan bir etiket var mı?
- Kafatası belirgin şekilde delik ya da kopuk mu?

`qc` sütununa `pass` veya `fail` yaz. `notes` sütununa kısa bir not yaz (örneğin "sol temporalde kafatası ince"). Emin değilsen `fail` yerine `check` yaz; K1 bakar.

## Teslim

1. `deliver_K2` klasörünü ve `qc_K2.csv` dosyasını zip'le. `m2m_*` klasörlerinin tamamını gönderme; büyükler ve gerekmiyorlar. Yine de silme, istenirse diye sakla.
2. Zip'i ekip Drive'ına, K1'in söyleyeceği klasöre yükle ve K1'e haber ver.
3. K1 her dosyayı `SHA256SUMS.txt` ile doğrular.

## Kurallar

- Test (`test_face`) ve kalibrasyon kişilerini çalıştırma, eğitimde de kullanma. Araç zaten yalnızca `train` grubunu çalıştırır.
- Ayar, bayrak veya sürüm değiştirme. Bir sorun çıkarsa K1'e sor. Farklı ayarla üretilen etiketler iki makinenin sonuçlarını karşılaştırılamaz hale getirir.
- IXI verisi CC BY-SA 3.0 lisanslı. Çıktılar yalnızca ekip Drive'ında tutulur, Git'e girmez.

## Testler

```bash
python -m unittest discover -s tools/charm_batch -v
```

Testler sahte bir charm kullanır. Gerçek charm sonucunu doğrulamazlar; yalnızca aracın akışını (atama, bayraklar, atlama, paketleme) sınarlar.

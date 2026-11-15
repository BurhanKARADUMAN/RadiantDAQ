# RadiantDAQ — Windows üzerinden kullanım

Bu proje mevcut GitHub depolarından **bağımsız yeni bir depo** olarak yayımlanmak üzere hazırlanmıştır.

## 1. ZIP'i çıkar

ZIP dosyasını **Tümünü ayıkla** ile çıkar. İçindeki `RadiantDAQ_Detector_Readout_MVP_2026` klasörünü aç.

## 2. Test et (önerilen)

Klasörde Dosya Gezgini adres çubuğuna `powershell` yazıp Enter'a bas. Ardından:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m radiantdaq demo --events 1600 --seed 2026 --out outputs/demo
.\.venv\Scripts\python.exe -m radiantdaq sweep --events 1100 --seed 2026 --out outputs/demo
```

Python veya pip kurulumu başarısızsa ortamı kontrol et. GATE veya Geant4, bu ilk sürüm için gerekli değildir.

## 3. GitHub'da yeni depo aç

GitHub CLI oturumun açıkken, aynı klasörde:

```powershell
powershell -ExecutionPolicy Bypass -File .\PUBLISH_NEW_REPOSITORY.ps1
```

Betik önce `BurhanKARADUMAN/RadiantDAQ` deposunun henüz bulunmadığını kontrol eder; depo mevcutsa işlemi durdurur. Başarılıysa yeni herkese açık depoyu açıp dosyaları gönderir.

**Diğer depoları değiştirmez**; hiçbir eski depoyu klonlamaz, üzerine yazmaz veya force-push yapmaz.

## 4. GitHub profilinde göster

Repo yayımlandıktan sonra `https://github.com/BurhanKARADUMAN/RadiantDAQ` adresinden açılacaktır. Profil sayfanda `Customize your pins` seçeneğinden sabitleyebilir veya araştırma sitene bir proje kartı ekleyebilirsin.

## Bilimsel durum

İlk sürüm bir **sentetik dedektör modeli**: gerçek PET cihazı, gerçek SiPM ölçümü, klinik validasyon veya Geant4/GATE çıktısı içermez.

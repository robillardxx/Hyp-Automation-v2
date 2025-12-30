# HYP Otomasyon - İş Yerinde Devam Promptu

Bu promptu iş yerindeki bilgisayarda Claude Code'a yapıştır:

---

```
HYP Otomasyon projesinde kaldığımız yerden devam edeceğiz.

ADIM 1: GitHub'dan güncel versiyonu indir
- Repo: https://github.com/robillardxx/Hyp-Automation
- Masaüstündeki eski hyp_yeni klasörünü sil (varsa)
- Repoyu masaüstüne klonla ve klasör adını hyp_yeni yap

ADIM 2: Dosyaları oku
- CHANGELOG.md - son değişiklikleri gör
- hyp_settings.json - hedef ve yapılan sayıları gör
- ise_gidince.md - bekleyen işleri gör

ADIM 3: Özet ver ve ne yapmak istediğimi sor

---

Proje: Türkiye Sağlık Bakanlığı HYP sistemi için Selenium otomasyon uygulaması
Mevcut versiyon: v6.9.6

Son seansta yaptıklarımız (evde):
- Çoklu tarih sorgulaması 30x hızlandırıldı
- Türkçe karakter sorunu çözüldü (normalize_tr)
- KVR protokol takılması çözüldü
- DEVAM EDİYOR durumu algılama eklendi
- GUI donma önlendi

Bekleyen işler:
1. OBE_IZLEM'de Edmonton evrelemesi kontrolü
2. WebDriverWait optimizasyonu
3. Yeni HYP modülleri (Koroner, İnme, KOAH, Astım, Böbrek)
```

---

## İş Yeri Bilgileri

- **GitHub Repo:** https://github.com/robillardxx/Hyp-Automation
- Chrome profil: `C:\Users\osman\AppData\Local\Google\Chrome\User Data\hyp_profile`
- Test: `python gui_app.py`

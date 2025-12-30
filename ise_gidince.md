# HYP Otomasyon - Claude Code Devam Promptu

Asagidaki promptu Claude Code'a yapistir:

---

```
C:\Users\osman\Desktop\hyp_yeni klasorundeki HYP Otomasyon projesinde calismaya devam edecegiz.

Oncelikle su dosyalari oku:
1. CHANGELOG.md - son degisiklikleri gor
2. hyp_settings.json - mevcut hedef ve yapilan sayilarini gor
3. ise_gidince.md - bekleyen isleri gor

Proje: Turkiye Saglik Bakanligi HYP sistemi icin Selenium otomasyon + CustomTkinter GUI uygulamasi.

Ana dosyalar:
- hyp_automation.py (Selenium motoru, ~300KB)
- gui_app.py (GUI, ~200KB)

Mevcut versiyon: v6.9.6

Son seansda yaptiklarimiz:
- Coklu tarih sorgulamasi 30x hizlandirildi (bellekte filtreleme)
- Turkce karakter sorunu cozuldu (normalize_tr)
- KVR protokol takilmasi cozuldu (same-page detection)
- DEVAM EDIYOR durumu algilama eklendi
- GUI donma onlendi (150ms refresh timer)

Bekleyen isler:
1. OBE_IZLEM'de Edmonton evrelemesi kontrolu (HYP v2.7.9)
2. WebDriverWait optimizasyonu (time.sleep yerine)
3. Yeni HYP modulleri (Koroner, Inme, KOAH, Astim, Bobrek)

Dosyalari okuduktan sonra bana ozet ver ve ne yapmak istedigimi sor.
```

---

## Notlar

- **GitHub Repo:** https://github.com/robillardxx/Hyp-Automation
- Chrome profil yolu: `C:\Users\osman\AppData\Local\Google\Chrome\User Data\hyp_profile`
- Paylasimli klasor: `Z:\Dr Osman`
- Hemsire uygulamasi: `hemsire_app/` klasoru
- Test: `python gui_app.py`

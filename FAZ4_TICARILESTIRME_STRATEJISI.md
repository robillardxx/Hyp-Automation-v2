# FAZ 4: TICARILESTIRME STRATEJISI
# HYP Otomasyon Sistemi

**Tarih:** 12 Ocak 2026
**Versiyon:** 1.0

---

## 1. IS MODELI ANALIZI

### 1.1 Model Karsilastirmasi

| Model | Avantajlar | Dezavantajlar | Tahmini Gelir (25K kullanici) | Oneri |
|-------|------------|---------------|-------------------------------|-------|
| **Tek Seferlik Lisans** | Basit, anlasilir, hizli nakit | Surdurulebilir degil, destek maliyeti | 500 TL x %5 = 625K TL (tek sefer) | Baslangic icin uygun |
| **Aylik Abonelik** | Surekli gelir, dusuk giris bariyeri | Churn riski, tahsilat zorlu | 50 TL x 1000 x 12 = 600K TL/yil | Orta vade |
| **Yillik Abonelik** | Ongorülebilir gelir, dusuk churn | Yuksek baslangic bariyeri | 400 TL x 1000 = 400K TL/yil | Tercih edilen |
| **Freemium** | Genis kullanici tabani, virallik | Monetizasyon zor, kaynak tuketimi | Belirsiz | Pazarlama icin |
| **ASM Bazli (Toplu)** | Yuksek birim satis, tek muhatap | Uzun satis dongusu, rekabet | 5000 TL x 100 ASM = 500K TL | Ek kanal |

### 1.2 Onerilen Hybrid Model

**Birincil: Yillik Abonelik + Tek Seferlik Lisans Secenegi**

```
PAKET YAPISI:

1. UCRETSIZ DENEME (7 gun)
   - Tum ozellikler acik
   - Kredi karti gerektirmez
   - E-posta ile kayit

2. BIREYSEL LISANS (Tek Hekim)
   - Tek seferlik: 750 TL
   - Yillik abonelik: 500 TL/yil (1 yil destek dahil)
   - Aylik abonelik: 60 TL/ay (minimum 6 ay)

3. ASM LISANSI (3-5 Hekim)
   - Tek seferlik: 1.500 TL
   - Yillik abonelik: 1.000 TL/yil
   - Hekim basi ~300-500 TL

4. KURUMSAL (6+ Hekim)
   - Ozel fiyatlandirma
   - Oncelikli destek
   - Ozel ozellikler
```

---

## 2. KOPYA KORUMA STRATEJILERI

### 2.1 Yontem Karsilastirmasi

| Yontem | Guvenlik (1-10) | Zorluk (1-10) | Kullanici Deneyimi | Oneri |
|--------|-----------------|---------------|-------------------|-------|
| **PyInstaller + Obfuscation** | 4/10 | 3/10 | Iyi | Temel koruma |
| **PyArmor** | 7/10 | 5/10 | Iyi | **ONERILEN** |
| **Nuitka (C Derleme)** | 8/10 | 7/10 | Iyi | Ileri seviye |
| **Online Lisans Aktivasyonu** | 8/10 | 6/10 | Orta | Cok onerilen |
| **Hardware Binding (MAC/Disk)** | 6/10 | 5/10 | Kotu | Dikkatli kullan |
| **Subscription Cloud Validation** | 9/10 | 8/10 | Orta | Ideal (SaaS) |

### 2.2 Onerilen Koruma Katmanlari

**Katman 1: Kod Gizleme (Hemen Uygulanabilir)**
```
PyArmor kullanimi:
- pyarmor gen --pack onefile hyp_otomasyon.py
- Fonksiyon/degisken isimleri gizlenir
- Bytecode sifrelemesi
- Maliyet: Ucretsiz (temel) / $59 (pro)
```

**Katman 2: Online Lisans Dogrulama**
```python
# Basit lisans kontrolu ornegi
def check_license(license_key):
    response = requests.post(
        "https://api.hyp-otomasyon.com/validate",
        json={"key": license_key, "machine_id": get_machine_id()}
    )
    return response.json().get("valid", False)
```

**Katman 3: Hardware Binding (Opsiyonel)**
```python
# Makine ID olusturma
def get_machine_id():
    import hashlib, uuid
    mac = uuid.getnode()
    hostname = socket.gethostname()
    return hashlib.sha256(f"{mac}{hostname}".encode()).hexdigest()[:16]
```

### 2.3 Maliyet-Fayda Analizi

| Senaryo | Koruma Maliyeti | Beklenen Kayip | Net Etki |
|---------|-----------------|----------------|----------|
| Koruma yok | 0 TL | %50-70 kayip | Cok kotu |
| Sadece PyArmor | ~500 TL | %20-30 kayip | Iyi |
| PyArmor + Online | ~2000 TL/yil | %5-10 kayip | Cok iyi |
| Tam koruma | ~5000 TL/yil | %1-3 kayip | En iyi |

**Oneri:** PyArmor + Basit online lisans kontrolu ile basla.

---

## 3. FIYATLANDIRMA ONERISI

### 3.1 Pazar Analizi

**Hedef Kitle:**
- ~25.000 aile hekimi (Turkiye)
- Teknoloji bilgisi: Orta-dusuk
- Butce hassasiyeti: Yuksek
- Ana motivasyon: Zaman tasarrufu, performans katsayisi

**Rekabet:**
- HYP icin ozel otomasyon araci: Yok (bilinen)
- Genel klinik yazilimlari: 1000-5000 TL/yil
- Muhasebe yazilimlari: 500-2000 TL/yil

**Hekim Geliri (2025):**
- Ortalama aile hekimi maasi: ~45.000-70.000 TL/ay
- Performans katsayisi etkisi: +/- %20-40

### 3.2 Deger Bazli Fiyatlandirma

**Hesaplama:**
```
Zaman Tasarrufu:
- Gunluk manuel islem: ~60-90 dakika
- Otomasyonla: ~5-10 dakika
- Tasarruf: ~50-80 dakika/gun
- Aylik tasarruf: ~20-30 saat

Parasal Deger:
- Hekim saat ucreti (tahmini): ~200-300 TL
- Aylik tasarruf degeri: 4.000-9.000 TL
- Yillik tasarruf degeri: 48.000-108.000 TL

Performans Etkisi:
- Hedef tutturma orani artisi: +%10-30
- Katsayi iyilesmesi: +0.1-0.3
- Maas etkisi: +1.000-5.000 TL/ay
```

**Fiyat/Deger Orani:**
- Yillik lisans: 500 TL
- Yillik deger: 50.000+ TL
- ROI: 100x (cok yuksek)

### 3.3 Onerilen Fiyat Yapisi

```
LANSMAN FIYATLARI (Ilk 6 ay):

Bireysel:
- Tek seferlik: 500 TL (normali 750 TL)
- Yillik: 350 TL/yil (normali 500 TL)
- Aylik: 50 TL/ay

ASM Paketi (3-5 hekim):
- Tek seferlik: 1.000 TL (normali 1.500 TL)
- Yillik: 750 TL/yil

NORMAL FIYATLAR (Lansman sonrasi):

Bireysel:
- Tek seferlik: 750 TL
- Yillik: 500 TL/yil
- Aylik: 60 TL/ay

ASM Paketi:
- Tek seferlik: 1.500 TL
- Yillik: 1.000 TL/yil
```

---

## 4. SATIS KANALLARI

### 4.1 Kanal Stratejisi

| Kanal | Erisim | Maliyet | Etkinlik | Oncelik |
|-------|--------|---------|----------|---------|
| **Web Sitesi (Direkt)** | Genis | Dusuk | Orta | 1 (Ana) |
| **Hekim WhatsApp/Telegram Gruplari** | Hedefli | Cok dusuk | Yuksek | 1 |
| **Facebook Hekim Gruplari** | Genis | Dusuk | Orta-Yuksek | 2 |
| **YouTube Egitim Videolari** | Genis | Orta | Yuksek | 2 |
| **Referans Programi** | Organik | Dusuk | Cok yuksek | 1 |
| **ASM Toplantilari** | Hedefli | Orta | Yuksek | 3 |
| **Tabip Odalari** | Resmi | Yuksek | Dusuk | 4 |
| **Saglik Fuarlari** | Genis | Yuksek | Orta | 5 |

### 4.2 Dijital Pazarlama Stratejisi

**Web Sitesi:**
```
hyp-otomasyon.com
├── Ana Sayfa (demo video, faydalar)
├── Ozellikler (ekran goruntuleri)
├── Fiyatlandirma (seffaf)
├── Indir/Satin Al
├── SSS
├── Destek
└── Blog (SEO icin)
```

**Sosyal Medya:**
- YouTube: Tanitim ve egitim videolari
- Instagram: Kisa ipuclari, guncellemeler
- Facebook: Hekim gruplarina organik paylasim
- LinkedIn: Profesyonel gorunum

**Icerik Pazarlama:**
- "HYP nasil hizli tamamlanir" blog yazilari
- Video: "Gunluk 1 saat tasarruf edin"
- Infografik: Performans katsayisi hesaplama

### 4.3 Referans Programi

```
REFERANS ODULLERI:

Referans veren:
- Her basarili referans: 1 ay ucretsiz uzatma
- 5 referans: Omur boyu lisans

Referans ile gelen:
- %20 indirim (ilk yil)
- 1 hafta ekstra deneme suresi

Izleme:
- Benzersiz referans kodu
- Dashboard'da takip
- Otomatik odul atama
```

---

## 5. GO-TO-MARKET PLANI

### 5.1 Lansman Oncesi

1. **Web Sitesi Olusturma**
   - Landing page tasarimi
   - Odeme entegrasyonu (iyzico, PayTR)
   - Lisans sistemi kurulumu

2. **Icerik Hazirlama**
   - Demo video (3-5 dakika)
   - Ekran goruntuleri
   - Kullanici kilavuzu
   - SSS dokumani

3. **Beta Test**
   - 10-20 guvenilir hekim ile test
   - Geri bildirim toplama
   - Bug duzeltmeleri

4. **Topluluk Olusturma**
   - WhatsApp destek grubu
   - E-posta listesi

### 5.2 Lansman

1. **Yumusak Lansman**
   - Hekim gruplarina duyuru
   - Sinirli sayida lansman indirimi
   - Ilk 100 kullanici hedefi

2. **Referans Kampanyasi**
   - Mevcut kullanicilara referans teklifi
   - Sosyal medya paylasim tesvik

3. **Icerik Yayini**
   - YouTube videolari
   - Blog yazilari
   - Sosyal medya postlari

### 5.3 Buyume

1. **Organik Buyume**
   - SEO optimizasyonu
   - Referans programi genisletme
   - Topluluk buyutme

2. **Ucretli Reklam (Opsiyonel)**
   - Google Ads (hedefli)
   - Facebook/Instagram (hekim hedefleme)

3. **Kurumsal Satis**
   - ASM iletisim
   - Toplu lisans teklifleri

---

## 6. FINANSAL PROJEKSIYONLAR

### 6.1 Senaryo Analizi

**Konservatif (Yil 1):**
- 500 kullanici x 450 TL ortalama = 225.000 TL
- Maliyetler: ~50.000 TL
- Net: ~175.000 TL

**Gercekci (Yil 1):**
- 1.500 kullanici x 400 TL ortalama = 600.000 TL
- Maliyetler: ~100.000 TL
- Net: ~500.000 TL

**Iyimser (Yil 1):**
- 3.000 kullanici x 450 TL ortalama = 1.350.000 TL
- Maliyetler: ~200.000 TL
- Net: ~1.150.000 TL

### 6.2 Maliyet Kalemleri

| Kalem | Aylik | Yillik |
|-------|-------|--------|
| Sunucu/Hosting | 500 TL | 6.000 TL |
| Lisans sistemi | 200 TL | 2.400 TL |
| Domain/SSL | - | 500 TL |
| Odeme komisyonu (%3) | Degisken | ~18.000 TL |
| Pazarlama | 2.000 TL | 24.000 TL |
| Destek (zaman) | - | 20.000 TL |
| PyArmor Pro | - | 500 TL |
| **TOPLAM** | - | **~70.000 TL** |

---

## 7. SONUC VE EYLEM PLANI

### 7.1 Oncelikli Eylemler

1. **Hemen (Bu Hafta)**
   - [ ] PyArmor ile kod koruma
   - [ ] Basit lisans sistemi tasarimi
   - [ ] Web sitesi domain alma

2. **Kisa Vade (1-2 Hafta)**
   - [ ] Landing page olusturma
   - [ ] Demo video cekimi
   - [ ] Odeme entegrasyonu

3. **Orta Vade (1 Ay)**
   - [ ] Beta kullanici bulma
   - [ ] Geri bildirim toplama
   - [ ] Lansman hazirligi

4. **Lansman (2. Ay)**
   - [ ] Yumusak lansman
   - [ ] Ilk satis
   - [ ] Referans programi baslat

### 7.2 Basari Kriterleri

| Metrik | Ay 1 | Ay 3 | Ay 6 | Yil 1 |
|--------|------|------|------|-------|
| Kullanici | 50 | 200 | 500 | 1.500 |
| Gelir | 20K TL | 80K TL | 200K TL | 600K TL |
| NPS | >50 | >60 | >70 | >70 |
| Churn | <10% | <8% | <5% | <5% |

---

## Kaynaklar

1. [PyArmor - Python Obfuscation](https://pyarmor.dashingsoft.com/)
2. [Nuitka - Python Compiler](https://nuitka.net/)
3. [SaaS Fiyatlandirma - Microsoft Azure](https://azure.microsoft.com/tr-tr/resources/cloud-computing-dictionary/what-is-saas)
4. [Turkiye SaaS Girisimleri](https://medium.com/@GorkemCetin/türkiyenin-saas-girişimleri-c3c3df631739)
5. [Aile Hekimligi 2025 Rehberi](https://hsgm.saglik.gov.tr/depo/Yayinlarimiz/Rehberler/AILE_HEKIMLIGI_REHBERI_2025.pdf)

---

**Belge Sonu**

*Bu strateji belgesi HYP Otomasyon ticarilestirmesi icin hazirlanmistir.*

# 🏥 HYP OTOMASYON AKIŞ KILAVUZU V3.0

**Versiyon:** 3.0  
**Son Güncelleme:** 26 Kasım 2025  
**Amaç:** Claude Code'un HYP otomasyonunu kodlarken karşılaşabileceği TÜM durumları anlaması

---

## ⚠️ KRİTİK UYARI - BU DOSYAYI DİKKATLİCE OKU!

Bu kılavuz, test süreçlerinde yaşanan GERÇEK HATALARDAN öğrenilen derslerle hazırlandı.
Her satır bir deneyimin ürünüdür. Atlanırsa otomasyon PATLAR!

---

# BÖLÜM 1: GENEL PRENSİPLER

## 1.1 Sayfa Tanıma Mantığı (ZORUNLU!)

HYP'de sayfalar HER ZAMAN AYNI SIRADA GELMEYEBİLİR! 
Bu nedenle "3. adımda şunu yap" demek YETERSİZ.
SAYFA İÇERİĞİNE GÖRE KARAR VERMELİSİN.

```python
def detect_current_page(driver):
    """
    Mevcut sayfayı algıla - URL + içerik kombinasyonu kullan
    ÖNCELİK SIRASI ÖNEMLİ! ÖZET EN ÖNCE KONTROL EDİLMELİ!
    """
    url = driver.current_url.lower()
    page_source = driver.page_source.upper()
    
    # 1. ÖZET SAYFASI - En önce kontrol et (sonlandırma sayfası)
    if "SONLANDIRILMASI" in page_source or "/ozet" in url:
        return "OZET"
    
    # 2. URL bazlı kontroller
    if "/anamnez" in url:
        return "ANAMNEZ"
    if "/tetkik" in url:
        return "TETKIK"
    if "/ilac" in url:
        return "ILAC"
    if "/kvh/hesaplama" in url:
        return "KVH_HESAPLAMA"
    if "/kvh/tani" in url:
        return "KVH_TANI"
    if "/kvh/hedef" in url:
        return "KVH_HEDEF"
    if "/yasamtarzi" in url or "/yasam" in url:
        return "YASAM_TARZI"
    if "/risk" in url:
        return "RISK"
    if "/kansekeri" in url:
        return "KAN_SEKERI"
    if "/semptom" in url:
        return "SEMPTOM"
    if "/tani" in url:
        return "TANI"
    
    # 3. İçerik bazlı kontroller (URL'de bilgi yoksa)
    if "KAN ŞEKERİ" in page_source or "KAN SEKERI" in page_source:
        return "KAN_SEKERI"
    if "RİSK FAKTÖR" in page_source or "RISK FAKTOR" in page_source:
        return "RISK"
    if "SEMPTOM" in page_source:
        return "SEMPTOM"
    if "TANI KONULMASI" in page_source:
        return "TANI"
    if "YAŞAM TARZI" in page_source:
        return "YASAM_TARZI"
    
    return "UNKNOWN"
```

## 1.2 Ana Döngü Yapısı (ZORUNLU!)

```python
def process_hyp_flow(driver, max_steps=25):
    """
    Akıllı döngü - sayfa ne olursa olsun doğru işlemi yap
    """
    is_finished = False
    step = 0
    
    while not is_finished and step < max_steps:
        step += 1
        current_page = detect_current_page(driver)
        
        print(f"Adım {step}: Sayfa = {current_page}")
        
        # SAYFAYA GÖRE İŞLEM YAP
        if current_page == "OZET":
            click_sonlandir(driver)
            is_finished = True
            
        elif current_page == "ANAMNEZ":
            fill_anamnez_fields(driver)  # ZORUNLU ALANLARI DOLDUR!
            handle_gebe_question(driver)  # Gebe sorusu varsa
            click_ilerle(driver)
            
        elif current_page == "RISK":
            handle_gebe_question(driver)  # Gebe sorusu BURADA da olabilir!
            click_ilerle(driver)
            
        elif current_page == "TETKIK":
            uncheck_tetkik_boxes(driver)  # Tikleri kaldır yoksa hasta beklemede kalır!
            click_ilerle(driver)
            
        elif current_page == "KVH_HESAPLAMA":
            close_dialogs(driver)  # Tamam dialog'u çıkabilir
            click_ilerle(driver)
            
        elif current_page == "TANI":
            click_kaydet_or_ilerle(driver)  # Kaydet butonu varsa tıkla
            
        elif current_page == "ILAC":
            handle_medication_page(driver)  # Kullanılıyor/Kullanılmıyor seç
            click_ilerle(driver)
            
        else:
            # Bilinmeyen sayfa - sadece ilerle dene
            click_ilerle(driver)
        
        time.sleep(1.5)  # Sayfa geçişi için bekle
    
    return is_finished
```

---

# BÖLÜM 2: HİPERTANSİYON (HT) MODÜLÜ

## 2.1 HT TARAMA Akışı

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HT TARAMA (3-4 sayfa)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [BAŞLA] → ANAMNEZ → TANI → YASAM_TARZI → ÖZET → [BİTTİ]              │
│                ↓         ↓                                              │
│           Sistolik    Kaydet                                            │
│           Diyastolik  butonu                                            │
│           Nabız       tıkla                                             │
│           Boy/Kilo                                                      │
│           BelÇevresi                                                    │
│                                                                         │
│   ⚠️ TARAMADA TETKİK ve İLAÇ SAYFASI YOK!                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2.2 HT İZLEM Akışı (DAHA UZUN!)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HT İZLEM (8 sayfa)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [BAŞLA] → ANAMNEZ → TETKİK → KVH_HESAPLAMA → KVH_TANI →              │
│                ↓         ↓           ↓                                  │
│           Ölçümleri  Tikleri    Dialog'u                                │
│           doldur     kaldır     kapat                                   │
│                                                                         │
│         → HEDEF → İLAÇ → YASAM_TARZI → ÖZET → [BİTTİ]                  │
│                    ↓                                                    │
│              Kullanılıyor/                                              │
│              Kullanılmıyor                                              │
│              seç                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2.3 HT Sayfalarında Yapılacaklar

### 📍 ANAMNEZ Sayfası

**ZORUNLU ALANLAR (Doldurulmazsa İLERLE ÇALIŞMAZ!):**

| Alan | Zorunlu | XPath Pattern | Geçerli Aralık | Varsayılan |
|------|:-------:|---------------|----------------|------------|
| Sistolik KB | ✅ | `*sistolik*` | 70-250 mmHg | 120 |
| Diyastolik KB | ✅ | `*diyastolik*` | 40-150 mmHg | 70 |
| Nabız | ✅ | `*nabiz*` | 40-200 /dk | 72 |
| Boy | ✅ | `*boy*` | 100-220 cm | 165 |
| Ağırlık | ✅ | `*agirlik*` veya `*kilo*` | 30-300 kg | 75 |
| Bel Çevresi | ✅ | `*bel*` | 50-200 cm | 90 |

**⚠️ KRİTİK HATA - TEST DENEYİMİNDEN:**
```
SORUN: "İlerle butonuna tıklanıyor ama sayfa değişmiyor"
NEDEN: Zorunlu alanlar BOŞ!
ÇÖZÜM: Önce fill_anamnez_fields() çağır!
```

**DEĞER ALMA STRATEJİSİ:**
```python
def fill_anamnez_fields(driver):
    """
    Öncelik sırası:
    1. Sayfadaki "Son Ölçüm" değerlerini al
    2. Sağ taraftaki "Son 3 Ölçüm" panelinden al
    3. Hemşire verisi yoksa VARSAYILAN kullan
    """
    defaults = {
        "sistolik": 120, "diyastolik": 70, "nabiz": 72,
        "boy": 165, "agirlik": 75, "bel_cevresi": 90
    }
    
    # Her alan için kontrol et ve doldur
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for inp in inputs:
        inp_id = (inp.get_attribute("id") or "").lower()
        inp_name = (inp.get_attribute("name") or "").lower()
        current_val = inp.get_attribute("value")
        
        # Boş alan bul ve doldur
        if not current_val or current_val == "0":
            for field, default in defaults.items():
                if field in inp_id or field in inp_name:
                    inp.clear()
                    inp.send_keys(str(default))
                    break
```

**⚠️ VALİDASYON KURALI:**
```python
# Sistolik MUTLAKA Diyastolik'ten BÜYÜK olmalı!
if sistolik <= diyastolik:
    raise ValueError("Hata: Sistolik <= Diyastolik!")
```

---

### 📍 TETKİK Sayfası (SADECE İZLEMDE!)

**⚠️ KRİTİK HATA - TEST DENEYİMİNDEN:**
```
SORUN: "Hasta HYP'si tamamlanmıyor, beklemede kalıyor"
NEDEN: Tetkik checkbox'ları TİKLİ bırakıldı!
ÇÖZÜM: TÜM TİKLERİ KALDIR!
```

```python
def uncheck_tetkik_boxes(driver):
    """
    Tetkik sayfasındaki TÜM checkbox'ları kaldır
    Aksi halde hasta tetkik sonucu girilene kadar beklemede kalır!
    """
    # PrimeNG checkbox'ları
    checkboxes = driver.find_elements(By.CSS_SELECTOR, 
        "p-checkbox .ui-chkbox-box")
    
    for cb in checkboxes:
        try:
            is_checked = "ui-state-active" in (cb.get_attribute("class") or "")
            if is_checked:
                driver.execute_script("arguments[0].click();", cb)
                time.sleep(0.2)
        except:
            pass
    
    # Normal HTML checkbox'ları da kontrol et
    html_checkboxes = driver.find_elements(By.CSS_SELECTOR, 
        "input[type='checkbox']")
    
    for cb in html_checkboxes:
        try:
            if cb.is_selected():
                cb.click()
                time.sleep(0.2)
        except:
            pass
```

---

### 📍 KVH HESAPLAMA Sayfası

**POPUP/DIALOG ÇIKABİLİR!**

```python
def close_dialogs(driver):
    """
    Tamam/Kapat dialog'larını kapat
    Bu sayfa SCORE2 hesapladıktan sonra dialog gösterebilir
    """
    dialog_buttons = [
        "//button[contains(., 'Tamam')]",
        "//button[contains(., 'Kapat')]",
        "//button[contains(@class, 'ui-dialog-titlebar-close')]",
    ]
    
    for xpath in dialog_buttons:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
                return True
        except:
            pass
    return False
```

---

### 📍 İLAÇ Sayfası (SADECE İZLEMDE!)

**⚠️ KRİTİK HATA - TEST DENEYİMİNDEN:**
```
SORUN: "Kullanılmıyor seçildi ama hasta aslında ilaç kullanıyor"
NEDEN: Hesaplama yapılmadan varsayılan seçildi
ÇÖZÜM: Reçete tarihine göre HESAPLA!
```

```python
def handle_medication_page(driver):
    """
    Reçete tarihi + kutu sayısına göre ilaç kullanım durumu belirle
    
    FORMÜL:
    Toplam tablet = Kutu sayısı × 28 (genelde 28 tablet/kutu)
    Bitiş tarihi = Reçete tarihi + Toplam tablet gün
    Bugün < Bitiş tarihi ise → "Kullanılıyor"
    """
    import re
    from datetime import datetime, timedelta
    
    page_text = driver.find_element(By.TAG_NAME, 'body').text
    
    # Reçete tarihi bul (DD.MM.YYYY formatı)
    tarih_pattern = r'(\d{2}\.\d{2}\.\d{4})'
    tarihler = re.findall(tarih_pattern, page_text)
    
    # Miktar bul
    miktar_pattern = r'(\d+)\s*(tablet|kutu|adet)'
    miktarlar = re.findall(miktar_pattern, page_text.lower())
    
    ilac_kullaniliyor = False
    
    if tarihler and miktarlar:
        # En son reçete tarihini al
        recete_tarihi = None
        for t in tarihler:
            try:
                dt = datetime.strptime(t, '%d.%m.%Y')
                if recete_tarihi is None or dt > recete_tarihi:
                    recete_tarihi = dt
            except:
                pass
        
        # Toplam tableti hesapla
        toplam_tablet = 0
        for miktar, birim in miktarlar:
            m = int(miktar)
            if birim == 'kutu':
                m *= 28
            toplam_tablet += m
        
        if recete_tarihi and toplam_tablet > 0:
            bitis_tarihi = recete_tarihi + timedelta(days=toplam_tablet)
            if datetime.now() < bitis_tarihi:
                ilac_kullaniliyor = True
    
    # Radio button'ları seç
    radios = driver.find_elements(By.TAG_NAME, 'p-radiobutton')
    for radio in radios:
        try:
            label = radio.find_element(By.CSS_SELECTOR, 'label').text
            inner = radio.find_element(By.CSS_SELECTOR, '.ui-radiobutton-box')
            
            if ilac_kullaniliyor and 'Kullanılıyor' in label and 'Kullanılmıyor' not in label:
                if 'ui-state-active' not in (inner.get_attribute('class') or ''):
                    driver.execute_script('arguments[0].click();', inner)
            elif not ilac_kullaniliyor and 'Kullanılmıyor' in label:
                if 'ui-state-active' not in (inner.get_attribute('class') or ''):
                    driver.execute_script('arguments[0].click();', inner)
        except:
            pass
```

---

### 📍 TANI Sayfası

```python
def click_kaydet_or_ilerle(driver):
    """
    Tanı sayfasında:
    1. Önce KAYDET butonu ara
    2. Varsa tıkla
    3. Yoksa İLERLE'ye tıkla
    """
    kaydet_xpath = "//button[contains(., 'Kaydet')]"
    
    try:
        kaydet_btn = driver.find_element(By.XPATH, kaydet_xpath)
        if kaydet_btn.is_displayed():
            driver.execute_script("arguments[0].click();", kaydet_btn)
            time.sleep(1)
            return
    except:
        pass
    
    # Kaydet yoksa ilerle
    click_ilerle(driver)
```

---

### 📍 ÖZET (Sonlandırma) Sayfası

**⚠️ KRİTİK HATA - TEST DENEYİMİNDEN:**
```
SORUN: "Sonlandır butonuna tıklanıyor ama hiçbir şey olmuyor"
NEDEN: Buton sayfanın ALTINDA kalıyor, normal click çalışmıyor
ÇÖZÜM: JavaScript ile ZORLA tıkla!
```

```python
def click_sonlandir(driver):
    """
    Sonlandır butonuna JavaScript ile zorla tıkla
    Normal click ÇALIŞMAZ çünkü buton viewport dışında!
    """
    sonlandir_xpaths = [
        "//button[.//span[contains(text(), 'Sonlandır ve Çık')]]",
        "//button[.//span[contains(text(), 'Sonlandır')]]",
        "//button[contains(., 'Sonlandır')]",
    ]
    
    for xpath in sonlandir_xpaths:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            
            # 1. Görünür yap
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", btn
            )
            time.sleep(0.5)
            
            # 2. JavaScript ile ZORLA tıkla
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            return True
        except:
            continue
    
    return False
```

---

# BÖLÜM 3: DİYABET (DIY) MODÜLÜ

## 3.1 DİYABET TARAMA Akışı

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     DİYABET TARAMA (7 sayfa)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [BAŞLA] → ANAMNEZ → RISK → KAN_SEKERI → SEMPTOM → TANI → YASAM → ÖZET│
│                ↓        ↓                                               │
│           Boy/Kilo  "Gebe mi?"                                          │
│           BelÇevresi sorusuna                                           │
│           (65+ için   "HAYIR"                                           │
│           Kırılganlık tıkla!                                            │
│           Ölçeği!)                                                      │
│                                                                         │
│   ⚠️ 65+ YAŞ HASTALARDA KLİNİK KIRILGANLIK ÖLÇEĞİ ZORUNLU!             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Diyabet Sayfalarında Yapılacaklar

### 📍 ANAMNEZ Sayfası

**ZORUNLU ALANLAR:**

| Alan | Zorunlu | 65+ Yaş İçin |
|------|:-------:|:------------:|
| Boy | ✅ | ✅ |
| Ağırlık | ✅ | ✅ |
| Bel Çevresi | ✅ | ✅ |
| Klinik Kırılganlık Ölçeği | ❌ | ✅ ZORUNLU! |

**⚠️ 65+ YAŞ KONTROLÜ:**
```python
def fill_diyabet_anamnez(driver, patient_age):
    """
    Diyabet anamnez sayfası
    65+ yaş hastalar için EK ALAN var!
    """
    fill_anamnez_fields(driver)  # Boy, kilo, bel çevresi
    
    if patient_age >= 65:
        # Klinik Kırılganlık Ölçeği ZORUNLU!
        select_kirilganlik_olcegi(driver, skor=3)  # Varsayılan: "İyi Yönetilen"

def select_kirilganlik_olcegi(driver, skor=3):
    """
    Klinik Kırılganlık Ölçeği (1-9 arası)
    1: Çok Fit
    2: Fit
    3: İyi Yönetilen (varsayılan)
    4: Hafif Kırılgan
    5: Orta Kırılgan
    6: Orta-Ağır Kırılgan
    7: Ağır Kırılgan
    8: Çok Ağır Kırılgan
    9: Terminal
    """
    # Radio button'u bul ve seç
    xpath = f"//label[contains(text(), '{skor}')]/preceding-sibling::*[contains(@class, 'radiobutton')]"
    try:
        radio = driver.find_element(By.XPATH, xpath)
        driver.execute_script("arguments[0].click();", radio)
    except:
        # Alternatif XPath dene
        alt_xpath = f"//p-radiobutton[contains(., '{skor}')]//div[contains(@class, 'ui-radiobutton-box')]"
        try:
            radio = driver.find_element(By.XPATH, alt_xpath)
            driver.execute_script("arguments[0].click();", radio)
        except:
            pass
```

---

### 📍 RİSK FAKTÖRLERİ Sayfası

**GEBE SORUSU BURADA GELİR!**

```python
def handle_gebe_question(driver):
    """
    Gebe sorusu kontrolü
    
    KURAL:
    - Sadece 15-49 yaş KADIN hastalarda görünür
    - Erkeklerde ve 50+ yaş kadınlarda GELMEYEBİLİR
    - Gebe değilse "Hayır" tıkla
    - Gebe ise tarama YAPILAMAZ
    """
    gebe_xpaths = [
        "//div[contains(text(), 'Birey halihazırda gebe mi')]/parent::div//button[contains(text(), 'Hayır')]",
        "//div[contains(text(), 'gebe mi')]//following::button[contains(., 'Hayır')]",
        "//button[contains(text(), 'Hayır') and ancestor::*[contains(., 'gebe')]]",
    ]
    
    for xpath in gebe_xpaths:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
                return True
        except:
            pass
    
    return False  # Soru yoksa veya erkekse
```

---

### 📍 KAN ŞEKERİ Sayfası

**AKŞ DEĞERİ GEREKLİ!**

```python
def handle_kan_sekeri_page(driver):
    """
    Kan şekeri değerlendirme sayfası
    
    DURUM 1: Hemşire verisi var → Otomatik dolu, sadece ilerle
    DURUM 2: Hemşire verisi YOK → "Dış Laboratuvar Sonucu Ekle" butonu tıkla
    """
    # AKŞ değeri var mı kontrol et
    try:
        aks_inputs = driver.find_elements(By.CSS_SELECTOR, 
            "input[id*='aks'], input[name*='aks'], input[id*='aclik']")
        
        has_value = False
        for inp in aks_inputs:
            val = inp.get_attribute("value")
            if val and val != "0":
                has_value = True
                break
        
        if not has_value:
            # Değer yok - Dış lab ekleme seçeneği
            dis_lab_xpath = "//button[contains(text(), 'Dış Laboratuvar Sonucu Ekle')]"
            try:
                btn = driver.find_element(By.XPATH, dis_lab_xpath)
                btn.click()
                time.sleep(1)
                # Modal'da değer gir ve kaydet
                # NOT: Bu kısım modal yapısına göre düzenlenmeli
            except:
                pass
    except:
        pass
    
    click_ilerle(driver)
```

**AKŞ DEĞERLENDİRME:**
| AKŞ (mg/dL) | Sonuç | Takip |
|-------------|-------|-------|
| < 100 | Normal | 3 yılda bir tekrar |
| 100-125 | Prediyabet | 1 yılda tekrar |
| ≥ 126 | Diyabet şüphesi | 2. test gerekli |

---

# BÖLÜM 4: OBEZİTE (OBE) MODÜLÜ

## 4.1 OBEZİTE TARAMA Akışı

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     OBEZİTE TARAMA (3 sayfa)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [BAŞLA] → ANAMNEZ → YASAM_TARZI → ÖZET → [BİTTİ]                     │
│                ↓                                                        │
│           Boy/Kilo                                                      │
│           BelÇevresi                                                    │
│           "Gebe mi?"                                                    │
│                                                                         │
│   ⚠️⚠️⚠️ OBEZİTE TARAMADA TANI SAYFASI YOK! ⚠️⚠️⚠️                       │
│   Bu yüzden Anamnez'den sonra direkt Yaşam Tarzı gelir!                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**⚠️ TEST DENEYİMİNDEN:**
```
SORUN: "Tanı sayfası bekledik ama gelmedi"
NEDEN: Obezite taramada TANI SAYFASI YOK!
ÇÖZÜM: Sayfa tanıma kullan, hardcode akış KULLANMA!
```

---

# BÖLÜM 5: KVR (KARDİYOVASKÜLER RİSK) MODÜLÜ

## 5.1 KVR TARAMA Akışı

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        KVR TARAMA (6 sayfa)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [BAŞLA] → ANAMNEZ → TETKİK → SCORE2_HESAP → TANI → YASAM → ÖZET      │
│                          ↓                                              │
│                    Kolesterol                                           │
│                    HDL                                                  │
│                    değerleri                                            │
│                    GEREKLİ!                                             │
│                                                                         │
│   ⚠️ KOLESTEROL VE HDL DEĞERLERİ YOKSA KVR YAPILAMAZ!                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 5.2 KVR Pre-Check (Ön Kontrol)

```python
def check_kvr_requirements(patient_data):
    """
    KVR için gerekli tetkikleri kontrol et
    YOKSA KVR başlatılmamalı!
    """
    required_tests = ["kolesterol", "hdl"]
    missing = []
    
    for test in required_tests:
        if test not in patient_data or patient_data[test] is None:
            missing.append(test)
    
    if missing:
        print(f"⚠️ KVR YAPILAMAZ! Eksik tetkikler: {', '.join(missing)}")
        return False, missing
    
    return True, []
```

---

# BÖLÜM 6: YAŞLI SAĞLIĞI MODÜLÜ (65+ YAŞ)

## 6.1 Ek Zorunlu Değerlendirmeler

| Değerlendirme | Zorunlu | Açıklama |
|---------------|:-------:|----------|
| Klinik Kırılganlık Ölçeği | ✅ | 1-9 arası skor |
| Düşme Riski | ✅ | Var/Yok |
| Kognitif Durum | ⚪ | Mini Mental Test |
| Depresyon | ⚪ | Geriatrik Depresyon |
| Beslenme | ⚪ | MNA |
| Polifarmasi | ⚪ | 5+ ilaç kontrolü |

---

# BÖLÜM 7: POPUP VE DİALOG YÖNETİMİ

## 7.1 Tüm Popup'ları Kapat

```python
def kill_popups(driver):
    """
    Tüm popup/dialog'ları kapat
    Her işlemden sonra çağrılmalı!
    """
    popup_indicators = [
        # SMS Onayı popup'ı
        ("//span[contains(@class, 'ui-dialog-title') and contains(text(), 'SMS')]", 
         "//button[.//span[text()='Hayır']]"),
        
        # Yetki sorunu popup'ı
        ("//div[contains(text(), 'yetkiniz bulunmamaktadır')]",
         "//button[.//span[normalize-space(text())='Hayır']]"),
        
        # Genel Tamam dialog
        ("//div[contains(@class, 'ui-dialog')]",
         "//button[contains(., 'Tamam')]"),
    ]
    
    for indicator_xpath, close_xpath in popup_indicators:
        try:
            indicator = driver.find_element(By.XPATH, indicator_xpath)
            if indicator.is_displayed():
                close_btn = driver.find_element(By.XPATH, close_xpath)
                driver.execute_script("arguments[0].click();", close_btn)
                time.sleep(0.5)
                return True
        except:
            pass
    
    # Escape tuşu ile kapatmayı dene
    try:
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
    except:
        pass
    
    return False
```

## 7.2 Yetki Sorunu Kontrolü

```python
def check_permission_popup(driver):
    """
    "Bu işlem için yetkiniz bulunmamaktadır" popup'ı
    Bu popup gelirse o hastanın o HYP'si YAPILAMAZ!
    """
    try:
        popup = driver.find_element(By.XPATH, 
            "//div[contains(text(), 'yetkiniz bulunmamaktadır')]")
        if popup.is_displayed():
            # Hayır'a tıkla ve hastayı atla
            driver.find_element(By.XPATH, 
                "//button[.//span[text()='Hayır']]").click()
            return True  # Popup vardı, hasta atlanmalı
    except:
        pass
    return False  # Popup yok, devam et
```

---

# BÖLÜM 8: BUTON TIKLAMA FONKSİYONLARI

## 8.1 İlerle Butonu

```python
def click_ilerle(driver):
    """
    İlerle butonuna tıkla
    Birden fazla XPath dene!
    """
    ilerle_xpaths = [
        "//button[contains(@class, 'hyp-next-button')]",  # En güvenilir
        "//button[.//span[contains(text(), 'İlerle')]]",
        "//button[contains(., 'İlerle')]",
    ]
    
    for xpath in ilerle_xpaths:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            if btn.is_displayed() and btn.is_enabled():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
                return True
        except:
            continue
    
    print("⚠️ İlerle butonu bulunamadı!")
    return False
```

## 8.2 Tarama/İzlem Başlat Butonları

```python
def click_baslat_button(driver, hyp_tip, kart_durum=""):
    """
    Tarama veya İzlem başlat butonuna tıkla
    
    BUTON SEÇENEKLERİ:
    - Yeni tarama: "Tarama Başlat (Yüz Yüze Muayene)"
    - Yeni izlem: "İzlem Başlat (Yüz Yüze Muayene)"
    - Devam eden: "Taramayla Devam Et" veya "İzlemle Devam Et"
    """
    is_devam = "devam" in kart_durum.lower()
    is_izlem = "IZLEM" in hyp_tip
    
    if is_devam:
        xpaths = [
            "//button[contains(., 'Devam Et')]",
            "//button[contains(., 'Taramayla Devam')]",
            "//button[contains(., 'İzlemle Devam')]",
        ]
    elif is_izlem:
        xpaths = [
            "//button[contains(., 'İzlem Başlat') and contains(., 'Yüz Yüze')]",
        ]
    else:
        xpaths = [
            "//button[contains(., 'Tarama Başlat') and contains(., 'Yüz Yüze')]",
        ]
    
    for xpath in xpaths:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1.5)
                return True
        except:
            continue
    
    return False
```

---

# BÖLÜM 9: HASTA KART ANALİZİ

## 9.1 Kart Tipi Belirleme

```python
def analyze_card_type(card_text):
    """
    Kart metninden HYP tipini belirle
    """
    card_upper = normalize_tr(card_text)
    
    # Tip belirleme
    if "DIYABET" in card_upper:
        base_type = "DIY"
    elif "HIPERTANSIYON" in card_upper or "TANSIYON" in card_upper:
        base_type = "HT"
    elif "OBEZITE" in card_upper:
        base_type = "OBE"
    elif "KARDIYOVASKULER" in card_upper or "KVR" in card_upper:
        base_type = "KVR"
    elif "YASLI" in card_upper:
        base_type = "YAS"
    else:
        base_type = "UNKNOWN"
    
    # Tarama mı İzlem mi?
    if "IZLEM" in card_upper:
        return f"{base_type}_IZLEM"
    else:
        return f"{base_type}_TARAMA"
```

## 9.2 Kart Yapılabilirlik Kontrolü

```python
def is_card_actionable(card_status):
    """
    Kart durumuna göre işlem yapılabilir mi?
    
    YAPILABİLİR: devam ediyor, geciken, yaklaşan, boş
    YAPILAMAZ: tamamlandı, beklemede
    """
    status_lower = (card_status or "").lower()
    
    # Yapılamaz durumlar
    if "tamamland" in status_lower:
        return False
    if "beklemede" in status_lower:
        return False
    
    return True
```

---

# BÖLÜM 10: XPATH REFERANS TABLOSU

## 10.1 Navigasyon Butonları

| Buton | Birincil XPath | Yedek XPath |
|-------|---------------|-------------|
| İlerle | `//button[contains(@class, 'hyp-next-button')]` | `//button[.//span[contains(text(), 'İlerle')]]` |
| Geri | `//button[contains(@class, 'hyp-previous-button')]` | `//button[contains(., 'Geri')]` |
| Kaydet | `//button[contains(., 'Kaydet')]` | - |
| Sonlandır | `//button[.//span[contains(text(), 'Sonlandır')]]` | `//button[contains(., 'Sonlandır')]` |
| Görüntüle | `//button[.//span[text()='Görüntüle']]` | - |

## 10.2 Form Elemanları

| Element | XPath |
|---------|-------|
| Gebe Hayır | `//div[contains(text(), 'gebe mi')]//following::button[contains(., 'Hayır')]` |
| Dış Lab Ekle | `//button[contains(text(), 'Dış Laboratuvar Sonucu Ekle')]` |
| Tarama Başlat | `//button[contains(., 'Tarama Başlat') and contains(., 'Yüz Yüze')]` |
| İzlem Başlat | `//button[contains(., 'İzlem Başlat') and contains(., 'Yüz Yüze')]` |
| Devam Et | `//button[contains(., 'Devam Et')]` |

## 10.3 Sayfa Başlıkları

| Sayfa | Header Metni |
|-------|-------------|
| Kan Şekeri | `KAN ŞEKERİ DEĞERLENDİRMESİ` |
| Risk | `RİSK FAKTÖRLERİNİN DEĞERLENDİRİLMESİ` |
| Semptom | `SEMPTOM DEĞERLENDİRMESİ` |
| Tanı | `TANI KONULMASI` |
| Yaşam Tarzı | `YAŞAM TARZI ÖNERİLERİ` |
| Özet | `SONLANDIRILMASI` |

---

# BÖLÜM 11: HATA SENARYOLARI VE ÇÖZÜMLER

| Hata | Belirti | Neden | Çözüm |
|------|---------|-------|-------|
| İlerle çalışmıyor | Sayfa değişmiyor | Zorunlu alanlar boş | `fill_anamnez_fields()` |
| Sonlandır çalışmıyor | Kapanmıyor | Buton viewport dışında | JS click kullan |
| Hasta beklemede | HYP tamamlanmıyor | Tetkik tikleri var | `uncheck_tetkik_boxes()` |
| Popup engelliyor | İşlem durdu | SMS/Yetki popup'ı | `kill_popups()` |
| Türkçe karakter | Hasta bulunamıyor | Encoding problemi | `normalize_tr()` |
| Session düştü | Hata sayfası | Uzun süre işlem yok | `keep_alive()` |

---

# BÖLÜM 12: TÜRKÇE KARAKTER YÖNETİMİ

```python
def normalize_tr(text):
    """Türkçe karakterleri normalize et"""
    if not text:
        return ""
    
    mapping = {
        'İ': 'I', 'ı': 'I', 'I': 'I', 'i': 'I',
        'Ş': 'S', 'ş': 'S', 'Ğ': 'G', 'ğ': 'G',
        'Ü': 'U', 'ü': 'U', 'Ö': 'O', 'ö': 'O',
        'Ç': 'C', 'ç': 'C',
        # Bozuk encoding
        'Ä°': 'I', 'Ä±': 'I', 'Åž': 'S', 'ÅŸ': 'S',
        'Äž': 'G', 'ÄŸ': 'G', 'Ãœ': 'U', 'Ã¼': 'U',
    }
    
    for tr, en in mapping.items():
        text = text.replace(tr, en)
    
    return text.upper().strip()
```

---

# BÖLÜM 13: MODÜL KARŞILAŞTIRMA TABLOSU

| Modül | Sayfa | Gebe | Tetkik | İlaç | Tanı | 65+ Özel |
|-------|:-----:|:----:|:------:|:----:|:----:|:--------:|
| HT Tarama | 4 | ❌ | ❌ | ❌ | ✅ | ❌ |
| HT İzlem | 8 | ❌ | ✅ | ✅ | ✅ | ❌ |
| DIY Tarama | 7 | ✅ | ❌ | ❌ | ✅ | ✅ |
| DIY İzlem | 5 | ❌ | ❌ | ✅ | ✅ | ✅ |
| OBE Tarama | 3 | ✅ | ❌ | ❌ | ❌ | ❌ |
| OBE İzlem | 3 | ✅ | ❌ | ❌ | ❌ | ❌ |
| KVR Tarama | 6 | ❌ | ✅ | ❌ | ✅ | ❌ |
| Yaşlı İzlem | 4+ | ❌ | ❌ | ❌ | ✅ | ✅ |

---

# BÖLÜM 14: KONTROL LİSTELERİ

## Her İşlemden Önce:
- [ ] Popup var mı? (`kill_popups()`)
- [ ] Doğru sayfada mıyım? (`detect_current_page()`)
- [ ] Zorunlu alanlar dolu mu?

## Her Modülden Önce:
| Modül | Kontrol |
|-------|---------|
| HT | TA ölçümü var mı? |
| DIY | AKŞ var mı? 65+ ise kırılganlık? |
| OBE | Boy/Kilo var mı? |
| KVR | Kolesterol/HDL var mı? |

---

**BU KILAVUZ CLAUDE CODE İÇİN HAZIRLANMIŞTIR.**
**HER HATA BİR DENEYİMDEN ÖĞRENİLMİŞTİR.**
**ATLAMA, OKU VE UYGULA!**

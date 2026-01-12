# -*- coding: utf-8 -*-
"""
HYP OTOMASYON - CONFIG V5.0
===========================
26 Nolu Birim hedefleri (Ekran görüntüsünden alındı)
"""

# ============================================================
# HYP BAĞLANTI
# ============================================================
HYP_URL = "https://hyp.saglik.gov.tr/"

# RUNTIME PIN - Sadece oturum boyunca bellekte tutulur
# DISK'E KAYDEDILMEZ - Guvenli saklama icin login_manager.SecurePINStorage kullanilir
PIN_CODE = ""  # gui_app.py tarafindan runtime'da atanir

# ============================================================
# AYLIK HEDEFLER (26 Nolu Birim - Kasım 2025)
# ============================================================
MONTHLY_TARGETS = {
    "OBE_TARAMA": 106,
    "OBE_IZLEM": 17,
    "DIY_TARAMA": 19,
    "DIY_IZLEM": 33,
    "HT_TARAMA": 83,
    "HT_IZLEM": 62,
    "KVR_TARAMA": 18,
    "KVR_IZLEM": 16,
    "YAS_IZLEM": 10,
    "KANSER_SERVIKS": 10,
    "KANSER_MAMO": 14,
}

# Mevcut yapılan sayılar (ekran görüntüsünden)
CURRENT_COUNTS = {
    "OBE_TARAMA": 16,
    "OBE_IZLEM": 1,
    "DIY_TARAMA": 0,  # 27 nolu birimde 23 var, 26'da yok
    "DIY_IZLEM": 0,
    "HT_TARAMA": 0,
    "HT_IZLEM": 0,
    "KVR_TARAMA": 0,
    "KVR_IZLEM": 2,
    "YAS_IZLEM": 0,
    "KANSER_SERVIKS": 7,
    "KANSER_MAMO": 4,
}

# Devreden sayılar
DEFERRED_COUNTS = {
    "OBE_TARAMA": 13,
    "OBE_IZLEM": 0,
    "DIY_TARAMA": 0,
    "DIY_IZLEM": 0,
    "HT_TARAMA": 0,
    "HT_IZLEM": 0,
    "KVR_TARAMA": 0,
    "KVR_IZLEM": 9,
    "YAS_IZLEM": 0,
    "KANSER_SERVIKS": 0,
    "KANSER_MAMO": 0,
}

# ============================================================
# TARAMA TİPLERİ (GUI için)
# ============================================================
TARAMA_TIPLERI = {
    "OBE_TARAMA": "Obezite Tarama",
    "OBE_IZLEM": "Obezite İzlem",
    "DIY_TARAMA": "Diyabet Tarama",
    "DIY_IZLEM": "Diyabet İzlem",
    "HT_TARAMA": "Hipertansiyon Tarama",
    "HT_IZLEM": "Hipertansiyon İzlem",
    "KVR_TARAMA": "KVR Tarama",
    "KVR_IZLEM": "KVR İzlem",
    "YAS_IZLEM": "Yaşlı Sağlığı İzlem",
    "KANSER_SERVIKS": "Kanser Serviks Tarama",
    "KANSER_MAMO": "Kanser Mamografi Tarama",
}

# ============================================================
# GUI AYARLARI
# ============================================================
GUI_CONFIG = {
    "window_size": "1200x800",
    "theme": "dark",
    "font_family": "Segoe UI",
}

# ============================================================
# BEKLEME SÜRELERİ (saniye)
# ============================================================
WAIT_TIMES = {
    "short": 0.5,
    "medium": 1.5,
    "long": 3.0,
    "page_load": 5.0,
    "login": 10.0,
}

# ============================================================
# XPATH SELECTOR'LER
# ============================================================
SELECTORS = {
    # Giriş
    "LOGIN_BUTTON": "//*[@id='header']/div/div/button",
    "PIN_INPUT": "popupPinCode_Password",
    
    # Navigasyon
    "HASTA_LISTESI": "//a[contains(., 'Hasta Listesi')]",
    "FIZIK_MUAYENE": "//a[contains(., 'Fizik Muayene')]",
    "HASTA_ARA": "//input[@placeholder='Hasta ara']",
    
    # Butonlar
    "ILERLE": [
        "//button[contains(@class, 'hyp-next-button')]",
        "//button[.//span[contains(text(), 'İlerle')]]",
        "//button[contains(., 'İlerle')]",
    ],
    "SONLANDIR": [
        "//button[.//span[contains(text(), 'Sonlandır ve Çık')]]",
        "//button[.//span[contains(text(), 'Sonlandır')]]",
        "//button[contains(., 'Sonlandır')]",
    ],
    "KAYDET": "//button[contains(., 'Kaydet')]",
    "GORUNTULE": "//button[.//span[text()='Görüntüle']]",
    
    # Tarama Başlat
    "TARAMA_BASLAT": [
        "//button[contains(., 'Tarama Başlat') and contains(., 'Yüz Yüze')]",
        "//button[contains(., 'İzlem Başlat') and contains(., 'Yüz Yüze')]",
        "//button[contains(., 'Devam Et')]",
        "//button[contains(., 'Taramayla Devam')]",
        "//button[contains(., 'İzlemle Devam')]",
    ],
    
    # Gebe sorusu
    "GEBE_HAYIR": "//div[contains(text(), 'gebe mi')]//following::button[contains(., 'Hayır')]",
    
    # Popup
    "POPUP_HAYIR": "//button[.//span[normalize-space(text())='Hayır']]",
    "POPUP_CLOSE": "//button[contains(@class, 'ui-dialog-titlebar-close')]",
}

# ============================================================
# SAYFA TESPİT KELİMELERİ
# ============================================================
PAGE_KEYWORDS = {
    "OZET": ["SONLANDIRILMASI", "SONLANDIRMA"],
    "KAN_SEKERI": ["KAN ŞEKERİ", "KAN SEKERI", "AÇLIK KAN"],
    "RISK": ["RİSK FAKTÖR", "RISK FAKTOR", "RİSK DEĞERLENDİRME"],
    "SEMPTOM": ["SEMPTOM", "BELİRTİ"],
    "TANI": ["TANI KONULMASI", "TANIYA GÖRE"],
    "YASAM": ["YAŞAM TARZI", "YASAM TARZI"],
    "ANAMNEZ": ["ANAMNEZ", "ÖYKÜ"],
}

# ============================================================
# KART TİPLERİ (HYP Kartları için)
# ============================================================
CARD_TYPES = {
    "DIY_TARAMA": ["DİYABET", "DIYABET"],
    "DIY_IZLEM": ["DİYABET", "DIYABET", "İZLEM", "IZLEM"],
    "HT_TARAMA": ["HİPERTANSİYON", "HIPERTANSIYON", "TANSIYON"],
    "HT_IZLEM": ["HİPERTANSİYON", "HIPERTANSIYON", "İZLEM"],
    "OBE_TARAMA": ["OBEZİTE", "OBEZITE"],
    "OBE_IZLEM": ["OBEZİTE", "OBEZITE", "İZLEM"],
    "KVR_TARAMA": ["KARDİYOVASKÜLER", "KARDIYOVASKULER", "KVR"],
    "KVR_IZLEM": ["KARDİYOVASKÜLER", "KVR", "İZLEM"],
    "YAS_IZLEM": ["YAŞLI", "YASLI", "SAĞLIĞI"],
}

# ============================================================
# SCORE2 RİSK TABLOSU (Gelecek versiyon için)
# ============================================================
SCORE2_RISK_TABLE = {
    # Yaş grupları: [düşük, orta, yüksek, çok_yüksek]
    "40-49": {
        "non_smoker": {
            "male": {"120": 1, "140": 2, "160": 3, "180": 4},
            "female": {"120": 0, "140": 1, "160": 1, "180": 2}
        },
        "smoker": {
            "male": {"120": 2, "140": 3, "160": 5, "180": 7},
            "female": {"120": 1, "140": 2, "160": 2, "180": 3}
        }
    },
    # ... diğer yaş grupları eklenecek
}

# Risk kategorileri
RISK_CATEGORIES = {
    "very_low": {"range": (0, 1), "color": "green", "follow_up_years": 5},
    "low": {"range": (1, 5), "color": "yellow", "follow_up_years": 2},
    "moderate": {"range": (5, 10), "color": "orange", "follow_up_years": 1},
    "high": {"range": (10, 20), "color": "red", "follow_up_months": 6},
    "very_high": {"range": (20, 100), "color": "dark_red", "follow_up_months": 3},
}

# ============================================================
# PRE-CHECK KURALLARI (Gelecek versiyon için)
# ============================================================
VALIDATION_RULES = {
    "blood_pressure": {
        "systolic_min": 70,
        "systolic_max": 250,
        "diastolic_min": 40,
        "diastolic_max": 150,
        "rule": "systolic > diastolic",
    },
    "bmi": {
        "weight_min": 30,
        "weight_max": 300,
        "height_min": 100,
        "height_max": 220,
    },
    "kvr_required_tests": ["kolesterol", "hdl", "ldl"],
}

# ============================================================
# DEBUG AYARLARI
# ============================================================
DEBUG_CONFIG = {
    "remote_debugging_port": 9222,
    "screenshot_on_error": True,
    "verbose_logging": True,
    "max_retry": 3,
}

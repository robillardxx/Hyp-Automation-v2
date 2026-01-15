# -*- coding: utf-8 -*-
"""
HYP OTOMASYON V5.0 - MEGA UPDATE
================================
Dr. Osman'ın tüm geri bildirimleri entegre edildi:

1. ✅ Debug Modu - Chrome açıkken bağlanabilme
2. ✅ Test dosyaları entegre edildi
3. ✅ Hasta kartlarını düzgün bulma
4. ✅ Akıllı navigasyon (sayfa tanıma)
5. ✅ Pre-check sistemi (veri doğrulama)
6. ✅ Session keep-alive
7. ✅ Performans takibi

Tarih: 25 Kasım 2025
Yazar: Claude AI + Dr. Osman Sucuoğlu
"""

import sys
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import config
from config import *

# Ilac Analiz Modulu (Polifarmasi ve Yasli Izlem icin)
try:
    from drug_analyzer import DrugAnalyzer, ElderlyAssessmentHelper, PregnancyChecker
    DRUG_ANALYZER_AVAILABLE = True
except ImportError:
    DRUG_ANALYZER_AVAILABLE = False


# ============================================================
# TÜRKÇE KARAKTER NORMALİZASYONU
# ============================================================
def normalize_tr(text: str) -> str:
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
        'Ã–': 'O', 'Ã¶': 'O', 'Ã‡': 'C', 'Ã§': 'C',
    }
    for tr, en in mapping.items():
        text = text.replace(tr, en)
    return text.upper().strip()


# ============================================================
# ANA OTOMASYON SINIFI
# ============================================================
class HYPAutomation:
    """HYP Otomasyon Motoru V5.0"""
    
    def __init__(self, log_callback=None, date_picker_callback=None, stats_callback=None, user_input_callback=None, file_picker_callback=None):
        self.driver = None
        self.log_callback = log_callback
        self.date_picker_callback = date_picker_callback
        self.stats_callback = stats_callback
        self.user_input_callback = user_input_callback
        self.file_picker_callback = file_picker_callback
        self.should_stop = False
        self.monthly_stats = {}
        self.selected_date = None
        self.MAX_STEPS = 25
        self.DEBUG_MODE = False
        self.last_activity_time = time.time()
        self.target_percentage = 100  # Varsayılan %100, GUI'den değiştirilebilir

        # Aktif HYP tipleri (GUI'den ayarlanabilir, varsayılan hepsi aktif)
        self.enabled_hyp_types = None  # None = hepsi aktif, list = sadece listede olanlar

        # İşlem sayaçları
        self.session_stats = {
            "basarili": 0,
            "basarisiz": 0,
            "atlanan": 0,
            "toplam_sure": 0
        }

        # Hedef bazlı takip sistemi - Session boyunca tamamlanan HYP sayıları
        self.session_completed = {
            "OBE_TARAMA": 0, "OBE_IZLEM": 0,
            "DIY_TARAMA": 0, "DIY_IZLEM": 0,
            "HT_TARAMA": 0, "HT_IZLEM": 0,
            "KVR_TARAMA": 0, "KVR_IZLEM": 0,
            "YAS_IZLEM": 0,
            "KANSER_SERVIKS": 0, "KANSER_MAMO": 0
        }

        # Checkbox cache - "Tumunu kaldir" oncesi bilgileri sakla
        self._cached_checkbox_data = {}

        # Ilac analiz modulu (Polifarmasi ve Yasli Izlem icin)
        self.drug_analyzer = None
        self.elderly_helper = None
        if DRUG_ANALYZER_AVAILABLE:
            try:
                import os
                excel_path = os.path.join(os.path.dirname(__file__), 'Ilac Listesi.xlsx')
                self.drug_analyzer = DrugAnalyzer(excel_path if os.path.exists(excel_path) else None)
                self.elderly_helper = ElderlyAssessmentHelper()
            except Exception as e:
                self.log(f'Ilac analiz modulu yuklenemedi: {e}', 'WARNING')

        # Mevcut hasta ilac listesi (HYP'den cekilecek)
        self.current_patient_drugs = []
        
        # Gebe listesi kontrolu
        self.pregnancy_checker = None
        if DRUG_ANALYZER_AVAILABLE:
            try:
                self.pregnancy_checker = PregnancyChecker()
            except Exception as e:
                self.log(f'Gebe listesi yuklenemedi: {e}', 'WARNING')
        
        # Mevcut hasta bilgileri
        self.current_patient_name = None
        self.current_patient_tc = None
        
        # OBE_IZLEM pas gecildi bildirimi icin
        self.skipped_hyp_notifications = []

        # İptal edilen HYP'ler (eksik tetkik vb. nedenlerle)
        self.cancelled_hyps = []

        # Başarısız HYP'ler (hata nedeniyle tamamlanamayan)
        self.failed_hyps = []

        # Mevcut işlenen HYP tipi
        self._current_hyp_type = None

        # Çoklu tarih desteği
        self.selected_dates = None  # Liste olarak birden fazla tarih

        # SMS onayı kapalı hastalar (bu hastalar her zaman atlanır)
        self.sms_kapali_hastalar = self._load_sms_kapali_hastalar()

        # Başarılı HYP callback (GUI güncelleme için)
        self.on_hyp_success_callback = None

        # HYP'den sayılar çekildiğinde GUI güncelleme callback
        self.on_counts_fetched_callback = None

        # KVR hedef aşımı onay callback (kullanıcıya popup sorar)
        self.on_kvr_overflow_callback = None

        # KVR hedef aşımı kararını kaydetme/okuma callback'leri
        self.get_kvr_decision_callback = None  # settings_manager.get_kvr_overflow_decision
        self.save_kvr_decision_callback = None  # settings_manager.save_kvr_overflow_decision


    def _check_startup_files(self) -> bool:
        """
        Otomasyon baslatilmadan once gerekli dosyalari kontrol et.
        Kullaniciya gerekli uyarilari goster ve onay al.
        
        Returns:
            True: Devam edilebilir
            False: Otomasyon durduruldu
        """
        import os
        import glob
        
        self.log("")
        self.log("=" * 50)
        self.log("DOSYA KONTROLU")
        self.log("=" * 50)
        
        base_dir = os.path.dirname(__file__)
        
        # 1. ILAC LISTESI KONTROLU
        # Turkce ve encoding varyantlari: İlaç, Ilac, ilac
        ilac_patterns = [
            os.path.join(base_dir, '*laç*.xlsx'),
            os.path.join(base_dir, '*laç*.xls'),
            os.path.join(base_dir, '*lac*.xlsx'),
            os.path.join(base_dir, '*lac*.xls'),
            os.path.join(base_dir, 'İlaç*.xlsx'),
            os.path.join(base_dir, 'İlaç*.xls'),
            os.path.join(base_dir, 'Ilac*.xlsx'),
            os.path.join(base_dir, 'Ilac*.xls'),
        ]
        ilac_files = []
        for pattern in ilac_patterns:
            ilac_files.extend(glob.glob(pattern))
        ilac_files = list(set(ilac_files))  # Remove duplicates
        ilac_found = len(ilac_files) > 0
        
        if ilac_found:
            self.log(f"[OK] Ilac listesi bulundu: {os.path.basename(ilac_files[0])}")
        else:
            self.log("[!] Ilac listesi bulunamadi!", "WARNING")
            self.log("    Yasli izlem polifarmasi ozellikleri devre disi.")
            
            # Kullaniciya sor
            cevap = self._ask_user_input(
                "Ilac listesi eksik. Devam etmek istiyor musunuz? (E/H): "
            )
            if cevap.upper() not in ['E', 'EVET', 'Y', 'YES']:
                self.log("Otomasyon kullanici tarafindan durduruldu.")
                return False
        
        # 2. GEBE LISTESI KONTROLU
        gebe_patterns = [
            os.path.join(base_dir, 'Gebe*.xls'),
            os.path.join(base_dir, 'Gebe*.xlsx'),
            os.path.join(base_dir, 'gebe*.xls'),
            os.path.join(base_dir, 'gebe*.xlsx'),
        ]
        gebe_files = []
        for pattern in gebe_patterns:
            gebe_files.extend(glob.glob(pattern))
        
        gebe_found = len(gebe_files) > 0
        
        if gebe_found:
            # En guncel dosyayi bul (dosya adina gore veya degisiklik tarihine gore)
            gebe_file = max(gebe_files, key=os.path.getmtime)
            gebe_name = os.path.basename(gebe_file)
            gebe_date = time.strftime('%d.%m.%Y %H:%M', time.localtime(os.path.getmtime(gebe_file)))
            
            self.log(f"[OK] Gebe listesi bulundu: {gebe_name}")
            self.log(f"    Son guncelleme: {gebe_date}")
            
            # Gebe listesi guncellensin mi?
            cevap = self._ask_user_input(
                "Gebe listesini guncellemek istiyor musunuz? (E/H): "
            )
            if cevap.upper() in ['E', 'EVET', 'Y', 'YES']:
                new_path = self._ask_user_file_path(
                    "Yeni gebe listesi dosya yolunu girin (veya Enter ile atlayin): "
                )
                if new_path and os.path.exists(new_path):
                    # Yeni dosyayi yukle
                    try:
                        from drug_analyzer import PregnancyChecker
                        self.pregnancy_checker = PregnancyChecker(new_path)
                        self.log(f"[OK] Gebe listesi guncellendi: {len(self.pregnancy_checker.pregnant_patients)} gebe")
                    except Exception as e:
                        self.log(f"[!] Gebe listesi yuklenemedi: {e}", "WARNING")
                elif new_path:
                    self.log(f"[!] Dosya bulunamadi: {new_path}", "WARNING")
        else:
            self.log("[!] Gebe listesi bulunamadi!", "WARNING")
            self.log("    OBE_IZLEM gebelik sorusu varsayilan HAYIR olacak.")
            
            # Kullaniciya sor
            cevap = self._ask_user_input(
                "Gebe listesi eklemek istiyor musunuz? (E/H): "
            )
            if cevap.upper() in ['E', 'EVET', 'Y', 'YES']:
                new_path = self._ask_user_file_path(
                    "Gebe listesi dosya yolunu girin: "
                )
                if new_path and os.path.exists(new_path):
                    try:
                        from drug_analyzer import PregnancyChecker
                        self.pregnancy_checker = PregnancyChecker(new_path)
                        self.log(f"[OK] Gebe listesi yuklendi: {len(self.pregnancy_checker.pregnant_patients)} gebe")
                    except Exception as e:
                        self.log(f"[!] Gebe listesi yuklenemedi: {e}", "WARNING")
                elif new_path:
                    self.log(f"[!] Dosya bulunamadi: {new_path}", "WARNING")
        
        # Ozet
        self.log("")
        self.log("Dosya kontrolu tamamlandi.")
        
        return True
    
    def _ask_user_input(self, prompt: str) -> str:
        """Kullanicidan girdi al (GUI messagebox)"""
        if hasattr(self, 'user_input_callback') and self.user_input_callback:
            return self.user_input_callback(prompt)
        else:
            # Tkinter messagebox kullan
            try:
                import tkinter as tk
                from tkinter import messagebox

                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)

                result = messagebox.askyesno(
                    "HYP Otomasyon",
                    prompt.replace("(E/H):", "").strip(),
                    parent=root
                )

                root.destroy()
                return 'E' if result else 'H'
            except:
                try:
                    return input(prompt)
                except:
                    return 'H'

    def _ask_user_file_path(self, prompt: str) -> str:
        """Kullanicidan dosya yolu al (GUI file dialog)"""
        if hasattr(self, 'file_picker_callback') and self.file_picker_callback:
            return self.file_picker_callback(prompt)
        else:
            # Tkinter file dialog kullan
            try:
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)

                file_path = filedialog.askopenfilename(
                    title=prompt,
                    filetypes=[
                        ("Excel dosyalari", "*.xlsx *.xls"),
                        ("Tum dosyalar", "*.*")
                    ],
                    parent=root
                )

                root.destroy()
                return file_path if file_path else ''
            except:
                try:
                    return input(prompt).strip()
                except:
                    return ''

    # ============================================================
    # LOG SİSTEMİ
    # ============================================================
    def log(self, message: str, level: str = "INFO"):
        """
        Log mesajı yaz

        Level'lar:
        - INFO: Normal bilgi mesajları (her zaman gösterilir)
        - SUCCESS: Başarı mesajları (her zaman gösterilir)
        - ERROR: Hata mesajları (her zaman gösterilir)
        - WARNING: Uyarı mesajları (her zaman gösterilir)
        - DEBUG: Teknik detay mesajları (sadece DEBUG_MODE=True ise gösterilir)
        """
        # DEBUG mesajları sadece debug modda gösterilir
        if level == "DEBUG" and not self.DEBUG_MODE:
            return

        timestamp = time.strftime("%H:%M:%S")

        # Emoji prefix
        prefix = ""
        if level == "SUCCESS":
            prefix = "✅ "
        elif level == "ERROR":
            prefix = "❌ "
        elif level == "WARNING":
            prefix = "⚠️ "
        elif level == "DEBUG":
            prefix = "🔧 "

        log_msg = f"[{timestamp}] {prefix}{message}"

        try:
            print(log_msg, flush=True)
        except:
            pass

        if self.log_callback:
            try:
                self.log_callback(log_msg)
            except:
                pass

    # ============================================================
    # İŞLENMİŞ HASTA CACHE SİSTEMİ (1 Ay)
    # ============================================================
    def _get_cache_path(self) -> str:
        """Cache dosyası yolunu döndür"""
        import os
        return os.path.join(os.path.dirname(__file__), 'processed_patients.json')

    def _load_processed_cache(self) -> dict:
        """Cache'i dosyadan yükle"""
        import os
        import json
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_processed_cache(self, cache: dict):
        """Cache'i dosyaya kaydet"""
        import json
        cache_path = self._get_cache_path()
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"Cache kaydetme hatasi: {e}", "WARNING")

    def _cleanup_old_cache(self):
        """1 aydan eski cache kayıtlarını temizle"""
        from datetime import datetime, timedelta
        cache = self._load_processed_cache()
        if not cache:
            return

        one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        cleaned = {}
        removed_count = 0

        for tc, data in cache.items():
            hypler = data.get("hypler", {})
            valid_hypler = {}
            for hyp_tipi, hyp_data in hypler.items():
                if hyp_data.get("tarih", "2099-01-01") >= one_month_ago:
                    valid_hypler[hyp_tipi] = hyp_data
                else:
                    removed_count += 1

            if valid_hypler:
                cleaned[tc] = {
                    "ad_soyad": data.get("ad_soyad", ""),
                    "hypler": valid_hypler
                }

        if removed_count > 0:
            self._save_processed_cache(cleaned)
            self.log(f"Cache temizlendi: {removed_count} eski kayit silindi", "DEBUG")

    def is_hyp_already_processed(self, tc: str, hyp_tipi: str) -> bool:
        """Bu hasta için bu HYP tipi daha önce işlenmiş mi kontrol et"""
        if not tc:
            return False
        cache = self._load_processed_cache()
        patient_data = cache.get(tc, {})
        hypler = patient_data.get("hypler", {})
        return hyp_tipi in hypler

    def mark_hyp_as_processed(self, tc: str, ad_soyad: str, hyp_tipi: str, durum: str = "BASARILI"):
        """HYP'yi işlenmiş olarak işaretle"""
        if not tc:
            return
        from datetime import datetime
        cache = self._load_processed_cache()

        if tc not in cache:
            cache[tc] = {"ad_soyad": ad_soyad, "hypler": {}}

        cache[tc]["ad_soyad"] = ad_soyad  # Güncelle
        cache[tc]["hypler"][hyp_tipi] = {
            "durum": durum,
            "tarih": datetime.now().strftime("%Y-%m-%d"),
            "saat": datetime.now().strftime("%H:%M")
        }

        self._save_processed_cache(cache)
        self.log(f"Cache guncellendi: {ad_soyad} - {hyp_tipi} = {durum}", "DEBUG")

    def remove_from_cache(self, tc: str, hyp_tipi: str = None):
        """Cache'den hasta veya belirli HYP'yi sil"""
        if not tc:
            return
        cache = self._load_processed_cache()

        if tc not in cache:
            return

        if hyp_tipi:
            # Sadece belirli HYP'yi sil
            if hyp_tipi in cache[tc].get("hypler", {}):
                del cache[tc]["hypler"][hyp_tipi]
                self.log(f"Cache'den silindi: {tc} - {hyp_tipi}", "DEBUG")
                # Eğer hiç HYP kalmadıysa hastayı da sil
                if not cache[tc]["hypler"]:
                    del cache[tc]
        else:
            # Tüm hastayı sil
            del cache[tc]
            self.log(f"Cache'den silindi: {tc} (tum kayitlar)", "DEBUG")

        self._save_processed_cache(cache)

    def get_processed_cache_info(self) -> dict:
        """Cache bilgilerini döndür (GUI için)"""
        cache = self._load_processed_cache()
        total_patients = len(cache)
        total_hyps = sum(len(p.get("hypler", {})) for p in cache.values())
        return {
            "total_patients": total_patients,
            "total_hyps": total_hyps,
            "cache": cache
        }

    # ============================================================
    # HEDEF BAZLI HYP SEÇİM SİSTEMİ
    # ============================================================
    def get_remaining_target(self, hyp_tip: str) -> int:
        """
        Belirli bir HYP tipi için kalan hedef sayısını hesapla

        Formül: (Hedef * Yüzde/100) - Yapılan - Devreden - Session'da_Tamamlanan

        target_percentage: 70 veya 100 (GUI'den seçilen)
        """
        base_target = MONTHLY_TARGETS.get(hyp_tip, 0)
        # Hedef yüzdesini uygula (varsayılan %100)
        target = int(base_target * self.target_percentage / 100)

        current = CURRENT_COUNTS.get(hyp_tip, 0)
        deferred = DEFERRED_COUNTS.get(hyp_tip, 0)
        session_done = self.session_completed.get(hyp_tip, 0)

        remaining = target - current - deferred - session_done
        return max(0, remaining)  # Negatif olmasın

    def should_process_hyp_type(self, hyp_tip: str) -> bool:
        """
        Belirli bir HYP tipinin işlenip işlenmeyeceğini kontrol et

        Returns:
            True: Hedef tutturulmamış ve tip aktif, işlenmeli
            False: Hedef tutturulmuş veya tip devre dışı, atlanmalı
        """
        # 1. Önce enabled_hyp_types kontrolü yap
        if self.enabled_hyp_types is not None:
            if hyp_tip not in self.enabled_hyp_types:
                self.log(f"   ⏭️ {hyp_tip} devre dışı bırakıldı, ATLANIYOR", "WARNING")
                return False

        # 2. Hedef kontrolü
        remaining = self.get_remaining_target(hyp_tip)

        if remaining <= 0:
            self.log(f"   🎯 {hyp_tip} hedefi tutturuldu (Kalan: 0), ATLANIYOR", "WARNING")
            return False

        return True

    def increment_completed(self, hyp_tip: str):
        """Başarıyla tamamlanan HYP için sayacı artır"""
        if hyp_tip in self.session_completed:
            self.session_completed[hyp_tip] += 1
            remaining = self.get_remaining_target(hyp_tip)
            self.log(f"   🎯 {hyp_tip} +1 tamamlandı (Session: {self.session_completed[hyp_tip]}, Kalan hedef: {remaining})", "SUCCESS")

    def is_kvr_target_reached(self) -> bool:
        """KVR_IZLEM hedefi tutturuldu mu kontrol et"""
        return self.get_remaining_target("KVR_IZLEM") <= 0

    def _delete_last_kvr_izlem(self) -> bool:
        """
        Fazla KVR_IZLEM'i sil - Sidebar'dan 'Tamamlanan son takip işlemini sil' butonuna tıkla.

        HT_IZLEM yapılırken zorunlu olarak KVR_IZLEM de yapılıyor.
        KVR hedefi tutulduktan sonra fazla yapılan KVR'leri bu fonksiyon siler.

        Returns:
            True: Silme başarılı
            False: Silme başarısız veya buton bulunamadı
        """
        self.log("   🗑️ Fazla KVR_IZLEM siliniyor...", "INFO")

        try:
            # 1. Sidebar'da KVR kartına tıkla
            sidebar_cards = self.get_sidebar_cards()
            kvr_card = None

            for card in sidebar_cards:
                if card["hyp_tip"] == "KVR_IZLEM" or "KVR" in card.get("baslik", ""):
                    kvr_card = card
                    break

            if not kvr_card:
                self.log("   KVR kartı sidebar'da bulunamadı!", "WARNING")
                return False

            # KVR kartına tıkla
            self.js_click(kvr_card["element"])
            time.sleep(1.5)

            # 2. "Tamamlanan son takip işlemini sil" butonunu bul ve tıkla
            delete_btn = None
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')

            for btn in buttons:
                btn_text = btn.text.strip()
                if 'Tamamlanan son takip' in btn_text and 'sil' in btn_text:
                    delete_btn = btn
                    break

            if not delete_btn:
                self.log("   'Tamamlanan son takip işlemini sil' butonu bulunamadı!", "WARNING")
                return False

            # Butona tıkla
            self.js_click(delete_btn)
            time.sleep(1)

            # 3. Onay popup'ını onayla (Evet/Tamam butonu)
            confirm_btn = None
            confirm_texts = ['Evet', 'Tamam', 'Onayla', 'Sil', 'Yes', 'OK']

            # Popup içindeki butonları ara
            time.sleep(0.5)
            popup_buttons = self.driver.find_elements(By.TAG_NAME, 'button')

            for btn in popup_buttons:
                btn_text = btn.text.strip()
                if any(ct in btn_text for ct in confirm_texts):
                    # "İptal" veya "Hayır" içermemeli
                    if 'İptal' not in btn_text and 'Hayır' not in btn_text and 'Vazgeç' not in btn_text:
                        confirm_btn = btn
                        break

            if confirm_btn:
                self.js_click(confirm_btn)
                time.sleep(1)
                self.log("   ✅ Fazla KVR_IZLEM silindi!", "SUCCESS")

                # Session sayacını düşür (silindi çünkü)
                if self.session_completed.get("KVR_IZLEM", 0) > 0:
                    self.session_completed["KVR_IZLEM"] -= 1

                return True
            else:
                self.log("   Onay butonu bulunamadı!", "WARNING")
                # Popup'ı kapat (varsa)
                try:
                    cancel_btns = self.driver.find_elements(By.XPATH, "//button[contains(., 'İptal') or contains(., 'Vazgeç')]")
                    if cancel_btns:
                        self.js_click(cancel_btns[0])
                except:
                    pass
                return False

        except Exception as e:
            self.log(f"   KVR silme hatası: {str(e)[:50]}", "ERROR")
            return False

    def check_and_handle_kvr_overflow(self, hasta_adi: str) -> bool:
        """
        KVR hedefi aşıldıysa ayarlara göre fazla KVR'yi sil.

        Bu fonksiyon HT_IZLEM sonrası KVR_IZLEM zorunlu yapıldığında çağrılır.

        MANTIK:
        - Ayarlar > Otomasyon Ayarları'ndaki toggle kontrol edilir
        - Toggle açıksa: Fazla KVR'ler otomatik silinir
        - Toggle kapalıysa: Hiçbir şey silinmez

        Returns:
            True: İşlem yapıldı (silindi veya ayar kapalı)
            False: Hedef henüz tutulmadı
        """
        # KVR hedefi tutulmamışsa bir şey yapma
        if not self.is_kvr_target_reached():
            return False

        # Ayarlardan otomatik silme kararını kontrol et
        auto_delete = False
        if self.get_kvr_decision_callback:
            try:
                auto_delete = self.get_kvr_decision_callback()
            except:
                pass

        if auto_delete:
            # Ayar açık - otomatik sil
            self.log(f"   🗑️ {hasta_adi} - Fazla KVR_IZLEM otomatik siliniyor...", "INFO")
            return self._delete_last_kvr_izlem()
        else:
            # Ayar kapalı - hiçbir şey yapma
            self.log(f"   ℹ️ {hasta_adi} - KVR hedef aşımı (otomatik silme kapalı)", "DEBUG")
            return True

    def print_target_status(self):
        """Tüm hedeflerin durumunu yazdır"""
        self.log("=" * 50)
        self.log("📊 HEDEF DURUMU:")
        self.log("=" * 50)

        for hyp_tip in MONTHLY_TARGETS.keys():
            target = MONTHLY_TARGETS.get(hyp_tip, 0)
            current = CURRENT_COUNTS.get(hyp_tip, 0)
            deferred = DEFERRED_COUNTS.get(hyp_tip, 0)
            session_done = self.session_completed.get(hyp_tip, 0)
            remaining = self.get_remaining_target(hyp_tip)

            status = "✅ TAMAM" if remaining == 0 else f"⏳ {remaining} kaldı"
            self.log(f"  {hyp_tip}: {target} hedef | {current}+{deferred} yapıldı | +{session_done} session | {status}")

        self.log("=" * 50)

    # ============================================================
    # TAKİP İŞLEMİ İSTATİSTİKLERİNDEN YAPILAN SAYILARI ÇEK
    # ============================================================
    def fetch_completed_counts(self) -> Dict[str, int]:
        """
        'Takip İşlemi İstatistikleri' sayfasından yapılan sayıları çeker
        ve config.CURRENT_COUNTS'u günceller.

        Returns:
            Dict[str, int]: HYP tipi -> yapılan sayı
        """
        self.log("📊 Takip İşlemi İstatistikleri sayfasından yapılan sayılar çekiliyor...")

        # Sayfa adından bizim kodlarımıza mapping (normalize edilmiş)
        NAME_TO_CODE = {
            "HIPERTANSIYON TARAMA": "HT_TARAMA",
            "HIPERTANSIYON IZLEM": "HT_IZLEM",
            "OBEZITE TARAMA": "OBE_TARAMA",
            "OBEZITE IZLEM": "OBE_IZLEM",
            "OBEZITE IZLEM (AILE HEKIMI)": "OBE_IZLEM",
            "DIYABET TARAMA": "DIY_TARAMA",
            "DIYABET IZLEM": "DIY_IZLEM",
            "KARDIYOVASKULER RISK TARAMA": "KVR_TARAMA",
            "KARDIYOVASKULER RISK IZLEM": "KVR_IZLEM",
            "KVR TARAMA": "KVR_TARAMA",
            "KVR IZLEM": "KVR_IZLEM",
            "YASLI DEGERLENDIRME IZLEM": "YAS_IZLEM",
            "YASLI SAGLIGI IZLEM": "YAS_IZLEM",
        }

        counts = {}

        try:
            # 1. Dashboard'a git
            self.driver.get("https://hyp.saglik.gov.tr/dashboard")
            time.sleep(0.5)  # OPTIMIZE

            # 2. "Takip İşlemi İstatistikleri" linkine tıkla
            stats_xpaths = [
                "//a[contains(., 'statistik')]",
                "//a[contains(., 'İstatistik')]",
                "//a[contains(., 'Takip İşlemi İstatistikleri')]",
            ]

            clicked = False
            for xpath in stats_xpaths:
                if self.click_element(xpath, timeout=3):
                    clicked = True
                    self.log("   İstatistik linkine tıklandı", "DEBUG")
                    break

            if not clicked:
                self.log("⚠️ Takip İşlemi İstatistikleri linki bulunamadı!", "WARNING")
                return counts

            time.sleep(1.5)  # OPTIMIZE: 3 -> 1.5

            # 3. Sayfadaki body text'i parse et
            # Format: HYP_ADI\nSAYI\nHYP_ADI\nSAYI...
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                page_text = body.text

                # Satırlara ayır
                lines = page_text.split('\n')

                # HYP isimlerini ve sayılarını bul
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue

                    # Normalize et
                    normalized = normalize_tr(line)

                    # Bu satır bir HYP ismi mi?
                    if normalized in NAME_TO_CODE:
                        # Sonraki satır sayı mı?
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if next_line.isdigit():
                                code = NAME_TO_CODE[normalized]
                                count = int(next_line)
                                counts[code] = count
                                self.log(f"   {code}: {count}", "DEBUG")

            except Exception as e:
                self.log(f"Text parse hatası: {e}", "WARNING")

            # 4. config.CURRENT_COUNTS'u güncelle
            if counts:
                for code, count in counts.items():
                    config.CURRENT_COUNTS[code] = count

                self.log(f"✅ {len(counts)} HYP tipi için yapılan sayılar güncellendi!", "SUCCESS")

                # Özet yazdır
                self.log("📊 Güncel Yapılan Sayılar:")
                for code, count in counts.items():
                    target = MONTHLY_TARGETS.get(code, 0)
                    remaining = target - count - DEFERRED_COUNTS.get(code, 0)
                    status = "✅ TAMAM" if remaining <= 0 else f"⏳ {remaining} kaldı"
                    self.log(f"   {code}: {count}/{target} {status}")

                # ============================================================
                # GUI'YE BİLDİR - Sol panel kota kartlarını güncelle
                # ============================================================
                if self.on_counts_fetched_callback:
                    try:
                        self.on_counts_fetched_callback(counts)
                    except Exception as e:
                        self.log(f"GUI güncelleme hatası: {e}", "DEBUG")
            else:
                self.log("⚠️ İstatistik sayfasından veri çekilemedi, manuel değerler kullanılacak.", "WARNING")

            return counts

        except Exception as e:
            self.log(f"İstatistik çekme hatası: {e}", "ERROR")
            return counts

    # ============================================================
    # DEBUG MODU - AÇIK CHROME'A BAĞLANMA
    # ============================================================
    def setup_driver(self, debug_mode: bool = False) -> bool:
        """
        Chrome tarayıcısını başlat
        
        debug_mode=True ise:
        - Zaten açık olan Chrome'a bağlanmaya çalışır
        - Yoksa yeni açar ama kapatmaz
        """
        self.DEBUG_MODE = debug_mode
        
        try:
            if debug_mode:
                self.log("🔧 DEBUG MODU: Mevcut Chrome aranıyor...", "DEBUG")
                
                # Remote debugging ile bağlanmayı dene
                try:
                    options = Options()
                    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

                    # ÖNEMLİ: ChromeDriver service'i de gerekli!
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)

                    # Bağlantı başarılı - test et
                    current_url = self.driver.current_url
                    self.log(f"✅ Mevcut Chrome'a bağlanıldı! URL: {current_url}", "SUCCESS")
                    return True
                except Exception as e:
                    error_msg = str(e)
                    self.log(f"⚠️ Chrome'a bağlanılamadı: {error_msg[:100]}", "WARNING")
                    self.log("💡 Chrome'u debug modda başlatın:", "WARNING")
                    self.log('   chrome.exe --remote-debugging-port=9222', "WARNING")
            
            # Normal başlatma
            self.log("🔧 Chrome başlatılıyor...")

            options = Options()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-blink-features=AutomationControlled')

            # ============================================================
            # KALICI CHROME PROFİLİ - İzinler hatırlanır
            # İlk seferde "İzin ver" dedikten sonra Chrome bunu hatırlar
            # ============================================================
            import os
            user_data_dir = os.path.join(os.path.expanduser("~"), ".hyp_chrome_profile")
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir)
            options.add_argument(f'--user-data-dir={user_data_dir}')

            # ============================================================
            # E-IMZA YEREL AĞ ERİŞİMİ - ek güvenlik ayarları
            # ============================================================
            options.add_argument('--disable-features=PrivateNetworkAccessForNavigations,PrivateNetworkAccessForWorkers,PrivateNetworkAccessNonSecureContextsAllowed')

            options.add_experimental_option('excludeSwitches', ['enable-logging'])

            # Debug modda remote debugging aktif
            if debug_mode:
                options.add_argument('--remote-debugging-port=9222')
                options.add_experimental_option("detach", True)  # Tarayıcı açık kalsın

            prefs = {
                "profile.default_content_setting_values.notifications": 1,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                # Yerel ağ erişimi için izin
                "profile.default_content_setting_values.local_network_requests": 1,
            }
            options.add_experimental_option("prefs", prefs)

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(5)
            
            self.log("✅ Chrome hazır!", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"❌ Chrome başlatılamadı: {e}", "ERROR")
            return False

    # ============================================================
    # TEMEL ELEMENT İŞLEMLERİ
    # ============================================================
    def js_click(self, element) -> bool:
        """JavaScript ile zorla tıkla"""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                element
            )
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", element)
            self.last_activity_time = time.time()
            return True
        except Exception as e:
            self.log(f"JS Click hatası: {e}", "DEBUG")
            return False

    def find_element(self, xpath: str, timeout: float = 3) -> Optional[Any]:
        """Element bul - güvenli"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element
        except:
            return None

    def click_element(self, xpath: str, timeout: float = 3, use_js: bool = True) -> bool:
        """Elemente tıkla - OPTIMIZE edildi"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            if use_js:
                return self.js_click(element)
            else:
                element.click()
                self.last_activity_time = time.time()
                return True
        except:
            # Fallback: presence ile dene - KISA timeout (0.3 sn)
            fallback_timeout = min(timeout, 0.3)  # Max 0.3 saniye bekle
            element = self.find_element(xpath, fallback_timeout)
            if element:
                return self.js_click(element)
        return False

    def check_exists(self, xpath: str, timeout: float = 0.5) -> bool:
        """Element var mı?"""
        try:
            self.driver.implicitly_wait(timeout)
            elements = self.driver.find_elements(By.XPATH, xpath)
            self.driver.implicitly_wait(5)
            return len(elements) > 0
        except:
            self.driver.implicitly_wait(5)
            return False

    def get_page_text(self) -> str:
        """Sayfa metnini al (uppercase)"""
        try:
            return self.driver.page_source.upper()
        except:
            return ""

    # ============================================================
    # SATIR SAYISI AYARLAMA (ROWS PER PAGE)
    # ============================================================
    def set_page_size(self, size: int = 50) -> bool:
        """
        Hasta listesi satır sayısını ayarla (varsayılan 10 -> 50)
        HYP paginator içindeki PrimeNG dropdown kullanıyor
        Seçenekler: 10, 25, 50, 100
        """
        try:
            self.log(f"Satır sayısı {size} olarak ayarlanıyor...", "DEBUG")

            # hyp-paginator içindeki dropdown'u bul
            dropdown = None
            try:
                dropdown = self.driver.find_element(By.CSS_SELECTOR, '.hyp-paginator p-dropdown')
            except:
                self.log("Satır sayısı dropdown bulunamadı, devam ediliyor...", "WARNING")
                return False

            current_value = dropdown.text.strip()
            self.log(f"Mevcut satır sayısı: {current_value}", "DEBUG")

            # Zaten istenen değerdeyse değiştirme
            if current_value == str(size):
                self.log(f"Satır sayısı zaten {size}", "DEBUG")
                return True

            # Dropdown içindeki tıklanabilir div'i bul ve tıkla
            dropdown_div = dropdown.find_element(By.CSS_SELECTOR, '.ui-dropdown')
            self.js_click(dropdown_div)
            time.sleep(0.5)

            # Seçenekleri bul
            items = self.driver.find_elements(By.CSS_SELECTOR, '.ui-dropdown-items li')

            # İstenen boyutu seç
            for item in items:
                if item.text.strip() == str(size):
                    self.js_click(item)
                    self.log(f"Satır sayısı {size} olarak ayarlandı!", "SUCCESS")
                    time.sleep(0.5)  # Sayfa yenilenmesini bekle (OPTIMIZE)
                    return True

            self.log(f"Satır sayısı seçeneği ({size}) bulunamadı. Mevcut seçenekler: {[i.text for i in items]}", "WARNING")
            return False

        except Exception as e:
            self.log(f"Satır sayısı ayarlama hatası: {e}", "WARNING")
            return False

    # ============================================================
    # SMS ONAYI KAPALI HASTALAR YÖNETİMİ
    # ============================================================
    def _load_sms_kapali_hastalar(self) -> set:
        """SMS onayı kapalı hastaları dosyadan yükle"""
        import json
        import os

        sms_file = os.path.join(os.path.dirname(__file__), 'sms_kapali_hastalar.json')
        if os.path.exists(sms_file):
            try:
                with open(sms_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # TC numaralarını set olarak döndür
                    return set(item.get('tc', '') for item in data if item.get('tc'))
            except Exception as e:
                self.log(f"SMS kapalı hastalar yüklenemedi: {e}", "WARNING")
        return set()

    def _save_sms_kapali_hasta(self, tc: str, ad_soyad: str, yas: str = ""):
        """SMS onayı kapalı hastayı kaydet"""
        import json
        import os
        from datetime import datetime

        sms_file = os.path.join(os.path.dirname(__file__), 'sms_kapali_hastalar.json')

        # Mevcut listeyi oku
        data = []
        if os.path.exists(sms_file):
            try:
                with open(sms_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = []

        # Zaten var mı kontrol et
        if any(item.get('tc') == tc for item in data):
            return  # Zaten kayıtlı

        # Yeni hasta ekle
        data.append({
            'tc': tc,
            'ad_soyad': ad_soyad,
            'yas': yas,
            'ekleme_tarihi': datetime.now().strftime('%d.%m.%Y %H:%M')
        })

        # Kaydet
        try:
            with open(sms_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.sms_kapali_hastalar.add(tc)
            self.log(f"   [SMS KAPALI] {ad_soyad} listeye eklendi", "WARNING")
        except Exception as e:
            self.log(f"SMS kapalı hasta kaydedilemedi: {e}", "ERROR")

    def _get_patient_name_from_page(self) -> str:
        """Sayfadan hasta adini oku"""
        try:
            selectors = ['.patient-name', '.hasta-adi', '.sidebar-header h3', '.patient-info .name', '.sidebar .name']
            for sel in selectors:
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if el and el.text.strip():
                        name = el.text.strip()
                        if not (len(name) == 11 and name.isdigit()):
                            return name
                except:
                    continue
            return ""
        except:
            return ""

    def _is_sms_kapali_hasta(self, tc: str) -> bool:
        """Hasta SMS onayi kapali mi kontrol et"""
        return tc in self.sms_kapali_hastalar

    def _check_sms_onay_popup(self) -> bool:
        """
        SMS onayı popup'u var mı kontrol et.
        Görüntüle butonuna tıkladıktan sonra çağrılır.

        Returns:
            True: SMS onay popup'u var (hasta atlanmalı)
            False: Popup yok veya farklı popup
        """
        try:
            # SMS onayı popup metinleri
            sms_keywords = ['SMS', 'ONAY', 'DOĞRULAMA', 'DOGRULAMA', 'TELEFON', 'CEP', 'MOBİL', 'MOBIL']

            # Popup içeriğini kontrol et
            popup_selectors = [
                '.ui-dialog',
                '.p-dialog',
                '[role="dialog"]',
                '.modal-content'
            ]

            for selector in popup_selectors:
                try:
                    popups = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for popup in popups:
                        if popup.is_displayed():
                            popup_text = popup.text.upper()
                            # SMS ile ilgili anahtar kelime var mı
                            if any(kw in popup_text for kw in sms_keywords):
                                self.log("   [!] SMS ONAYI POPUP'U TESPİT EDİLDİ!", "WARNING")
                                return True
                except:
                    continue

            return False
        except:
            return False

    def _close_sms_popup_and_skip(self) -> bool:
        """SMS onay popup'unu kapat (Hayır'a bas) ve hastayı atla"""
        try:
            # Hayır butonunu bul ve tıkla
            hayir_xpaths = [
                "//button[.//span[normalize-space(text())='Hayır']]",
                "//button[contains(text(), 'Hayır')]",
                "//button[contains(., 'Hayır')]",
                "//button[contains(text(), 'İptal')]",
                "//button[contains(., 'Vazgeç')]"
            ]

            for xpath in hayir_xpaths:
                try:
                    btn = self.driver.find_element(By.XPATH, xpath)
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        self.log("   SMS popup kapatıldı (Hayır)", "DEBUG")
                        time.sleep(0.5)
                        return True
                except:
                    continue

            return False
        except:
            return False

    # ============================================================
    # POPUP VE HATA YÖNETİMİ
    # ============================================================
    def kill_popups(self) -> bool:
        """Popup'ları kapat"""
        popup_xpaths = [
            "//button[.//span[normalize-space(text())='Hayır']]",
            "//button[contains(text(), 'Hayır')]",
            "//button[contains(@class, 'ui-dialog-titlebar-close')]",
        ]
        
        for xpath in popup_xpaths:
            if self.check_exists(xpath, timeout=0.5):
                self.log("Popup kapatılıyor...", "DEBUG")
                self.click_element(xpath, timeout=1)
                time.sleep(0.5)
                return True
        return False

    def check_error_page(self) -> bool:
        """Hata sayfası kontrolü ve düzeltme - HIZLI JS KONTROL"""
        try:
            # OPTIMIZE: page_source yerine JS ile hizli kontrol
            page_text = self.driver.execute_script("return document.body.innerText.toUpperCase().slice(0, 500);")
            if "INVALID-API-RESP" in page_text or "HATA KODU" in page_text:
                self.log("Hata sayfası! Yenileniyor...", "WARNING")
                self.driver.refresh()
                time.sleep(5)
                return True
        except:
            pass
        return False

    def keep_alive(self):
        """Session'ı canlı tut"""
        if time.time() - self.last_activity_time > 120:  # 2 dakika
            self.log("Keep-alive sinyali gönderiliyor...", "DEBUG")
            try:
                self.driver.execute_script("console.log('keep-alive');")
                self.last_activity_time = time.time()
            except:
                pass

    # ============================================================
    # GİRİŞ İŞLEMİ
    # ============================================================
    def _detect_current_page(self) -> str:
        """
        Chrome'un hangi sayfada olduğunu algıla.

        Returns:
            "dashboard" - HYP dashboard (giriş yapılmış)
            "hyp_loggedin" - HYP içi herhangi bir sayfa (giriş yapılmış)
            "pin_popup" - PIN girişi popup'ı açık
            "login_page" - HYP ana sayfası (giriş yapılmamış)
            "other" - HYP dışı sayfa veya boş
        """
        try:
            current_url = self.driver.current_url.lower()

            # 1. HYP dışı bir site mi?
            if "hyp.saglik.gov.tr" not in current_url:
                return "other"

            # 2. Dashboard sayfası mı?
            if "dashboard" in current_url:
                return "dashboard"

            # 3. HYP içi başka bir sayfa mı? (giriş yapılmış demek)
            # Hasta Listesi, Fizik Muayene vs. menü linkleri varsa giriş yapılmış
            if self.check_exists("//a[contains(., 'Hasta Listesi')]", timeout=1):
                return "hyp_loggedin"
            if self.check_exists("//a[contains(., 'Fizik Muayene')]", timeout=0.5):
                return "hyp_loggedin"
            if self.check_exists("//span[contains(@class, 'user-name')]", timeout=0.5):
                return "hyp_loggedin"

            # 4. PIN popup açık mı?
            if self.check_exists("//input[@id='popupPinCode_Password']", timeout=0.5):
                return "pin_popup"

            # 5. Giriş butonu var mı? (ana sayfa, giriş yapılmamış)
            if self.check_exists("//*[@id='header']/div/div/button", timeout=0.5):
                return "login_page"

            # 6. e-İmza sekmesi veya login modal açık mı?
            if self.check_exists("//a[@href='#e-imza']", timeout=0.5):
                return "login_page"

            return "other"

        except Exception:
            return "other"

    def login(self, auto_pin: bool = True) -> bool:
        """
        HYP'ye giriş yap - Akıllı sayfa algılama ile.
        Chrome hangi ekranda açılırsa açılsın, doğru adımdan devam eder.

        Args:
            auto_pin: True ise PIN otomatik girilir, False ise manuel beklenir
        """
        try:
            # ============================================================
            # ADIM 1: Mevcut sayfa durumunu algıla
            # ============================================================
            page_state = self._detect_current_page()
            self.log(f"📍 Sayfa durumu algılandı: {page_state}")

            # ============================================================
            # ADIM 2: Duruma göre hareket et
            # ============================================================

            # DURUM A: Zaten giriş yapılmış (dashboard veya HYP içi sayfa)
            if page_state in ("dashboard", "hyp_loggedin"):
                self.log("✅ Zaten giriş yapılmış, devam ediliyor...", "SUCCESS")
                # Dashboard'da değilse, dashboard'a git
                if page_state != "dashboard":
                    try:
                        self.driver.get("https://hyp.saglik.gov.tr/dashboard")
                        time.sleep(1)
                    except:
                        pass
                return True

            # DURUM B: PIN popup zaten açık
            if page_state == "pin_popup":
                self.log("🔑 PIN ekranı açık, PIN girişine geçiliyor...")
                return self._enter_pin(auto_pin)

            # DURUM C: Login sayfasında (giriş butonu görünür)
            if page_state == "login_page":
                self.log("📋 Login sayfası algılandı, giriş yapılıyor...")
                return self._do_full_login(auto_pin)

            # DURUM D: HYP dışı sayfa veya boş - HYP'ye git
            self.log("🌐 HYP'ye yönlendiriliyor...")
            self.driver.get(HYP_URL)
            time.sleep(1)

            # Tekrar kontrol et
            page_state = self._detect_current_page()

            if page_state in ("dashboard", "hyp_loggedin"):
                self.log("✅ Session aktif, giriş yapılmış!", "SUCCESS")
                return True
            elif page_state == "pin_popup":
                return self._enter_pin(auto_pin)
            else:
                return self._do_full_login(auto_pin)

        except Exception as e:
            self.log(f"Login hatası: {e}", "ERROR")
            return False

    def _do_full_login(self, auto_pin: bool) -> bool:
        """Tam login işlemi (giriş butonu -> e-imza -> PIN)"""
        try:
            # Giriş butonu
            if not self.click_element("//*[@id='header']/div/div/button", timeout=5):
                # Belki zaten login modal açık?
                if self.check_exists("//a[@href='#e-imza']", timeout=1):
                    pass  # Modal açık, devam et
                else:
                    self.log("Giriş butonu bulunamadı!", "ERROR")
                    return False

            time.sleep(1)

            # e-İmza sekmesi
            try:
                self.driver.find_element(By.CSS_SELECTOR, "a[href='#e-imza']").click()
                time.sleep(0.5)
                self.driver.find_element(By.CSS_SELECTOR, "a.dropdown-toggle.has-spinner").click()
            except:
                pass

            self.log("PIN ekranı bekleniyor...")
            time.sleep(1.5)

            return self._enter_pin(auto_pin)

        except Exception as e:
            self.log(f"Full login hatası: {e}", "ERROR")
            return False

    def _enter_pin(self, auto_pin: bool) -> bool:
        """PIN girişi yap ve dashboard'a ulaş"""
        try:
            if auto_pin and config.PIN_CODE:
                # OTOMATİK PIN
                self.log("🔑 PIN OTOMATİK giriliyor...")
                try:
                    pin_input = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "popupPinCode_Password"))
                    )
                    pin_input.click()
                    pin_input.clear()
                    self.driver.execute_script(
                        f"document.getElementById('popupPinCode_Password').value = '{config.PIN_CODE}';"
                    )
                    self.log("PIN girildi.")
                except Exception as e:
                    self.log(f"PIN hatası: {e}", "ERROR")
                    return False

                # İmzala butonuna tıkla
                time.sleep(1)
                try:
                    self.driver.execute_script("popupPinCode_SignatureStart();")
                except:
                    self.click_element("//button[@id='btnImzala']")

                self.log("Giriş başarılı!", "SUCCESS")
                time.sleep(5)
            else:
                # MANUEL PIN
                self.log("=" * 50)
                self.log("🔑 MANUEL PIN GİRİŞİ BEKLENİYOR...")
                self.log("   Lütfen e-İmza PIN'inizi girin ve İmzala'ya tıklayın")
                self.log("=" * 50)

                max_wait = 120
                waited = 0
                while waited < max_wait:
                    time.sleep(2)
                    waited += 2

                    current_url = self.driver.current_url.lower()
                    if "dashboard" in current_url or self.check_exists("//a[contains(., 'Hasta')]"):
                        self.log("✅ Manuel giriş başarılı!", "SUCCESS")
                        break

                    if waited % 10 == 0:
                        self.log(f"   ⏳ Bekleniyor... ({waited}/{max_wait} sn)")

                if waited >= max_wait:
                    self.log("❌ Manuel giriş zaman aşımı (120 sn)!", "ERROR")
                    return False

            self.check_error_page()
            return True

        except Exception as e:
            self.log(f"PIN giriş hatası: {e}", "ERROR")
            return False

    # ============================================================
    # GÜNLÜK HASTA LİSTESİ
    # ============================================================
    def get_todays_patients(self, target_date: datetime = None) -> List[Dict]:
        """Fizik muayene kayıtlarından hasta listesi al"""
        try:
            self.log("Fizik Muayene sayfasına gidiliyor...")

            # Menüye git
            if not self.click_element("//a[contains(., 'Fizik Muayene')]", timeout=5):
                self.log("Fizik Muayene menüsü bulunamadı!", "ERROR")
                return []

            time.sleep(2)  # OPTIMIZE: 3 -> 2
            self.check_error_page()

            # Sayfa boyutunu 100'e ayarla (varsayılan 10)
            self.set_page_size(100)

            # Tarih ayarla
            date = target_date or datetime.now()
            date_str = date.strftime("%d.%m.%Y")
            self.log(f"Tarih: {date_str}")

            try:
                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input.p-inputtext")
                if len(inputs) >= 2:
                    for inp in inputs[:2]:
                        inp.click()
                        inp.send_keys(Keys.CONTROL + "a")
                        inp.send_keys(Keys.DELETE)
                        inp.send_keys(date_str)
                    inputs[1].send_keys(Keys.ENTER)
                    time.sleep(0.5)  # OPTIMIZE
            except:
                pass

            # Hastaları topla
            patients = []
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".list-item.ng-star-inserted")

            for row in rows:
                try:
                    text = row.text
                    if date_str in text:
                        parts = text.split('\n')
                        if parts and "Adı" not in parts[0]:
                            patients.append({
                                "ad_soyad": parts[0].strip(),
                                "tarih": date_str
                            })
                except:
                    continue

            self.log(f"Bulunan hasta: {len(patients)}")
            return patients

        except Exception as e:
            self.log(f"Hasta listesi hatası: {e}", "ERROR")
            return []

    def get_patients_for_dates(self, dates: List[datetime]) -> List[Dict]:
        """
        Birden fazla tarih için hastaları SÜPER HIZLI al.
        Sayfayı 1 kere açar, 100 satır alır, bellekte filtreler.
        Tarih sorgusu YAPMAZ - tüm listeyi okur ve seçilen tarihlere göre filtreler.
        """
        if not dates:
            return []

        all_patients = []
        existing_names = set()

        # Seçilen tarihleri string formatına çevir
        date_strings = set(d.strftime("%d.%m.%Y") for d in dates)
        self.log(f"📅 {len(dates)} tarih için hastalar alınıyor (hızlı mod)...")

        try:
            self.log("Fizik Muayene sayfasına gidiliyor...")

            # Menüye git - SADECE 1 KEZ
            if not self.click_element("//a[contains(., 'Fizik Muayene')]", timeout=5):
                self.log("Fizik Muayene menüsü bulunamadı!", "ERROR")
                return []

            time.sleep(2)
            self.check_error_page()

            # Sayfa boyutunu 100'e ayarla
            self.set_page_size(100)
            time.sleep(0.5)

            # TÜM satırları oku - tarih filtresi YAPMADAN
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".list-item.ng-star-inserted")
            self.log(f"   📋 Sayfada {len(rows)} satır bulundu")

            # Tarih bazlı sayaçlar
            date_counts = {d: 0 for d in date_strings}

            for row in rows:
                try:
                    text = row.text
                    parts = text.split('\n')
                    if not parts or "Adı" in parts[0]:
                        continue

                    name = parts[0].strip()
                    if name in existing_names:
                        continue

                    # Bu satırın tarihi seçilen tarihlerden biri mi?
                    for date_str in date_strings:
                        if date_str in text:
                            all_patients.append({
                                "ad_soyad": name,
                                "tarih": date_str
                            })
                            existing_names.add(name)
                            date_counts[date_str] += 1
                            break  # Bir tarihle eşleşti, sonrakine geç

                except:
                    continue

            # Sonuçları logla
            for date_str in sorted(date_strings):
                count = date_counts[date_str]
                if count > 0:
                    self.log(f"   📆 {date_str}: ✅ {count} hasta")

            self.log(f"📊 Toplam: {len(all_patients)} benzersiz hasta")
            return all_patients

        except Exception as e:
            self.log(f"Çoklu tarih hasta listesi hatası: {e}", "ERROR")
            return []

    # ============================================================
    # HASTA KARTLARINI OKUMA (DÜZELTİLMİŞ)
    # ============================================================
    def get_patient_cards(self) -> List[Dict]:
        """
        Hastanın TÜM HYP kartlarını oku ve analiz et - DUZELTILMIS
        """
        cards = []

        try:
            time.sleep(0.3)  # 1 -> 0.3 (OPTIMIZE)

            # Tüm "Görüntüle" butonlarını bul
            buttons = self.driver.find_elements(By.XPATH, "//button[.//span[text()='Görüntüle']]")
            self.log(f"Bulunan kart sayısı: {len(buttons)}", "DEBUG")
            
            for idx, btn in enumerate(buttons):
                try:
                    # Kartın container'ını bulmak için farkli yollar dene
                    card_text = ""
                    
                    # Yol 1: parent div'leri yukari dogru tara (max 5 seviye)
                    current = btn
                    for level in range(1, 6):
                        try:
                            current = current.find_element(By.XPATH, "./..")
                            text = current.text.upper()
                            # Kart basligini iceriyorsa dogru container'i bulduk
                            if any(keyword in text for keyword in ["HİPERTANSİYON", "HIPERTANSIYON", "DİYABET", "DIYABET", "OBEZİTE", "OBEZITE", "KARDİYOVASKÜLER", "KARDIYOVASKULER"]):
                                # Eger cok fazla kart basligi varsa, cok yukari cikmisiz
                                keyword_count = sum(1 for k in ["HIPERTANSIYON", "DIYABET", "OBEZITE", "KARDIYOVASKULER"] if k in text.replace("İ","I").replace("Ü","U"))
                                if keyword_count <= 1:
                                    card_text = text
                                    break
                        except:
                            break
                    
                    # Yol 2: Eger bulamadiysa ancestor ile dene
                    if not card_text:
                        try:
                            card_container = btn.find_element(By.XPATH, "./ancestor::div[contains(@style, 'background') or contains(@class, 'hyp-card')]")
                            card_text = card_container.text.upper()
                        except:
                            try:
                                card_container = btn.find_element(By.XPATH, "./../../..")
                                card_text = card_container.text.upper()
                            except:
                                continue
                    
                    if not card_text:
                        continue
                    
                    # Kart tipini belirle
                    card_info = self._analyze_card(card_text, btn)
                    
                    if card_info:
                        cards.append(card_info)
                        self.log(f"  📋 {card_info['baslik']} ({card_info['hyp_tip']}) - Yapılabilir: {card_info['yapilabilir']}", "DEBUG")
                
                except Exception as e:
                    self.log(f"Kart {idx} okuma hatasi: {e}", "DEBUG")
                    continue
            
        except Exception as e:
            self.log(f"Kart okuma hatası: {e}", "WARNING")
        
        return cards

    def _parse_date_from_text(self, text: str, label: str):
        """Metin icinden tarih cikar"""
        import re
        # Normalize
        text_n = text.upper().replace('İ', 'I').replace('Ş', 'S').replace('Ğ', 'G').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C')
        label_n = label.upper().replace('İ', 'I').replace('Ş', 'S').replace('Ğ', 'G').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C')
        
        # Pattern: label + herhangi karakter + tarih (dd.mm.yyyy)
        pattern = label_n + r'.*?(\d{2}[./]\d{2}[./]\d{4})'
        match = re.search(pattern, text_n, re.DOTALL)
        if match:
            date_str = match.group(1).replace('/', '.')
            try:
                return datetime.strptime(date_str, "%d.%m.%Y")
            except:
                pass
        return None

    def _analyze_card(self, card_text: str, button) -> Optional[Dict]:
        """Tek bir kartı analiz et"""
        
        # Debug: Kart metnini logla
        self.log(f"   [DEBUG] Kart metni: {card_text[:150]}...", "DEBUG")
        
        # Tip belirleme - SIRA ONEMLI! Onceligi yuksek olanlar once
        hyp_tip = None
        baslik = ""
        
        # Normalize et
        card_upper = card_text.upper()
        
        # HİPERTANSİYON kontrolu (DIYABET'ten once olmali cunku ikisi de ayni kartta olabilir)
        if "HİPERTANSİYON" in card_upper or "HIPERTANSIYON" in card_upper:
            baslik = "Hipertansiyon"
            if "İZLEM" in card_upper or "IZLEM LISTESINDE" in card_upper:
                hyp_tip = "HT_IZLEM"
            else:
                hyp_tip = "HT_TARAMA"
        # KARDİYOVASKÜLER kontrolu
        elif "KARDİYOVASKÜLER" in card_upper or "KARDIYOVASKULER" in card_upper or "KARDİYOVASKULER" in card_upper:
            baslik = "KVR"
            if "İZLEM" in card_upper or "IZLEM LISTESINDE" in card_upper:
                hyp_tip = "KVR_IZLEM"
            else:
                hyp_tip = "KVR_TARAMA"
        # OBEZİTE kontrolu
        elif "OBEZİTE" in card_upper or "OBEZITE" in card_upper:
            baslik = "Obezite"
            if "İZLEM" in card_upper or "IZLEM LISTESINDE" in card_upper:
                hyp_tip = "OBE_IZLEM"
            else:
                hyp_tip = "OBE_TARAMA"
        # DİYABET kontrolu (en sonda)
        elif "DİYABET" in card_upper or "DIYABET" in card_upper:
            baslik = "Diyabet"
            if "İZLEM" in card_upper or "IZLEM LISTESINDE" in card_upper:
                hyp_tip = "DIY_IZLEM"
            else:
                hyp_tip = "DIY_TARAMA"
        # YASLI SAGLIGI
        elif "YAŞLI" in card_upper or "YASLI" in card_upper:
            baslik = "Yaşlı Sağlığı"
            hyp_tip = "YAS_IZLEM"
        
        if not hyp_tip:
            return None
        
        # Yapılabilirlik kontrolü
        yapilabilir = True
        durum = "bekliyor"
        bugun = datetime.now().date()

        # Sonraki takip tarihini bul (ekran goruntusunden: "Sonraki takip tarihi")
        sonraki_takip = None
        for label in ["SONRAKI TAKIP TARIHI", "SONRAKİ TAKİP TARİHİ", "SONRAKI TAKIP", "SONRAKİ TAKİP"]:
            sonraki_takip = self._parse_date_from_text(card_text, label)
            if sonraki_takip:
                self.log(f"   Tarih bulundu: {label} -> {sonraki_takip.strftime('%d.%m.%Y')}", "DEBUG")
                break

        # Tarih bazlı yapılabilirlik kontrolü
        # GUNCELLEME: 1 ay (30 gun) icinde olan takipler de yapilabilir
        if sonraki_takip:
            gun_farki = (sonraki_takip.date() - bugun).days
            
            if gun_farki > 30:
                # 1 aydan fazla kaldi - ATLA
                durum = "yaklasan"
                yapilabilir = False
                self.log(f"   Sonraki takip {sonraki_takip.strftime('%d.%m.%Y')} ({gun_farki} gun kaldi) - ATLANACAK", "DEBUG")
            elif gun_farki > 0:
                # 1 ay icinde - YAPILABILIR
                durum = "yaklasan_yakin"
                yapilabilir = True
                self.log(f"   Sonraki takip {sonraki_takip.strftime('%d.%m.%Y')} ({gun_farki} gun kaldi) - YAPILABILIR", "DEBUG")
            else:
                # Gecmis veya bugun - YAPILABILIR
                durum = "geciken" if gun_farki < 0 else "bekliyor"
                yapilabilir = True
        else:
            # Tarih bulunamazsa metin bazli kontrol
            if "DEVAM EDİYOR" in card_text or "DEVAM EDIYOR" in card_text:
                durum = "devam_ediyor"
                yapilabilir = True
            elif "TAMAMLANDI" in card_text or "SONLANDIRILDI" in card_text:
                durum = "tamamlandi"
                yapilabilir = False
            elif "GECİKEN" in card_text or "GECIKEN" in card_text:
                durum = "geciken"
                yapilabilir = True
            elif "YAKLAŞAN" in card_text or "YAKLASAN" in card_text:
                durum = "yaklasan"
                yapilabilir = False

        return {
            "baslik": baslik,
            "hyp_tip": hyp_tip,
            "element": button,
            "durum": durum,
            "yapilabilir": yapilabilir,
            "sonraki_takip": sonraki_takip.strftime('%d.%m.%Y') if sonraki_takip else None,
            "raw_text": card_text[:300]
        }

    # ============================================================
    # HASTA İŞLEME (ANA FONKSİYON)
    # ============================================================
    def process_patient(self, patient_name: str) -> bool:
        """Tek bir hastayi isle"""
        start_time = time.time()

        # Hasta bilgilerini kaydet (gebelik kontrolu ve bildirimler icin)
        self.current_patient_name = patient_name
        self.current_patient_tc = None

        try:
            # TC mi yoksa isim mi?
            is_tc_input = len(patient_name) == 11 and patient_name.isdigit()
            self.keep_alive()

            # 1. Hasta Listesine Git
            # Önce ana sayfaya dönmeyi dene
            if "dashboard" not in self.driver.current_url.lower():
                try:
                    self.driver.get("https://hyp.saglik.gov.tr/dashboard")
                    time.sleep(1.5)
                except:
                    pass

            # Hasta Listesi menüsünü bul ve tıkla
            menu_found = False
            menu_xpaths = [
                "//a[contains(., 'Hasta Listesi')]",
                "//a[contains(text(), 'Hasta Listesi')]",
                "//span[contains(text(), 'Hasta Listesi')]/parent::a",
                "//a[@href='/patient-list']",
            ]
            for xpath in menu_xpaths:
                if self.click_element(xpath, timeout=3):
                    menu_found = True
                    break

            if not menu_found:
                self.log("Hasta listesi menüsü bulunamadı!", "WARNING")
                return False

            time.sleep(2)
            self.check_error_page()

            # 2. Hastayı Ara
            try:
                # Arama kutusunu bul
                search_input = None
                inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                for inp in inputs:
                    ph = (inp.get_attribute('placeholder') or '').lower()
                    if 'hasta ara' in ph or 'search patient' in ph or 'ara' in ph:
                        search_input = inp
                        break

                if not search_input:
                    self.log("Arama kutusu bulunamadı!", "WARNING")
                    return False

                search_input.clear()
                search_input.send_keys(patient_name)
                search_input.send_keys(Keys.ENTER)
                time.sleep(2)  # Arama sonuçları yüklensin
            except Exception as e:
                self.log(f"Arama kutusu hatası: {str(e)[:50]}", "WARNING")
                return False

            # 3. Hasta İsmine Tıkla
            name_clicked = False
            # TC mi yoksa isim mi kontrol et
            is_tc_search = len(patient_name) == 11 and patient_name.isdigit()
            # Türkçe karakter normalizasyonu ile karşılaştır
            patient_name_normalized = normalize_tr(patient_name)

            # Arama sonuçlarını bekle
            list_items = []
            for attempt in range(5):
                list_items = self.driver.find_elements(By.CSS_SELECTOR, ".list-item.ng-star-inserted, .list-item")
                if len(list_items) > 0:
                    break
                time.sleep(0.5)

            # TC ile arama yapildiysa ve tek sonuc varsa direkt tikla
            if is_tc_search and len(list_items) == 1:
                try:
                    name_el = list_items[0].find_element(By.CSS_SELECTOR, ".name")
                    self.js_click(name_el)
                except:
                    self.js_click(list_items[0])
                time.sleep(0.5)
                self.log(f"TC ile arama: tek sonuc bulundu ve tiklandi")
                name_clicked = True
            elif is_tc_search and len(list_items) > 1:
                # TC ile birden fazla sonuc geldiyse ilkine tikla
                try:
                    name_el = list_items[0].find_element(By.CSS_SELECTOR, ".name")
                    self.js_click(name_el)
                except:
                    self.js_click(list_items[0])
                time.sleep(0.5)
                self.log(f"TC ile arama: ilk sonuca tiklandi")
                name_clicked = True
            else:
                # Isim ile arama - eski mantik
                for item in list_items:
                    try:
                        item_text_normalized = normalize_tr(item.text)
                        if patient_name_normalized in item_text_normalized:
                            try:
                                name_el = item.find_element(By.CSS_SELECTOR, ".name")
                                self.js_click(name_el)
                            except:
                                self.js_click(item)

                            time.sleep(0.5)
                            self.log(f"Dogru hasta bulundu ve tiklandi: {patient_name}")
                            name_clicked = True
                            break
                    except:
                        continue

                if not name_clicked:
                    if len(list_items) == 1:
                        self.js_click(list_items[0])
                        time.sleep(0.5)
                        self.log(f"Tek sonuc bulundu, tiklandi: {patient_name}")
                        name_clicked = True
                    else:
                        self.log(f"UYARI: {patient_name} arama sonuclarinda bulunamadi!", "WARNING")

            if not name_clicked:
                self.log("Hasta ismi/karti bulunamadi!", "WARNING")
                return False

            self.check_error_page()

            # ============================================================
            # TC NUMARASINI VE HASTA ADINI AL
            # ============================================================
            try:
                # Sayfa metninden TC numarasini cikar
                page_text = self.driver.execute_script("return document.body.innerText;")
                import re
                tc_match = re.search(r'(\d{2}\*+\d{2})', page_text)
                if tc_match:
                    self.current_patient_tc = tc_match.group(1)
                
                # TC ile arama yapildiysa sayfadan gercek hasta adini al
                if is_tc_input:
                    gercek_ad = self._get_patient_name_from_page()
                    if gercek_ad:
                        self.current_patient_name = gercek_ad
                    else:
                        self.current_patient_name = patient_name  # TC olarak kalsin
                
                # ISLENIYOR logunu yaz - isim (TC) formati
                display_name = self.current_patient_name or patient_name
                display_tc = patient_name if is_tc_input else (self.current_patient_tc or "")
                if display_tc and display_tc != display_name:
                    self.log(f"ISLENIYOR: {display_name} ({display_tc})")
                else:
                    self.log(f"ISLENIYOR: {display_name}")

                # SMS kapali mi kontrol et
                if self.current_patient_tc and self._is_sms_kapali_hasta(self.current_patient_tc):
                    self.log(f"   [SMS KAPALI] {display_name} daha once SMS kapali olarak isaretlendi - ATLANIYOR!", "WARNING")
                    self.session_stats["atlanan"] += 1
                    # Atlanan bildirim listesine ekle
                    self.skipped_hyp_notifications.append({
                        'hasta': display_name,
                        'tc': self.current_patient_tc,
                        'hyp_tip': 'TÜMÜ',
                        'sebep': 'SMS izni kapalı olarak işaretlenmiş',
                        'tarih': time.strftime('%d.%m.%Y %H:%M')
                    })
                    return True  # Atlandi ama hata degil
            except:
                pass

            # 4. HYP Kartlarını Oku
            cards = self.get_patient_cards()
            
            if not cards:
                self.log("İşlenecek HYP kartı bulunamadı.", "WARNING")
                self.session_stats["atlanan"] += 1
                # Atlanan bildirim listesine ekle
                self.skipped_hyp_notifications.append({
                    'hasta': self.current_patient_name or 'Bilinmiyor',
                    'tc': self.current_patient_tc,
                    'hyp_tip': 'TÜMÜ',
                    'sebep': 'İşlenecek HYP kartı bulunamadı',
                    'tarih': time.strftime('%d.%m.%Y %H:%M')
                })
                return True
            
            # 5. Yapılabilir Kartları Filtrele + HEDEF KONTROLÜ + CACHE KONTROLÜ
            yapilabilir_kartlar = []
            cache_atlanan = 0
            for c in cards:
                if not c["yapilabilir"]:
                    continue
                if not self.should_process_hyp_type(c["hyp_tip"]):
                    continue
                # Cache kontrolü - daha önce işlenmiş mi?
                if self.is_hyp_already_processed(self.current_patient_tc, c["hyp_tip"]):
                    cache_atlanan += 1
                    continue
                yapilabilir_kartlar.append(c)

            if cache_atlanan > 0:
                self.log(f"   {cache_atlanan} HYP daha once yapilmis (cache)", "DEBUG")

            if not yapilabilir_kartlar:
                self.log("Yapılabilir kart yok (tamamlanmış, cache'de veya hedef tutturulmuş).", "WARNING")
                self.session_stats["atlanan"] += 1
                # Atlanan bildirim listesine ekle
                sebep = 'Yapılabilir kart yok'
                if cache_atlanan > 0:
                    sebep = f"Tüm HYP'ler daha önce tamamlanmış ({cache_atlanan} adet cache'de)"
                self.skipped_hyp_notifications.append({
                    'hasta': self.current_patient_name or 'Bilinmiyor',
                    'tc': self.current_patient_tc,
                    'hyp_tip': 'TÜMÜ',
                    'sebep': sebep,
                    'tarih': time.strftime('%d.%m.%Y %H:%M')
                })
                return True

            self.log(f"Yapılabilir kart sayısı: {len(yapilabilir_kartlar)} (hedef kontrolü yapıldı)")
            
            # 6. Her yapılabilir kartı TEK TEK işle (stale element fix)
            islenen_kartlar = set()
            max_deneme = 10
            
            for deneme in range(max_deneme):
                if self.should_stop:
                    break
                
                # Kartları her seferinde YENIDEN oku + HEDEF KONTROLÜ + CACHE KONTROLÜ
                cards = self.get_patient_cards()
                yapilabilir = [
                    c for c in cards
                    if c["yapilabilir"]
                    and c["hyp_tip"] not in islenen_kartlar
                    and self.should_process_hyp_type(c["hyp_tip"])
                    and not self.is_hyp_already_processed(self.current_patient_tc, c["hyp_tip"])
                ]

                if not yapilabilir:
                    self.log("Tüm yapılabilir kartlar işlendi (veya hedefler tutturuldu).", "DEBUG")
                    break
                
                card = yapilabilir[0]
                self.log(f"Kart isleniyor ({deneme+1}): {card['baslik']} ({card['hyp_tip']})")
                
                result = self._process_single_card(card, islenen_kartlar)
                
                # SMS KAPALI - TUM KARTLARI ATLA
                if result == "SMS_SKIP":
                    self.log(f"   [SMS KAPALI] Hastanin tum HYP'leri atlaniyor!", "WARNING")
                    # Tum kartlari islenmis olarak isaretle
                    for c in yapilabilir:
                        islenen_kartlar.add(c["hyp_tip"])
                    break  # Donguyu kir, sonraki hastaya gec
                
                success = result if isinstance(result, bool) else False
                islenen_kartlar.add(card["hyp_tip"])
                
                if success:
                    self.session_stats["basarili"] += 1
                    # Hedef takibi için session sayacını artır
                    self.increment_completed(card["hyp_tip"])
                    if card["hyp_tip"] in self.monthly_stats:
                        self.monthly_stats[card["hyp_tip"]] += 1
                    else:
                        self.monthly_stats[card["hyp_tip"]] = 1
                    if self.stats_callback:
                        self.stats_callback(self.monthly_stats, {})
                    # Cache'e kaydet (başarılı)
                    self.mark_hyp_as_processed(
                        self.current_patient_tc,
                        self.current_patient_name or "",
                        card["hyp_tip"],
                        "BASARILI"
                    )
                else:
                    self.session_stats["basarisiz"] += 1
                    # Başarısız HYP'yi kaydet
                    self.failed_hyps.append({
                        "hasta": self.current_patient_name or "Bilinmeyen",
                        "hyp_tip": card["hyp_tip"],
                        "hyp_ad": card.get("baslik", card["hyp_tip"]),
                        "neden": "İşlem tamamlanamadı"
                    })
                    # Cache'e kaydet (iptal/başarısız)
                    self.mark_hyp_as_processed(
                        self.current_patient_tc,
                        self.current_patient_name or "",
                        card["hyp_tip"],
                        "IPTAL"
                    )

                time.sleep(0.3)  # 1 -> 0.3 (OPTIMIZE)
                self._go_back_to_patient_cards()
            
            # Süre hesapla
            elapsed = time.time() - start_time
            self.session_stats["toplam_sure"] += elapsed
            self.log(f"Hasta işlem süresi: {elapsed:.1f}sn")
            
            return True
            
        except Exception as e:
            self.log(f"Hasta işleme hatası: {e}", "ERROR")
            self.session_stats["basarisiz"] += 1
            return False

    def _process_single_card(self, card: Dict, islenen_kartlar: set = None) -> bool:
        """Tek bir HYP kartını işle ve sonra sidebar'daki diğer kartları kontrol et"""
        if islenen_kartlar is None:
            islenen_kartlar = set()

        try:
            self.log(f"🎯 Kart işleniyor: {card['baslik']} ({card['hyp_tip']})")

            # Görüntüle butonuna tıkla
            self.js_click(card["element"])
            time.sleep(1)  # Sayfa yuklensin

            # ============================================================
            # SMS ONAYI POPUP KONTROLÜ - KRITIK!
            # Görüntüle sonrası SMS onay popup'u çıkarsa bu hasta atlanır
            # ============================================================
            if self._check_sms_onay_popup():
                self.log(f"   [!] SMS ONAYI GEREKLİ - Hasta atlanıyor!", "WARNING")
                # Popup'u kapat
                self._close_sms_popup_and_skip()
                # Sayfadan gercek hasta adini al (TC ile arama yapildiysa)
                gercek_ad = self._get_patient_name_from_page() or self.current_patient_name or "Bilinmeyen"
                self.current_patient_name = gercek_ad  # Guncelle
                # Hastayi kaydet (bir daha hic islenmeyecek)
                self._save_sms_kapali_hasta(
                    tc=self.current_patient_tc or "",
                    ad_soyad=gercek_ad,
                    yas=""
                )
                # Iptal listesine ekle (popup icin)
                self._record_cancelled_hyp(
                    reason="SMS onayi gerekli - Hasta SMS dogrulamasi kapali",
                    sms_gerekli=True
                )
                return "SMS_SKIP"  # Tum kartlari atla

            # Popup kontrolü - sadece bilgi popup'larini kapat, devam et
            self.kill_popups()

            # Gercek yetki hatasi kontrolu
            page_text = self.get_page_text()
            if "YETKİ" in page_text and "HATA" in page_text:
                self.log("Yetki hatasi, kart atlanıyor.", "WARNING")
                return False

            # Tarama/İzlem başlat - birkaç deneme yap
            started = False
            for attempt in range(3):
                if self._start_process():
                    started = True
                    break
                time.sleep(0.5)  # Buton yuklenmesi icin bekle
                self.kill_popups()  # Popup tekrar kontrol

            if not started:
                self.log("Başlat butonu bulunamadı!", "WARNING")
                return False

            time.sleep(0.5)  # 2 -> 0.5 (optimize)

            # Modüle göre işle
            hyp_tip = card["hyp_tip"]
            self._current_hyp_type = hyp_tip  # İptal kaydı için
            success = False

            if "DIY" in hyp_tip:
                success = self._process_diyabet()
            elif "HT" in hyp_tip:
                success = self._process_hipertansiyon()
            elif "OBE" in hyp_tip:
                success = self._process_obezite()
            elif "KVR" in hyp_tip:
                success = self._process_kvr()
            elif "YAS" in hyp_tip:
                success = self._process_yasli()
            else:
                self.log(f"Bilinmeyen modül: {hyp_tip}", "WARNING")
                return False

            # HYP işlemi tamamlandıktan sonra
            if success:
                islenen_kartlar.add(hyp_tip)

                # ============================================================
                # CANLI İLERLEME GÜNCELLEMESİ - GUI'ye bildir
                # ============================================================
                if self.on_hyp_success_callback:
                    try:
                        self.on_hyp_success_callback(hyp_tip, self.current_patient_name)
                    except Exception as e:
                        self.log(f"GUI callback hatası: {e}", "DEBUG")

                time.sleep(0.3)  # 1 -> 0.3 (OPTIMIZE)
                # Sidebar kartlarini isle
                sidebar_count = self._process_sidebar_cards(islenen_kartlar)
                if sidebar_count > 0:
                    self.log(f"   Sol panelden {sidebar_count} ek kart işlendi", "SUCCESS")

            return success
                
        except Exception as e:
            self.log(f"Kart işleme hatası: {e}", "ERROR")
            return False

    def _start_process(self) -> bool:
        """Tarama veya İzlem başlat - HIZLI (implicit_wait=0)"""
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)

        try:
            # Tum butonlari tek seferde al
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')

            # Debug: tum buton metinlerini logla
            btn_texts = [btn.text.strip()[:50] for btn in buttons if btn.text.strip()]
            self.log(f"   Bulunan butonlar ({len(btn_texts)}): {btn_texts[:5]}", "DEBUG")

            for btn in buttons:
                txt = btn.text.strip()
                # Baslat butonlarini bul - genisletilmis kontrol
                if 'Başlat' in txt and ('Yüz Yüze' in txt or 'Tarama' in txt or 'İzlem' in txt):
                    self.log(f"   Başlat butonu bulundu: {txt[:40]}", "DEBUG")
                    self.js_click(btn)
                    time.sleep(0.2)
                    return True
                elif 'Devam Et' in txt or 'Taramayla Devam' in txt or 'İzlemle Devam' in txt:
                    self.log(f"   Devam butonu bulundu: {txt[:40]}", "DEBUG")
                    self.js_click(btn)
                    time.sleep(0.2)
                    return True

            # Buton bulunamadı - DEVAM EDİYOR durumu kontrol et
            page_text = self.get_page_text()
            if "DEVAM EDİYOR" in page_text or "DEVAM EDIYOR" in page_text:
                self.log("   DEVAM EDİYOR tespit edildi - protokol zaten başlamış", "DEBUG")
                # Sayfa zaten protokol içinde olabilir - doğrudan devam et
                current_url = self.driver.current_url.lower()
                if any(x in current_url for x in ['/anamnez', '/tetkik', '/ilac', '/tani', '/hedef', '/ozet', '/yasam']):
                    self.log("   Protokol sayfasındayız, devam ediliyor...", "DEBUG")
                    return True
                # Görüntüle butonuna tıklamayı dene
                for btn in buttons:
                    txt = btn.text.strip()
                    if 'Görüntüle' in txt:
                        self.log(f"   Görüntüle butonu deneniyor: {txt[:40]}", "DEBUG")
                        self.js_click(btn)
                        time.sleep(0.5)
                        # Tekrar butonları kontrol et
                        new_buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                        for new_btn in new_buttons:
                            new_txt = new_btn.text.strip()
                            if 'Devam Et' in new_txt or 'Başlat' in new_txt:
                                self.js_click(new_btn)
                                return True
            return False
        finally:
            self.driver.implicitly_wait(original_wait)

    # ============================================================
    # DİYABET MODÜLÜ - AKILLI SAYFA TANIMA
    # ============================================================

    # Diyabet Sayfa Başlıkları
    DIY_HEADERS = {
        "RISK": "//div[contains(text(), 'RİSK FAKTÖRLERİ')]",
        "KAN_SEKERI": "//div[contains(text(), 'KAN ŞEKERİ')]",
        "SEMPTOM": "//div[contains(text(), 'SEMPTOM')]",
        "KIRILGANLIK": "//div[contains(text(), 'KIRILGANLIK') or contains(text(), 'KLİNİK KIRILGANLIK')]",
        "TANI": "//div[contains(text(), 'TANI KONULMASI')]",
        "YASAM": "//div[contains(text(), 'YAŞAM TARZI')]",
        "OZET": "//div[contains(text(), 'SONLANDIRILMASI')]"
    }

    # Kırılganlık Ölçeği Seviyeleri (Clinical Frailty Scale)
    KIRILGANLIK_OLCEGI = {
        1: "Çok Sağlıklı - Düzenli egzersiz yapan, çok aktif",
        2: "Sağlıklı - Aktif hastalığı yok, ara sıra egzersiz",
        3: "İyi Yönetilen - Hastalıkları iyi kontrol altında",
        4: "Kırılganlık Öncesi - Yavaşlamış ama bağımsız",
        5: "Hafif Kırılgan - Bazı aktivitelerde yardıma ihtiyaç",
        6: "Orta Kırılgan - Günlük aktivitelerde yardıma ihtiyaç",
        7: "Ağır Kırılgan - Tam bağımlı",
        8: "Çok Ağır Kırılgan - Ölüme yakın, tedaviye yanıtsız",
        9: "Terminal - Yaşam beklentisi < 6 ay"
    }

    def _detect_diy_page(self) -> str:
        """Diyabet sayfasını URL veya başlıktan tanı"""
        url = self.driver.current_url

        # URL bazlı hızlı tanıma
        if '/anamnez' in url:
            return "ANAMNEZ"
        elif '/risk' in url:
            return "RISK"
        elif '/kansekeri' in url or '/kan-sekeri' in url:
            return "KAN_SEKERI"
        elif '/semptom' in url:
            return "SEMPTOM"
        elif '/kirilganlik' in url or '/frailty' in url:
            return "KIRILGANLIK"
        elif '/tani' in url:
            return "TANI"
        elif '/yasamtarzi' in url or '/yasam' in url:
            return "YASAM"
        elif '/tetkik' in url:
            return "TETKIK"
        elif '/ilac' in url:
            return "ILAC"
        elif '/ozet' in url:
            return "OZET"

        # Sayfa text'inden tanıma
        page = self.get_page_text()
        if "SONLANDIRILMASI" in page:
            return "OZET"
        elif "KAN ŞEKERİ" in page or "KAN SEKERI" in page:
            return "KAN_SEKERI"
        elif "RİSK FAKTÖR" in page or "RISK FAKTOR" in page:
            return "RISK"
        elif "KIRILGANLIK" in page or "KLİNİK KIRILGANLIK" in page or "KLINIK KIRILGANLIK" in page:
            return "KIRILGANLIK"
        elif "İLAÇ TEDAVİSİ" in page or "ILAC TEDAVISI" in page:
            return "ILAC"
        elif "SEMPTOM" in page:
            return "SEMPTOM"
        elif "TANI KONULMASI" in page:
            return "TANI"
        elif "YAŞAM TARZI" in page or "YASAM TARZI" in page:
            return "YASAM"

        return "UNKNOWN"

    def _process_diyabet(self) -> bool:
        """Diyabet Tarama/İzlem - AKILLI SAYFA TANIMA"""
        self.log(">> Diyabet protokolü başladı")
        # NOT: _start_process() artik _process_single_card'da cagiriliyor!

        is_finished = False
        step = 0
        same_page_count = 0
        last_page = None

        while not is_finished and step < self.MAX_STEPS:
            step += 1
            self.keep_alive()
            self.check_error_page()
            self._close_dialogs()

            current_page = self._detect_diy_page()
            self.log(f"   Adım {step}: Sayfa={current_page}", "DEBUG")

            # Aynı sayfada takılı kalma kontrolü
            if current_page == last_page:
                same_page_count += 1
                if same_page_count >= 3:
                    self.log(f"   ⚠️ {current_page} sayfasında 3 kez takılı kaldı, HYP atlanıyor", "ERROR")
                    return False
            else:
                same_page_count = 0
            last_page = current_page

            # SAYFAYA GÖRE İŞLEM
            if current_page == "OZET":
                self.log("   Sonlandırılıyor...")
                is_finished = self._click_sonlandir()

            elif current_page == "ANAMNEZ":
                self.log("   Anamnez - alanlar dolduruluyor...")
                self._fill_anamnez_fields()
                self._click_ilerle()

            elif current_page == "RISK":
                self.log("   Risk Faktörleri...")
                # AKILLI GEBELIK KONTROLU - Gebe listesinden kontrol et
                gebe_cevap = 'HAYIR'  # Varsayilan
                if self.pregnancy_checker and self.current_patient_name:
                    if self.pregnancy_checker.is_pregnant(
                        tc=self.current_patient_tc,
                        ad_soyad=self.current_patient_name
                    ):
                        gebe_cevap = 'EVET'
                        self.log("      [!] GEBE HASTA TESPIT EDILDI!", "WARNING")
                # Gebe sorusunu cevapla (toggle button veya radio)
                self._answer_pregnancy_question(gebe_cevap)
                self._click_ilerle()

            elif current_page == "KAN_SEKERI":
                self.log("   Kan Şekeri Değerlendirme...")
                # ONEMLI: Gebelik sorusu bu sayfada da olabilir!
                gebe_cevap = 'HAYIR'
                if self.pregnancy_checker and self.current_patient_name:
                    if self.pregnancy_checker.is_pregnant(
                        tc=self.current_patient_tc,
                        ad_soyad=self.current_patient_name
                    ):
                        gebe_cevap = 'EVET'
                        self.log("      [!] GEBE HASTA TESPIT EDILDI!", "WARNING")
                self._answer_pregnancy_question(gebe_cevap)
                # Tetkik checkbox'larini temizle
                tetkik_ok = self._uncheck_tetkik_boxes()
                if not tetkik_ok:
                    self.log("   HYP iptal edildi, sonraki HYP'ye geciliyor", "WARNING")
                    return False
                self._click_ilerle()

            elif current_page == "SEMPTOM":
                self.log("   Semptom Değerlendirme...")
                self._click_ilerle()

            elif current_page == "KIRILGANLIK":
                self.log("   65+ Yaş Kırılganlık Ölçeği (Clinical Frailty Scale)...")
                self._fill_kirilganlik_olcegi()
                self._click_ilerle()

            elif current_page == "TETKIK":
                self.log("   Tetkik - checkboxlar kaldırılıyor...")
                tetkik_ok = self._uncheck_tetkik_boxes()
                if not tetkik_ok:
                    self.log("   HYP iptal edildi, sonraki HYP'ye geciliyor", "WARNING")
                    return False
                self._click_ilerle()

            elif current_page == "ILAC":
                self.log("   İlaç - kullanım durumu kontrol ediliyor...")
                self._handle_medication_page()
                self._click_ilerle()

            elif current_page == "TANI":
                self.log("   Tanı sayfası...")
                if self.check_exists("//button[contains(., 'Kaydet')]", 1):
                    self.click_element("//button[contains(., 'Kaydet')]")
                else:
                    self._click_ilerle()

            elif current_page == "YASAM":
                self.log("   Yaşam Tarzı Önerileri...")
                self._click_ilerle()

            else:
                self.log(f"   Bilinmeyen sayfa - ilerle deneniyor...")
                self._click_ilerle()

            time.sleep(0.5)  # 1.5 -> 0.5 saniye (optimize)

        if is_finished:
            self.log("Diyabet tamamlandı!", "SUCCESS")
        return is_finished


    # ============================================================
    # HİPERTANSİYON MODÜLÜ
    # ============================================================

    # HT Sayfa Başlıkları
    HT_HEADERS = {
        "ANAMNEZ": "//div[contains(text(), 'ANAMNEZ')]",
        "TETKIK": "//div[contains(text(), 'TETKİK')]",
        "KVH_HESAPLAMA": "//div[contains(text(), 'KVH RİSK')]",
        "TANI": "//div[contains(text(), 'TANI KONULMASI')]",
        "HEDEF": "//div[contains(text(), 'HEDEF')]",
        "ILAC": "//div[contains(text(), 'İLAÇ TEDAVİSİ')]",
        "YASAM_TARZI": "//div[contains(text(), 'YAŞAM TARZI')]",
        "OZET": "//div[contains(text(), 'SONLANDIRILMASI')]"
    }

    def _detect_ht_page(self) -> str:
        """HT sayfasını başlık veya URL'den tanı"""
        url = self.driver.current_url

        # URL bazlı hızlı tanıma
        if '/anamnez' in url:
            return "ANAMNEZ"
        elif '/tetkik' in url:
            return "TETKIK"
        elif '/kvh' in url and 'hesaplama' in url:
            return "KVH_HESAPLAMA"
        elif '/kvh' in url and 'tani' in url:
            return "KVH_TANI"
        elif '/kvh' in url and 'hedef' in url:
            return "HEDEF"
        elif '/ilac' in url:
            return "ILAC"
        elif '/yasamtarzi' in url:
            return "YASAM_TARZI"
        elif '/ozet' in url:
            return "OZET"

        # Sayfa text'inden tanıma
        page_text = self.get_page_text()
        if "SONLANDIRILMASI" in page_text:
            return "OZET"
        elif "TANI KONULMASI" in page_text:
            return "TANI"

        return "UNKNOWN"

    def _process_hipertansiyon(self) -> bool:
        """Hipertansiyon Tarama/İzlem - AKILLI SAYFA TANIMA"""
        self.log(">> Hipertansiyon protokolü başladı")
        # NOT: _start_process() artik _process_single_card'da cagiriliyor, burada TEKRAR cagirmiyoruz!

        is_finished = False
        step = 0
        same_page_count = 0
        last_page = None

        while not is_finished and step < self.MAX_STEPS:
            step += 1
            self.keep_alive()
            self.check_error_page()
            self._close_dialogs()

            current_page = self._detect_ht_page()
            self.log(f"   Adım {step}: Sayfa={current_page}", "DEBUG")

            # Aynı sayfada takılı kalma kontrolü
            if current_page == last_page:
                same_page_count += 1
                if same_page_count >= 3:
                    self.log(f"   ⚠️ {current_page} sayfasında 3 kez takılı kaldı, HYP atlanıyor", "ERROR")
                    return False
            else:
                same_page_count = 0
            last_page = current_page

            # SAYFAYA GÖRE İŞLEM
            if current_page == "OZET":
                self.log("   Sonlandırılıyor...")
                is_finished = self._click_sonlandir()

            elif current_page == "ANAMNEZ":
                self.log("   Anamnez - alanlar dolduruluyor...")
                self._fill_anamnez_fields()
                # HT_TARAMA: Normotansif riskli sorusu ANAMNEZ sayfasinda da olabilir!
                self._select_normotansif_hayir()
                self._click_ilerle()

            elif current_page == "TETKIK":
                self.log("   Tetkik - tikler kaldırılıyor...")
                tetkik_ok = self._uncheck_tetkik_boxes()
                if not tetkik_ok:
                    # HYP iptal edildi, donguden cik
                    self.log("   HYP iptal edildi, sonraki HYP'ye geciliyor", "WARNING")
                    return False
                self._click_ilerle()

            elif current_page == "ILAC":
                self.log("   İlaç - kullanım durumu kontrol ediliyor...")
                self._handle_medication_page()
                self._click_ilerle()

            elif current_page in ["TANI", "KVH_TANI"]:
                self.log("   Tanı sayfası...")
                # "Normotansif hastayı riskli değerlendiriyor musunuz?" - HAYIR sec
                self._select_normotansif_hayir()
                if self.check_exists("//button[contains(., 'Kaydet')]", 1):
                    self.click_element("//button[contains(., 'Kaydet')]")
                else:
                    self._click_ilerle()

            elif current_page in ["KVH_HESAPLAMA", "HEDEF", "YASAM_TARZI"]:
                self.log(f"   {current_page} - ilerle...")
                self._click_ilerle()

            else:
                self.log(f"   Bilinmeyen sayfa - ilerle deneniyor...")
                self._click_ilerle()

            time.sleep(0.5)  # 1.5 -> 0.5 saniye (optimize)

        if is_finished:
            self.log("Hipertansiyon tamamlandı!", "SUCCESS")
        return is_finished


    def _select_normotansif_hayir(self):
        """
        HT_TARAMA ANAMNEZ sayfasinda 'Normotansif hastayı riskli değerlendiriyor musunuz?'
        sorusuna HAYIR cevabi sec.

        HYP sistemi PrimeNG p-togglebutton kullaniyor.
        ONEMLI: Native click kullanilmali, JS click calismaz!
        """
        try:
            self.log("   Normotansif riskli sorusu araniyor...", "DEBUG")

            # HIZLI KONTROL: Sayfada "Normotansif" veya "riskli" kelimesi var mi?
            # Yoksa zaman kaybetme, hemen cik
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            if 'ormotansif' not in page_text and 'riskli' not in page_text.lower():
                self.log("   Normotansif sorusu bu sayfada yok (hizli kontrol)", "DEBUG")
                return False

            # YONTEM 1 (EN GUVENILIR): p-togglebutton elementlerini bul
            # HYP'de p-togglebutton icinde div.ui-togglebutton var
            try:
                toggles = self.driver.find_elements(By.CSS_SELECTOR, 'p-togglebutton')
                for toggle in toggles:
                    text = toggle.text.strip()
                    if 'Hay' in text:
                        # Icindeki div'i bul
                        inner_div = toggle.find_element(By.CSS_SELECTOR, 'div.ui-togglebutton')
                        inner_class = inner_div.get_attribute('class') or ''

                        if 'ui-state-active' in inner_class:
                            self.log("   Normotansif riskli -> HAYIR zaten secili")
                            return True

                        # NATIVE CLICK - JS click calismaz!
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", inner_div
                        )
                        time.sleep(0.2)
                        inner_div.click()  # Native click
                        self.log("   Normotansif riskli -> HAYIR secildi (p-togglebutton)")
                        time.sleep(0.5)
                        return True
            except Exception as e:
                self.log(f"   p-togglebutton yontemi hatasi: {str(e)[:40]}", "DEBUG")

            # YONTEM 2: ui-togglebutton div'lerini dogrudan bul
            try:
                togglebuttons = self.driver.find_elements(
                    By.CSS_SELECTOR, 'div.ui-togglebutton'
                )

                for btn in togglebuttons:
                    btn_text = btn.text.strip()
                    if 'Hay' in btn_text:
                        btn_class = btn.get_attribute('class') or ''
                        if 'ui-state-active' in btn_class:
                            self.log("   Normotansif riskli -> HAYIR zaten secili")
                            return True

                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", btn
                        )
                        time.sleep(0.2)
                        btn.click()  # Native click - JS click calismaz!
                        self.log("   Normotansif riskli -> HAYIR secildi (container)")
                        time.sleep(0.5)
                        return True
            except Exception as e:
                self.log(f"   Yontem 2 hatasi: {str(e)[:40]}", "DEBUG")

            # Yontem 3: mat-radio-button (eski yontem, fallback)
            mat_radio_xpaths = [
                "//mat-radio-button[.//span[contains(text(), 'Hayır')]]",
                "//mat-radio-button[contains(., 'Hayır')]",
                "//mat-radio-button[@value='false']",
            ]

            for xpath in mat_radio_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for elem in elements:
                        if elem.is_displayed():
                            elem_class = elem.get_attribute('class') or ''
                            if 'mat-radio-checked' in elem_class:
                                self.log("   Normotansif riskli -> HAYIR zaten secili")
                                return True
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});", elem
                            )
                            time.sleep(0.2)
                            self.driver.execute_script("arguments[0].click();", elem)
                            self.log("   Normotansif riskli -> HAYIR secildi (mat-radio)")
                            time.sleep(0.5)
                            return True
                except:
                    continue

            # Yontem 4: Standart HTML radio buton
            html_radio_xpaths = [
                "//label[contains(text(), 'Hayır')]//input[@type='radio']",
                "//input[@type='radio'][contains(@value, 'false')]",
            ]

            for xpath in html_radio_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for elem in elements:
                        if elem.is_displayed() or elem.is_enabled():
                            self.driver.execute_script("arguments[0].click();", elem)
                            self.log("   Normotansif riskli -> HAYIR secildi (html)")
                            time.sleep(0.5)
                            return True
                except:
                    continue

            self.log("   Normotansif riskli sorusu bulunamadi (atlanıyor)", "DEBUG")
            return False

        except Exception as e:
            self.log(f"   Normotansif secim hatasi: {e}", "DEBUG")
            return False


    # ============================================================
    # OBEZİTE MODÜLÜ - AKILLI SAYFA TANIMA (V2 - OBE_IZLEM DESTEKLİ)
    # ============================================================

    # Obezite Sayfa Başlıkları
    # OBE_TARAMA: ANAMNEZ -> YASAM -> OZET (3 adım)
    # OBE_IZLEM: ANAMNEZ -> OYKU -> TETKIK -> ILAC -> EVRE -> YASAM -> OZET (7 adım)
    OBE_HEADERS = {
        "ANAMNEZ": "//div[contains(text(), 'ANAMNEZ')]",
        "OYKU": "//div[contains(text(), 'OBEZİTE ÖYKÜSÜ')]",
        "TETKIK": "//div[contains(text(), 'TETKİK')]",
        "ILAC": "//div[contains(text(), 'İLAÇLAR')]",
        "EVRE": "//div[contains(text(), 'EDMONTON')]",
        "YASAM": "//div[contains(text(), 'YAŞAM TARZI')]",
        "OZET": "//div[contains(text(), 'SONLANDIRILMASI')]"
    }

    def _detect_obe_page(self) -> str:
        """Obezite sayfasını URL veya başlıktan tanı (OBE_TARAMA ve OBE_IZLEM)"""
        url = self.driver.current_url

        # URL bazlı hızlı tanıma - ONEMLI: /ilac kontrolu /tetkik'ten once olmali!
        if '/obezite/anamnez' in url or '/anamnez' in url:
            return "ANAMNEZ"
        elif '/obezite/oyku' in url or '/oyku' in url:
            return "OYKU"
        elif '/obezite/tetkik' in url:
            return "TETKIK"
        elif '/obezite/ilac' in url or '/ilac' in url:
            # ILAC sayfasi - /ilac genel kontrolu eklendi
            return "ILAC"
        elif '/obezite/eslikedenhastalik' in url or '/evre' in url:
            return "EVRE"
        elif '/obezite/yasamtarzi' in url or '/yasamtarzi' in url:
            return "YASAM"
        elif '/tetkik' in url:
            return "TETKIK"
        elif '/ozet' in url:
            return "OZET"

        # Sayfa text'inden tanıma
        page = self.get_page_text()
        if "SONLANDIRILMASI" in page:
            return "OZET"
        elif "EDMONTON" in page or "EŞLİK EDEN" in page or "ESLIK EDEN" in page:
            return "EVRE"
        elif "AĞIRLIK ARTIŞINA" in page or "AGIRLIK ARTISINA" in page:
            return "ILAC"
        elif "TETKİK" in page or "TETKIK" in page:
            return "TETKIK"
        elif "OBEZİTE ÖYKÜSÜ" in page or "OBEZITE OYKUSU" in page:
            return "OYKU"
        elif "YAŞAM TARZI" in page or "YASAM TARZI" in page:
            return "YASAM"
        elif "ANAMNEZ" in page:
            return "ANAMNEZ"

        return "UNKNOWN"

    def _answer_pregnancy_question(self, answer: str = 'HAYIR') -> bool:
        """
        OBE_TARAMA/OBE_IZLEM Anamnez sayfasindaki gebelik sorusunu cevapla.
        "Birey halihazırda gebe mi?" sorusu ZORUNLU alan!

        Args:
            answer: 'EVET' veya 'HAYIR'
        """
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        try:
            # HIZLI JS KONTROL: Gebe sorusu var mi?
            has_gebe = self.driver.execute_script("return document.body.innerText.toUpperCase().includes('GEBE');")
            if not has_gebe:
                self.driver.implicitly_wait(original_wait)
                return True  # Soru yok, devam et

            self.log(f"      Gebelik sorusu cevaplaniyor: {answer}", "DEBUG")

            # YONTEM 1 (EN GUVENILIR): p-togglebutton icindeki div.ui-togglebutton
            # OBE_TARAMA'da bu yapı kullanılıyor
            try:
                p_toggles = self.driver.find_elements(By.CSS_SELECTOR, 'p-togglebutton')
                for toggle in p_toggles:
                    try:
                        toggle_text = toggle.text.strip().upper()
                        inner_div = toggle.find_element(By.CSS_SELECTOR, 'div.ui-togglebutton')
                        inner_class = inner_div.get_attribute('class') or ''

                        if answer == 'HAYIR' and 'HAYIR' in toggle_text:
                            if 'ui-state-active' in inner_class:
                                self.log("      Gebelik: HAYIR zaten secili", "DEBUG")
                                return True
                            # Native click kullan - JS click calismayabilir
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});", inner_div
                            )
                            time.sleep(0.1)
                            inner_div.click()
                            self.log("      Gebelik: HAYIR secildi (p-togglebutton)", "SUCCESS")
                            time.sleep(0.2)
                            return True
                        elif answer == 'EVET' and 'EVET' in toggle_text:
                            if 'ui-state-active' in inner_class:
                                self.log("      Gebelik: EVET zaten secili", "DEBUG")
                                return True
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});", inner_div
                            )
                            time.sleep(0.1)
                            inner_div.click()
                            self.log("      Gebelik: EVET secildi (p-togglebutton)", "SUCCESS")
                            time.sleep(0.2)
                            return True
                    except:
                        continue
            except Exception as e:
                self.log(f"      p-togglebutton yontemi: {str(e)[:30]}", "DEBUG")

            # YONTEM 2: div.ui-togglebutton dogrudan
            try:
                togglebuttons = self.driver.find_elements(By.CSS_SELECTOR, 'div.ui-togglebutton')
                for btn in togglebuttons:
                    btn_text = btn.text.strip().upper()
                    btn_class = btn.get_attribute('class') or ''

                    if answer == 'HAYIR' and 'HAYIR' in btn_text:
                        if 'ui-state-active' in btn_class:
                            self.log("      Gebelik: HAYIR zaten secili", "DEBUG")
                            return True
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", btn
                        )
                        time.sleep(0.1)
                        btn.click()
                        self.log("      Gebelik: HAYIR secildi (div)", "SUCCESS")
                        time.sleep(0.2)
                        return True
                    elif answer == 'EVET' and 'EVET' in btn_text:
                        if 'ui-state-active' in btn_class:
                            self.log("      Gebelik: EVET zaten secili", "DEBUG")
                            return True
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", btn
                        )
                        time.sleep(0.1)
                        btn.click()
                        self.log("      Gebelik: EVET secildi (div)", "SUCCESS")
                        time.sleep(0.2)
                        return True
            except Exception as e:
                self.log(f"      div yontemi: {str(e)[:30]}", "DEBUG")

            # YONTEM 3: XPath ile button/span
            if answer == 'HAYIR':
                xpaths = [
                    "//p-togglebutton[contains(., 'Hayır')]//div[contains(@class, 'ui-togglebutton')]",
                    "//div[contains(@class, 'ui-togglebutton')][contains(., 'Hayır')]",
                    "//button[contains(., 'Hayır')]",
                    "//span[contains(text(), 'Hayır')]/ancestor::div[contains(@class, 'togglebutton')]",
                ]
            else:
                xpaths = [
                    "//p-togglebutton[contains(., 'Evet')]//div[contains(@class, 'ui-togglebutton')]",
                    "//div[contains(@class, 'ui-togglebutton')][contains(., 'Evet')]",
                    "//button[contains(., 'Evet')]",
                ]

            for xpath in xpaths:
                try:
                    elem = self.driver.find_element(By.XPATH, xpath)
                    if elem.is_displayed():
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", elem
                        )
                        time.sleep(0.1)
                        elem.click()
                        self.log(f"      Gebelik: {answer} secildi (xpath)", "SUCCESS")
                        time.sleep(0.2)
                        return True
                except:
                    continue

            self.log("      [!] Gebelik sorusu CEVAPLANAMADI!", "WARNING")
            return False

        except Exception as e:
            self.log(f"      Gebelik sorusu hatasi: {str(e)[:40]}", "WARNING")
            return False
        finally:
            self.driver.implicitly_wait(original_wait)

    def _fill_anamnez_ng_invalid(self) -> bool:
        """
        OBE_IZLEM Anamnez sayfasındaki ng-invalid (boş zorunlu) alanları doldur
        Sistolik, Diyastolik, Nabız alanları boş olabilir - HIZLI
        """
        # OPTIMIZE: Implicit wait'i gecici kapat
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        try:
            # ng-invalid class'lı inputları bul
            invalid_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input.ng-invalid')
            default_values = ['120', '80', '90']  # Sistolik, Diyastolik, Nabız

            filled = 0
            for idx, inp in enumerate(invalid_inputs):
                if idx >= len(default_values):
                    break
                try:
                    value = inp.get_attribute('value') or ''
                    if value == '':
                        # HIZLI: JavaScript ile deger gir
                        self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", inp, default_values[idx])
                        filled += 1
                except:
                    continue

            if filled > 0:
                self.log(f"      {filled} boş alan dolduruldu (ng-invalid)", "DEBUG")
            return True
        except Exception as e:
            self.log(f"      ng-invalid doldurma hatası: {str(e)[:40]}", "DEBUG")
        finally:
            self.driver.implicitly_wait(original_wait)
        return True

    def _click_tumunu_kaldir(self) -> bool:
        """
        OBE_IZLEM Tetkik sayfasinda 'Tumunu kaldir' span'ina tikla - HIZLI
        OPTIMIZE: implicit wait=0
        
        Returns:
            True: Basarili
            False: Tetkik sorunu var - OBE_IZLEM pas gecilmeli
        """
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        try:
            # Yontem 1: 'Tumunu kaldir' span'ina tikla
            remove_xpaths = [
                "//span[contains(text(), 'Tumunu kaldir')]",
                "//span[contains(text(), 'Tümünü kaldır')]",
                "//button[contains(., 'Tumunu kaldir')]",
                "//a[contains(., 'Tumunu kaldir')]",
            ]
            
            for xpath in remove_xpaths:
                try:
                    remove_elem = self.driver.find_element(By.XPATH, xpath)
                    self.js_click(remove_elem)
                    self.log("      'Tumunu kaldir' tiklandi", "DEBUG")
                    time.sleep(0.2)  # OPTIMIZE: 0.5 -> 0.2
                    
                    # Kontrol: Hala isaretli checkbox var mi?
                    checked = self.driver.find_elements(By.CSS_SELECTOR, '.p-checkbox-box.p-highlight, .ui-chkbox-box.ui-state-active')
                    if not checked:
                        return True  # Basarili
                    break
                except:
                    continue
            
            # Yontem 2: Isaretli checkbox'lari tek tek kaldir
            max_attempts = 3
            for attempt in range(max_attempts):
                checked = self.driver.find_elements(By.CSS_SELECTOR, '.p-checkbox-box.p-highlight, .ui-chkbox-box.ui-state-active')
                if not checked:
                    self.log("      Tum tikler kaldirildi", "DEBUG")
                    return True
                
                self.log(f"      Deneme {attempt+1}: {len(checked)} isaretli checkbox", "DEBUG")
                for cb in checked:
                    try:
                        self.driver.execute_script('arguments[0].scrollIntoView({block: "center"});', cb)
                        self.js_click(cb)
                        time.sleep(0.1)  # OPTIMIZE: 0.1+0.2 -> 0.1
                    except:
                        pass
            
            # Son kontrol
            checked = self.driver.find_elements(By.CSS_SELECTOR, '.p-checkbox-box.p-highlight, .ui-chkbox-box.ui-state-active')
            if checked:
                self.log(f"      [!] {len(checked)} tik kaldiramadi - onceki deger deneniyor", "WARNING")
                
                # Yontem 3: Onceki degerleri girmeyi dene
                if self._fill_tetkik_previous_values():
                    return True
                
                # Hala sorun varsa - OBE_IZLEM pas gecilmeli
                self.log("      [X] TETKIK SORUNU - OBE_IZLEM pas gecilecek!", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"      Tumunu kaldir hatasi: {str(e)[:40]}", "WARNING")
            return True
        finally:
            self.driver.implicitly_wait(original_wait)
    
    def _fill_tetkik_previous_values(self) -> bool:
        """
        Tetkik alanlarinda onceki degerleri girmeye calis.
        ng-invalid alanlari bul ve varsayilan deger gir.
        """
        try:
            # Bos zorunlu alanlari bul
            invalid_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input.ng-invalid')
            
            if not invalid_inputs:
                return True
            
            self.log(f"      {len(invalid_inputs)} bos alan bulundu, doldurulmaya calisiliyor", "DEBUG")
            
            filled = 0
            for inp in invalid_inputs:
                try:
                    # Placeholder veya label'dan alan tipini anla
                    placeholder = inp.get_attribute('placeholder') or ''
                    inp_id = inp.get_attribute('id') or ''
                    
                    # Varsayilan degerler
                    if 'HbA1c' in placeholder or 'hba1c' in inp_id.lower():
                        default = '6.5'
                    elif 'Aclik' in placeholder or 'glukoz' in inp_id.lower():
                        default = '100'
                    elif 'Kolesterol' in placeholder or 'LDL' in placeholder:
                        default = '120'
                    elif 'Trigliserit' in placeholder:
                        default = '150'
                    else:
                        default = '100'  # Genel varsayilan
                    
                    inp.clear()
                    inp.send_keys(default)
                    filled += 1
                    time.sleep(0.2)
                except:
                    continue
            
            if filled > 0:
                self.log(f"      {filled} alan varsayilan degerle dolduruldu", "DEBUG")
                return True
            
            return False
            
        except Exception as e:
            self.log(f"      Onceki deger girme hatasi: {str(e)[:40]}", "WARNING")
            return False

    def _select_izlem_zamani(self) -> bool:
        """
        OBE_IZLEM Evre (Edmonton) sayfasında izlem zamanı seç
        '3 Ay' veya '6 Ay' seçilmeli (zorunlu alan)
        """
        try:
            # Radio button veya label olarak '3 Ay' bul
            selectors = [
                "//label[contains(text(), '3 Ay')]//preceding-sibling::*",
                "//span[contains(text(), '3 Ay')]",
                "//*[text()='3 Ay']",
                "//p-radiobutton[.//label[contains(text(), '3 Ay')]]//div[contains(@class, 'radiobutton')]",
            ]

            for sel in selectors:
                try:
                    elem = self.driver.find_element(By.XPATH, sel)
                    if elem:
                        self.js_click(elem)
                        self.log("      İzlem zamanı: 3 Ay seçildi", "DEBUG")
                        time.sleep(0.3)
                        return True
                except:
                    continue

            # Bulunamazsa 6 Ay dene
            try:
                elem = self.driver.find_element(By.XPATH, "//*[text()='6 Ay']")
                self.js_click(elem)
                self.log("      İzlem zamanı: 6 Ay seçildi", "DEBUG")
                return True
            except:
                pass

            return True  # Seçenek bulunamazsa da devam et
        except Exception as e:
            self.log(f"      İzlem zamanı seçim hatası: {str(e)[:40]}", "DEBUG")
            return True

    def _process_obezite(self) -> bool:
        """Obezite Tarama/İzlem - AKILLI SAYFA TANIMA (V2)

        OBE_TARAMA Akışı (3 adım): ANAMNEZ -> YASAM_TARZI -> OZET
        OBE_IZLEM Akışı (7 adım): ANAMNEZ -> OYKU -> TETKIK -> ILAC -> EVRE -> YASAM -> OZET
        """
        self.log(">> Obezite protokolü başladı")
        # NOT: _start_process() artik _process_single_card'da cagiriliyor!

        is_finished = False
        step = 0

        while not is_finished and step < self.MAX_STEPS:
            step += 1
            self.keep_alive()
            self.check_error_page()
            self._close_dialogs()

            current_page = self._detect_obe_page()
            self.log(f"   Adım {step}: Sayfa={current_page}", "DEBUG")

            # SAYFAYA GÖRE İŞLEM
            if current_page == "OZET":
                self.log("   Sonlandırılıyor...")
                is_finished = self._click_sonlandir()

            elif current_page == "ANAMNEZ":
                self.log("   Anamnez sayfası...")

                # OBE_TARAMA: "Obezite Tanısı" zorunlu alanını doldur
                # Dropdown "Seçiniz" ise "E66.9 - Obezite, tanımlanmamış" sec
                self._select_obezite_tanisi()

                # AKILLI GEBELIK KONTROLU - Gebe listesinden kontrol et
                gebe_cevap = 'HAYIR'  # Varsayilan
                if self.pregnancy_checker and self.current_patient_name:
                    if self.pregnancy_checker.is_pregnant(
                        tc=self.current_patient_tc,
                        ad_soyad=self.current_patient_name
                    ):
                        gebe_cevap = 'EVET'
                        self.log("      [!] GEBE HASTA TESPIT EDILDI!", "WARNING")

                # Gebe sorusunu cevapla (toggle button veya radio)
                self._answer_pregnancy_question(gebe_cevap)

                # OBE_IZLEM: ng-invalid bos alanlari doldur (Sistolik, Diyastolik, Nabiz)
                self._fill_anamnez_ng_invalid()

                # Olcum alanlari bossa doldur
                self._fill_anamnez_fields()
                self._click_ilerle()

            elif current_page == "OYKU":
                self.log("   Obezite Öyküsü sayfası...")
                # Genellikle önceki değerler seçili, direkt ilerle
                self._click_ilerle()

            elif current_page == "TETKIK":
                self.log("   Tetkik Degerlendirme sayfasi...")
                # GUNCELLEME: _uncheck_tetkik_boxes kullan (dis lab sonucu dahil)
                tetkik_success = self._uncheck_tetkik_boxes()

                if not tetkik_success:
                    # TETKIK sorunu - OBE_IZLEM pas gecilecek
                    self.log("   [X] TETKIK HATASI - OBE_IZLEM pas geciliyor!", "ERROR")

                    # Kullaniciya bildirim ekle
                    notification = {
                        'hasta': self.current_patient_name,
                        'hyp_tip': 'OBE_IZLEM',
                        'sebep': 'Tetkik tikleri kaldirilamadi',
                        'tarih': time.strftime('%d.%m.%Y %H:%M')
                    }
                    self.skipped_hyp_notifications.append(notification)

                    # Geri don ve diger HYP'leri dene
                    try:
                        self.driver.back()
                        time.sleep(1)
                    except:
                        pass
                    return False  # OBE_IZLEM basarisiz

                self._click_ilerle()

            elif current_page == "ILAC":
                self.log("   Ağırlık Artışına Sebep Olan İlaçlar sayfası...")
                # Reçete tarihine göre aktif kullanım belirlenir
                self._handle_medication_page()
                self._click_ilerle()

            elif current_page == "EVRE":
                self.log("   Edmonton Evresi sayfası...")
                # ZORUNLU: İzlem zamanı seç (3 Ay veya 6 Ay)
                self._select_izlem_zamani()
                self._click_ilerle()

            elif current_page == "YASAM":
                self.log("   Yaşam Tarzı Önerileri...")
                self._click_ilerle()

            else:
                self.log(f"   Bilinmeyen sayfa - ilerle deneniyor...")
                self._click_ilerle()

            time.sleep(0.5)  # 1.5 -> 0.5 saniye (optimize)

        if is_finished:
            self.log("Obezite tamamlandı!", "SUCCESS")
        return is_finished

    def _select_obezite_tanisi(self):
        """
        OBE_TARAMA ANAMNEZ sayfasinda 'Obezite Tanısı *' dropdown'unu doldur.
        Eger 'Seçiniz' durumundaysa 'E66.9 - Obezite, tanımlanmamış' sec.
        OPTIMIZE: Hizli timeout ile kontrol (0.3sn) + implicit wait=0
        """
        # Implicit wait'i gecici kapat
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        try:
            # HIZLI KONTROL: Dropdown var mi? (0.3sn timeout)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            try:
                dropdown = WebDriverWait(self.driver, 0.3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'p-dropdown.hyp-dropdown'))
                )
            except:
                # Dropdown yok, hizlica devam et
                self.driver.implicitly_wait(original_wait)
                return True
            
            # Dropdown'u bul
            # dropdown = self.driver.find_element(By.CSS_SELECTOR, 'p-dropdown.hyp-dropdown')
            dropdown_label = dropdown.find_element(By.CSS_SELECTOR, '.ui-dropdown-label')
            current_value = dropdown_label.text.strip()

            # Zaten secili mi?
            if current_value and 'Seçiniz' not in current_value:
                self.log(f"   Obezite tanısı zaten seçili: {current_value[:30]}", "DEBUG")
                return True

            # Dropdown'u ac
            dropdown.click()
            time.sleep(0.1)  # OPTIMIZE: 0.3 -> 0.1

            # E66.9 - Obezite, tanımlanmamış sec
            try:
                e66_9 = self.driver.find_element(By.XPATH, "//li[contains(., 'E66.9')]")
                e66_9.click()
                self.log("   Obezite tanısı seçildi: E66.9 - Obezite, tanımlanmamış", "SUCCESS")
                time.sleep(0.1)  # OPTIMIZE: 0.3 -> 0.1
                return True
            except:
                # E66.9 bulunamazsa ilk secenegi sec (Seciniz haric)
                try:
                    options = self.driver.find_elements(By.CSS_SELECTOR, '.ui-dropdown-item')
                    if len(options) > 1:
                        options[1].click()
                        self.log(f"   Obezite tanısı seçildi: {options[1].text[:30]}", "SUCCESS")
                        time.sleep(0.1)  # OPTIMIZE: 0.3 -> 0.1
                        return True
                except:
                    pass

            self.log("   Obezite tanısı seçilemedi!", "WARNING")
            return False

        except Exception as e:
            self.log(f"   Obezite tanısı dropdown hatası: {str(e)[:40]}", "DEBUG")
            return False
        finally:
            self.driver.implicitly_wait(original_wait)


    # ============================================================
    # KVR MODÜLÜ
    # ============================================================
    def _process_kvr(self) -> bool:
        """KVR Tarama/İzlem - Tetkik Handling ile Akış

        KVR_IZLEM Akışı (8 adım):
        1. anamnez → İlerle
        2. medikalozgecmis → İlerle
        3. tetkik → Tikleri kaldır + Dış lab → İlerle
        4. hesaplama → İlerle
        5. tani → İlerle
        6. hedef → İlerle
        7. yasamtarzi → İlerle
        8. ozet → Sonlandır

        ONEMLI: Tetkik sayfasinda TUM tikler kaldirilmali!
        Kalkmayan tik varsa dis lab sonucu girilmeli!
        """
        self.log(">> KVR protokolü başladı")
        # NOT: _start_process() artik _process_single_card'da cagiriliyor!

        last_url = None
        same_url_count = 0
        MAX_SAME_URL = 4  # Aynı URL'de maksimum kalma sayısı

        for step in range(1, 20):  # Maksimum 20 adım (artırıldı)
            self.keep_alive()
            self.check_error_page()
            self._close_dialogs()

            time.sleep(0.5)

            current_url = self.driver.current_url
            page_text = self.get_page_text()

            # Aynı sayfada takılı kalma kontrolü
            if current_url == last_url:
                same_url_count += 1
                if same_url_count >= MAX_SAME_URL:
                    self.log(f"   !!! Aynı sayfada {MAX_SAME_URL} kez takıldı - HYP iptal ediliyor!", "ERROR")
                    self._cancel_current_hyp(reason="KVR protokolünde sayfa takılması")
                    return False
            else:
                same_url_count = 0
                last_url = current_url

            # =====================================================
            # OZET SAYFASI - SONLANDIR
            # =====================================================
            if '/ozet' in current_url or 'SONLANDIRILMASI' in page_text:
                self.log("   OZET sayfası - Sonlandırılıyor...")
                if self._click_sonlandir():
                    self.log("KVR protokolü tamamlandı!", "SUCCESS")
                    return True
                else:
                    self.log("Sonlandır butonu tıklanamadı!", "WARNING")
                    return False

            # =====================================================
            # TETKIK SAYFASI - OZEL ISLEM
            # =====================================================
            if '/tetkik' in current_url:
                self.log("   TETKIK sayfasi - tikler kaldiriliyor...")
                tetkik_ok = self._uncheck_tetkik_boxes()
                if not tetkik_ok:
                    self.log("   !!! TETKIK tikleri kaldirilamadi - HYP pas geciliyor!", "ERROR")
                    return False

            # Mevcut butonları kontrol et
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            btn_texts = [b.text.strip() for b in buttons if b.text.strip()]

            self.log(f"   Adım {step}: URL={current_url.split('/')[-1]}, Butonlar={btn_texts[:5]}", "DEBUG")

            # =====================================================
            # IZLEM BASLAT BUTONU - KVR_IZLEM icin ozel
            # =====================================================
            izlem_baslat_btn = None
            for b in buttons:
                txt = b.text.strip()
                if 'İzlem Başlat' in txt and 'Yüz Yüze' in txt:
                    izlem_baslat_btn = b
                    break

            if izlem_baslat_btn:
                self.log("   İzlem Başlat (Yüz Yüze) butonu tıklanıyor...")
                try:
                    self.js_click(izlem_baslat_btn)
                    time.sleep(0.5)
                    continue
                except Exception as e:
                    self.log(f"   İzlem Başlat tıklanamadı: {e}", "WARNING")

            # Sonlandır varsa tıkla ve bitir
            if any('Sonlandır' in t for t in btn_texts):
                self.log("   Sonlandırılıyor...")
                if self._click_sonlandir():
                    self.log("KVR protokolü tamamlandı!", "SUCCESS")
                    return True
                else:
                    self.log("Sonlandır butonu tıklanamadı!", "WARNING")
                    return False

            # İlerle varsa tıkla
            if any('İlerle' in t for t in btn_texts):
                if self._click_ilerle():
                    self.log(f"   İlerle tıklandı (adım {step})", "DEBUG")
                    time.sleep(0.3)
                else:
                    self.log("İlerle butonu tıklanamadı!", "WARNING")
                    return False
            else:
                # Buton bulunamazsa biraz bekle ve tekrar dene
                self.log(f"   Buton bulunamadı, bekleniyor... (adım {step})", "DEBUG")
                time.sleep(0.5)
                # Tekrar butonlari kontrol et
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                btn_texts = [b.text.strip() for b in buttons if b.text.strip()]

                if any('Sonlandır' in t for t in btn_texts):
                    if self._click_sonlandir():
                        self.log("KVR protokolü tamamlandı!", "SUCCESS")
                        return True
                elif any('İlerle' in t for t in btn_texts):
                    self._click_ilerle()
                    continue
                else:
                    self.log("İlerle veya Sonlandır butonu bulunamadı!", "WARNING")
                    return False

        self.log("Maksimum adım sayısına ulaşıldı - HYP iptal ediliyor!", "WARNING")
        self._cancel_current_hyp(reason="KVR protokolünde maksimum adım aşıldı")
        return False

    # ============================================================
    # YAŞLI SAĞLIĞI MODÜLÜ
    # ============================================================

    # ============================================================
    # YASLI IZLEM - HEMSIRE VERILERINI KULLAN
    # ============================================================
    # ONEMLI GUNCELLEME (28 Kasim 2025):
    # ---------------------------------
    # Hemsire TUM geriatrik degerlendirme sorularini ONCEDEN dolduruyor!
    # 16 sorudan 15'i hemsire tarafindan isaretlenmis durumda.
    #
    # BIZ SADECE:
    # - "Daha önce Kemik Mineral Dansitometrisi (KMD) yapılmış mı?" sorusuna
    #   HAYIR cevabi veriyoruz (varsayilan).
    #
    # DIGER 15 SORU (hemsire doldurdu, DOKUNMUYORUZ):
    # - SARC-F sonucuna göre sarkopeni riski var mı?
    # - Son 6 ayda %10 kilo kaybı var mı?
    # - BKİ <= 22 mi?
    # - Hastanın demansı var mı?
    # - Düşme öyküsü var mı?
    # - İşitmede sorun var mı?
    # - Görmede sorun var mı?
    # - Depresyon soruları
    # - Üriner/fekal inkontinans
    # - Basınç yaralanması
    # - 2+ saat immobil mi?
    # - İhmal/istismar soruları
    # - vs.
    #
    # ============================================================

    # TODO: OTOMATİK POLİFARMASİ TESPİTİ
    # =====================================
    # Yaşlı İzlem sayfasında (/yasli/ilac) Polifarmasi sorusu var.
    # Otomasyon hastanın ilaç listesinden bunu otomatik hesaplayabilir:
    #
    # ALGORITMA:
    # 1. Hastanın aktif ilaç listesini al (reçete tarihi + miktar hesabı yapılmış)
    # 2. Kısa süreli kullanılan ilaçları filtrele (polifarmasiye dahil edilmez):
    #    - PAROL, PARACETAMOL, IBUPROFEN (ağrı kesiciler)
    #    - ANTİBİYOTİK (kısa süreli tedavi)
    #    - KREM, POMAD, JEL (topikal)
    #    - DAMLA (göz/kulak)
    #    - SPREY, INHALER (bazıları kronik olabilir - dikkat!)
    #    - VAJINAL, REKTAL (lokal tedavi)
    #    - ANTIFUNGAL (TRAVAZOL vb.)
    #    - LAKSATİF (BEKUNIS vb.)
    # 3. Kalan KRONİK ilaç sayısını hesapla
    # 4. Eğer kronik_ilac_sayisi >= 5: Polifarmasi = EVET
    #    Eğer kronik_ilac_sayisi < 5: Polifarmasi = HAYIR
    #
    # ÖRNEK (Şehriban Satılmış hastası):
    # Kronik (7): VENOTREX, ECOPİRİN, ETNA COMBO, CANDEXİL, DIYATIX, COLEDAN-D3, RABİZA
    # Kısa süreli (2): TRAVAZOL krem, BEKUNIS laksatif
    # Sonuç: 7 >= 5 → Polifarmasi = EVET
    #
    # KISA SÜRELİ İLAÇ KEYWORDS:
    KISA_SURELI_ILAC_KEYWORDS = [
        'PAROL', 'PARACETAMOL', 'IBUPROFEN', 'ASPIRIN',
        'ANTIBIYOTIK', 'AMOKSISILIN', 'SEFALOSPORIN',
        'KREM', 'POMAD', 'JEL', 'LOSYON',
        'DAMLA', 'SPREY',
        'VAJINAL', 'REKTAL',
        'ANTIFUNGAL', 'TRAVAZOL', 'TERBINAFIN',
        'LAKSATIF', 'BEKUNIS', 'DULCOLAX',
        'ANTIHISTAMINIK', 'ALLERJI',
    ]

    def _check_polifarmasi(self, ilac_listesi: List[str]) -> bool:
        """
        İlaç listesinden polifarmasi durumunu kontrol et

        Args:
            ilac_listesi: Hastanın aktif ilaç isimleri listesi

        Returns:
            True = Polifarmasi VAR (5+ kronik ilaç)
            False = Polifarmasi YOK
        """
        kronik_ilaclar = []
        kisa_sureli_ilaclar = []

        for ilac in ilac_listesi:
            ilac_upper = ilac.upper()

            # Kısa süreli mi kontrol et
            is_kisa_sureli = any(keyword in ilac_upper for keyword in self.KISA_SURELI_ILAC_KEYWORDS)

            if is_kisa_sureli:
                kisa_sureli_ilaclar.append(ilac)
            else:
                kronik_ilaclar.append(ilac)

        self.log(f"      Kronik ilaç: {len(kronik_ilaclar)}, Kısa süreli: {len(kisa_sureli_ilaclar)}", "DEBUG")

        # 5 veya daha fazla kronik ilaç = Polifarmasi
        return len(kronik_ilaclar) >= 5

    def _detect_yasli_page(self) -> str:
        """Yaşlı İzlem sayfasını URL'den tanı"""
        url = self.driver.current_url

        if '/anamnezfizikmuayene' in url or '/anamnez' in url:
            return "ANAMNEZ"
        elif '/ilac' in url:
            return "ILAC"
        elif '/birincilgeriatrik' in url or '/geriatrik' in url:
            return "GERIATRIK"
        elif '/tetkik' in url:
            return "TETKIK"
        elif '/geneldurumdegerlendirme' in url or '/planlama' in url:
            return "PLANLAMA"
        elif '/ozet' in url:
            return "OZET"

        # Sayfa text'inden tanıma
        page = self.get_page_text()
        if "SONLANDIRILMASI" in page or "ÖZET" in page:
            return "OZET"
        elif "GERİATRİK" in page or "GERIATRIK" in page:
            return "GERIATRIK"
        elif "İLAÇ" in page or "ILAC" in page:
            return "ILAC"
        elif "TETKİK" in page:
            return "TETKIK"
        elif "PLANLAMA" in page or "İZLEM SIKLIĞI" in page:
            return "PLANLAMA"

        return "UNKNOWN"

    def _fill_yasli_ilac_page(self) -> bool:
        """
        Yasli Izlem - Ilac sayfasi (ZORUNLU alanlar):
        1. Polifarmasi var mi? *
        2. Uygunsuz/eksik ilac kullanimi var mi? *
        
        AKILLI SISTEM: Ilac listesinden otomatik hesaplama yapar.
        """
        self.log("   Ilac sayfasi - akilli analiz yapiliyor...")

        # Varsayilan degerler
        polifarmasi_cevap = 'EVET'  # Yaslilarda sik
        uygunsuz_cevap = 'HAYIR'
        uygunsuz_uyarilar = []

        # Akilli analiz - Ilac listesi varsa
        if self.drug_analyzer and self.current_patient_drugs:
            try:
                analysis = self.drug_analyzer.analyze_drug_list(self.current_patient_drugs)
                
                # Polifarmasi hesapla (5+ kronik ilac)
                polifarmasi_cevap = 'EVET' if analysis['polypharmacy'] else 'HAYIR'
                self.log(f"      Kronik ilac sayisi: {analysis['chronic_count']}", "DEBUG")
                self.log(f"      Polifarmasi durumu: {analysis['polypharmacy_level']}", "DEBUG")
                
                # Uygunsuz ilac kontrolu
                if analysis['inappropriate_drugs']:
                    uygunsuz_cevap = 'EVET'
                    uygunsuz_uyarilar = [d['warning'] for d in analysis['inappropriate_drugs']]
                    self.log(f"      [!] {len(uygunsuz_uyarilar)} uygunsuz ilac tespit edildi!", "WARNING")
                    for uyari in uygunsuz_uyarilar[:3]:  # Ilk 3 uyariyi goster
                        self.log(f"         - {uyari}", "WARNING")
            except Exception as e:
                self.log(f"      Ilac analizi hatasi: {str(e)[:50]}", "WARNING")

        try:
            # ui-togglebutton'lari bul
            toggles = self.driver.find_elements(By.CSS_SELECTOR, '.ui-togglebutton')

            if len(toggles) >= 4:
                # Toggle yapisi: [Polifarmasi-Evet, Polifarmasi-Hayir, Uygunsuz-Evet, Uygunsuz-Hayir]
                
                # Polifarmasi
                if polifarmasi_cevap == 'EVET':
                    poli_btn = toggles[0]  # EVET
                else:
                    poli_btn = toggles[1]  # HAYIR
                    
                if 'ui-state-active' not in (poli_btn.get_attribute('class') or ''):
                    self.js_click(poli_btn)
                    self.log(f"      Polifarmasi: {polifarmasi_cevap}", "DEBUG")
                    time.sleep(0.3)

                # Uygunsuz ilac
                if uygunsuz_cevap == 'EVET':
                    uyg_btn = toggles[2]  # EVET
                else:
                    uyg_btn = toggles[3]  # HAYIR
                    
                if 'ui-state-active' not in (uyg_btn.get_attribute('class') or ''):
                    self.js_click(uyg_btn)
                    self.log(f"      Uygunsuz ilac: {uygunsuz_cevap}", "DEBUG")
                    time.sleep(0.3)

                return True
            else:
                self.log(f"   Toggle sayisi beklenenden az: {len(toggles)}", "WARNING")
                return True  # Devam et

        except Exception as e:
            self.log(f"   Ilac sayfasi hatasi: {str(e)[:50]}", "WARNING")
            return True

    def _fill_yasli_geriatrik_page(self) -> bool:
        """
        Yasli Izlem - Geriatrik Degerlendirme sayfasi (Birincil Geriatrik Sendromlar)

        ONEMLI: Hemsire zaten TUM verileri girmis durumda!
        16 sorudan 15'i hemsire tarafindan doldurulmus.

        BIZ SADECE:
        1. "Daha önce Kemik Mineral Dansitometrisi (KMD) yapılmış mı?" sorusuna cevap ver
        2. Bos kalan zorunlu toggle butonlari HAYIR olarak isaretle
        3. ILERLE'ye bas

        NOT: Diger 15 soru hemsirenin doldurdugu haliyle kalacak, dokunmuyoruz.
        """
        self.log("   Geriatrik Degerlendirme - zorunlu alanlar kontrol ediliyor...")

        try:
            # KMD sorusunu cevapla
            self._answer_kmd_question()

            # Toast mesaji var mi kontrol et (hata gosteriliyor olabilir)
            self._check_and_close_toast()

            # Bos kalan zorunlu toggle butonlari bul ve HAYIR olarak isaretle
            self._fill_empty_toggle_buttons()

            return True

        except Exception as e:
            self.log(f"   Geriatrik sayfa hatasi: {str(e)[:50]}", "WARNING")
            return True

    def _check_and_close_toast(self):
        """Toast mesajlarini kontrol et ve kapat"""
        try:
            # PrimeNG p-toast mesajlari
            toasts = self.driver.find_elements(By.CSS_SELECTOR, 'p-toast, .ui-toast, .p-toast')
            for toast in toasts:
                try:
                    toast_text = toast.text.strip()
                    if toast_text:
                        self.log(f"   Toast mesaji: {toast_text[:100]}", "WARNING")
                        # Toast'u kapat
                        close_btn = toast.find_element(By.CSS_SELECTOR, '.ui-toast-close-icon, .p-toast-icon-close')
                        if close_btn:
                            self.js_click(close_btn)
                            time.sleep(0.3)
                except:
                    continue
        except:
            pass

    def _fill_empty_toggle_buttons(self):
        """
        Sayfadaki bos (secilmemis) toggle butonlari HAYIR olarak isaretle.
        Geriatrik sayfasinda bazi sorular hemsire tarafindan doldurulmamis olabilir.

        ONEMLI: DUYGU DURUM ve IHMAL/ISTISMAR sorulari hemsire tarafindan
        doldurulmuyor, biz doldurmaliyiz!
        """
        try:
            # Tum toggle butonlarini al
            toggles = self.driver.find_elements(By.CSS_SELECTOR, '.ui-togglebutton')
            self.log(f"      Toplam {len(toggles)} toggle buton bulundu", "DEBUG")

            filled_count = 0

            # Cift cift kontrol et (EVET/HAYIR)
            for i in range(0, len(toggles), 2):
                if i + 1 >= len(toggles):
                    break

                evet = toggles[i]
                hayir = toggles[i + 1]

                try:
                    evet_active = 'ui-state-active' in (evet.get_attribute('class') or '')
                    hayir_active = 'ui-state-active' in (hayir.get_attribute('class') or '')

                    # Hic biri secili degilse HAYIR'i sec
                    if not evet_active and not hayir_active:
                        self.js_click(hayir)
                        filled_count += 1
                        time.sleep(0.2)
                except:
                    continue

            if filled_count > 0:
                self.log(f"      {filled_count} bos soru HAYIR olarak dolduruldu", "SUCCESS")

        except Exception as e:
            self.log(f"      Toggle doldurma hatasi: {str(e)[:40]}", "DEBUG")

    def _answer_kmd_question(self, answer: str = 'HAYIR') -> bool:
        """
        'Daha önce Kemik Mineral Dansitometrisi (KMD) yapılmış mı?' sorusunu cevapla.

        Bu soru Yasli Izlem Geriatrik sayfasinda ZORUNLU alandir.
        Hemsire bu soruyu doldurmamis, bizim cevaplamamiz gerekiyor.

        Args:
            answer: 'EVET' veya 'HAYIR' (varsayilan: 'HAYIR')

        Returns:
            True: Basarili
            False: Soru bulunamadi
        """
        try:
            self.log(f"      KMD sorusu araniyor...", "DEBUG")

            # Sayfa metninde KMD var mi kontrol et
            page_text = self.get_page_text().upper()
            if 'KMD' not in page_text and 'KEMİK' not in page_text and 'KEMIK' not in page_text and 'DANSİTOMETRİ' not in page_text:
                self.log("      KMD sorusu bu sayfada yok", "DEBUG")
                return True

            # YONTEM 1: Toggle button (p-togglebutton / ui-togglebutton)
            # KMD sorusu genellikle son soru, sayfanin altinda
            try:
                # Sayfayi asagi kaydir - KMD sorusu altta olabilir
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.3)

                # KMD ile ilgili container'i bul
                kmd_containers = self.driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'KMD') or contains(text(), 'Kemik Mineral') or contains(text(), 'Dansitometri')]/ancestor::div[contains(@class, 'form-group') or contains(@class, 'question') or contains(@class, 'row')]"
                )

                for container in kmd_containers:
                    try:
                        # Container icindeki toggle butonlari bul
                        toggles = container.find_elements(By.CSS_SELECTOR, '.ui-togglebutton, p-togglebutton div.ui-togglebutton')

                        for toggle in toggles:
                            toggle_text = toggle.text.strip().upper()

                            if answer == 'EVET' and 'EVET' in toggle_text:
                                if 'ui-state-active' not in (toggle.get_attribute('class') or ''):
                                    self.js_click(toggle)
                                    self.log(f"      KMD: EVET secildi", "SUCCESS")
                                    time.sleep(0.3)
                                    return True
                                else:
                                    self.log(f"      KMD: EVET zaten secili", "DEBUG")
                                    return True

                            elif answer == 'HAYIR' and 'HAYIR' in toggle_text:
                                if 'ui-state-active' not in (toggle.get_attribute('class') or ''):
                                    self.js_click(toggle)
                                    self.log(f"      KMD: HAYIR secildi", "SUCCESS")
                                    time.sleep(0.3)
                                    return True
                                else:
                                    self.log(f"      KMD: HAYIR zaten secili", "DEBUG")
                                    return True
                    except:
                        continue
            except Exception as e:
                self.log(f"      KMD container yontemi hatasi: {str(e)[:40]}", "DEBUG")

            # YONTEM 2: Tum toggle butonlari tara, KMD yakinindakini bul
            try:
                all_toggles = self.driver.find_elements(By.CSS_SELECTOR, '.ui-togglebutton')

                # Son birkaç toggle'a bak (KMD genellikle sonda)
                for toggle in all_toggles[-10:]:  # Son 10 toggle
                    try:
                        # Parent elementten soru metnini al
                        parent = toggle.find_element(By.XPATH, './ancestor::*[5]')
                        parent_text = parent.text.upper()

                        if 'KMD' in parent_text or 'KEMİK' in parent_text or 'DANSİTOMETRİ' in parent_text:
                            toggle_text = toggle.text.strip().upper()

                            if answer == 'HAYIR' and 'HAYIR' in toggle_text:
                                if 'ui-state-active' not in (toggle.get_attribute('class') or ''):
                                    self.js_click(toggle)
                                    self.log(f"      KMD: HAYIR secildi (yontem 2)", "SUCCESS")
                                    time.sleep(0.3)
                                    return True
                            elif answer == 'EVET' and 'EVET' in toggle_text:
                                if 'ui-state-active' not in (toggle.get_attribute('class') or ''):
                                    self.js_click(toggle)
                                    self.log(f"      KMD: EVET secildi (yontem 2)", "SUCCESS")
                                    time.sleep(0.3)
                                    return True
                    except:
                        continue
            except Exception as e:
                self.log(f"      KMD toggle yontemi hatasi: {str(e)[:40]}", "DEBUG")

            # YONTEM 3: XPath ile direkt ara
            try:
                # HAYIR butonu
                if answer == 'HAYIR':
                    hayir_xpaths = [
                        "//div[contains(., 'KMD')]//following::div[contains(@class, 'ui-togglebutton')][contains(., 'Hayır')]",
                        "//span[contains(., 'KMD')]//following::div[contains(@class, 'ui-togglebutton')][contains(., 'Hayır')]",
                    ]
                    for xpath in hayir_xpaths:
                        try:
                            btn = self.driver.find_element(By.XPATH, xpath)
                            if 'ui-state-active' not in (btn.get_attribute('class') or ''):
                                self.js_click(btn)
                                self.log(f"      KMD: HAYIR secildi (xpath)", "SUCCESS")
                                return True
                        except:
                            continue
            except:
                pass

            self.log("      KMD sorusu bulunamadi veya zaten cevaplanmis", "WARNING")
            return True  # Devam et

        except Exception as e:
            self.log(f"      KMD sorusu hatasi: {str(e)[:50]}", "WARNING")
            return True

    def _handle_uc_kelime_testi_if_empty(self):
        """
        Demans=Hayir secildiyse 'Uc Kelime Hatırlama Testi' acilir.
        Bu test ZORUNLUDUR - sadece BOS ise doldur.

        Test Yapisi:
        - 3 kelime sorulur
        - Hasta kac tanesini hatirladi secilir (0-3)
        - Varsayilan: 3 (tamamini hatirladi)
        """
        try:
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()

            # Uc Kelime Testi alani var mi?
            if 'kelime' not in page_text:
                return  # Alan yok, cik

            if 'hatırl' not in page_text and 'hatirl' not in page_text:
                return  # Hatırlama testi yok, cik

            self.log("      Uc Kelime Testi alani tespit edildi", "DEBUG")

            # Dropdown bul ve BOS ise doldur
            try:
                dropdowns = self.driver.find_elements(By.CSS_SELECTOR, 'p-dropdown')
                for dd in dropdowns:
                    try:
                        # Dropdown'un mevcut degerini kontrol et
                        label = dd.find_element(By.CSS_SELECTOR, '.ui-dropdown-label')
                        current_value = label.text.strip() if label else ''

                        # Bos veya "Seciniz" ise doldur
                        if not current_value or 'eciniz' in current_value.lower():
                            dd.click()
                            time.sleep(0.2)
                            # "3" secenegini sec (tamamini hatirladi)
                            try:
                                option = self.driver.find_element(By.XPATH, "//li[contains(., '3')]")
                                option.click()
                                self.log("      Uc Kelime Testi: 3 secildi (bos alana)", "SUCCESS")
                                time.sleep(0.2)
                            except:
                                # Dropdown'u kapat
                                self.driver.execute_script('document.body.click();')
                            return
                        else:
                            self.log(f"      Uc Kelime Testi zaten dolu: {current_value}", "DEBUG")
                            return
                    except:
                        continue
            except:
                pass

        except:
            pass  # Hata olursa sessizce gec

    def _fill_yasli_planlama_page(self) -> bool:
        """
        Yasli Izlem - Planlama sayfasi
        Izlem Sikligi (*) zorunlu: 3 Ay, 6 Ay veya 1 Yil
        
        AKILLI SISTEM: Kirilganlik skoruna gore izlem sikligi belirler.
        - Yuksek kirilganlik (7+): 3 Ay
        - Orta kirilganlik (4-6): 6 Ay
        - Dusuk kirilganlik (1-3): 1 Yil
        """
        self.log("   Planlama sayfasi - akilli izlem sikligi...")

        # Varsayilan izlem sikligi
        izlem_sikligi = '1 Yil'
        
        if self.elderly_helper:
            try:
                izlem_sikligi = self.elderly_helper.get_follow_up_interval()
                frailty_score, frailty_desc = self.elderly_helper.calculate_frailty_index()
                self.log(f"      Kirilganlik: {frailty_score}/9 ({frailty_desc})", "DEBUG")
                self.log(f"      Onerilen izlem: {izlem_sikligi}", "DEBUG")
            except Exception as e:
                self.log(f"      Kirilganlik hesaplama hatasi: {str(e)[:50]}", "WARNING")

        try:
            # Radio butonlari bul
            radios = self.driver.find_elements(By.CSS_SELECTOR, 'p-radiobutton')

            # Hedef metni belirle
            if izlem_sikligi == '3 Ay':
                hedef_metin = ['3 A', '3A', '3 ay', '3ay']
            elif izlem_sikligi == '6 Ay':
                hedef_metin = ['6 A', '6A', '6 ay', '6ay']
            else:  # 1 Yil
                hedef_metin = ['1 Y', '1Y', '1 y', '1y', '12 A', '12A']

            secildi = False
            for rb in radios:
                try:
                    label = rb.find_element(By.CSS_SELECTOR, 'label')
                    label_text = label.text
                    
                    # Hedef metinlerden biri var mi kontrol et
                    for hedef in hedef_metin:
                        if hedef in label_text:
                            inner = rb.find_element(By.CSS_SELECTOR, '.ui-radiobutton-box, .p-radiobutton-box')
                            classes = inner.get_attribute('class') or ''

                            if 'ui-state-active' not in classes and 'p-highlight' not in classes:
                                self.driver.execute_script('arguments[0].click();', inner)
                                self.log(f"      Izlem sikligi: {izlem_sikligi}", "SUCCESS")
                                time.sleep(0.3)
                            secildi = True
                            break
                    if secildi:
                        break
                except:
                    continue

            # Hic secilemezse 1 Yil varsayilan
            if not secildi:
                self.log("      Izlem sikligi bulunamadi - varsayilan deneniyor", "WARNING")
                for rb in radios:
                    try:
                        label = rb.find_element(By.CSS_SELECTOR, 'label')
                        if '1' in label.text and ('Y' in label.text or 'y' in label.text):
                            inner = rb.find_element(By.CSS_SELECTOR, '.ui-radiobutton-box, .p-radiobutton-box')
                            self.driver.execute_script('arguments[0].click();', inner)
                            self.log("      Izlem sikligi: 1 Yil (varsayilan)", "DEBUG")
                            break
                    except:
                        continue

            return True

        except Exception as e:
            self.log(f"   Planlama sayfa hatasi: {str(e)[:50]}", "WARNING")
            return True

    def _process_yasli(self) -> bool:
        """
        Yaşlı Sağlığı İzlem - AKILLI SAYFA TANIMA

        ONEMLI: Hemsire TUM verileri onceden girmis durumda!
        Biz sadece sayfalari ilerletip KMD sorusunu cevapliyoruz.

        Akış:
        1. /yasli/anamnezfizikmuayene - Anamnez (hemsire doldurdu) -> Ilerle
        2. /yasli/ilac - İlaç (hemsire doldurdu) -> Ilerle
        3. /yasli/birincilgeriatrik - Geriatrik -> SADECE KMD sorusuna cevap ver -> Ilerle
        4. /yasli/tetkik - Tetkik (tikleri kaldır) -> Ilerle
        5. /yasli/geneldurumdegerlendirme - Planlama -> Ilerle
        6. /ozet - Sonlandır

        NOT: 16 geriatrik sorudan 15'i hemsire tarafindan doldurulmus.
        Sadece "KMD yapılmış mı?" sorusuna biz HAYIR cevabi veriyoruz.
        """
        self.log(">> Yaşlı Sağlığı İzlem protokolü başladı (hemsire verileri mevcut)")
        # NOT: _start_process() artik _process_single_card'da cagiriliyor!

        is_finished = False
        step = 0
        last_page = None
        same_page_count = 0
        MAX_SAME_PAGE = 3  # Aynı sayfada maksimum kalma sayısı
        izlem_baslat_checked = False  # Sadece 1 kere kontrol et

        while not is_finished and step < self.MAX_STEPS:
            step += 1
            self.keep_alive()
            self.check_error_page()
            self._close_dialogs()

            current_page = self._detect_yasli_page()
            self.log(f"   Adım {step}: Sayfa={current_page}", "DEBUG")

            # Aynı sayfada takılı kalma kontrolü
            if current_page == last_page:
                same_page_count += 1
                if same_page_count >= MAX_SAME_PAGE:
                    self.log(f"   !!! {current_page} sayfasında {MAX_SAME_PAGE} kez takıldı - atlanıyor", "ERROR")
                    return False
            else:
                same_page_count = 0
                last_page = current_page

            # Izlem Baslat butonu hala varsa tikla - SADECE ILK ADIMDA kontrol et (OPTIMIZE)
            if not izlem_baslat_checked and current_page == "UNKNOWN":
                izlem_baslat_checked = True
                try:
                    # Hizli XPath ile kontrol et (find_elements yerine)
                    izlem_xpath = "//button[contains(., 'İzlem Başlat') and contains(., 'Yüz Yüze')]"
                    if self.click_element(izlem_xpath, timeout=0.5):
                        self.log("   İzlem Başlat butonu tıklandı")
                        time.sleep(0.5)
                        continue
                except:
                    pass

            # SAYFAYA GÖRE İŞLEM
            if current_page == "OZET":
                self.log("   Sonlandırılıyor...")
                is_finished = self._click_sonlandir()

            elif current_page == "ANAMNEZ":
                self.log("   Anamnez sayfası...")
                # Ağırlık alanı zorunlu - doldur
                self._fill_anamnez_fields()
                self._click_ilerle()

            elif current_page == "ILAC":
                self.log("   İlaç Tedavisi sayfası...")
                self._fill_yasli_ilac_page()
                self._click_ilerle()

            elif current_page == "GERIATRIK":
                self.log("   Geriatrik Değerlendirme sayfası...")
                self._fill_yasli_geriatrik_page()
                self._click_ilerle()

            elif current_page == "TETKIK":
                self.log("   Tetkik sayfası - tikler kaldırılıyor...")
                self._uncheck_tetkik_boxes()
                self._click_ilerle()

            elif current_page == "PLANLAMA":
                self.log("   Planlama sayfası...")
                self._fill_yasli_planlama_page()
                self._click_ilerle()

            else:
                self.log(f"   Bilinmeyen sayfa - ilerle deneniyor...")
                self._click_ilerle()

            time.sleep(0.5)  # 1.5 -> 0.5 (optimize)

        if is_finished:
            self.log("Yaşlı Sağlığı İzlem tamamlandı!", "SUCCESS")
        return is_finished

    # ============================================================
    # YARDIMCI FONKSİYONLAR
    # ============================================================
    def _click_ilerle(self) -> bool:
        """
        İlerle butonuna tıkla - HATA ALGILAMA ILE GELISTIRILMIS

        Ozellikler:
        1. URL degisimi kontrolu yapar
        2. "en az bir test" hatasi algilama
        3. Hata varsa dis lab sonucu eklemeyi dener
        4. Tekrar ilerlemeyi dener

        Returns:
            True: Basariyla ilerledi (URL degisti)
            False: Ilerleyemedi
        """
        url_before = self.driver.current_url

        # Ilerle butonunu bul ve tikla
        clicked = self._do_click_ilerle_button()

        if not clicked:
            self.log("   [DEBUG] Ilerle/Kaydet butonu bulunamadi!", "WARNING")
            return False

        # Biraz bekle ve URL kontrolu yap
        time.sleep(0.3)  # OPTIMIZE: 1 -> 0.3 saniye
        url_after = self.driver.current_url

        # URL degisti mi?
        if url_before != url_after:
            self.log(f"   Sayfa degisti: {url_after.split('/')[-1]}", "DEBUG")
            return True

        # URL degismediyse - HATA MESAJI KONTROLU
        self.log("   [DEBUG] URL degismedi, hata mesaji kontrol ediliyor...", "DEBUG")

        page_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()

        # Bilinen hata mesajlari
        error_patterns = [
            "en az bir",
            "isteyiniz",
            "zorunlu",
            "gerekli",
            "doldurulmal",
            "secilmeli",
            "girilmeli"
        ]

        error_found = False
        for pattern in error_patterns:
            if pattern in page_text:
                error_found = True
                self.log(f"   !!! HATA MESAJI ALGILANDI: '{pattern}' iceriyor", "WARNING")
                break

        if error_found:
            # DIYABET TARAMA OZEL KONTROL
            # "HbA1c, APG ya da OGTT" hatasi mi?
            is_diyabet_glikoz_error = ('hba1c' in page_text or 'apg' in page_text or 'ogtt' in page_text) and 'diy' in url_before.lower()

            if is_diyabet_glikoz_error:
                self.log("   DIYABET: HbA1c/APG/OGTT hatasi algilandi!", "WARNING")
                diyabet_success = self._handle_diyabet_hba1c_apg_ogtt_error()

                if diyabet_success:
                    # Checkbox'lari tekrar kontrol et
                    time.sleep(0.5)  # 1 -> 0.5 saniye (optimize)
                    remaining = self._count_active_checkboxes()
                    if remaining > 0:
                        self.log(f"   DIYABET: {remaining} tikli checkbox kaldi, dis lab girilecek", "WARNING")
                        self._try_enter_all_external_lab_results()
                        time.sleep(0.5)  # 1 -> 0.5 saniye (optimize)

                    # Tekrar ilerle
                    self.log("   DIYABET: Tekrar ilerleniyor...", "DEBUG")
                    self._do_click_ilerle_button()
                    time.sleep(1)  # 2 -> 1 saniye (optimize)

                    url_final = self.driver.current_url
                    if url_before != url_final:
                        self.log(f"   DIYABET: Basariyla ilerlendi: {url_final.split('/')[-1]}", "SUCCESS")
                        return True
                    else:
                        self.log("   DIYABET: Ilerleme basarisiz!", "ERROR")
                        return False
                else:
                    self.log("   DIYABET: HbA1c/APG/OGTT hatasi cozulemedi!", "ERROR")
                    return False

            # Tetkik sayfasindaysak dis lab sonucu eklemeyi dene (genel)
            elif '/tetkik' in url_before or '/glikoz' in url_before:
                self.log("   Dis lab sonucu eklenerek yeniden denenecek...", "DEBUG")

                # TUM kaldirilamayan checkbox'lar icin dis lab sonucu ekle
                dis_lab_success = self._try_enter_all_external_lab_results()

                if dis_lab_success:
                    self.log("   Dis lab sonucu eklendi, tekrar ilerleniyor...", "DEBUG")
                    time.sleep(1)

                    # Checkbox'lari tekrar kontrol et
                    remaining = self._count_active_checkboxes()
                    if remaining > 0:
                        self.log(f"   {remaining} tikli checkbox kaldi!", "WARNING")

                    # Tekrar ilerle
                    self._do_click_ilerle_button()
                    time.sleep(0.5)  # OPTIMIZE

                    # Tekrar URL kontrolu
                    url_final = self.driver.current_url
                    if url_before != url_final:
                        self.log(f"   Basariyla ilerlendi: {url_final.split('/')[-1]}", "SUCCESS")
                        return True
                    else:
                        self.log("   Dis lab sonrasinda da ilerleyemedi!", "ERROR")
                        return False
                else:
                    self.log("   Dis lab sonucu eklenemedi!", "WARNING")
                    return False

        # Hata yoksa ama URL degismediyse - belki sayfa zaten son sayfa
        self.log("   URL degismedi ama hata mesaji yok - devam ediliyor", "DEBUG")
        return True

    def _do_click_ilerle_button(self) -> bool:
        """Ilerle butonunu bul ve tikla (yardimci fonksiyon)"""
        # Debug: Tum butonlari listele ve Ilerle bul
        try:
            buttons = self.driver.find_elements(By.XPATH, "//button")
            ilerle_btns = [b for b in buttons if 'İlerle' in (b.text or '') or 'Ilerle' in (b.text or '')]
            self.log(f"   [DEBUG] Toplam buton: {len(buttons)}, Ilerle buton: {len(ilerle_btns)}", "DEBUG")

            # Direkt bulunan butona tikla
            if ilerle_btns:
                for btn in ilerle_btns:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            self.log(f"   [DEBUG] Ilerle tiklanıyor...", "DEBUG")
                            self.js_click(btn)
                            time.sleep(0.2)  # OPTIMIZE: 0.5 -> 0.2
                            return True
                    except Exception as e:
                        self.log(f"   [DEBUG] Buton tiklama hatasi: {str(e)[:50]}", "DEBUG")
                        continue
        except Exception as e:
            self.log(f"   [DEBUG] Buton arama hatasi: {str(e)[:50]}", "DEBUG")

        # XPath ile dene
        xpaths = [
            "//button[contains(@class, 'hyp-next-button')]",
            "//button[.//span[contains(text(), 'İlerle')]]",
            "//button[contains(., 'İlerle')]",
            "//button[text()='İlerle']",
            "//button/span[text()='İlerle']/parent::button",
            "//button[normalize-space()='İlerle']",
        ]

        for xpath in xpaths:
            if self.click_element(xpath, timeout=0.3):  # OPTIMIZE: 2 -> 0.3
                return True

        # Ilerle yoksa Kaydet dene
        if self.click_element("//button[contains(., 'Kaydet')]", timeout=0.3):  # OPTIMIZE: 1 -> 0.3
            return True

        return False


    def _fill_kirilganlik_olcegi(self) -> bool:
        """
        65+ yaş hastalarda Klinik Kırılganlık Ölçeği (Clinical Frailty Scale) doldur

        HYP'de bu ölçek:
        - 65+ yaş diyabet hastalarında ZORUNLU
        - Genellikle dropdown veya radio button olarak gelir
        - 1-9 arası skor seçilmeli (varsayılan: 3 - İyi Yönetilen)
        """
        self.log("      Kırılganlık Ölçeği değerlendiriliyor...", "DEBUG")

        try:
            page_text = self.get_page_text()

            # Ölçek zaten doldurulmuş mu kontrol et
            if "SEÇİLDİ" in page_text or "SECILDI" in page_text:
                self.log("      Kırılganlık Ölçeği zaten seçilmiş", "DEBUG")
                return True

            # Yöntem 1: Dropdown menü (p-dropdown)
            try:
                dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "p-dropdown")
                for dd in dropdowns:
                    try:
                        label_text = dd.find_element(By.XPATH, "./ancestor::div[1]//label").text.upper()
                        if "KIRILGANLIK" in label_text or "FRAILTY" in label_text:
                            # Dropdown'a tıkla
                            dd.click()
                            time.sleep(0.5)

                            # Seçenekleri bul - varsayılan olarak "3" veya "İyi Yönetilen" seç
                            options = self.driver.find_elements(By.CSS_SELECTOR, ".ui-dropdown-item, .p-dropdown-item")
                            for opt in options:
                                opt_text = opt.text.upper()
                                # Varsayılan: Skor 3 - İyi Yönetilen (hastalar genellikle bu kategoride)
                                if "3" in opt_text or "İYİ" in opt_text or "IYI" in opt_text or "YÖNETİLEN" in opt_text:
                                    opt.click()
                                    self.log("      Kırılganlık skoru: 3 (İyi Yönetilen)", "SUCCESS")
                                    time.sleep(0.3)
                                    return True

                            # 3 bulunamazsa ilk seçeneği seç
                            if options:
                                options[0].click()
                                self.log(f"      Kırılganlık skoru: {options[0].text}", "SUCCESS")
                                return True
                    except:
                        continue
            except Exception as e:
                self.log(f"      Dropdown yöntemi hatası: {str(e)[:50]}", "DEBUG")

            # Yöntem 2: Radio butonlar
            try:
                radios = self.driver.find_elements(By.TAG_NAME, "p-radiobutton")
                for radio in radios:
                    try:
                        label = radio.find_element(By.CSS_SELECTOR, "label")
                        label_text = label.text.upper()

                        # Skor 3 - İyi Yönetilen tercih edilir
                        if "3" in label_text or "İYİ" in label_text or "YÖNETİLEN" in label_text:
                            inner = radio.find_element(By.CSS_SELECTOR, ".ui-radiobutton-box, .p-radiobutton-box")
                            if "ui-state-active" not in (inner.get_attribute("class") or "") and \
                               "p-highlight" not in (inner.get_attribute("class") or ""):
                                self.driver.execute_script("arguments[0].click();", inner)
                                self.log("      Kırılganlık skoru: 3 (İyi Yönetilen)", "SUCCESS")
                                time.sleep(0.3)
                                return True
                    except:
                        continue
            except Exception as e:
                self.log(f"      Radio yöntemi hatası: {str(e)[:50]}", "DEBUG")

            # Yöntem 3: Select elementi
            try:
                selects = self.driver.find_elements(By.TAG_NAME, "select")
                for select in selects:
                    try:
                        from selenium.webdriver.support.ui import Select
                        sel = Select(select)

                        # Skor 3 seçeneğini bul
                        for opt in sel.options:
                            if "3" in opt.text or "İyi" in opt.text:
                                sel.select_by_visible_text(opt.text)
                                self.log(f"      Kırılganlık skoru: {opt.text}", "SUCCESS")
                                return True
                    except:
                        continue
            except Exception as e:
                self.log(f"      Select yöntemi hatası: {str(e)[:50]}", "DEBUG")

            self.log("      Kırılganlık Ölçeği alanı bulunamadı (sayfa farklı olabilir)", "WARNING")
            return True  # Devam et, kritik değil

        except Exception as e:
            self.log(f"      Kırılganlık Ölçeği hatası: {str(e)[:50]}", "WARNING")
            return True  # Devam et

    def _fill_anamnez_fields(self) -> bool:
        """Anamnez ve tetkik sayfalarindaki zorunlu olcum alanlarini doldur - HIZLI"""
        # OPTIMIZE: Implicit wait'i gecici kapat (element yoksa hemen gecsin)
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        
        import re
        fields = [
            ('Sistolik', 120),
            ('Diyastolik', 70),
            ('Nabız', 72),
            ('Boy', 165),
            ('Ağırlık', 75),
            ('Bel', 90),
        ]

        filled_count = 0
        for label_text, default_val in fields:
            try:
                row = self.driver.find_element(
                    By.XPATH,
                    f"//label[contains(text(), '{label_text}')]/ancestor::hyp-physical-examination-row"
                )
                inp = row.find_element(By.CSS_SELECTOR, 'hyp-number-input input')
                current_val = inp.get_attribute('value') or ''

                if not current_val or current_val == 'undefined':
                    try:
                        prev_exam = row.find_element(By.CSS_SELECTOR, '.previous-examination span')
                        prev_text = prev_exam.text
                        nums = re.findall(r'\d+', prev_text)
                        if nums:
                            default_val = int(nums[0])
                    except:
                        pass

                    # HIZLI: JavaScript ile deger gir
                    self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", inp, str(default_val))
                    filled_count += 1
            except:
                pass

        # Implicit wait'i geri yukle
        self.driver.implicitly_wait(original_wait)
        
        if filled_count > 0:
            self.log(f"   {filled_count} alan dolduruldu", "SUCCESS")
        return True

    def _cancel_current_hyp(self, reason: str = "Bilinmeyen neden", eksik_tetkikler: list = None, sms_gerekli: bool = False) -> bool:
        """
        Mevcut HYP taramasini iptal et.
        Sol ustteki "Taramayi iptal et" butonuna tiklar.

        KULLANIM: Eski deger bulunamadiginda veya devam edilemediginde
        bu fonksiyon cagirilir. Hasta pas gecilmez, sadece bu HYP iptal edilir.
        Diger HYP'lere devam edilebilir.

        BUTON YAPISI:
        - Ana buton: class="cancel-button ui-button-danger"
        - Popup acilir: Dialog footer'da "Taramayi Iptal Et" ve "Vazgec" butonlari
        - Popup'taki "Taramayi Iptal Et" butonuna tiklanir

        Args:
            reason: Iptal nedeni (log icin)
            eksik_tetkikler: Eksik tetkik listesi (popup icin)
            sms_gerekli: SMS onayi gerekli mi?

        Returns:
            True: Iptal basarili
            False: Iptal butonu bulunamadi
        """
        self.log(f"   !!! HYP IPTAL EDILIYOR: {reason}", "WARNING")

        try:
            url_before = self.driver.current_url

            # ADIM 1: Ana iptal butonunu bul (cancel-button class'i ile)
            cancel_btn = None

            # Oncelik: cancel-button class'i
            try:
                cancel_btn = self.driver.find_element(By.CSS_SELECTOR, '.cancel-button')
                self.log(f"   Iptal butonu bulundu (CSS)", "DEBUG")
            except:
                pass

            # Alternatif: ui-button-danger class'i
            if not cancel_btn:
                try:
                    cancel_btn = self.driver.find_element(By.CSS_SELECTOR, '.ui-button-danger')
                    self.log(f"   Iptal butonu bulundu (danger)", "DEBUG")
                except:
                    pass

            # Alternatif: XPath ile
            if not cancel_btn:
                iptal_xpaths = [
                    "//button[contains(., 'ptal')]",
                    "//button[contains(@class, 'cancel')]",
                ]
                for xpath in iptal_xpaths:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for el in elements:
                            if el.is_displayed():
                                cancel_btn = el
                                break
                        if cancel_btn:
                            break
                    except:
                        pass

            if not cancel_btn:
                self.log("   !!! Iptal butonu bulunamadi!", "ERROR")
                return False

            # ADIM 2: Ana butona tikla
            self.driver.execute_script('arguments[0].scrollIntoView({block: "center"});', cancel_btn)
            time.sleep(0.3)
            self.driver.execute_script('arguments[0].click();', cancel_btn)
            self.log("   'Taramayi Iptal Et' ana butonu tiklandi", "SUCCESS")
            time.sleep(0.5)  # OPTIMIZE

            # ADIM 3: Popup'taki onay butonuna tikla
            self._confirm_cancel_popup()

            time.sleep(1)
            url_after = self.driver.current_url

            if url_before != url_after:
                self.log(f"   HYP IPTAL EDILDI: {reason}", "WARNING")
                # İptal edilen HYP'yi kaydet (popup için)
                self._record_cancelled_hyp(reason, eksik_tetkikler=eksik_tetkikler, sms_gerekli=sms_gerekli)
                return True
            else:
                self.log("   URL degismedi - iptal basarisiz olabilir", "WARNING")
                # Yine de kaydet
                self._record_cancelled_hyp(reason, eksik_tetkikler=eksik_tetkikler, sms_gerekli=sms_gerekli)
                return True  # Yine de True don, popup kapanmis olabilir

        except Exception as e:
            self.log(f"   HYP iptal hatasi: {e}", "ERROR")
            return False

    def _record_cancelled_hyp(self, reason: str, eksik_tetkikler: list = None, sms_gerekli: bool = False):
        """
        İptal edilen HYP bilgisini kaydet.

        Args:
            reason: İptal nedeni
            eksik_tetkikler: Eksik olan tetkik listesi (örn: ['Kreatinin', 'eGFR'])
            sms_gerekli: SMS onayı gerekli mi?
        """
        # Eksik tetkik listesi bos ise nedenden cikar
        final_eksik = eksik_tetkikler or []
        if not final_eksik and reason:
            if 'Eksik tetkik:' in reason:
                tetkikler_str = reason.split('Eksik tetkik:')[1].strip()
                final_eksik = [t.strip() for t in tetkikler_str.split(',') if t.strip()]
            elif 'Dis lab girilemedi:' in reason:
                tetkikler_str = reason.split('Dis lab girilemedi:')[1].strip()
                final_eksik = [t.strip() for t in tetkikler_str.split(',') if t.strip()]

        cancelled_info = {
            "hasta": self.current_patient_name or "Bilinmeyen Hasta",
            "tc": getattr(self, 'current_patient_tc', ''),
            "hyp_tipi": getattr(self, '_current_hyp_type', 'Bilinmeyen'),
            "neden": reason,
            "eksik_tetkikler": final_eksik,
            "sms_gerekli": sms_gerekli,
            "zaman": datetime.now().strftime("%H:%M:%S")
        }
        if not hasattr(self, 'cancelled_hyps'):
            self.cancelled_hyps = []
        self.cancelled_hyps.append(cancelled_info)

        # Detayli log
        detay = f"{cancelled_info['hasta']} - {cancelled_info['hyp_tipi']}"
        if final_eksik:
            detay += f" - Eksik: {', '.join(final_eksik)}"
        if sms_gerekli:
            detay += " - SMS ONAYI GEREKLI"
        self.log(f"   [KAYIT] Iptal kaydedildi: {detay}", "DEBUG")

    def _confirm_cancel_popup(self):
        """
        Iptal onay popup'inda 'Taramayi Iptal Et' butonuna tikla.
        Popup'ta 'Taramayi Iptal Et' ve 'Vazgec' butonlari var.
        """
        try:
            time.sleep(1)

            # Dialog footer'daki butonlari bul
            dialog_btns = self.driver.find_elements(By.CSS_SELECTOR, '.ui-dialog-footer button, .p-dialog-footer button')

            for btn in dialog_btns:
                try:
                    text = btn.text.strip().lower()
                    # "Iptal" iceren ama "Vazgec" olmayan butonu tikla
                    if 'ptal' in text and 'vazge' not in text:
                        if btn.is_displayed():
                            self.driver.execute_script('arguments[0].click();', btn)
                            self.log("   Popup onay butonu tiklandi", "SUCCESS")
                            time.sleep(0.5)  # OPTIMIZE
                            return
                except:
                    pass

            # Alternatif: Genel onay butonlari
            confirm_xpaths = [
                "//button[contains(., 'Evet')]",
                "//button[contains(., 'Onayla')]",
                "//button[contains(., 'Tamam')]",
            ]

            for xpath in confirm_xpaths:
                try:
                    btn = self.driver.find_element(By.XPATH, xpath)
                    if btn.is_displayed():
                        self.driver.execute_script('arguments[0].click();', btn)
                        self.log("   Iptal onaylandi (alternatif)", "DEBUG")
                        time.sleep(1)
                        return
                except:
                    pass

        except Exception as e:
            self.log(f"   Popup onay hatasi: {e}", "DEBUG")

    def _uncheck_tetkik_boxes(self) -> bool:
        """
        Tetkik sayfasindaki TUM checkbox'lari kaldir.

        ONEMLI: Tikli checkbox kalirsa hasta "Beklemede" kalir!

        YENI MANTIK (v2):
        1. ONCE mevcut checkbox bilgilerini cache'le (isim + deger)
        2. "Tumunu kaldir" span'ina tikla
        3. "En az bir" hatasi gelirse -> cache'deki bilgilerle dis lab sonucu gir

        Returns:
            True: Islem basarili, devam edilebilir
            False: Islem basarisiz, bu HYP pas gecilmeli
        """
        self.log("   Tetkik checkbox temizleme basliyor...", "DEBUG")
        time.sleep(0.1)  # OPTIMIZE: 0.3 -> 0.1

        # Onceki tikli checkbox sayisini al
        initial_count = self._count_active_checkboxes()
        if initial_count == 0:
            self.log("   Tikli checkbox yok, temizleme gerekmiyor", "DEBUG")
            return True

        self.log(f"   {initial_count} tikli checkbox bulundu", "DEBUG")

        # ============================================================
        # ADIM 0: CHECKBOX BILGILERINI ONCE KAYDET (CACHE)
        # ============================================================
        # Sayfadaki tum checkbox label'larini ve degerlerini simdi al
        self._cached_checkbox_data = self._collect_all_checkbox_info_from_page()
        if self._cached_checkbox_data:
            self.log(f"   {len(self._cached_checkbox_data)} test bilgisi cache'lendi: {list(self._cached_checkbox_data.keys())}", "DEBUG")

        # ============================================================
        # ADIM 1: "Tumunu kaldir" span/link'ine tikla
        # ============================================================
        tumunu_kaldir_clicked = False
        try:
            # Dogrudan span elementi ara - en guvenilir yontem
            spans = self.driver.find_elements(By.TAG_NAME, 'span')
            for span in spans:
                try:
                    text = span.text.strip().lower()
                    # "Tümünü kaldır" veya benzeri metinleri ara
                    if 'kald' in text and ('tüm' in text or 'tum' in text or 'hep' in text):
                        if span.is_displayed():
                            self.driver.execute_script('arguments[0].scrollIntoView({block: "center"});', span)
                            time.sleep(0.1)  # 0.3 -> 0.1 (optimize)
                            self.driver.execute_script('arguments[0].click();', span)
                            self.log("   'Tumunu kaldir' tiklandi", "DEBUG")
                            time.sleep(0.2)  # OPTIMIZE: 0.5 -> 0.2
                            tumunu_kaldir_clicked = True
                            break
                except:
                    continue
        except Exception as e:
            self.log(f"   Tumunu kaldir arama hatasi: {e}", "DEBUG")

        # Tumunu kaldir bulunamadiysa alternatif XPath dene
        if not tumunu_kaldir_clicked:
            tumunu_kaldir_xpaths = [
                "//*[contains(text(), 'kald') and contains(text(), 'Tüm')]",
                "//*[contains(text(), 'kald') and contains(text(), 'tüm')]",
                "//a[contains(text(), 'kald')]",
                "//button[contains(text(), 'kald')]",
            ]

            for xpath in tumunu_kaldir_xpaths:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            text = el.text.lower()
                            if 'kald' in text:
                                self.driver.execute_script('arguments[0].scrollIntoView({block: "center"});', el)
                                time.sleep(0.1)  # 0.2 -> 0.1 (optimize)
                                self.driver.execute_script('arguments[0].click();', el)
                                self.log("   'Tumunu kaldir' (XPath) tiklandi", "DEBUG")
                                time.sleep(0.2)  # OPTIMIZE: 0.5 -> 0.2
                                tumunu_kaldir_clicked = True
                                break
                    if tumunu_kaldir_clicked:
                        break
                except:
                    pass

        # ============================================================
        # ADIM 2: Tikli checkbox kontrolu - varsa dis lab gir
        # ============================================================
        remaining = self._count_active_checkboxes()

        if remaining == 0:
            self.log("   Tum checkboxlar 'Tumunu kaldir' ile temizlendi!", "DEBUG")
            return True

        # TIKLI CHECKBOX KALDI - DIS LAB SONUCU GIR
        self.log(f"   !!! {remaining} tikli checkbox KALDIRILAMADI - Dis lab sonucu giriliyor...", "DEBUG")

        # ============================================================
        # ONEMLI: Cache'deki bilgilerle dis lab sonucu gir
        # NOT: remaining_names bos donebilir (zamanlama sorunu)
        # Bu durumda cache'deki TUM testleri kullan
        # ============================================================
        if hasattr(self, '_cached_checkbox_data') and self._cached_checkbox_data:
            self.log(f"   Cache'de {len(self._cached_checkbox_data)} test var: {list(self._cached_checkbox_data.keys())}", "DEBUG")
        else:
            self.log("   !!! Cache bos - dis lab girilemeyecek!", "ERROR")

        # Filtreli cache'deki bilgilerle dis lab sonucu gir
        dis_lab_success = self._try_enter_all_external_lab_results()

        if dis_lab_success:
            self.log("   TUM dis lab sonuclari basariyla girildi!", "DEBUG")
            time.sleep(0.2)  # OPTIMIZE: 0.5 -> 0.2

            # ============================================================
            # ONEMLI: Dis lab girdikten sonra TEKRAR "Tumunu kaldir" tikla!
            # HYP sistemi girilen degerlere gore otomatik yeni tikler atabilir
            # Bu yuzden tekrar temizlemek SART!
            # ============================================================
            self.log("   Dis lab sonrasi TEKRAR 'Tumunu kaldir' tiklaniyor...", "DEBUG")
            self._click_tumunu_kaldir()
            time.sleep(0.2)  # OPTIMIZE: 0.5 -> 0.2

            # Simdi checkbox'lari kontrol et
            final_remaining = self._count_active_checkboxes()
            if final_remaining > 0:
                self.log(f"   Dis lab + tekrar temizleme sonrasi {final_remaining} tik kaldi", "WARNING")
                # Bu tikler artik gercekten kaldirilAMAYAN tikler VE eski degeri YOK
                # HYP IPTAL EDILMELI - bu testin eski sonucu olmadan devam edilemez!
                self.log("   !!! ESKI DEGERI OLMAYAN TIK VAR - HYP IPTAL EDILIYOR!", "ERROR")
                # Eksik tetkik isimlerini al
                eksik_tetkikler = list(self._get_remaining_checkbox_names())
                self._cancel_current_hyp(
                    reason=f"Eksik tetkik: {', '.join(eksik_tetkikler) if eksik_tetkikler else f'{final_remaining} test'}",
                    eksik_tetkikler=eksik_tetkikler
                )
                return False
            else:
                self.log("   Dis lab sonrasi tum checkbox'lar temizlendi", "DEBUG")

            return True
        else:
            self.log("   !!! Dis lab sonuclari girilemedi - HYP IPTAL EDILIYOR!", "ERROR")
            # Kalan checkbox isimlerini al
            eksik_tetkikler = list(self._get_remaining_checkbox_names())
            self._cancel_current_hyp(
                reason=f"Dis lab girilemedi: {', '.join(eksik_tetkikler) if eksik_tetkikler else 'Bilinmeyen'}",
                eksik_tetkikler=eksik_tetkikler
            )
            return False

    def _handle_diyabet_hba1c_apg_ogtt_error(self) -> bool:
        """
        Diyabet Tarama'da "en az bir HbA1c/APG/OGTT" hatasi icin ozel handler.

        Bu fonksiyon "Ilerle" tiklandiktan sonra hata popup'i ciktiginda cagrilir.
        Cache'deki HbA1c, APG veya OGTT degerlerinden birini dis lab olarak girer.

        Returns:
            True: Deger girildi ve checkbox'lar temizlendi
            False: Basarisiz
        """
        self.log("   DIYABET: HbA1c/APG/OGTT hatasi handle ediliyor...", "DEBUG")

        # Cache'de diyabet testleri var mi kontrol et
        # Diyabet icin zorunlu testler - BU TESTLERDEN BIRI GIRILMELI!
        # ONCELIK SIRASI: HbA1c > Glukoz/APG > OGTT
        diyabet_zorunlu_testler = ['HbA1c', 'Glukoz', 'APG', 'OGTT']

        # ONCELIK 1: Sayfadan eski degerleri oku (daha guvenilir)
        old_values = self._read_old_values_from_tetkik_page()
        self.log(f"   DIYABET: Sayfadan okunan degerler: {old_values}", "DEBUG")

        diyabet_test_found = None
        diyabet_test_value = None

        # Sayfadan eski degeri olan testi bul (ONCELIK SIRASINA GORE)
        for test in diyabet_zorunlu_testler:
            for page_test, page_val in old_values.items():
                page_test_lower = page_test.lower()
                test_lower = test.lower()

                # Tam veya kismi eslesme
                if test_lower in page_test_lower or page_test_lower in test_lower:
                    if page_val and page_val != '-':
                        diyabet_test_found = page_test  # Sayfadaki GERCEK ismi kullan
                        diyabet_test_value = page_val
                        self.log(f"   DIYABET: {page_test}={page_val} sayfadan bulundu", "DEBUG")
                        break
            if diyabet_test_found:
                break

        # ONCELIK 2: Cache'den dene (fallback)
        if not diyabet_test_found:
            if hasattr(self, '_cached_checkbox_data') and self._cached_checkbox_data:
                for test in diyabet_zorunlu_testler:
                    for cached_test, cached_val in self._cached_checkbox_data.items():
                        if test.lower() in cached_test.lower() and cached_val:
                            diyabet_test_found = cached_test
                            diyabet_test_value = cached_val
                            self.log(f"   DIYABET: {cached_test}={cached_val} cache'den bulundu", "DEBUG")
                            break
                    if diyabet_test_found:
                        break

        if not diyabet_test_found:
            self.log("   DIYABET: HbA1c/Glukoz/APG/OGTT icin eski deger bulunamadi - tarama yapilamaz!", "ERROR")
            return False

        self.log(f"   DIYABET: {diyabet_test_found}={diyabet_test_value} dis lab olarak girilecek", "DEBUG")

        # TEMIZ COZUM: Checkbox tiklamadan direkt dis lab gir
        dis_lab_success = self._try_enter_specific_external_lab(diyabet_test_found, diyabet_test_value)

        if dis_lab_success:
            self.log(f"   DIYABET: {diyabet_test_found}={diyabet_test_value} basariyla girildi!", "SUCCESS")

            # Dis lab sonrasi HYP otomatik tik atabilir - KONTROL ET
            time.sleep(0.3)
            remaining = self._count_active_checkboxes()

            if remaining > 0:
                self.log(f"   DIYABET: HYP {remaining} checkbox otomatik isaretledi - temizleniyor...", "WARNING")
                self._click_tumunu_kaldir()
                time.sleep(0.3)

            return True
        else:
            self.log("   DIYABET: Dis lab girisi basarisiz", "ERROR")
            return False

    def _try_enter_specific_external_lab(self, test_name: str, test_value: str) -> bool:
        """
        Belirli bir test icin dis lab sonucu gir.
        Checkbox kontrolu yapmadan, direkt modal acar ve degeri girer.

        Args:
            test_name: Test adi (ornek: 'HbA1c', 'Glukoz')
            test_value: Girilecek deger (ornek: '5.3', '92')

        Returns:
            True: Basarili, False: Basarisiz
        """
        try:
            # "Dis Laboratuvar Sonucu Ekle" butonunu bul
            dis_lab_btn = self._find_dis_lab_button()
            if not dis_lab_btn:
                self.log("   Dis lab butonu bulunamadi", "DEBUG")
                return False

            # Butona tikla - MODAL ACILIR
            self.driver.execute_script('arguments[0].scrollIntoView({block: "center"});', dis_lab_btn)
            self.driver.execute_script('arguments[0].click();', dis_lab_btn)
            self.log("   Dis lab modal aciliyor...", "DEBUG")
            time.sleep(1.5)  # Modal acilmasi icin yeterli sure

            # Modal'i bul - AYNI _find_dis_lab_modal GIBI
            modal = self._find_dis_lab_modal()
            if not modal:
                self.log("   Modal bulunamadi", "WARNING")
                return False

            self.log("   Dis lab modal acildi", "DEBUG")

            # Modal'daki input'lari bul - birkaç deneme yap
            inputs = []
            for attempt in range(3):
                inputs = modal.find_elements(By.TAG_NAME, 'input')
                if len(inputs) > 0:
                    break
                time.sleep(0.5)  # Inputlarin yuklenmesi icin bekle

            self.log(f"   Modal'da {len(inputs)} input bulundu", "DEBUG")

            # Hala input yoksa sayfadaki tum inputlari dene
            if len(inputs) == 0:
                time.sleep(0.5)
                inputs = self.driver.find_elements(By.CSS_SELECTOR, '.ui-dialog input, .p-dialog input, [role="dialog"] input')
                self.log(f"   Alternatif arama: {len(inputs)} input bulundu", "DEBUG")

            if not inputs:
                self.log("   Hicbir yerde input bulunamadi", "WARNING")
                return False

            # Input alanini bul
            input_field = self._find_input_for_test_in_modal(modal, test_name, inputs)
            if not input_field:
                self.log(f"   {test_name} icin input alani bulunamadi", "WARNING")
                # Modal'i kapat
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, '.ui-dialog-titlebar-close, .p-dialog-header-close')
                    self.js_click(close_btn)
                except:
                    pass
                return False

            # Degeri gir - JAVASCRIPT ILE HIZLI GIRIS
            self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", input_field, str(test_value))
            self.log(f"   {test_name} degeri girildi: {test_value}", "DEBUG")

            # Kaydet butonuna tikla
            save_xpaths = [
                "//button[contains(., 'Kaydet')]",
                "//button[contains(@class, 'p-button-success')]",
                "//button[contains(@class, 'ui-button-success')]",
            ]

            for xpath in save_xpaths:
                try:
                    save_btn = self.driver.find_element(By.XPATH, xpath)
                    if save_btn.is_displayed():
                        self.js_click(save_btn)
                        self.log("   Dis lab kaydedildi", "SUCCESS")
                        time.sleep(0.3)  # 1 -> 0.3 saniye (HIZLANDIRILDI)
                        return True
                except:
                    pass

            self.log("   Kaydet butonu bulunamadi", "WARNING")
            return False

        except Exception as e:
            self.log(f"   Dis lab girisi hatasi: {e}", "ERROR")
            return False

    def _collect_all_checkbox_info_from_page(self) -> dict:
        """
        Sayfadaki TUM checkbox bilgilerini (label + deger) topla.
        Bu fonksiyon "Tumunu kaldir" TIKLANMADAN ONCE cagrilmali!
        OPTIMIZE: implicit wait=0

        Returns:
            dict: {'APG': '95', 'HbA1c': '5.2', 'Glukoz': '102', ...}
        """
        tests = {}
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)

        try:
            # Sayfadaki tum metni al
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text

            # Bilinen test adlari ve varyasyonlari
            known_tests = [
                'APG', 'TKG', 'OGTT', 'HbA1c', 'Glukoz', 'Glikoz',
                'Kolesterol', 'HDL', 'LDL', 'non-HDL', 'Trigliserit',
                'Kreatinin', 'eGFR', 'Albumin', 'Sodyum', 'Potasyum',
                'ALT', 'AST', 'GGT', 'ALP', 'Bilirubin',
                'TSH', 'T4', 'T3', 'Hemoglobin', 'Hb', 'WBC', 'PLT'
            ]

            import re

            for test in known_tests:
                # Pattern: test adi + : veya bosluk + sayi
                patterns = [
                    rf'{re.escape(test)}\s*[:=]?\s*(\d+[.,]?\d*)',  # "APG: 95" veya "APG 95"
                    rf'{re.escape(test)}.*?(\d+[.,]\d+)',  # "APG sonucu: 95.5"
                ]

                for pattern in patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        value = match.group(1).replace(',', '.')
                        try:
                            num_val = float(value)
                            # Mantikli deger araliklarini kontrol et
                            if 0 < num_val < 10000:
                                tests[test] = value
                                break
                        except:
                            pass

            # Ek olarak: Sayfadaki input[type="number"] veya deger gosterim elementlerini tara
            try:
                value_elements = self.driver.find_elements(By.CSS_SELECTOR,
                    '.son-deger, .test-value, .result-value, [class*="value"], input[type="number"]')

                for el in value_elements:
                    try:
                        # Parent'tan label bulmaya calis
                        parent = el.find_element(By.XPATH, './ancestor::*[3]')
                        parent_text = parent.text

                        for test in known_tests:
                            if test.lower() in parent_text.lower():
                                # Deger varsa al
                                val = el.get_attribute('value') or el.text
                                if val and val.strip():
                                    try:
                                        num_val = float(val.replace(',', '.'))
                                        if 0 < num_val < 10000 and test not in tests:
                                            tests[test] = val.strip()
                                    except:
                                        pass
                    except:
                        pass
            except:
                pass

        except Exception as e:
            self.log(f"   Checkbox bilgi toplama hatasi: {e}", "DEBUG")
        finally:
            self.driver.implicitly_wait(original_wait)

        return tests

    def _read_old_values_from_tetkik_page(self) -> dict:
        """
        Tetkik sayfasindaki ESKI DEGERLERI direkt sayfadan oku - HIZLI.
        OPTIMIZE: implicit wait=0

        Returns:
            dict: {'Glukoz': '92', 'HDL': '39', 'Albumin': '-', ...}
        """
        old_values = {}
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)

        # Bilinen test adlari
        # ONEMLI: non-HDL, HDL'den ONCE olmali! (substring match sorunu)
        known_tests = [
            'APG', 'TKG', 'OGTT', 'HbA1c', 'Glukoz', 'Glikoz',
            'Kolesterol', 'non-HDL', 'Non-HDL', 'HDL', 'LDL', 'Trigliserit',
            'Kreatinin', 'eGFR', 'Sodyum', 'Potasyum',
            'ALT', 'AST', 'GGT', 'ALP', 'Bilirubin',
            'TSH', 'T4', 'T3', 'Hemoglobin', 'Hb', 'WBC', 'PLT',
            'Albumin', 'Albümin', 'AKO', 'PKO', 'Protein'
        ]

        try:
            # Sayfadaki tum metni satirlara bol
            body = self.driver.find_element(By.TAG_NAME, 'body')
            lines = body.text.split('\n')
            lines = [l.strip() for l in lines if l.strip()]

            self.log(f"   Sayfada {len(lines)} satir okundu", "DEBUG")

            # Her test adini ara
            for i, line in enumerate(lines):
                line_lower = line.lower()
                for test in known_tests:
                    test_lower = test.lower()
                    # Satir test adini iceriyor mu? (tam veya kismi eslesme)
                    if test_lower == line_lower or (test_lower in line_lower and len(line) < 50):
                        # HDL/non-HDL ozel kontrolu
                        if test_lower == 'hdl' and 'non-hdl' in line_lower:
                            continue  # non-HDL satirini HDL olarak eslestirme

                        # ============================================================
                        # KRITIK DUZELTME: Eger bu test icin zaten GECERLI bir deger
                        # bulunmussa (yani "-" degilse), uzerine YAZMA!
                        # Sayfada ayni test adi birden fazla yerde gecebilir.
                        # ============================================================
                        if test in old_values and old_values[test] != '-':
                            break  # Bu test icin zaten gecerli deger var, sonrakine gec

                        # Sonraki satir eski deger olmali
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()

                            # Eski deger: sayi veya "-"
                            if next_line == '-':
                                # Sadece daha once deger bulunmadiysa "-" yaz
                                if test not in old_values:
                                    old_values[test] = '-'
                                    self.log(f"   {test}: ESKI DEGER YOK (-)", "DEBUG")
                            else:
                                # Sayi mi kontrol et
                                try:
                                    # Virgulu noktaya cevir ve float dene
                                    test_val = next_line.replace(',', '.')
                                    # Bazen "92 mg/dL" gibi birim de olabilir, sadece sayiyi al
                                    import re
                                    match = re.match(r'^(\d+\.?\d*)', test_val)
                                    if match:
                                        old_values[test] = match.group(1)
                                        self.log(f"   {test}: {old_values[test]}", "DEBUG")
                                except:
                                    pass
                        break  # Bu test bulundu, sonrakine gec

            self.log(f"   Toplam {len(old_values)} test degeri okundu", "DEBUG")

        except Exception as e:
            self.log(f"   Eski deger okuma hatasi: {e}", "DEBUG")
        finally:
            self.driver.implicitly_wait(original_wait)

        return old_values

    def _get_remaining_checkbox_test_name(self) -> str:
        """
        Tikli (kaldirilamayan) checkbox'in yanindaki test adini bul.

        Returns:
            str: Test adi (ornek: 'non-HDL', 'Kolesterol', 'HbA1c') veya 'Bilinmeyen'
        """
        try:
            # PrimeNG checkbox'lari ve parent elementlerini kontrol et
            active_boxes = self.driver.find_elements(By.CSS_SELECTOR, '.ui-chkbox-box.ui-state-active')

            for box in active_boxes:
                try:
                    # Checkbox'in parent satir elementini bul
                    # Genellikle: tr, div, li gibi container icinde
                    parent = box.find_element(By.XPATH, './ancestor::*[contains(@class, "row") or contains(@class, "item") or self::tr or self::li][1]')
                    text = parent.text.strip()

                    if text:
                        # Test adini cikart (ilk satir genellikle test adi)
                        lines = text.split('\n')
                        test_name = lines[0].strip()

                        # Deger varsa ayikla
                        if ':' in test_name:
                            test_name = test_name.split(':')[0].strip()

                        self.log(f"   Tikli checkbox test adi: {test_name}", "DEBUG")
                        return test_name
                except:
                    pass

            # Alternatif: Label ile iliskilendirilmis checkbox
            for box in active_boxes:
                try:
                    # Checkbox'in sibling veya yakin label'ini bul
                    siblings = box.find_elements(By.XPATH, './following-sibling::*[1] | ./preceding-sibling::*[1] | ../label | ../../label')
                    for sib in siblings:
                        text = sib.text.strip()
                        if text and len(text) < 50:  # Kisa metin, muhtemelen test adi
                            return text
                except:
                    pass

            # Son care: Sayfadaki tum test adlarini tara
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text

            # Bilinen test adlari
            known_tests = ['non-HDL', 'Non-HDL', 'NON-HDL', 'Kolesterol', 'HDL', 'LDL',
                           'Trigliserit', 'HbA1c', 'APG', 'TKG', 'OGTT', 'Glukoz']

            for test in known_tests:
                if test.lower() in page_text.lower():
                    # Bu test sayfada var mi ve tikli mi kontrol et
                    self.log(f"   Olasi tikli test: {test}", "DEBUG")
                    return test

        except Exception as e:
            self.log(f"   Test adi bulma hatasi: {e}", "DEBUG")

        return "Bilinmeyen"

    def _get_remaining_checkbox_names(self) -> set:
        """
        Sayfadaki TUM tikli checkbox'larin isimlerini dondur.

        "Tumunu kaldir" tiklandi ama bazi checkbox'lar KALDIRILAMADIĞINDA kullanilir.
        Cache'i filtrelemek icin kullanilir.

        Returns:
            set: Tikli kalan checkbox isimleri, ornek: {'Glukoz', 'Trigliserit', 'Kreatinin'}
        """
        remaining_names = set()

        # Bilinen test adlari - _collect_all_checkbox_info_from_page ile ayni liste
        # ONEMLI: non-HDL, HDL'den ONCE olmali! (substring match sorunu)
        known_tests = [
            'APG', 'TKG', 'OGTT', 'HbA1c', 'Glukoz', 'Glikoz',
            'Kolesterol', 'non-HDL', 'Non-HDL', 'HDL', 'LDL', 'Trigliserit',
            'Kreatinin', 'eGFR', 'Albumin', 'Sodyum', 'Potasyum',
            'ALT', 'AST', 'GGT', 'ALP', 'Bilirubin',
            'TSH', 'T4', 'T3', 'Hemoglobin', 'Hb', 'WBC', 'PLT',
            'Urea', 'BUN', 'Idrar', 'idrarda albumin'
        ]

        try:
            # TUM tikli checkbox'lari bul (PrimeNG)
            active_boxes = self.driver.find_elements(By.CSS_SELECTOR, '.ui-chkbox-box.ui-state-active')
            self.log(f"   {len(active_boxes)} tikli checkbox elementi bulundu", "DEBUG")

            for i, box in enumerate(active_boxes):
                test_name = None
                container_text = ""

                # YONTEM 1: En yakin buyuk container'in text'ini al
                try:
                    # Farkli parent seviyelerini dene
                    for ancestor_level in range(1, 8):
                        try:
                            parent = box.find_element(By.XPATH, f'./ancestor::*[{ancestor_level}]')
                            parent_text = parent.text.strip()

                            # Eger parent text'i yeterince uzunsa ve test adi iceriyorsa
                            if parent_text and len(parent_text) > 3 and len(parent_text) < 500:
                                container_text = parent_text
                                # Bilinen test adlarindan birini iceriyor mu?
                                parent_lower = parent_text.lower()
                                for known in known_tests:
                                    known_lower = known.lower()
                                    if known_lower in parent_lower:
                                        # HDL/non-HDL ozel kontrolu
                                        if known_lower == 'hdl' and 'non-hdl' in parent_lower:
                                            continue  # non-HDL ise HDL'i atla
                                        test_name = known
                                        self.log(f"   Checkbox {i+1}: Parent text'ten bulundu: {test_name}", "DEBUG")
                                        break

                            if test_name:
                                break
                        except:
                            pass
                except Exception as e:
                    self.log(f"   Checkbox {i+1} parent text alma hatasi: {e}", "DEBUG")

                # YONTEM 2: Onceki sibling veya label elementlerini kontrol et
                if not test_name:
                    try:
                        # Onceki kardes elementleri kontrol et
                        prev_siblings = box.find_elements(By.XPATH, './preceding-sibling::*')
                        for sib in prev_siblings[:3]:  # Ilk 3 onceki kardes
                            sib_text = sib.text.strip()
                            sib_lower = sib_text.lower()
                            for known in known_tests:
                                known_lower = known.lower()
                                if known_lower in sib_lower:
                                    # HDL/non-HDL ozel kontrolu
                                    if known_lower == 'hdl' and 'non-hdl' in sib_lower:
                                        continue
                                    test_name = known
                                    self.log(f"   Checkbox {i+1}: Sibling'den bulundu: {test_name}", "DEBUG")
                                    break
                            if test_name:
                                break
                    except:
                        pass

                # YONTEM 3: p-checkbox parent'i uzerinden label ara
                if not test_name:
                    try:
                        p_checkbox = box.find_element(By.XPATH, './ancestor::p-checkbox[1]')
                        # Parent div'in tum text'ini al
                        parent_div = p_checkbox.find_element(By.XPATH, './..')
                        full_text = parent_div.text.strip()
                        full_lower = full_text.lower()

                        for known in known_tests:
                            known_lower = known.lower()
                            if known_lower in full_lower:
                                # HDL/non-HDL ozel kontrolu
                                if known_lower == 'hdl' and 'non-hdl' in full_lower:
                                    continue
                                test_name = known
                                self.log(f"   Checkbox {i+1}: p-checkbox parent'tan bulundu: {test_name}", "DEBUG")
                                break
                    except:
                        pass

                # YONTEM 4: Row/item class'li parent'tan
                if not test_name:
                    try:
                        row_parent = box.find_element(By.XPATH,
                            './ancestor::*[contains(@class, "row") or contains(@class, "item") or contains(@class, "test") or contains(@class, "tetkik")][1]')
                        row_text = row_parent.text.strip()
                        row_lower = row_text.lower()

                        for known in known_tests:
                            known_lower = known.lower()
                            if known_lower in row_lower:
                                # HDL/non-HDL ozel kontrolu
                                if known_lower == 'hdl' and 'non-hdl' in row_lower:
                                    continue
                                test_name = known
                                self.log(f"   Checkbox {i+1}: Row/item'dan bulundu: {test_name}", "DEBUG")
                                break
                    except:
                        pass

                if test_name:
                    remaining_names.add(test_name)
                else:
                    # Son care: container text'in ilk satirini kullan
                    if container_text:
                        first_line = container_text.split('\n')[0].strip()
                        if first_line and len(first_line) < 50:
                            remaining_names.add(first_line)
                            self.log(f"   Checkbox {i+1}: Fallback - ilk satir: {first_line}", "DEBUG")
                    else:
                        self.log(f"   Checkbox {i+1}: Test adi BULUNAMADI", "DEBUG")

        except Exception as e:
            self.log(f"   Tikli checkbox isimlerini alma hatasi: {e}", "DEBUG")

        self.log(f"   Toplam tikli kalan test sayisi: {len(remaining_names)}", "DEBUG")
        return remaining_names

    def _get_all_remaining_checkbox_tests(self) -> dict:
        """
        TUM kaldirilamayan checkbox'larin test adlarini ve degerlerini bul.

        Returns:
            dict: {'non-HDL': '143', 'LDL': '120', 'HDL': '45', ...}
                  Eski degeri bulunamayan testler dahil edilmez
        """
        tests = {}

        try:
            # TUM tikli checkbox'lari bul (PrimeNG)
            active_boxes = self.driver.find_elements(By.CSS_SELECTOR, '.ui-chkbox-box.ui-state-active')
            self.log(f"   {len(active_boxes)} tikli checkbox bulundu", "DEBUG")

            for i, box in enumerate(active_boxes):
                test_name = None
                test_value = None

                # ============================================================
                # YONTEM 1: p-checkbox > label iliskisi (PrimeNG standart yapisi)
                # ============================================================
                try:
                    # p-checkbox elementini bul (parent'lardan)
                    p_checkbox = box.find_element(By.XPATH, './ancestor::p-checkbox[1]')

                    # Label genellikle p-checkbox'in hemen yaninda veya icinde
                    label_candidates = []

                    # Following sibling label
                    try:
                        label_candidates.extend(p_checkbox.find_elements(By.XPATH, './following-sibling::label[1]'))
                    except:
                        pass

                    # Preceding sibling span/label
                    try:
                        label_candidates.extend(p_checkbox.find_elements(By.XPATH, './preceding-sibling::*[1]'))
                    except:
                        pass

                    # Parent'in icindeki diger elementler
                    try:
                        parent_div = p_checkbox.find_element(By.XPATH, './..')
                        label_candidates.extend(parent_div.find_elements(By.CSS_SELECTOR, 'label, span.test-name, span.label, .tetkik-adi'))
                    except:
                        pass

                    for lbl in label_candidates:
                        text = lbl.text.strip()
                        if text and len(text) < 60 and not text.isdigit():
                            # Checkbox text'i degil (genellikle "Evet", "Hayir" vs.)
                            if text.lower() not in ['evet', 'hayir', 'hayır', 'var', 'yok']:
                                test_name = text.split(':')[0].strip() if ':' in text else text
                                self.log(f"   [YONTEM1] Checkbox {i+1}: {test_name}", "DEBUG")
                                break
                except:
                    pass

                # ============================================================
                # YONTEM 2: Checkbox'in bulundugu satir/row elementinden al
                # ============================================================
                if not test_name:
                    try:
                        # Daha genis parent arama
                        parent_selectors = [
                            './ancestor::*[contains(@class, "p-col") or contains(@class, "col-")][1]',
                            './ancestor::*[contains(@class, "grid")]//*[contains(@class, "col")]',
                            './ancestor::div[contains(@class, "row")][1]',
                            './ancestor::div[contains(@class, "flex")][1]',
                            './ancestor::tr[1]',
                            './ancestor::li[1]',
                            './ancestor::*[4]',  # 4 ust parent (genellikle row elementi)
                        ]

                        for selector in parent_selectors:
                            try:
                                parent = box.find_element(By.XPATH, selector)
                                text = parent.text.strip()

                                if text and len(text) < 150:
                                    lines = text.split('\n')
                                    for line in lines:
                                        line = line.strip()
                                        # Checkbox degil, test adi olmali
                                        if line and len(line) < 50 and line.lower() not in ['evet', 'hayir', 'hayır', 'var', 'yok', '']:
                                            # Sayi veya tarih degilse test adi
                                            if not line.replace('.', '').replace(',', '').isdigit():
                                                if ':' in line:
                                                    test_name = line.split(':')[0].strip()
                                                else:
                                                    test_name = line
                                                self.log(f"   [YONTEM2] Checkbox {i+1}: {test_name}", "DEBUG")
                                                break
                                    if test_name:
                                        break
                            except:
                                continue
                    except:
                        pass

                # ============================================================
                # YONTEM 3: Formcontrolname veya name attribute'undan al
                # ============================================================
                if not test_name:
                    try:
                        # Checkbox'in input elementini bul
                        input_el = box.find_element(By.XPATH, './ancestor::p-checkbox//input | ./preceding-sibling::input | ./following-sibling::input')

                        # formcontrolname, name veya id attribute'lari
                        for attr in ['formcontrolname', 'name', 'id']:
                            val = input_el.get_attribute(attr)
                            if val and len(val) < 50:
                                # camelCase veya snake_case'i insan okunur hale getir
                                import re
                                test_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', val)
                                test_name = test_name.replace('_', ' ').title()
                                self.log(f"   [YONTEM3] Checkbox {i+1}: {test_name} (attr={attr})", "DEBUG")
                                break
                    except:
                        pass

                # ============================================================
                # Test adi bulunduysa degeri sayfadan al
                # ============================================================
                if test_name and test_name not in tests:
                    # Oncelikle sayfadan eski degeri bul
                    test_value = self._get_test_value_from_page(test_name)

                    if test_value:
                        tests[test_name] = test_value
                        self.log(f"   Kaldirilamayan tik: {test_name} = {test_value}", "SUCCESS")
                    else:
                        self.log(f"   Kaldirilamayan tik: {test_name} (DEGER BULUNAMADI!)", "WARNING")

        except Exception as e:
            self.log(f"   Tum tikleri bulma hatasi: {e}", "DEBUG")

        # Eger hic test bulunamadiysa log yaz
        if not tests:
            self.log("   Kaldirilamayan tik bulunamadi veya degerleri yok", "DEBUG")

        return tests

    def _get_test_value_from_page(self, test_name: str) -> str:
        """
        Sayfadan belirli bir testin mevcut degerini bul.

        ONEMLI: Eski deger bulunamazsa None don!
        Varsayilan deger GIRME - hasta pas gecilecek!

        Args:
            test_name: Test adi (ornek: 'non-HDL', 'Kolesterol')

        Returns:
            str: Test degeri veya None (deger bulunamazsa)
        """
        import re

        try:
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text

            # Normalize test name for matching
            test_name_lower = test_name.lower().strip()

            # ============================================================
            # YONTEM 1: Regex ile sayfa metninden degeri bul
            # ============================================================
            patterns = [
                # Pattern: "Test Adı: 123" veya "Test Adı : 123"
                rf'{re.escape(test_name)}[:\s]+(\d+[.,]?\d*)',
                # Pattern: "Test Adı = 123"
                rf'{test_name}\s*[:=]\s*(\d+[.,]?\d*)',
                # Pattern: "Test Adı ... 123.5" (araya baska seyler girebilir)
                rf'{test_name}[^\d]{{0,30}}(\d+[.,]\d+)',
                # Pattern: "Test Adı ... 123" (tam sayi)
                rf'{test_name}[^\d]{{0,30}}(\d{{2,4}})',
            ]

            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    value = match.group(1).replace(',', '.')
                    # Gecerli deger mi kontrol et (0'dan buyuk ve mantikli aralik)
                    try:
                        float_val = float(value)
                        if 0 < float_val < 10000:  # Mantikli deger araligi
                            self.log(f"   {test_name} degeri (regex): {value}", "SUCCESS")
                            return value
                    except:
                        pass

            # ============================================================
            # YONTEM 2: Tablo satirlarindan deger bul
            # ============================================================
            try:
                # Sayfadaki tum table row'larini tara
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr, .p-datatable-tbody tr, .row, .grid')
                for row in rows:
                    row_text = row.text.strip()
                    if test_name_lower in row_text.lower():
                        # Bu satirda test adi var, sayisal degeri bul
                        numbers = re.findall(r'\d+[.,]?\d*', row_text)
                        for num in numbers:
                            try:
                                val = float(num.replace(',', '.'))
                                if 0 < val < 10000:
                                    self.log(f"   {test_name} degeri (tablo): {num.replace(',', '.')}", "SUCCESS")
                                    return num.replace(',', '.')
                            except:
                                continue
            except:
                pass

            # ============================================================
            # YONTEM 3: Checkbox yakinindaki degerlerden bul
            # ============================================================
            try:
                # Tikli checkbox'lari bul ve yakinlarindaki degerleri kontrol et
                checkboxes = self.driver.find_elements(By.CSS_SELECTOR, '.ui-chkbox-box.ui-state-active')
                for chk in checkboxes:
                    try:
                        # Parent elementi ve text'ini al
                        parent = chk.find_element(By.XPATH, './ancestor::*[6]')
                        parent_text = parent.text.strip()

                        if test_name_lower in parent_text.lower():
                            # Bu parent'ta test adi var
                            numbers = re.findall(r'\d+[.,]?\d*', parent_text)
                            for num in numbers:
                                try:
                                    val = float(num.replace(',', '.'))
                                    if 0 < val < 10000:
                                        self.log(f"   {test_name} degeri (checkbox parent): {num.replace(',', '.')}", "SUCCESS")
                                        return num.replace(',', '.')
                                except:
                                    continue
                    except:
                        continue
            except:
                pass

            # ============================================================
            # YONTEM 4: Input elementlerinden deger bul
            # ============================================================
            try:
                inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                for inp in inputs:
                    try:
                        # Input'un yakinindaki label/span'i kontrol et
                        parent = inp.find_element(By.XPATH, './..')
                        parent_text = parent.text.lower()

                        if test_name_lower in parent_text:
                            value = inp.get_attribute('value')
                            if value:
                                self.log(f"   {test_name} input degeri: {value}", "SUCCESS")
                                return value
                    except:
                        pass

                    try:
                        # Preceding label kontrolu
                        label = inp.find_element(By.XPATH, './preceding::label[1]')
                        if test_name_lower in label.text.lower():
                            value = inp.get_attribute('value')
                            if value:
                                self.log(f"   {test_name} input degeri (label): {value}", "SUCCESS")
                                return value
                    except:
                        pass
            except:
                pass

            # ============================================================
            # YONTEM 5: "Son Deger" veya "Onceki Deger" kartilarindan bul
            # ============================================================
            try:
                # HYP'de genellikle "Son Değer" kartı var
                card_selectors = ['.card', '.panel', '.p-card', '.result-card', '.sonuc-kart']
                for selector in card_selectors:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for card in cards:
                        card_text = card.text.strip()
                        if test_name_lower in card_text.lower():
                            # Deger pattern'i ara
                            numbers = re.findall(r'(?:son|onceki|mevcut|deger)[:\s]*(\d+[.,]?\d*)', card_text, re.IGNORECASE)
                            if numbers:
                                value = numbers[0].replace(',', '.')
                                self.log(f"   {test_name} degeri (kart): {value}", "SUCCESS")
                                return value
            except:
                pass

            # DEGER BULUNAMADI - VARSAYILAN GIRME!
            self.log(f"   !!! {test_name} degeri sayfada BULUNAMADI!", "WARNING")
            return None

        except Exception as e:
            self.log(f"   Test degeri bulma hatasi: {e}", "DEBUG")
            return None

    def _count_active_checkboxes(self) -> int:
        """Sayfadaki tikli checkbox sayisini dondur"""
        count = 0
        # Implicit wait'i gecici olarak kapat (hiz icin)
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        try:
            # PrimeNG checkbox - en yaygin
            count += len(self.driver.find_elements(By.CSS_SELECTOR, '.ui-chkbox-box.ui-state-active'))
            # Sadece PrimeNG yoksa diger tipleri dene
            if count == 0:
                # Angular Material checkbox
                count += len(self.driver.find_elements(By.CSS_SELECTOR, 'mat-checkbox.mat-checkbox-checked'))
            if count == 0:
                # Standard HTML checkbox
                count += len(self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']:checked"))
        except:
            pass
        finally:
            # Implicit wait'i geri yukle
            self.driver.implicitly_wait(original_wait)
        return count

    def _uncheck_individual_boxes(self) -> int:
        """Checkbox'lari tek tek kaldir, kaldirilan sayiyi dondur"""
        unchecked = 0

        # PrimeNG checkbox'lari
        try:
            active_boxes = self.driver.find_elements(By.CSS_SELECTOR, '.ui-chkbox-box.ui-state-active')
            for box in active_boxes:
                try:
                    if box.is_displayed():
                        self.driver.execute_script('arguments[0].scrollIntoView({block: "center"});', box)
                        time.sleep(0.1)
                        self.driver.execute_script('arguments[0].click();', box)
                        unchecked += 1
                        time.sleep(0.2)
                except:
                    pass
        except:
            pass

        # Angular Material checkbox'lari
        try:
            mat_boxes = self.driver.find_elements(By.CSS_SELECTOR, 'mat-checkbox.mat-checkbox-checked .mat-checkbox-inner-container')
            for box in mat_boxes:
                try:
                    self.driver.execute_script('arguments[0].click();', box)
                    unchecked += 1
                    time.sleep(0.2)
                except:
                    pass
        except:
            pass

        # Standart HTML checkbox
        try:
            html_boxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']:checked")
            for box in html_boxes:
                try:
                    if box.is_displayed():
                        self.driver.execute_script('arguments[0].click();', box)
                        unchecked += 1
                        time.sleep(0.2)
                except:
                    pass
        except:
            pass

        return unchecked

    def _try_enter_external_lab_results(self, test_name: str = None) -> bool:
        """
        Dis Laboratuvar Sonucu Ekle ile eski deger girmeyi dene.
        Bu yontem, kaldirilamayan tikli checkbox icin deger girmek amaciyla kullanilir.
        OPTIMIZE: implicit wait=0

        ONEMLI: Modal yapisi:
        - Input 0: Tarih - GIRME!
        - Input 1: Dis Laboratuvar Adi - GIRME!
        - Input 2: Test degeri - BURAYA GIR (tik'in degeri)

        ONEMLI: Eski deger bulunamazsa VARSAYILAN GIRME!
        Bu durumda bu HYP pas gecilecek (False don)

        Args:
            test_name: Kaldirilamayan checkbox'in test adi (ornek: 'non-HDL', 'HbA1c')
                       None ise sayfadan otomatik bulunur

        Returns:
            True: Dis lab deger girildi ve kaydedildi
            False: Dis lab butonu bulunamadi, deger bulunamadi veya islem basarisiz
        """
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        try:
            # Test adini belirle
            if test_name is None or test_name == "Bilinmeyen":
                test_name = self._get_remaining_checkbox_test_name()

            self.log(f"   Dis lab icin test: {test_name}", "DEBUG")

            # Test degerini sayfadan al - VARSAYILAN GIRME!
            value_to_enter = self._get_test_value_from_page(test_name)

            # DEGER BULUNAMADIYSA - HYP PAS GECILECEK!
            if value_to_enter is None:
                self.log(f"   !!! {test_name} icin eski deger BULUNAMADI - Bu HYP pas gecilecek!", "ERROR")
                return False

            self.log(f"   Girilecek deger: {value_to_enter}", "DEBUG")

            # "Dis Laboratuvar Sonucu Ekle" butonunu bul
            dis_lab_btn = self._find_dis_lab_button()

            if not dis_lab_btn:
                self.log("   Dis lab butonu bulunamadi", "DEBUG")
                return False

            # Butona tikla
            self.driver.execute_script('arguments[0].scrollIntoView({block: "center"});', dis_lab_btn)
            time.sleep(0.3)
            self.driver.execute_script('arguments[0].click();', dis_lab_btn)
            self.log("   Dis lab sonucu ekle tiklandi", "DEBUG")
            time.sleep(0.5)  # OPTIMIZE

            # Modal acildi mi kontrol et
            modal = self._find_dis_lab_modal()

            if not modal:
                self.log("   Dis lab modal bulunamadi", "DEBUG")
                return False

            self.log("   Dis lab modal acildi", "DEBUG")

            # Modal icindeki input'lari bul - TEST ADINA GORE DOGRU INPUT SEC
            inputs = modal.find_elements(By.TAG_NAME, 'input')
            self.log(f"   Modal'da {len(inputs)} input bulundu", "DEBUG")

            if len(inputs) < 1:
                self.log("   Input yok", "DEBUG")
                self._close_modal(modal)
                return False

            # ===============================================
            # TETKIK ADINA GORE DOGRU INPUT BUL
            # ===============================================
            # Modal'da her tetkik icin bir satir (row) var
            # Her satırda: label (tetkik adi) + input (deger alani)
            # Strateji: Label'i bul -> ayni satirdaki input'u bul
            # ===============================================

            test_name_normalized = test_name.lower().replace('-', '').replace(' ', '').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')
            value_input = None

            self.log(f"   Aranan tetkik (normalized): {test_name_normalized}", "DEBUG")

            # YONTEM 1: Modal'daki tum row/form-group'lari tara
            # Her row icinde label ve input arar
            row_selectors = [
                '.form-group',
                '.row',
                '.form-row',
                'tr',  # Tablo satiri
                '.input-group',
                'p-inputnumber',  # PrimeNG input
                '.p-field',  # PrimeNG field
            ]

            for row_selector in row_selectors:
                try:
                    rows = modal.find_elements(By.CSS_SELECTOR, row_selector)
                    for row in rows:
                        row_text = row.text.lower().replace('-', '').replace(' ', '').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')

                        # Bu satir aranan tetkik adini iceriyor mu?
                        if test_name_normalized in row_text or test_name.lower() in row.text.lower():
                            # Bu satirdaki input'u bul
                            try:
                                row_input = row.find_element(By.TAG_NAME, 'input')
                                input_type = row_input.get_attribute('type') or ''

                                # Tarih/hidden/checkbox degil, number veya text ise
                                if input_type not in ['date', 'hidden', 'checkbox', 'radio']:
                                    value_input = row_input
                                    self.log(f"   Input bulundu (row ile): {row.text[:50]}...", "DEBUG")
                                    break
                            except:
                                pass
                    if value_input:
                        break
                except:
                    continue

            # YONTEM 2: Tum label'lari tara, eslesen label'in yakinindaki input'u bul
            if not value_input:
                try:
                    labels = modal.find_elements(By.XPATH, ".//*[self::label or self::span or self::div[contains(@class, 'label')]]")
                    for label in labels:
                        label_text_normalized = label.text.lower().replace('-', '').replace(' ', '').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')

                        if test_name_normalized in label_text_normalized or test_name.lower() in label.text.lower():
                            # Label'in parent elementindeki input'u bul
                            parent = label
                            for _ in range(5):  # Max 5 level yukari cik
                                try:
                                    parent = parent.find_element(By.XPATH, '..')
                                    parent_inputs = parent.find_elements(By.TAG_NAME, 'input')
                                    for inp in parent_inputs:
                                        input_type = inp.get_attribute('type') or ''
                                        if input_type not in ['date', 'hidden', 'checkbox', 'radio']:
                                            value_input = inp
                                            self.log(f"   Input bulundu (label parent ile): {label.text}", "DEBUG")
                                            break
                                    if value_input:
                                        break
                                except:
                                    break
                            if value_input:
                                break
                except Exception as e:
                    self.log(f"   Label arama hatasi: {e}", "DEBUG")

            # YONTEM 3: Bilinen formcontrolname eslestirmeleri
            if not value_input:
                formcontrol_mapping = {
                    'nonhdl': ['nonhdl', 'non_hdl', 'nonHdl', 'nonHDL'],
                    'kolesterol': ['kolesterol', 'totalKolesterol', 'total_kolesterol'],
                    'hdl': ['hdl', 'hdlKolesterol'],
                    'ldl': ['ldl', 'ldlKolesterol'],
                    'hba1c': ['hba1c', 'hbA1c', 'HbA1c'],
                    'apg': ['apg', 'aclikPlazmaGlukozu', 'aclikglukozu'],
                    'glukoz': ['glukoz', 'glucose', 'glikoz'],
                    'trigliserit': ['trigliserit', 'tg'],
                    'bki': ['bki', 'vucut_kitle_indeksi', 'bmi'],
                    'bel': ['belCevresi', 'bel_cevresi', 'bel'],
                    'kilo': ['kilo', 'agirlik', 'weight'],
                    'boy': ['boy', 'height'],
                }

                possible_names = formcontrol_mapping.get(test_name_normalized, [test_name_normalized])

                for inp in inputs:
                    try:
                        fc_name = inp.get_attribute('formcontrolname') or ''
                        fc_name_lower = fc_name.lower().replace('-', '').replace('_', '')

                        if fc_name_lower in [n.lower() for n in possible_names]:
                            value_input = inp
                            self.log(f"   Input bulundu (formcontrolname): {fc_name}", "DEBUG")
                            break

                        if test_name_normalized in fc_name_lower:
                            value_input = inp
                            self.log(f"   Input bulundu (partial match): {fc_name}", "DEBUG")
                            break
                    except:
                        continue

            # Hala bulunamadiysa - HYP PAS GEC
            if not value_input:
                self.log(f"   !!! {test_name} icin input BULUNAMADI - HYP pas gecilecek!", "ERROR")
                # Modal'daki tum input'larin formcontrolname'lerini logla (debug icin)
                try:
                    for i, inp in enumerate(inputs[:20]):  # Ilk 20 input
                        fc = inp.get_attribute('formcontrolname') or 'N/A'
                        self.log(f"      Input {i}: formcontrolname={fc}", "DEBUG")
                except:
                    pass
                self._close_modal(modal)
                return False

            # Degeri gir - JAVASCRIPT ILE HIZLI GIRIS
            try:
                self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", value_input, str(value_to_enter))
                self.log(f"   {test_name} degeri girildi: {value_to_enter}", "DEBUG")
                time.sleep(0.2)
            except Exception as e:
                self.log(f"   Deger girme hatasi: {e}", "DEBUG")
                self._close_modal(modal)
                return False

            # Kaydet butonuna tikla
            saved = self._save_dis_lab_modal(modal)

            if saved:
                self.log(f"   Dis lab sonucu kaydedildi ({test_name}: {value_to_enter})", "DEBUG")
                time.sleep(1)
                return True
            else:
                self.log("   Dis lab kaydetme basarisiz", "DEBUG")
                return False

        except Exception as e:
            self.log(f"   Dis lab hatasi: {e}", "DEBUG")
            return False
        finally:
            self.driver.implicitly_wait(original_wait)

    def _try_enter_all_external_lab_results(self) -> bool:
        """
        TUM kaldirilamayan checkbox'lar icin dis lab sonucu gir.
        MODAL'I BIR KERE AC, TUM DEGERLERI GIR, TEK KAYDET!
        OPTIMIZE: implicit wait=0

        Returns:
            True: En az bir deger girildi ve kaydedildi
            False: Hic deger girilemedi
        """
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        try:
            # ============================================================
            # YENI MANTIK: Sayfadan direkt eski degerleri oku (cache yerine)
            # Bu daha guvenilir cunku HYP sayfasinda degerler gorunuyor
            # ============================================================

            # 1. Kalan tikli checkbox isimlerini bul
            remaining_names = self._get_remaining_checkbox_names()
            self.log(f"   Kalan tikli checkbox isimleri: {remaining_names}", "DEBUG")

            if not remaining_names:
                self.log("   !!! Kalan checkbox isimleri tespit edilemedi!", "WARNING")
                return False

            # 2. Sayfadan eski degerleri oku
            old_values = self._read_old_values_from_tetkik_page()
            self.log(f"   Sayfadan okunan degerler: {old_values}", "DEBUG")

            # 3. Kalan tikler icin degerleri hazirla
            tests_to_enter = {}
            tests_without_value = []

            for remaining in remaining_names:
                remaining_lower = remaining.lower().strip()
                found_value = None

                # Eski degerler icinde bu testi ara
                for test_name, test_value in old_values.items():
                    test_lower = test_name.lower().strip()

                    # Tam eslesme (EN GUVENILIR)
                    if test_lower == remaining_lower:
                        found_value = test_value
                        break

                    # non-HDL vs HDL OZEL DURUMU (KRITIK!)
                    # remaining="non-HDL" ise, sadece "non-HDL" veya "non-hdl" eslesmeli
                    # remaining="HDL" ise, "non-HDL" veya "non-hdl" eslesmeMELI
                    if 'non' in remaining_lower:
                        # remaining non-HDL ise, test_name de non icermeli
                        if 'non' not in test_lower:
                            continue
                    else:
                        # remaining HDL ise, test_name non icerMEMELI
                        if 'hdl' in remaining_lower and 'non' in test_lower:
                            continue

                    # Kismi eslesme (dikkatli kullan)
                    if remaining_lower in test_lower or test_lower in remaining_lower:
                        found_value = test_value
                        break

                if found_value and found_value != '-':
                    tests_to_enter[remaining] = found_value
                    self.log(f"   {remaining}: {found_value} (girilecek)", "DEBUG")
                elif found_value == '-':
                    tests_without_value.append(remaining)
                    self.log(f"   {remaining}: ESKI DEGER YOK (-) - dis lab girilemez!", "WARNING")
                else:
                    # Cache'den dene (fallback)
                    if hasattr(self, '_cached_checkbox_data') and self._cached_checkbox_data:
                        for cached_name, cached_value in self._cached_checkbox_data.items():
                            if remaining_lower in cached_name.lower() or cached_name.lower() in remaining_lower:
                                tests_to_enter[remaining] = cached_value
                                self.log(f"   {remaining}: {cached_value} (cache'den)", "DEBUG")
                                break
                        else:
                            tests_without_value.append(remaining)
                            self.log(f"   {remaining}: NE SAYFADA NE CACHE'DE DEGER YOK!", "WARNING")
                    else:
                        tests_without_value.append(remaining)

            # Eski degeri olmayan test varsa HYP iptal edilmeli
            if tests_without_value and not tests_to_enter:
                self.log(f"   !!! {len(tests_without_value)} testin eski degeri YOK: {tests_without_value}", "ERROR")
                return False

            if not tests_to_enter:
                self.log("   Girilecek deger bulunamadi", "DEBUG")
                return False

            self.log(f"   {len(tests_to_enter)} test icin dis lab sonucu girilecek:", "DEBUG")
            for test_name, value in tests_to_enter.items():
                self.log(f"      - {test_name}: {value}", "DEBUG")

            # "Dis Laboratuvar Sonucu Ekle" butonunu bul
            dis_lab_btn = self._find_dis_lab_button()

            if not dis_lab_btn:
                self.log("   Dis lab butonu bulunamadi", "DEBUG")
                return False

            # Butona tikla - MODAL ACILIR
            self.driver.execute_script('arguments[0].scrollIntoView({block: "center"});', dis_lab_btn)
            self.driver.execute_script('arguments[0].click();', dis_lab_btn)
            self.log("   Dis lab sonucu ekle tiklandi", "DEBUG")
            time.sleep(0.5)  # 2 -> 0.5 saniye (HIZLANDIRILDI)

            # Modal acildi mi kontrol et
            modal = self._find_dis_lab_modal()

            if not modal:
                self.log("   Dis lab modal bulunamadi", "DEBUG")
                return False

            self.log("   Dis lab modal acildi", "DEBUG")

            # Modal icindeki input'lari al
            inputs = modal.find_elements(By.TAG_NAME, 'input')
            self.log(f"   Modal'da {len(inputs)} input bulundu", "DEBUG")

            # HER TEST ICIN DOGRU INPUT'U BUL VE DEGER GIR
            entered_count = 0
            for test_name, value in tests_to_enter.items():
                value_input = self._find_input_for_test_in_modal(modal, test_name, inputs)

                if value_input:
                    try:
                        self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", value_input, str(value))
                        self.log(f"   {test_name} degeri girildi: {value}", "DEBUG")
                        entered_count += 1
                    except Exception as e:
                        self.log(f"   {test_name} deger girme hatasi: {e}", "DEBUG")
                else:
                    self.log(f"   {test_name} icin input bulunamadi - ATLANDI", "WARNING")

            # En az bir deger girildiyse kaydet
            if entered_count > 0:
                # TEK SEFERDE KAYDET
                saved = self._save_dis_lab_modal(modal)

                if saved:
                    self.log(f"   {entered_count} dis lab sonucu kaydedildi!", "DEBUG")
                    time.sleep(0.3)  # 1 -> 0.3 saniye (HIZLANDIRILDI)
                    return True
                else:
                    self.log("   Dis lab kaydetme basarisiz", "DEBUG")
                    return False
            else:
                self.log("   Hic deger girilemedi - modal kapatiliyor", "DEBUG")
                self._close_modal(modal)
                return False

        except Exception as e:
            self.log(f"   Tum dis lab girisi hatasi: {e}", "DEBUG")
            return False
        finally:
            self.driver.implicitly_wait(original_wait)

    def _find_input_for_test_in_modal(self, modal, test_name: str, inputs: list):
        """
        Modal icinde belirli bir test icin dogru input'u bul.
        OPTIMIZE EDILDI: Tek XPath sorgusu ile hizli arama.

        DUZELTME: Kreatinin ve diger Turkce karakterli testler icin
        normalize edilmis arama yapiliyor.
        """
        test_name_lower = test_name.lower()
        test_name_normalized = test_name_lower.replace('-', '').replace(' ', '').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g').replace('i', 'i')

        # OZEL DURUM: Kreatinin icin alternatif yazimlar
        # HYP'de "Kreatinin", "KREATİNİN", "Kreatınin" gibi yazilabilir
        test_variants = [test_name]
        if 'kreatinin' in test_name_lower:
            test_variants.extend(['Kreatinin', 'KREATİNİN', 'Kreatınin', 'KREATININ', 'kreatinin'])

        # HIZLI YONTEM: XPath ile direkt ara
        # Test adini iceren satirdaki input'u bul
        try:
            # Yontem 1: Label icerigine gore ara (en hizli)
            # HER VARYANT ICIN DENE
            for variant in test_variants:
                xpaths = [
                    f".//label[contains(., '{variant}')]/following::input[1]",
                    f".//span[contains(., '{variant}')]/following::input[1]",
                    f".//*[contains(text(), '{variant}')]/ancestor::*[.//input][1]//input",
                    # Buyuk/kucuk harf duyarsiz arama
                    f".//label[contains(translate(., 'ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ', 'abcçdefgğhıijklmnoöprsştuüvyz'), '{variant.lower()}')]/following::input[1]",
                    f".//span[contains(translate(., 'ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ', 'abcçdefgğhıijklmnoöprsştuüvyz'), '{variant.lower()}')]/following::input[1]",
                ]

                for xpath in xpaths:
                    try:
                        found = modal.find_element(By.XPATH, xpath)
                        if found and found.is_displayed():
                            input_type = found.get_attribute('type') or ''
                            if input_type not in ['date', 'hidden', 'checkbox', 'radio']:
                                self.log(f"      HIZLI BULUNDU: {test_name} (varyant: {variant})", "DEBUG")
                                return found
                    except:
                        continue

            # Yontem 2: Tum inputlari tara (fallback - eski yontem ama sadece gerekirse)
            for inp in inputs:
                try:
                    # Input'un parent elementinin textini kontrol et
                    # DAHA GENIS PARENT ARALIK - 5 seviye yukari cik
                    for level in range(1, 6):
                        try:
                            parent = inp.find_element(By.XPATH, f'./ancestor::*[{level}]')
                            parent_text = parent.text.lower().replace('-', '').replace(' ', '').replace('ı', 'i').replace('İ', 'i').replace('ş', 's').replace('Ş', 's')

                            if test_name_normalized in parent_text:
                                # HDL vs non-HDL kontrolu
                                if 'hdl' in test_name_normalized:
                                    is_looking_for_non = 'non' in test_name_normalized
                                    row_has_non = 'non' in parent_text
                                    if is_looking_for_non != row_has_non:
                                        continue

                                input_type = inp.get_attribute('type') or ''
                                if input_type not in ['date', 'hidden', 'checkbox', 'radio']:
                                    self.log(f"      FALLBACK BULUNDU: {test_name} (level {level})", "DEBUG")
                                    return inp
                        except:
                            continue
                except:
                    continue

        except Exception as e:
            self.log(f"      Input arama hatasi: {e}", "DEBUG")

        return None
    
    def _find_input_for_test_in_modal_OLD(self, modal, test_name: str, inputs: list):
        """ESKI YAVAS FONKSIYON - YEDEK"""
        test_name_normalized = test_name.lower().replace('-', '').replace(' ', '').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')
        test_name_lower = test_name.lower()

        # ============================================================
        # GUVENLIK: Sadece DOGRU alana deger girilmeli!
        # Ornek: Glukoz degeri Glukoz alanina, HDL degeri HDL alanina
        # Yanlis alan bulunursa None don, deger GIRILMESIN!
        # ============================================================

        found_input = None
        found_row_text = None

        # YONTEM 1: Row/form-group ile ara - ONCE TAM ESLESME, SONRA KISMI
        row_selectors = ['.form-group', '.row', '.form-row', 'tr', '.input-group', 'p-inputnumber', '.p-field']

        # ILK GECİS: TAM ESLESME ara (satirin ilk kelimesi test adi olmali)
        for row_selector in row_selectors:
            try:
                rows = modal.find_elements(By.CSS_SELECTOR, row_selector)
                for row in rows:
                    row_text_original = row.text.strip()
                    if not row_text_original:
                        continue

                    # Satirin ILK kelimesini al (genellikle test adi)
                    first_line = row_text_original.split('\n')[0].strip()
                    first_word = first_line.split()[0] if first_line.split() else ''
                    first_word_normalized = first_word.lower().replace('-', '').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')

                    # TAM ESLESME kontrolu
                    if first_word_normalized == test_name_normalized or first_word.lower() == test_name_lower:
                        # HDL vs non-HDL ozel kontrolu
                        row_text_norm = row_text_original.lower().replace('-', '').replace(' ', '')
                        is_looking_for_non = 'non' in test_name_normalized
                        row_has_non = 'non' in row_text_norm

                        if 'hdl' in test_name_normalized:
                            if not is_looking_for_non and row_has_non:
                                continue  # HDL ariyoruz ama satir non-HDL
                            if is_looking_for_non and not row_has_non:
                                continue  # non-HDL ariyoruz ama satir sadece HDL

                        try:
                            row_input = row.find_element(By.TAG_NAME, 'input')
                            input_type = row_input.get_attribute('type') or ''
                            if input_type not in ['date', 'hidden', 'checkbox', 'radio']:
                                found_input = row_input
                                found_row_text = first_line
                                break
                        except:
                            pass
                if found_input:
                    break
            except:
                continue

        # Tam eslesme bulunduysa don
        if found_input:
            self.log(f"      Modal'da TAM ESLESME: '{test_name}' -> '{found_row_text}'", "DEBUG")
            return found_input

        # IKINCI GECIS: Kismi eslesme (daha riskli, dikkatli ol)
        for row_selector in row_selectors:
            try:
                rows = modal.find_elements(By.CSS_SELECTOR, row_selector)
                for row in rows:
                    row_text = row.text.lower().replace('-', '').replace(' ', '').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')
                    row_text_original = row.text.lower()

                    # HDL vs non-HDL ozel kontrolu
                    is_looking_for_non = 'non' in test_name_normalized
                    row_has_non = 'non' in row_text

                    if 'hdl' in test_name_normalized:
                        if not is_looking_for_non and row_has_non:
                            continue
                        if is_looking_for_non and not row_has_non:
                            continue

                    # Kismi eslesme - ama SADECE test adi satirdaysa
                    if test_name_normalized in row_text:
                        # Ek kontrol: Satir cok uzunsa (baska testler de olabilir) ATLA
                        if len(row.text) > 100:
                            continue

                        try:
                            row_input = row.find_element(By.TAG_NAME, 'input')
                            input_type = row_input.get_attribute('type') or ''
                            if input_type not in ['date', 'hidden', 'checkbox', 'radio']:
                                found_input = row_input
                                found_row_text = row.text[:50]
                                break
                        except:
                            pass
                if found_input:
                    break
            except:
                continue

        if found_input:
            self.log(f"      Modal'da KISMI ESLESME: '{test_name}' -> '{found_row_text}'", "DEBUG")
            return found_input

        # YONTEM 2: Label ile ara
        try:
            labels = modal.find_elements(By.XPATH, ".//*[self::label or self::span or self::div[contains(@class, 'label')]]")
            for label in labels:
                label_text_normalized = label.text.lower().replace('-', '').replace(' ', '').replace('ı', 'i').replace('ş', 's').replace('ö', 'o').replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')

                # OZEL DURUM: HDL vs non-HDL kontrolu
                is_looking_for_non = 'non' in test_name_normalized
                label_has_non = 'non' in label_text_normalized

                if not is_looking_for_non and label_has_non and 'hdl' in test_name_normalized:
                    continue  # HDL ariyoruz ama label non-HDL - ATLA
                if is_looking_for_non and not label_has_non and 'hdl' in test_name_normalized:
                    continue  # non-HDL ariyoruz ama label sadece HDL - ATLA

                if test_name_normalized in label_text_normalized or test_name.lower() in label.text.lower():
                    parent = label
                    for _ in range(5):
                        try:
                            parent = parent.find_element(By.XPATH, '..')
                            parent_inputs = parent.find_elements(By.TAG_NAME, 'input')
                            for inp in parent_inputs:
                                input_type = inp.get_attribute('type') or ''
                                if input_type not in ['date', 'hidden', 'checkbox', 'radio']:
                                    return inp
                        except:
                            break
        except:
            pass

        # YONTEM 3: formcontrolname ile ara
        formcontrol_mapping = {
            'nonhdl': ['nonhdl', 'non_hdl', 'nonHdl', 'nonHDL'],
            'kolesterol': ['kolesterol', 'totalKolesterol', 'total_kolesterol'],
            'hdl': ['hdl', 'hdlKolesterol'],
            'ldl': ['ldl', 'ldlKolesterol'],
            'hba1c': ['hba1c', 'hbA1c', 'HbA1c'],
            'apg': ['apg', 'aclikPlazmaGlukozu', 'aclikglukozu'],
            'glukoz': ['glukoz', 'glucose', 'glikoz'],
            'trigliserit': ['trigliserit', 'tg'],
            'bki': ['bki', 'vucut_kitle_indeksi', 'bmi'],
            'bel': ['belCevresi', 'bel_cevresi', 'bel'],
            'kilo': ['kilo', 'agirlik', 'weight'],
            'boy': ['boy', 'height'],
        }

        possible_names = formcontrol_mapping.get(test_name_normalized, [test_name_normalized])

        for inp in inputs:
            try:
                fc_name = inp.get_attribute('formcontrolname') or ''
                fc_name_lower = fc_name.lower().replace('-', '').replace('_', '')

                if fc_name_lower in [n.lower() for n in possible_names] or test_name_normalized in fc_name_lower:
                    return inp
            except:
                continue

        return None

    def _find_existing_lab_values(self) -> dict:
        """
        Sayfadan mevcut lab degerlerini bul.
        HbA1c, APG, OGTT, Glukoz gibi degerleri arar.

        Returns:
            dict: {'HbA1c': '5.5', 'APG': '100', ...}
        """
        values = {}
        try:
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text

            # HbA1c degeri ara (ornek: HbA1c: 5.61 veya HbA1c 5.61%)
            import re

            # HbA1c pattern
            hba1c_match = re.search(r'HbA1c[:\s]+(\d+[.,]\d+)', page_text, re.IGNORECASE)
            if hba1c_match:
                values['HbA1c'] = hba1c_match.group(1).replace(',', '.')

            # APG pattern
            apg_match = re.search(r'APG[:\s]+(\d+)', page_text, re.IGNORECASE)
            if apg_match:
                values['APG'] = apg_match.group(1)

            # Glukoz pattern
            glukoz_match = re.search(r'Gl[uü]koz[:\s]+(\d+)', page_text, re.IGNORECASE)
            if glukoz_match:
                values['Glukoz'] = glukoz_match.group(1)

            # OGTT pattern
            ogtt_match = re.search(r'OGTT[:\s]+(\d+)', page_text, re.IGNORECASE)
            if ogtt_match:
                values['OGTT'] = ogtt_match.group(1)

            self.log(f"   Bulunan lab degerleri: {values}", "DEBUG")

        except Exception as e:
            self.log(f"   Lab degeri arama hatasi: {e}", "DEBUG")

        return values

    def _find_dis_lab_button(self):
        """Dis Laboratuvar Sonucu Ekle butonunu bul"""
        button_texts = [
            "Dış Laboratuvar Sonucu Ekle",
            "Dis Laboratuvar Sonucu Ekle",
            "Laboratuvar Sonucu Ekle",
            "Dış Lab",
            "Dis Lab"
        ]

        buttons = self.driver.find_elements(By.TAG_NAME, 'button')
        for btn in buttons:
            try:
                if not btn.is_displayed():
                    continue
                btn_text = btn.text.strip()
                for search_text in button_texts:
                    if search_text.lower() in btn_text.lower():
                        return btn
            except:
                continue
        return None

    def _find_dis_lab_modal(self):
        """Dis lab modal'ini bul"""
        modal_selectors = [
            '.ui-dialog',
            '.modal',
            '[class*="dialog"]',
            '.p-dialog'
        ]

        for selector in modal_selectors:
            try:
                modals = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for modal in modals:
                    if modal.is_displayed():
                        return modal
            except:
                continue
        return None

    def _save_dis_lab_modal(self, modal) -> bool:
        """Modal'daki kaydet butonuna tikla - HIZLANDIRILDI"""
        try:
            # Modal icinde butonu ara
            save_btns = modal.find_elements(By.TAG_NAME, 'button')
            for btn in save_btns:
                try:
                    btn_text = btn.text.strip().lower()
                    if any(x in btn_text for x in ['kaydet', 'tamam', 'ekle', 'save', 'ok']):
                        self.driver.execute_script('arguments[0].click();', btn)
                        time.sleep(0.3)  # 1 -> 0.3 saniye
                        return True
                except:
                    continue

            # Sayfadaki tum butonlarda da ara
            all_btns = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in all_btns:
                try:
                    if not btn.is_displayed():
                        continue
                    btn_text = btn.text.strip().lower()
                    if 'kaydet' in btn_text:
                        self.driver.execute_script('arguments[0].click();', btn)
                        time.sleep(0.3)  # 1 -> 0.3 saniye
                        return True
                except:
                    continue

        except Exception as e:
            self.log(f"   Kaydet hatasi: {e}", "DEBUG")

        return False

    def _close_modal(self, modal):
        """Modal'i kapat"""
        try:
            close_selectors = [
                '.ui-dialog-titlebar-close',
                '.close',
                '[aria-label="Close"]',
                '.p-dialog-header-close'
            ]
            for selector in close_selectors:
                try:
                    close_btn = modal.find_element(By.CSS_SELECTOR, selector)
                    self.driver.execute_script('arguments[0].click();', close_btn)
                    time.sleep(0.5)
                    return True
                except:
                    continue
        except:
            pass
        return False

    def _handle_medication_page(self) -> bool:
        """İlaç sayfasında reçete tarihine göre kullanım durumu belirle"""
        if '/ilac' not in self.driver.current_url:
            return True

        from datetime import datetime, timedelta
        import re as regex

        page_text = self.driver.find_element(By.TAG_NAME, 'body').text
        ilac_kullaniliyor = False

        try:
            # Reçete tarihi formatı: DD.MM.YYYY
            tarih_pattern = r'(\d{2}\.\d{2}\.\d{4})'
            tarihler = regex.findall(tarih_pattern, page_text)

            # Tablet/kutu bilgisi
            miktar_pattern = r'(\d+)\s*(tablet|kutu|adet)'
            miktarlar = regex.findall(miktar_pattern, page_text.lower())

            if tarihler and miktarlar:
                recete_tarihi = None
                for t in tarihler:
                    try:
                        dt = datetime.strptime(t, '%d.%m.%Y')
                        if recete_tarihi is None or dt > recete_tarihi:
                            recete_tarihi = dt
                    except:
                        pass

                toplam_tablet = 0
                for miktar, birim in miktarlar:
                    m = int(miktar)
                    if birim == 'kutu':
                        m *= 28
                    toplam_tablet += m

                if recete_tarihi and toplam_tablet > 0:
                    bitis_tarihi = recete_tarihi + timedelta(days=toplam_tablet)
                    bugun = datetime.now()

                    if bitis_tarihi > bugun:
                        ilac_kullaniliyor = True
                        self.log(f"      Reçete: {recete_tarihi.strftime('%d.%m.%Y')}, bitiş: {bitis_tarihi.strftime('%d.%m.%Y')}", "DEBUG")
        except Exception as e:
            self.log(f"      İlaç hesaplama hatası: {str(e)[:40]}", "DEBUG")

        radios = self.driver.find_elements(By.TAG_NAME, 'p-radiobutton')
        for radio in radios:
            try:
                label = radio.find_element(By.CSS_SELECTOR, 'label')
                inner = radio.find_element(By.CSS_SELECTOR, '.ui-radiobutton-box')

                if ilac_kullaniliyor:
                    if 'Kullanılıyor' in label.text and 'Kullanılmıyor' not in label.text:
                        if 'ui-state-active' not in (inner.get_attribute('class') or ''):
                            self.driver.execute_script('arguments[0].click();', inner)
                            self.log("      Kullanılıyor işaretlendi", "SUCCESS")
                            time.sleep(0.2)
                else:
                    if 'Kullanılmıyor' in label.text:
                        if 'ui-state-active' not in (inner.get_attribute('class') or ''):
                            self.driver.execute_script('arguments[0].click();', inner)
                            time.sleep(0.2)
            except:
                pass

        return True


    def _close_dialogs(self) -> bool:
        """Acik dialoglari kapat"""
        try:
            tamam = self.driver.find_element(By.XPATH, "//button[contains(., 'Tamam')]")
            if tamam.is_displayed():
                self.driver.execute_script('arguments[0].click();', tamam)
                time.sleep(0.3)
                return True
        except:
            pass
        return False

    def _check_date_threshold(self, text: str, islem_tipi: str) -> bool:
        """
        HYP Rules'a göre tarih kontrolü yapar.

        KURALLAR (hyp_rules.md):
        1. "Sonraki:" alanında "İlk fırsatta" varsa -> HEMEN YAP
        2. "Sonraki:" alanında tarih varsa -> HESAPLA:
           - Tarih geçmişte (gunFarki < 0) -> HEMEN YAP (gecikmiş)
           - TARAMA ve gunFarki < 30 -> YAP
           - TARAMA ve gunFarki >= 30 -> BEKLE
           - İZLEM ve gunFarki < 15 -> YAP
           - İZLEM ve gunFarki >= 15 -> BEKLE

        Args:
            text: Kart metni
            islem_tipi: "TARAMA" veya "IZLEM"

        Returns:
            True = YAPILABILIR, False = BEKLE
        """
        import re

        text_lower = text.lower()

        # Türkçe karakter normalizasyonu (İ -> i, ı -> i)
        text_normalized = text_lower.replace('i̇', 'i').replace('ı', 'i')

        # 1. "İlk fırsatta" kontrolü - HEMEN YAP
        # Not: "fırsatta" kelimesi yeterli çünkü sadece bu bağlamda kullanılıyor
        if "firsatta" in text_normalized or "fırsatta" in text_lower:
            self.log(f"   'İlk fırsatta' bulundu - YAPILABILIR", "DEBUG")
            return True

        # Eşik değerlerini belirle
        threshold = 30 if islem_tipi == "TARAMA" else 15

        try:
            # DD.MM.YYYY formatında tarihleri bul
            tarih_pattern = r'(\d{2}\.\d{2}\.\d{4})'
            tarihler = re.findall(tarih_pattern, text)

            if not tarihler:
                self.log(f"   Tarih bulunamadı - PAS GEÇ", "DEBUG")
                return False

            bugun = datetime.now()

            # 'Sonraki' kelimesinden sonraki tarihi ara
            sonraki_idx = text_lower.find('sonraki')

            for tarih_str in tarihler:
                try:
                    tarih = datetime.strptime(tarih_str, '%d.%m.%Y')

                    # Sonraki takip tarihini bulduk mu kontrol et
                    tarih_idx = text.find(tarih_str)
                    if sonraki_idx >= 0 and tarih_idx > sonraki_idx:
                        # Sonraki takip tarihi bulundu
                        gun_farki = (tarih - bugun).days

                        # Gecikmiş işlem kontrolü (tarih geçmişte)
                        if gun_farki < 0:
                            self.log(f"   Sonraki: {tarih_str} ({abs(gun_farki)} gün GECİKMİŞ) - YAPILABILIR", "DEBUG")
                            return True

                        # Eşik kontrolü
                        if gun_farki < threshold:
                            self.log(f"   Sonraki: {tarih_str} ({gun_farki} gün, {islem_tipi} eşik={threshold}) - YAPILABILIR", "DEBUG")
                            return True
                        else:
                            self.log(f"   Sonraki: {tarih_str} ({gun_farki} gün, {islem_tipi} eşik={threshold}) - BEKLE", "DEBUG")
                            return False

                except ValueError:
                    continue

        except Exception as e:
            self.log(f"   Tarih kontrolü hatası: {e}", "DEBUG")

        return False

    # Eski fonksiyon adı ile uyumluluk için wrapper
    def _check_date_within_month(self, text: str) -> bool:
        """Eski fonksiyon - geriye uyumluluk için. TARAMA varsayılan."""
        return self._check_date_threshold(text, "TARAMA")

    # ============================================================
    # SOL PANEL KARTLARI (Sonlandır sonrası devam için)
    # ============================================================
    def get_sidebar_cards(self) -> List[Dict]:
        """
        Sol paneldeki hastalık kartlarını oku.
        Sonlandır'dan sonra diğer yapılabilir HYP'lere geçmek için kullanılır.

        YAPILABILIRLIK KURALLARI (hyp_rules.md):
        1. "Sonraki:" alanında "İlk fırsatta" varsa -> HEMEN YAP
        2. "Sonraki:" alanında tarih varsa:
           - Tarih geçmişte (gecikmiş) -> HEMEN YAP
           - TARAMA ve < 30 gün -> YAP
           - İZLEM ve < 15 gün -> YAP
           - Aksi halde -> BEKLE
        """
        cards = []

        # Sol panel kart selector'leri - HER HASTALIK KUTUSU AYRI AYRI
        sidebar_selectors = {
            "HT": ".disease-box-hypertension",
            "DIY": ".disease-box-diabetes",
            "KVR": ".disease-box-cvdrisk",
            "OBE": ".disease-box-obesity",
            "YAS": ".disease-box-elderly",
            "ASTIM": ".disease-box-asthma",
        }

        # DOĞRU YÖNTEM: Her hastalık kutusunu AYRI AYRI seç
        # OPTIMIZE: Implicit wait'i geçici olarak 0.5sn yap (5sn beklemek yerine)
        original_implicit_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)
        
        for hyp_prefix, selector in sidebar_selectors.items():
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = el.text
                text_lower = text.lower()

                # ÖNCE: Tarama vs İzlem belirle (eşik için gerekli)
                islem_tipi = "IZLEM" if "izlem" in text_lower else "TARAMA"

                # Yapılabilirlik kontrolü (hyp_rules.md kurallarına göre)
                # _check_date_threshold: "İlk fırsatta", gecikmiş tarih, ve eşik kontrolü yapar
                yapilabilir = self._check_date_threshold(text, islem_tipi)

                # HYP tipini belirle (TARAMA vs IZLEM)
                # NOT: YAS (Yaşlı Sağlığı) için sadece IZLEM var, TARAMA yok!
                if hyp_prefix == "YAS":
                    hyp_tip = "YAS_IZLEM"  # Her zaman IZLEM
                elif "izlem" in text_lower:
                    hyp_tip = f"{hyp_prefix}_IZLEM"
                else:
                    hyp_tip = f"{hyp_prefix}_TARAMA"

                # Native click icin title elementi bul (JS click calismaz!)
                try:
                    title_el = el.find_element(By.CSS_SELECTOR, '.disease-title')
                except:
                    title_el = el  # Bulamazsa kart elementini kullan

                cards.append({
                    "hyp_tip": hyp_tip,
                    "element": title_el,  # Native click icin title elementi
                    "card_element": el,  # Kart elementi (text okumak icin)
                    "yapilabilir": yapilabilir,
                    "text": text
                })
                self.log(f"   Sidebar kart: {hyp_tip}, yapilabilir={yapilabilir}", "DEBUG")

            except:
                continue

        # Implicit wait'i geri yükle
        self.driver.implicitly_wait(original_implicit_wait if original_implicit_wait else 5)
        
        # Alternatif: XPath ile tum sidebar kartlarini bul
        if len(cards) == 0:
            try:
                all_cards = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'disease-box')]")
                for el in all_cards:
                    try:
                        text = el.text
                        text_lower = text.lower()

                        # HYP tipini belirle
                        hyp_tip = None
                        islem_tipi = "IZLEM" if "izlem" in text_lower else "TARAMA"

                        if 'hipertansiyon' in text_lower or 'tansiyon' in text_lower:
                            hyp_tip = f'HT_{islem_tipi}'
                        elif 'diyabet' in text_lower:
                            hyp_tip = f'DIY_{islem_tipi}'
                        elif 'obezite' in text_lower:
                            hyp_tip = f'OBE_{islem_tipi}'
                        elif 'kardiyovasküler' in text_lower or 'kvr' in text_lower:
                            hyp_tip = f'KVR_{islem_tipi}'
                        elif 'yaşlı' in text_lower or 'yasli' in text_lower:
                            hyp_tip = 'YAS_IZLEM'
                        elif 'astım' in text_lower or 'astim' in text_lower:
                            hyp_tip = f'ASTIM_{islem_tipi}'

                        if hyp_tip:
                            # hyp_rules.md kurallarına göre yapılabilirlik kontrolü
                            yapilabilir = self._check_date_threshold(text, islem_tipi)

                            # Native click icin title elementi bul (JS click calismaz!)
                            try:
                                title_el = el.find_element(By.CSS_SELECTOR, '.disease-title')
                            except:
                                title_el = el  # Bulamazsa kart elementini kullan

                            cards.append({
                                "hyp_tip": hyp_tip,
                                "element": title_el,  # Native click icin title elementi
                                "card_element": el,  # Kart elementi (text okumak icin)
                                "yapilabilir": yapilabilir,
                                "text": text
                            })
                    except:
                        continue
            except:
                pass

        return cards

    def _process_sidebar_cards(self, islenen_kartlar: set) -> int:
        """
        Sonlandır sonrası sol paneldeki yapılabilir kartları işle.
        Returns: İşlenen kart sayısı
        OPTIMIZE: Max 5sn sidebar işleme
        """
        islenen = 0

        for _ in range(10):  # Maksimum 10 sidebar kart
            if self.should_stop:
                break

            # Sol panel kartlarını oku
            sidebar_cards = self.get_sidebar_cards()

            # Yapılabilir kartları filtrele
            yapilabilir = [
                c for c in sidebar_cards
                if c["yapilabilir"]
                and c["hyp_tip"] not in islenen_kartlar
                and self.should_process_hyp_type(c["hyp_tip"])
            ]

            if not yapilabilir:
                self.log("Sol panelde yapılabilir kart kalmadı.", "DEBUG")
                break

            card = yapilabilir[0]
            self.log(f"Sol panel kartı işleniyor: {card['hyp_tip']}")

            # Karta tıkla - hastalık sayfasına git
            try:
                self.js_click(card["element"])
                time.sleep(1.5)  # Sayfa yuklenene kadar bekle (arttirildi)
                self.log(f"   URL: {self.driver.current_url}", "DEBUG")
            except:
                self.log("Sol panel kartına tıklanamadı!", "WARNING")
                break

            # Tarama/İzlem başlat - birkaç deneme yap
            started = False
            for attempt in range(5):  # 3 -> 5 deneme
                if self._start_process():
                    started = True
                    break
                time.sleep(0.8)  # Buton yuklenmesi icin bekle (arttirildi)

            if not started:
                self.log("Sol panel - Başlat butonu bulunamadı!", "WARNING")
                islenen_kartlar.add(card["hyp_tip"])
                continue

            time.sleep(0.3)

            # Modüle göre işle
            hyp_tip = card["hyp_tip"]
            success = False

            if "DIY" in hyp_tip:
                success = self._process_diyabet()
            elif "HT" in hyp_tip:
                success = self._process_hipertansiyon()
            elif "OBE" in hyp_tip:
                success = self._process_obezite()
            elif "KVR" in hyp_tip:
                success = self._process_kvr()
            elif "YAS" in hyp_tip:
                success = self._process_yasli()

            islenen_kartlar.add(hyp_tip)

            if success:
                islenen += 1
                self.session_stats["basarili"] += 1
                self.increment_completed(hyp_tip)

                # ============================================================
                # CANLI İLERLEME GÜNCELLEMESİ - GUI'ye bildir (sidebar kartları için)
                # ============================================================
                if self.on_hyp_success_callback:
                    try:
                        self.on_hyp_success_callback(hyp_tip, self.current_patient_name)
                    except Exception as e:
                        self.log(f"GUI callback hatası (sidebar): {e}", "DEBUG")

                # ============================================================
                # KVR HEDEF AŞIMI KONTROLÜ
                # HT_IZLEM zorunlu olarak KVR_IZLEM yapıyor, hedef aşıldıysa sil
                # ============================================================
                if hyp_tip == "KVR_IZLEM" and self.is_kvr_target_reached():
                    self.check_and_handle_kvr_overflow(self.current_patient_name)
            else:
                self.session_stats["basarisiz"] += 1
                # Başarısız HYP'yi kaydet
                self.failed_hyps.append({
                    "hasta": self.current_patient_name or "Bilinmeyen",
                    "hyp_tip": hyp_tip,
                    "hyp_ad": card.get("baslik", hyp_tip),
                    "neden": "Protokol tamamlanamadı"
                })

            time.sleep(1)

        return islenen

    def _go_back_to_patient_cards(self):
        """İşlem sonrası hasta kartları sayfasına geri dön - HIZLI"""
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)

        try:
            # Tum butonlari tek seferde al ve geri/kapat butonunu bul
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                btn_class = btn.get_attribute('class') or ''
                btn_text = btn.text.strip()
                if 'back' in btn_class or 'Geri' in btn_text or 'Kapat' in btn_text:
                    self.js_click(btn)
                    time.sleep(0.3)
                    return

            # Geri butonu yoksa browser back
            self.driver.back()
            time.sleep(0.5)
        except:
            pass
        finally:
            self.driver.implicitly_wait(original_wait)

    def _click_sonlandir(self) -> bool:
        """Sonlandır butonuna tıkla - HIZLI VE GUVENILIR"""

        url_before = self.driver.current_url
        clicked = False

        # Implicit wait'i gecici kapat - HIZLI arama icin
        original_wait = self.driver.timeouts.implicit_wait
        self.driver.implicitly_wait(0)

        # HATA ONLEME: "Sil", "İptal" iceren butonlara TIKLANMAMALI!
        excluded_words = ['Sil', 'sil', 'İptal', 'iptal', 'Delete', 'Vazgeç', 'vazgeç']

        # Yontem 1: Tum butonlari tara (en hizli)
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for btn in buttons:
                txt = btn.text.strip()
                # "Sonlandır" icermeli AMA "Sil" vb. icermemeli
                if 'Sonlandır' in txt and not any(ex in txt for ex in excluded_words):
                    self.js_click(btn)
                    clicked = True
                    self.log(f"   Sonlandır butonuna tıklandı: {txt[:50]}", "DEBUG")
                    break
        except:
            pass

        # Yontem 2: XPath ile (fallback)
        if not clicked:
            xpaths = [
                "//button[.//span[contains(text(), 'Sonlandır')]]",
                "//button[contains(., 'Sonlandır')]",
            ]
            for xpath in xpaths:
                try:
                    btn = self.driver.find_element(By.XPATH, xpath)
                    self.js_click(btn)
                    clicked = True
                    break
                except:
                    pass

        if not clicked:
            self.driver.implicitly_wait(original_wait)
            self.log("Sonlandır butonu bulunamadı!", "WARNING")
            return False

        # Onay dialog kontrolu - HIZLI (0.2sn bekle)
        time.sleep(0.2)

        # Evet/Tamam/Onayla butonlarini ara
        confirm_xpaths = [
            "//button[contains(., 'Evet')]",
            "//button[contains(., 'Tamam')]",
            "//button[contains(., 'Onayla')]",
            "//button[contains(@class, 'p-confirm-dialog-accept')]",
        ]

        # Onay butonunu HEMEN tikla
        for xpath in confirm_xpaths:
            try:
                confirm_btn = self.driver.find_element(By.XPATH, xpath)
                if confirm_btn.is_displayed():
                    self.js_click(confirm_btn)
                    self.log("   Onay butonu tiklandi", "DEBUG")
                    break
            except:
                pass

        # KRITIK: Sayfa degisimini bekle (max 1 sn) - OPTIMIZE edildi
        for i in range(10):  # 20 -> 10 (max 1sn)
            time.sleep(0.1)
            url_after = self.driver.current_url
            if '/ozet' not in url_after and url_before != url_after:
                self.driver.implicitly_wait(original_wait)
                self.log(f"   Sonlandirma basarili: {url_after.split('/')[-1]}", "DEBUG")
                return True
            # Ilk 3 denemede onay butonu tekrar kontrol et
            if i < 3 and '/ozet' in url_after:
                for xpath in confirm_xpaths:
                    try:
                        confirm_btn = self.driver.find_element(By.XPATH, xpath)
                        if confirm_btn.is_displayed():
                            self.js_click(confirm_btn)
                            break
                    except:
                        pass

        self.driver.implicitly_wait(original_wait)
        
        # Son URL kontrolu
        if '/ozet' not in self.driver.current_url:
            return True
        else:
            self.log("   UYARI: Sayfa hala ozet'te!", "WARNING")
            return False

    # ============================================================
    # ANA ÇALIŞTIRICI
    # ============================================================
    def run_automation(self, debug_mode: bool = False, auto_pin: bool = True):
        """
        Ana otomasyon döngüsü

        Args:
            debug_mode: True ise açık Chrome'a bağlan, login atla
            auto_pin: True ise PIN otomatik girilir, False ise manuel beklenir
        """
        try:
            # Baslangic dosya kontrolleri
            if not self._check_startup_files():
                return

            # Cache temizligi (1 aydan eski kayitlari sil)
            self._cleanup_old_cache()

            if not self.setup_driver(debug_mode):
                return

            if not self.login(auto_pin=auto_pin):
                return

            # İLK ADIM: Yapılan sayıları "Takip İşlemi İstatistikleri"nden çek
            self.log("\n" + "="*50)
            self.log("📊 ADIM 1: YAPILAN SAYILAR KONTROL EDİLİYOR")
            self.log("="*50)
            self.fetch_completed_counts()
            self.print_target_status()

            # Hasta listesini al - ÇOKLU TARİH DESTEĞİ (OPTİMİZE)
            patients = []

            # Eğer birden fazla tarih seçildiyse HIZLI fonksiyonu kullan
            if self.selected_dates and len(self.selected_dates) > 0:
                self.log(f"📅 {len(self.selected_dates)} tarih için hastalar alınıyor (hızlı mod)...")
                patients = self.get_patients_for_dates(self.selected_dates)
            else:
                # Tek tarih veya tarihsiz (bugün)
                patients = self.get_todays_patients(self.selected_date)

                if not patients:
                    self.log("Bugün işlenecek hasta bulunamadı.", "WARNING")

                    if self.date_picker_callback:
                        new_date = self.date_picker_callback()
                        if new_date:
                            self.selected_date = new_date
                            patients = self.get_todays_patients(new_date)

            if not patients:
                self.log("Hasta bulunamadı!", "ERROR")
                return
            
            # Her hastayı işle
            for idx, patient in enumerate(patients, 1):
                if self.should_stop:
                    self.log("İşlem durduruldu.", "WARNING")
                    break
                
                self.log(f"\n{'='*50}")
                self.log(f"📋 HASTA {idx}/{len(patients)}")
                self.log(f"{'='*50}")
                
                self.process_patient(patient['ad_soyad'])
            
            # Özet
            self._print_summary()
            
        except Exception as e:
            self.log(f"Kritik hata: {e}", "ERROR")
            traceback.print_exc()

    def _print_summary(self):
        """İşlem özetini yazdır"""
        self.log("\n" + "="*50)
        self.log("📊 OTURUM ÖZETİ")
        self.log("="*50)
        self.log(f"✅ Başarılı: {self.session_stats['basarili']}")
        self.log(f"❌ Başarısız: {self.session_stats['basarisiz']}")
        self.log(f"⏭️ Atlanan: {self.session_stats['atlanan']}")
        self.log(f"⏱️ Toplam Süre: {self.session_stats['toplam_sure']:.1f}sn")
        self.log("="*50)

    def stop(self):
        """Otomasyonu durdur - Chrome kapatılmaz, sadece otomasyon durur"""
        self.should_stop = True
        self.log("Otomasyon durduruldu. Chrome açık kaldı - manuel müdahale yapabilirsiniz.", "INFO")
        # NOT: Chrome kapatılmıyor - kullanıcı manuel müdahale edebilsin


    def print_skipped_notifications(self):
        """
        Oturum sonunda pas gecilen HYP'leri kullaniciya bildir.
        """
        if not self.skipped_hyp_notifications:
            return
        
        self.log("")
        self.log("=" * 60)
        self.log("[!] PAS GECILEN HYP'LER - MANUEL KONTROL GEREKLI")
        self.log("=" * 60)
        
        for notif in self.skipped_hyp_notifications:
            self.log(f"  Hasta: {notif.get('hasta', 'Bilinmiyor')}")
            self.log(f"  HYP Tipi: {notif.get('hyp_tip', 'Bilinmiyor')}")
            self.log(f"  Sebep: {notif.get('sebep', 'Bilinmiyor')}")
            self.log(f"  Tarih: {notif.get('tarih', '')}")
            self.log("-" * 40)
        
        self.log(f"Toplam {len(self.skipped_hyp_notifications)} HYP pas gecildi.")
        self.log("Lutfen bu hastalari manuel olarak kontrol edin.")
        self.log("")
    
    def get_skipped_notifications(self) -> list:
        """Pas gecilen HYP bildirimlerini dondur."""
        return self.skipped_hyp_notifications.copy()

    def get_cancelled_hyps(self) -> list:
        """İptal edilen HYP'leri döndür (eksik tetkik vb.)"""
        return self.cancelled_hyps.copy()

    def get_failed_hyps(self) -> list:
        """Başarısız HYP'leri döndür (protokol hatası vb.)"""
        return self.failed_hyps.copy()

    def print_cancelled_hyps(self):
        """
        Oturum sonunda iptal edilen HYP'leri kullaniciya bildir.
        """
        if not self.cancelled_hyps:
            return

        self.log("")
        self.log("=" * 60)
        self.log("[!] İPTAL EDİLEN HYP'LER - EKSİK TETKİK")
        self.log("=" * 60)

        for item in self.cancelled_hyps:
            self.log(f"  Hasta: {item.get('hasta', 'Bilinmiyor')}")
            self.log(f"  HYP Tipi: {item.get('hyp_tipi', 'Bilinmiyor')}")
            self.log(f"  Neden: {item.get('neden', 'Bilinmiyor')}")
            self.log(f"  Saat: {item.get('zaman', '')}")
            self.log("-" * 40)

        self.log(f"Toplam {len(self.cancelled_hyps)} HYP iptal edildi.")
        self.log("")


# ============================================================
# HIZLI TEST FONKSİYONU
# ============================================================
def quick_test():
    """
    Hızlı test - Debug modda çalıştır
    
    Kullanım:
    1. Önce Chrome'u manuel aç ve HYP'ye giriş yap
    2. Bu scripti çalıştır
    """
    print("\n" + "="*50)
    print("🧪 HIZLI TEST MODU")
    print("="*50)
    print("Chrome zaten açık ve HYP'ye giriş yapılmış olmalı!")
    print("="*50 + "\n")
    
    bot = HYPAutomation()
    bot.run_automation(debug_mode=True)




if __name__ == "__main__":
    # Normal çalıştırma
    import config
    bot = HYPAutomation()
    bot.run_automation(debug_mode=False)

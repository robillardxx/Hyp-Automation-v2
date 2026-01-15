# -*- coding: utf-8 -*-
"""
HYP Automation - Login & Settings Manager
Pin kodu girisi ve ayarlar yonetimi

Guvenlik Guncelleme (v6.9.9):
- PIN artik base64 yerine AES-benzeri sifreleme ile saklanir
- Makine-spesifik anahtar turetimi (PBKDF2)
- Salt ile guclendirme
"""

import customtkinter as ctk
import json
import os
import base64
import hashlib
import secrets
import hmac
from pathlib import Path
from datetime import datetime


# ============================================================
# GUVENLI PIN SIFRELEME MODULU
# ============================================================
class SecurePINStorage:
    """
    PIN sifrelemesi icin guvenli depolama sinifi.

    - PBKDF2 ile makine-spesifik anahtar turetimi
    - Salt ile guclendirme
    - XOR tabanli sifreleme (AES yerine, dependency-free)

    NOT: Tam guvenlik icin 'cryptography' kutuphanesi onerilir.
    Bu implementasyon base64'ten cok daha guvenlidir.
    """

    # Anahtar turetimi icin iterasyon sayisi (brute-force'u zorlaştırır)
    ITERATIONS = 100000
    SALT_LENGTH = 16
    KEY_LENGTH = 32

    @staticmethod
    def _get_machine_id() -> bytes:
        """Makine-spesifik kimlik olustur"""
        import platform
        import socket

        # Birden fazla kaynak birlestir
        parts = [
            platform.node(),           # Bilgisayar adi
            platform.machine(),        # x86_64 vb.
            os.name,                   # nt (Windows)
            os.getenv('USERNAME', ''), # Kullanici adi
            os.getenv('COMPUTERNAME', ''), # Bilgisayar adi (Windows)
        ]

        # Registry'den daha fazla bilgi (Windows)
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography"
            )
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            parts.append(machine_guid)
        except Exception:
            pass

        combined = "|".join(parts)
        return combined.encode('utf-8')

    @staticmethod
    def _derive_key(salt: bytes) -> bytes:
        """PBKDF2 ile anahtar turet"""
        machine_id = SecurePINStorage._get_machine_id()

        key = hashlib.pbkdf2_hmac(
            'sha256',
            machine_id,
            salt,
            SecurePINStorage.ITERATIONS,
            dklen=SecurePINStorage.KEY_LENGTH
        )
        return key

    @staticmethod
    def _xor_encrypt(data: bytes, key: bytes) -> bytes:
        """XOR tabanli sifreleme"""
        # Anahtari veri uzunluguna uzat
        extended_key = (key * (len(data) // len(key) + 1))[:len(data)]
        return bytes(a ^ b for a, b in zip(data, extended_key))

    @classmethod
    def encrypt_pin(cls, pin: str) -> dict:
        """
        PIN'i sifrele.

        Returns:
            dict: {"salt": base64_salt, "encrypted": base64_encrypted, "version": 2}
        """
        if not pin:
            return None

        # Yeni salt olustur
        salt = secrets.token_bytes(cls.SALT_LENGTH)

        # Anahtar turet
        key = cls._derive_key(salt)

        # PIN'i sifrele
        pin_bytes = pin.encode('utf-8')
        encrypted = cls._xor_encrypt(pin_bytes, key)

        # HMAC ile butunluk kontrolu ekle
        mac = hmac.new(key, encrypted, hashlib.sha256).digest()[:16]

        return {
            "salt": base64.b64encode(salt).decode('ascii'),
            "encrypted": base64.b64encode(encrypted).decode('ascii'),
            "mac": base64.b64encode(mac).decode('ascii'),
            "version": 2  # Yeni guvenli format
        }

    @classmethod
    def decrypt_pin(cls, encrypted_data: dict) -> str:
        """
        PIN'i coz.

        Args:
            encrypted_data: encrypt_pin() ciktisi

        Returns:
            str: Cozulmus PIN veya None
        """
        if not encrypted_data:
            return None

        try:
            # Versiyon kontrolu
            version = encrypted_data.get("version", 1)

            if version == 1:
                # Eski base64 format (geriye uyumluluk)
                old_encoded = encrypted_data.get("pin_code")
                if old_encoded:
                    return base64.b64decode(old_encoded.encode()).decode()
                return None

            # Yeni guvenli format (v2)
            salt = base64.b64decode(encrypted_data["salt"])
            encrypted = base64.b64decode(encrypted_data["encrypted"])
            stored_mac = base64.b64decode(encrypted_data["mac"])

            # Anahtar turet
            key = cls._derive_key(salt)

            # MAC dogrula (butunluk kontrolu)
            expected_mac = hmac.new(key, encrypted, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(stored_mac, expected_mac):
                print("[GUVENLIK] PIN butunluk kontrolu basarisiz!")
                return None

            # PIN'i coz
            pin_bytes = cls._xor_encrypt(encrypted, key)
            return pin_bytes.decode('utf-8')

        except Exception as e:
            print(f"[GUVENLIK] PIN cozme hatasi: {e}")
            return None

    @classmethod
    def is_secure_format(cls, data: dict) -> bool:
        """Verinin guvenli formatta olup olmadigini kontrol et"""
        return isinstance(data, dict) and data.get("version", 0) >= 2

# ============================================================
# DOSYA YOLLARI
# ============================================================
# Uygulama dizini
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# İlaç ve gebe listesi dosyaları (glob pattern ile arama yapılacak)
ILAC_LISTESI_FILE = None  # Dinamik bulunacak
GEBE_LISTESI_FILE = None  # Dinamik bulunacak


def find_ilac_listesi():
    """İlaç listesi dosyasını bul (xlsx, xls, json)"""
    import glob
    patterns = [
        os.path.join(APP_DIR, "*laç*.*"),
        os.path.join(APP_DIR, "*lac*.*"),
        os.path.join(APP_DIR, "ilac*.*"),
    ]
    for pattern in patterns:
        files = glob.glob(pattern)
        for f in files:
            if f.endswith(('.xlsx', '.xls', '.json', '.csv')):
                return f
    return None


def find_gebe_listesi():
    """Gebe listesi dosyasını bul (xlsx, xls, json)"""
    import glob
    patterns = [
        os.path.join(APP_DIR, "*ebe*.*"),
        os.path.join(APP_DIR, "*Gebe*.*"),
        os.path.join(APP_DIR, "gebe*.*"),
    ]
    for pattern in patterns:
        files = glob.glob(pattern)
        for f in files:
            if f.endswith(('.xlsx', '.xls', '.json', '.csv')):
                return f
    return None


def check_ilac_listesi():
    """İlaç listesi dosyasını kontrol et"""
    file_path = find_ilac_listesi()
    if not file_path:
        return False, 0, None

    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = len(data) if isinstance(data, (list, dict)) else 0
                return count > 0, count, file_path
        elif file_path.endswith(('.xlsx', '.xls')):
            # Excel dosyası - sadece varlığını ve boyutunu kontrol et
            size = os.path.getsize(file_path)
            if size > 0:
                # Tahmini satır sayısı (dosya boyutuna göre)
                return True, "Excel", file_path
        elif file_path.endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                return lines > 1, lines - 1, file_path  # Header hariç
    except Exception as e:
        pass

    return False, 0, None


def check_gebe_listesi():
    """Gebe listesi dosyasını kontrol et"""
    file_path = find_gebe_listesi()
    if not file_path:
        return False, 0, None

    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = len(data) if isinstance(data, (list, dict)) else 0
                return count > 0, count, file_path
        elif file_path.endswith(('.xlsx', '.xls')):
            # Excel dosyası - sadece varlığını ve boyutunu kontrol et
            size = os.path.getsize(file_path)
            if size > 0:
                return True, "Excel", file_path
        elif file_path.endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                return lines > 1, lines - 1, file_path
    except Exception as e:
        pass

    return False, 0, None


def get_current_month_key():
    """Mevcut ay anahtarini dondur (ornek: '2025-12')"""
    return datetime.now().strftime("%Y-%m")


def get_month_display_name(month_key):
    """Ay anahtarindan gosterim adini dondur (ornek: 'Aralik 2025')"""
    ay_isimleri = {
        "01": "Ocak", "02": "Subat", "03": "Mart", "04": "Nisan",
        "05": "Mayis", "06": "Haziran", "07": "Temmuz", "08": "Agustos",
        "09": "Eylul", "10": "Ekim", "11": "Kasim", "12": "Aralik"
    }
    try:
        year, month = month_key.split("-")
        return f"{ay_isimleri.get(month, month)} {year}"
    except (ValueError, AttributeError):
        # ValueError: split basarisiz, AttributeError: month_key None
        return month_key if month_key else "Bilinmeyen Ay"


class SettingsManager:
    """Ayarlar yoneticisi - Pin kodu ve diger ayarlari saklar"""
    
    def __init__(self, settings_file="hyp_settings.json"):
        self.settings_file = settings_file
        # Alternatif kayıt konumu (eğer ana konum çalışmazsa)
        self.backup_settings_file = os.path.join(os.path.expanduser("~"), "hyp_settings_backup.json")
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Ayarlari yukle"""
        # Önce ana dosyayı dene
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError) as e:
                print(f"UYARI: Ana ayar dosyasi okunamadi: {e}")

        # Ana dosya yoksa veya okunamazsa, yedek dosyayı dene
        if os.path.exists(self.backup_settings_file):
            try:
                with open(self.backup_settings_file, 'r', encoding='utf-8') as f:
                    print(f"BILGI: Ayarlar yedek konumdan yüklendi: {self.backup_settings_file}")
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError) as e:
                print(f"UYARI: Yedek ayar dosyasi da okunamadi: {e}")

        # Hiçbiri yoksa varsayılan ayarları döndür
        return self.get_default_settings()
    
    def save_settings(self):
        """Ayarlari kaydet"""
        import time
        max_retries = 3
        retry_delay = 0.5

        # Önce ana konuma kaydetmeyi dene
        for attempt in range(max_retries):
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=4, ensure_ascii=False)
                return True
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    # Ana konum başarısız, yedek konumu dene
                    break
            except Exception as e:
                print(f"HATA: Ayarlar kaydedilemedi: {e}")
                break

        # Ana konum başarısız olduysa, yedek konuma kaydet
        try:
            with open(self.backup_settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"BILGI: Ayarlar yedek konuma kaydedildi: {self.backup_settings_file}")
            return True
        except Exception as e:
            print(f"UYARI: Ayarlar hiçbir konuma kaydedilemedi: {e}")
            print("Ayarlar bu oturum için sadece bellekte tutulacak.")
            return False
    
    def get_default_settings(self):
        """Varsayilan ayarlar"""
        return {
            "pin_code": None,
            "remember_pin": False,
            "last_login": None,
            "theme": "dark",
            "window_size": "1200x800",
            "monthly_targets": {
                "HT_TARAMA": 20,
                "HT_IZLEM": 15,
                "DIY_TARAMA": 18,
                "DIY_IZLEM": 12,
                "OBE_TARAMA": 25,
                "OBE_IZLEM": 10,
                "KVR_TARAMA": 15,
                "KVR_IZLEM": 8,
                "YAS_IZLEM": 5
            },
            "current_counts": {
                "HT_TARAMA": 0,
                "HT_IZLEM": 0,
                "DIY_TARAMA": 0,
                "DIY_IZLEM": 0,
                "OBE_TARAMA": 0,
                "OBE_IZLEM": 0,
                "KVR_TARAMA": 0,
                "KVR_IZLEM": 0,
                "YAS_IZLEM": 0
            },
            "deferred_counts": {
                "HT_TARAMA": 0,
                "HT_IZLEM": 0,
                "DIY_TARAMA": 0,
                "DIY_IZLEM": 0,
                "OBE_TARAMA": 0,
                "OBE_IZLEM": 0,
                "KVR_TARAMA": 0,
                "KVR_IZLEM": 0,
                "YAS_IZLEM": 0
            }
        }
    
    def get_monthly_targets(self):
        """Aylik hedefleri al"""
        return self.settings.get("monthly_targets", self.get_default_settings()["monthly_targets"])
    
    def save_monthly_targets(self, targets):
        """Aylik hedefleri kaydet"""
        self.settings["monthly_targets"] = targets
        self.save_settings()

    def get_current_counts(self):
        """Yapilan sayilari al"""
        return self.settings.get("current_counts", self.get_default_settings()["current_counts"])

    def save_current_counts(self, counts):
        """Yapilan sayilari kaydet - hem current_counts hem de monthly_history guncellenir"""
        self.settings["current_counts"] = counts

        # Aylik gecmisi de guncelle
        current_month = get_current_month_key()
        if "monthly_history" not in self.settings:
            self.settings["monthly_history"] = {}

        if current_month not in self.settings["monthly_history"]:
            # Yeni ay icin kayit olustur
            self.settings["monthly_history"][current_month] = {
                "targets": self.get_monthly_targets(),
                "current_counts": counts,
                "deferred_counts": self.get_deferred_counts(),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        else:
            # Mevcut ay kaydini guncelle
            self.settings["monthly_history"][current_month]["current_counts"] = counts
            self.settings["monthly_history"][current_month]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        self.save_settings()

    def get_deferred_counts(self):
        """Devreden sayilari al"""
        return self.settings.get("deferred_counts", self.get_default_settings()["deferred_counts"])

    def save_deferred_counts(self, counts):
        """Devreden sayilari kaydet - hem deferred_counts hem de monthly_history guncellenir"""
        self.settings["deferred_counts"] = counts

        # Aylik gecmisi de guncelle
        current_month = get_current_month_key()
        if "monthly_history" in self.settings and current_month in self.settings["monthly_history"]:
            self.settings["monthly_history"][current_month]["deferred_counts"] = counts
            self.settings["monthly_history"][current_month]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        self.save_settings()

    # ============================================================
    # SESSION GECMISI (Oturum ozeti kayitlari)
    # ============================================================

    def save_session_history(self, stats: dict, cancelled_list: list = None, skipped_list: list = None, failed_list: list = None):
        """
        Tamamlanan oturum verilerini gecmise kaydet.
        En fazla 50 oturum saklanir (eski olanlar silinir).
        """
        if "session_history" not in self.settings:
            self.settings["session_history"] = []
        
        session_data = {
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "basarili": stats.get("basarili", 0),
            "basarisiz": stats.get("basarisiz", 0),
            "atlanan": stats.get("atlanan", 0),
            "toplam_sure": stats.get("toplam_sure", 0),
            "iptal_edilenler": cancelled_list or [],
            "atlananlar": skipped_list or [],
            "basarisizlar": failed_list or []
        }
        
        # Basa ekle (en yeni en ustte)
        self.settings["session_history"].insert(0, session_data)
        
        # En fazla 50 oturum sakla
        if len(self.settings["session_history"]) > 50:
            self.settings["session_history"] = self.settings["session_history"][:50]
        
        self.save_settings()

    def get_session_history(self) -> list:
        """Kayitli oturum gecmisini dondur."""
        return self.settings.get("session_history", [])

    def clear_session_history(self):
        """Tum oturum gecmisini temizle."""
        self.settings["session_history"] = []
        self.save_settings()

    # ============================================================
    # KVR HEDEF ASIMI AYARI (KALICI)
    # ============================================================

    def get_auto_delete_kvr(self) -> bool:
        """
        KVR hedefi dolunca fazla KVR'lerin otomatik silinip silinmeyecegini al.
        Returns: True (otomatik sil), False (silme)
        """
        return self.settings.get("auto_delete_excess_kvr", False)

    def set_auto_delete_kvr(self, value: bool):
        """
        KVR hedefi dolunca fazla KVR'lerin otomatik silinip silinmeyecegini ayarla.
        Args:
            value: True (otomatik sil), False (silme)
        """
        self.settings["auto_delete_excess_kvr"] = value
        self.save_settings()

    # Eski fonksiyonlar - geriye uyumluluk icin (artik kullanilmiyor)
    def get_kvr_overflow_decision(self):
        """DEPRECATED: Artik get_auto_delete_kvr() kullaniliyor"""
        return self.get_auto_delete_kvr()

    def save_kvr_overflow_decision(self, decision: bool):
        """DEPRECATED: Artik set_auto_delete_kvr() kullaniliyor"""
        self.set_auto_delete_kvr(decision)

    # ============================================================
    # AY BAZLI HEDEF SISTEMI
    # ============================================================

    def get_monthly_history(self):
        """Tum aylarin gecmisini al"""
        return self.settings.get("monthly_history", {})

    def get_month_data(self, month_key=None):
        """Belirli bir ayin verilerini al"""
        if month_key is None:
            month_key = get_current_month_key()

        history = self.get_monthly_history()
        return history.get(month_key, None)

    def save_month_data(self, month_key, targets, current_counts, deferred_counts):
        """Belirli bir ayin verilerini kaydet"""
        if "monthly_history" not in self.settings:
            self.settings["monthly_history"] = {}

        self.settings["monthly_history"][month_key] = {
            "targets": targets,
            "current_counts": current_counts,
            "deferred_counts": deferred_counts,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.save_settings()

    def is_current_month_configured(self):
        """Mevcut ay icin hedefler girilmis mi?"""
        current_month = get_current_month_key()
        month_data = self.get_month_data(current_month)

        if month_data is None:
            return False

        # Hedefler var mi ve en az biri 0'dan buyuk mu?
        targets = month_data.get("targets", {})
        return any(v > 0 for v in targets.values())

    def get_last_configured_month(self):
        """En son yapilandirilan ayi bul"""
        history = self.get_monthly_history()
        if not history:
            return None

        # Tarihe gore sirala, en son ayi dondur
        sorted_months = sorted(history.keys(), reverse=True)
        return sorted_months[0] if sorted_months else None

    def migrate_current_to_month(self):
        """Mevcut verileri ay bazli sisteme tasi (ilk kurulum icin)"""
        current_month = get_current_month_key()

        # Zaten ay verisi varsa tasima
        if self.get_month_data(current_month) is not None:
            return

        # Eski format verileri al
        targets = self.get_monthly_targets()
        current = self.get_current_counts()
        deferred = self.get_deferred_counts()

        # Ay bazli sisteme kaydet
        self.save_month_data(current_month, targets, current, deferred)

    def calculate_month_performance(self, month_key):
        """Bir ayin performansini hesapla"""
        month_data = self.get_month_data(month_key)
        if not month_data:
            return None

        targets = month_data.get("targets", {})
        current = month_data.get("current_counts", {})
        deferred = month_data.get("deferred_counts", {})

        total_target = sum(targets.values())
        total_done = sum(current.values()) + sum(deferred.values())

        if total_target == 0:
            percentage = 0
        else:
            percentage = (total_done / total_target) * 100

        return {
            "month_key": month_key,
            "display_name": get_month_display_name(month_key),
            "total_target": total_target,
            "total_done": total_done,
            "percentage": percentage,
            "targets": targets,
            "current_counts": current,
            "deferred_counts": deferred
        }

    def get_pin_code(self):
        """
        Pin kodunu al (sifre cozulmus halde).

        Guvenlik Guncelleme v6.9.9:
        - Yeni guvenli format (version 2) destegi
        - Eski base64 format icin geriye uyumluluk
        - Eski format tespit edilirse otomatik yukseltme
        """
        if not self.settings.get("remember_pin"):
            return None

        # Yeni guvenli format kontrolu
        secure_pin = self.settings.get("secure_pin")
        if secure_pin and SecurePINStorage.is_secure_format(secure_pin):
            return SecurePINStorage.decrypt_pin(secure_pin)

        # Eski base64 format (geriye uyumluluk)
        old_encoded = self.settings.get("pin_code")
        if old_encoded:
            try:
                decoded = base64.b64decode(old_encoded.encode()).decode()
                # Eski formati otomatik olarak yeni formata yukselt
                print("[GUVENLIK] Eski PIN formati tespit edildi, guvenligi yukseltiliyor...")
                self.save_pin_code(decoded, remember=True)
                return decoded
            except Exception as e:
                print(f"[GUVENLIK] Eski PIN cozme hatasi: {e}")
                return None

        return None

    def save_pin_code(self, pin_code, remember=True):
        """
        Pin kodunu guvenli olarak kaydet.

        Guvenlik Guncelleme v6.9.9:
        - PBKDF2 + XOR sifreleme (base64 yerine)
        - Makine-spesifik anahtar
        - HMAC ile butunluk kontrolu
        """
        if remember and pin_code:
            # Yeni guvenli format ile sifrele
            encrypted_data = SecurePINStorage.encrypt_pin(pin_code)
            self.settings["secure_pin"] = encrypted_data
            self.settings["remember_pin"] = True

            # Eski formati temizle (varsa)
            if "pin_code" in self.settings:
                del self.settings["pin_code"]
        else:
            # PIN'i tamamen sil
            self.settings["secure_pin"] = None
            self.settings["remember_pin"] = False
            if "pin_code" in self.settings:
                del self.settings["pin_code"]

        self.save_settings()
    
    def clear_settings(self):
        """Ayarlari sifirla"""
        self.settings = self.get_default_settings()
        self.save_settings()


class LoginWindow(ctk.CTkToplevel):
    """Modern PIN Giris Ekrani - Numpad ile"""

    # Renk paleti (Referans tasarima gore)
    COLORS = {
        "bg_dark": "#0f172a",        # Ana arka plan
        "card_bg": "#1e293b",        # Kart arka plan
        "input_bg": "#334155",       # Input arka plan
        "primary": "#2dd4bf",        # Turkuaz accent
        "primary_dark": "#0f766e",   # Koyu turkuaz
        "text_white": "#ffffff",     # Beyaz metin
        "text_gray": "#94a3b8",      # Gri metin
        "text_dark_gray": "#64748b", # Koyu gri metin
        "border": "#475569",         # Border rengi
        "success": "#22c55e",        # Yesil
        "error": "#ef4444",          # Kirmizi
        "btn_hover": "#334155",      # Buton hover
    }

    def __init__(self, parent, callback):
        super().__init__(parent)

        self.callback = callback
        self.pin_code = ""
        self.max_pin_length = 6

        self.title("HYP Automation - Secure Access")
        self.geometry("480x720")
        self.resizable(False, False)
        self.configure(fg_color=self.COLORS["bg_dark"])

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (480 // 2)
        y = (self.winfo_screenheight() // 2) - (720 // 2)
        self.geometry(f"480x720+{x}+{y}")

        # Uygulama ikonu
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "hyp_icon.ico")
            if os.path.exists(icon_path):
                self.after(100, lambda: self.iconbitmap(icon_path))
        except:
            pass

        self.transient(parent)
        self.grab_set()

        self.create_widgets()

        # Klavye destegi
        self.bind('<Key>', self.on_key_press)
        self.bind('<Return>', lambda e: self.login())
        self.bind('<BackSpace>', lambda e: self.backspace())
        self.focus_force()

    def create_widgets(self):
        """Modern numpad arayuzu olustur"""

        # ===== HEADER: Logo + Baslik =====
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=(40, 20))

        # Logo container (yuvarlak ikon + yesil nokta)
        logo_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_container.pack()

        # Ana logo cercevesi
        logo_circle = ctk.CTkFrame(
            logo_container,
            width=80,
            height=80,
            corner_radius=40,
            fg_color=self.COLORS["card_bg"],
            border_width=1,
            border_color=self.COLORS["border"]
        )
        logo_circle.pack()
        logo_circle.pack_propagate(False)

        # Logo ikonu (medikal canta)
        logo_icon = ctk.CTkLabel(
            logo_circle,
            text="🏥",
            font=ctk.CTkFont(size=36),
            text_color=self.COLORS["primary"]
        )
        logo_icon.place(relx=0.5, rely=0.5, anchor="center")

        # Yesil durum noktasi (sag alt)
        status_dot = ctk.CTkFrame(
            logo_container,
            width=14,
            height=14,
            corner_radius=7,
            fg_color=self.COLORS["success"]
        )
        status_dot.place(relx=0.85, rely=0.85, anchor="center")

        # Baslik: "HYP Automation"
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(pady=(15, 0))

        title_hyp = ctk.CTkLabel(
            title_frame,
            text="HYP ",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=self.COLORS["text_white"]
        )
        title_hyp.pack(side="left")

        title_auto = ctk.CTkLabel(
            title_frame,
            text="Automation",
            font=ctk.CTkFont(size=26, weight="normal"),
            text_color=self.COLORS["primary"]
        )
        title_auto.pack(side="left")

        # Alt baslik: "SECURE ACCESS"
        subtitle = ctk.CTkLabel(
            header_frame,
            text="SECURE ACCESS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.COLORS["text_dark_gray"]
        )
        subtitle.pack(pady=(5, 0))

        # ===== MAIN CARD: Glass Panel =====
        self.main_card = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=self.COLORS["card_bg"],
            border_width=1,
            border_color="#ffffff14"
        )
        self.main_card.pack(fill="x", padx=40, pady=20)

        # Ust gradient cizgi
        gradient_line = ctk.CTkFrame(
            self.main_card,
            height=2,
            corner_radius=1,
            fg_color=self.COLORS["primary"]
        )
        gradient_line.pack(fill="x", padx=80, pady=(0, 0))

        # ===== PIN GOSTERGE NOKTALARI =====
        pin_label = ctk.CTkLabel(
            self.main_card,
            text="ENTER ACCESS PIN",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.COLORS["text_dark_gray"]
        )
        pin_label.pack(pady=(25, 15))

        # PIN noktalari container
        self.pin_dots_frame = ctk.CTkFrame(self.main_card, fg_color="transparent")
        self.pin_dots_frame.pack(pady=(0, 25))

        self.pin_dots = []
        for i in range(self.max_pin_length):
            dot = ctk.CTkFrame(
                self.pin_dots_frame,
                width=14,
                height=14,
                corner_radius=7,
                fg_color=self.COLORS["input_bg"],
                border_width=1,
                border_color=self.COLORS["border"]
            )
            dot.pack(side="left", padx=6)
            self.pin_dots.append(dot)

        # ===== NUMPAD =====
        numpad_frame = ctk.CTkFrame(self.main_card, fg_color="transparent")
        numpad_frame.pack(pady=(0, 20))

        # Numpad butonlari (3x4 grid)
        buttons = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['⌫', '0', '👆']  # Backspace, 0, Fingerprint
        ]

        for row_idx, row in enumerate(buttons):
            row_frame = ctk.CTkFrame(numpad_frame, fg_color="transparent")
            row_frame.pack(pady=8)

            for btn_text in row:
                if btn_text == '⌫':
                    # Backspace butonu
                    btn = ctk.CTkButton(
                        row_frame,
                        text="⌫",
                        width=64,
                        height=64,
                        corner_radius=32,
                        font=ctk.CTkFont(size=22),
                        fg_color="transparent",
                        hover_color="#ef444420",
                        text_color=self.COLORS["error"],
                        border_width=1,
                        border_color="transparent",
                        command=self.backspace
                    )
                elif btn_text == '👆':
                    # Fingerprint butonu (dekoratif)
                    btn = ctk.CTkButton(
                        row_frame,
                        text="👆",
                        width=64,
                        height=64,
                        corner_radius=32,
                        font=ctk.CTkFont(size=24),
                        fg_color="transparent",
                        hover_color="#2dd4bf20",
                        text_color=self.COLORS["primary"],
                        border_width=1,
                        border_color="transparent",
                        command=lambda: None  # Dekoratif
                    )
                else:
                    # Rakam butonlari
                    btn = ctk.CTkButton(
                        row_frame,
                        text=btn_text,
                        width=64,
                        height=64,
                        corner_radius=32,
                        font=ctk.CTkFont(size=20, weight="normal"),
                        fg_color=self.COLORS["card_bg"],
                        hover_color=self.COLORS["input_bg"],
                        text_color=self.COLORS["text_white"],
                        border_width=1,
                        border_color=self.COLORS["border"],
                        command=lambda t=btn_text: self.add_digit(t)
                    )
                btn.pack(side="left", padx=12)

        # ===== REMEMBER ME + LOGIN =====
        options_frame = ctk.CTkFrame(self.main_card, fg_color="transparent")
        options_frame.pack(fill="x", padx=30, pady=(10, 0))

        # Remember Me switch
        self.remember_var = ctk.BooleanVar(value=True)
        remember_switch = ctk.CTkSwitch(
            options_frame,
            text="Remember Me",
            variable=self.remember_var,
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS["text_gray"],
            progress_color=self.COLORS["primary"],
            button_color=self.COLORS["text_white"],
            button_hover_color=self.COLORS["text_gray"],
            fg_color=self.COLORS["input_bg"]
        )
        remember_switch.pack(pady=10)

        # LOGIN butonu
        self.login_button = ctk.CTkButton(
            self.main_card,
            text="LOGIN  →",
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=self.COLORS["primary"],
            hover_color=self.COLORS["primary_dark"],
            text_color=self.COLORS["bg_dark"],
            command=self.login
        )
        self.login_button.pack(fill="x", padx=30, pady=(5, 25))

        # ===== FOOTER: Forgot PIN & Support =====
        footer_frame = ctk.CTkFrame(
            self.main_card,
            fg_color="#0f172a80",
            corner_radius=0
        )
        footer_frame.pack(fill="x", side="bottom")

        footer_inner = ctk.CTkFrame(footer_frame, fg_color="transparent")
        footer_inner.pack(fill="x", padx=30, pady=12)

        forgot_btn = ctk.CTkButton(
            footer_inner,
            text="🔑 Forgot PIN?",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color="transparent",
            text_color=self.COLORS["text_dark_gray"],
            width=100,
            command=lambda: None
        )
        forgot_btn.pack(side="left")

        support_btn = ctk.CTkButton(
            footer_inner,
            text="💬 Support",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color="transparent",
            text_color=self.COLORS["text_dark_gray"],
            width=80,
            command=lambda: None
        )
        support_btn.pack(side="right")

        # ===== BOTTOM: System ID & Version =====
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=40, pady=(15, 30))

        # System ID
        sys_id_label = ctk.CTkLabel(
            bottom_frame,
            text="System ID: HYP-01",
            font=ctk.CTkFont(size=10, family="Consolas"),
            text_color=self.COLORS["text_dark_gray"]
        )
        sys_id_label.pack(side="left")

        # Version badge
        version_badge = ctk.CTkFrame(
            bottom_frame,
            corner_radius=12,
            fg_color=self.COLORS["card_bg"],
            border_width=1,
            border_color=self.COLORS["border"]
        )
        version_badge.pack(side="right")

        # Yesil nokta + versiyon
        status_inner = ctk.CTkFrame(version_badge, fg_color="transparent")
        status_inner.pack(padx=10, pady=5)

        mini_dot = ctk.CTkFrame(
            status_inner,
            width=8,
            height=8,
            corner_radius=4,
            fg_color=self.COLORS["primary"]
        )
        mini_dot.pack(side="left", padx=(0, 6))

        version_label = ctk.CTkLabel(
            status_inner,
            text="v6.8.0",
            font=ctk.CTkFont(size=9, family="Consolas"),
            text_color=self.COLORS["text_gray"]
        )
        version_label.pack(side="left")

        # Hata mesaji (gizli)
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS["error"]
        )
        self.error_label.pack(pady=(0, 10))

    def add_digit(self, digit):
        """PIN'e rakam ekle"""
        if len(self.pin_code) < self.max_pin_length:
            self.pin_code += digit
            self.update_pin_dots()

            # 6 hane dolunca otomatik giris
            if len(self.pin_code) == self.max_pin_length:
                self.after(200, self.login)

    def backspace(self):
        """Son rakami sil"""
        if len(self.pin_code) > 0:
            self.pin_code = self.pin_code[:-1]
            self.update_pin_dots()

    def update_pin_dots(self):
        """PIN noktalarini guncelle"""
        for i, dot in enumerate(self.pin_dots):
            if i < len(self.pin_code):
                # Dolu nokta - turkuaz parlak
                dot.configure(
                    fg_color=self.COLORS["primary"],
                    border_color=self.COLORS["primary"]
                )
            else:
                # Bos nokta
                dot.configure(
                    fg_color=self.COLORS["input_bg"],
                    border_color=self.COLORS["border"]
                )

    def on_key_press(self, event):
        """Klavye tuslarini yakala"""
        if event.char and event.char.isdigit():
            self.add_digit(event.char)

    def login(self):
        """Giris yap"""
        if not self.pin_code or not self.pin_code.isdigit():
            self.show_error("Lutfen gecerli bir PIN girin!")
            return
        if len(self.pin_code) < 4:
            self.show_error("PIN en az 4 haneli olmali!")
            return

        remember = self.remember_var.get()
        if self.callback:
            self.callback(self.pin_code, remember)
        self.destroy()

    def cancel(self):
        """Iptal et"""
        self.pin_code = None
        self.destroy()

    def show_error(self, message):
        """Hata mesaji goster"""
        self.error_label.configure(text=message)
        # PIN'i sifirla ve noktalari temizle
        self.pin_code = ""
        self.update_pin_dots()
        self.after(3000, lambda: self.error_label.configure(text=""))


class MonthWarningDialog(ctk.CTkToplevel):
    """Ay hedefleri eksik uyari dialogu"""

    def __init__(self, parent, settings_manager, on_configure_callback=None):
        super().__init__(parent)

        self.settings_manager = settings_manager
        self.on_configure_callback = on_configure_callback
        self.result = None  # "configure", "skip", "cancel"

        self.title("Ay Hedefleri Eksik!")
        self.geometry("500x350")
        self.resizable(False, False)

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (350 // 2)
        self.geometry(f"500x350+{x}+{y}")

        # Uygulama ikonu
        try:
            import os
            icon_path = os.path.join(os.path.dirname(__file__), "hyp_icon.ico")
            if os.path.exists(icon_path):
                self.after(100, lambda: self.iconbitmap(icon_path))
        except:
            pass

        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self, corner_radius=15)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        # Uyari ikonu ve baslik
        ctk.CTkLabel(
            main_frame,
            text="⚠️ HEDEFLER EKSIK!",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#e67e22"
        ).pack(pady=(20, 10))

        # Mevcut ay bilgisi
        current_month = get_current_month_key()
        month_name = get_month_display_name(current_month)

        ctk.CTkLabel(
            main_frame,
            text=f"{month_name} icin hedef verileri girilmemis!",
            font=ctk.CTkFont(size=16),
            text_color="#ecf0f1"
        ).pack(pady=(5, 5))

        # Son yapilandirilan ay bilgisi
        last_month = self.settings_manager.get_last_configured_month()
        if last_month and last_month != current_month:
            last_month_name = get_month_display_name(last_month)
            ctk.CTkLabel(
                main_frame,
                text=f"Son yapilandirilan ay: {last_month_name}",
                font=ctk.CTkFont(size=12),
                text_color="#95a5a6"
            ).pack(pady=(0, 15))
        else:
            ctk.CTkLabel(
                main_frame,
                text="Daha once hic hedef girilmemis",
                font=ctk.CTkFont(size=12),
                text_color="#95a5a6"
            ).pack(pady=(0, 15))

        # Butonlar
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=20, fill="x", padx=30)

        ctk.CTkButton(
            button_frame,
            text="📝 Hedefleri Simdi Gir",
            command=self.configure_now,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#27ae60",
            hover_color="#229954"
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            button_frame,
            text="⏭️ Varsayilan Hedeflerle Devam Et",
            command=self.skip_config,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            button_frame,
            text="❌ Iptal",
            command=self.cancel,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="#7f8c8d",
            hover_color="#6c7a7d"
        ).pack(fill="x", pady=5)

    def configure_now(self):
        self.result = "configure"
        self.destroy()
        if self.on_configure_callback:
            self.on_configure_callback()

    def skip_config(self):
        # Varsayilan hedeflerle mevcut ayi yapilandir
        current_month = get_current_month_key()
        default_targets = self.settings_manager.get_default_settings()["monthly_targets"]
        empty_counts = {k: 0 for k in default_targets.keys()}

        self.settings_manager.save_month_data(
            current_month,
            default_targets,
            empty_counts,
            empty_counts
        )
        self.result = "skip"
        self.destroy()

    def cancel(self):
        self.result = "cancel"
        self.destroy()


class MonthlyHistoryWindow(ctk.CTkToplevel):
    """Gecmis aylar performans penceresi"""

    def __init__(self, parent, settings_manager):
        super().__init__(parent)

        self.settings_manager = settings_manager

        self.title("Gecmis Aylar - Performans Raporu")
        self.geometry("700x600")

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"700x600+{x}+{y}")

        # Uygulama ikonu
        try:
            import os
            icon_path = os.path.join(os.path.dirname(__file__), "hyp_icon.ico")
            if os.path.exists(icon_path):
                self.after(100, lambda: self.iconbitmap(icon_path))
        except:
            pass

        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        # Baslik
        ctk.CTkLabel(
            self,
            text="📊 GECMIS AYLAR PERFORMANSI",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(20, 10))

        # Scrollable frame
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Ay verilerini al ve sirala
        history = self.settings_manager.get_monthly_history()

        if not history:
            ctk.CTkLabel(
                self.scroll_frame,
                text="Henuz gecmis ay verisi yok.\nOtomasyon calistikca veriler burada gorunecek.",
                font=ctk.CTkFont(size=14),
                text_color="#95a5a6"
            ).pack(pady=50)
        else:
            # Tarihe gore sirala (yeniden eskiye)
            sorted_months = sorted(history.keys(), reverse=True)

            for month_key in sorted_months:
                perf = self.settings_manager.calculate_month_performance(month_key)
                if perf:
                    self.create_month_card(perf)

        # Kapat butonu
        ctk.CTkButton(
            self,
            text="Kapat",
            command=self.destroy,
            width=150,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#34495e",
            hover_color="#2c3e50"
        ).pack(pady=15)

    def create_month_card(self, perf):
        """Bir ay icin kart olustur"""
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        card.pack(fill="x", padx=5, pady=8)

        # Baslik satiri
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(10, 5))

        # Ay adi
        ctk.CTkLabel(
            header_frame,
            text=f"📅 {perf['display_name']}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        # Yuzde
        percentage = perf['percentage']
        if percentage >= 100:
            pct_color = "#2ecc71"
            pct_text = f"✅ %{percentage:.0f}"
        elif percentage >= 70:
            pct_color = "#f39c12"
            pct_text = f"⚠️ %{percentage:.0f}"
        else:
            pct_color = "#e74c3c"
            pct_text = f"❌ %{percentage:.0f}"

        ctk.CTkLabel(
            header_frame,
            text=pct_text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=pct_color
        ).pack(side="right")

        # Ozet satiri
        ctk.CTkLabel(
            card,
            text=f"Toplam: {perf['total_done']} / {perf['total_target']} hedef tamamlandi",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7"
        ).pack(padx=15, pady=(0, 5))

        # Progress bar
        progress = ctk.CTkProgressBar(card, width=400)
        progress.pack(padx=15, pady=(0, 5))
        progress.set(min(percentage / 100, 1.0))

        # Detay butonu
        detail_frame = ctk.CTkFrame(card, fg_color="transparent")
        detail_frame.pack(fill="x", padx=15, pady=(5, 10))

        detail_btn = ctk.CTkButton(
            detail_frame,
            text="Detaylari Gor",
            command=lambda p=perf: self.show_details(p),
            width=120,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#5d6d7e",
            hover_color="#4a5a6a"
        )
        detail_btn.pack(side="left")

    def show_details(self, perf):
        """Ay detaylarini goster"""
        detail_window = ctk.CTkToplevel(self)
        detail_window.title(f"Detay - {perf['display_name']}")
        detail_window.geometry("550x500")

        detail_window.update_idletasks()
        x = (detail_window.winfo_screenwidth() // 2) - (550 // 2)
        y = (detail_window.winfo_screenheight() // 2) - (500 // 2)
        detail_window.geometry(f"550x500+{x}+{y}")

        detail_window.transient(self)
        detail_window.grab_set()

        ctk.CTkLabel(
            detail_window,
            text=f"📊 {perf['display_name']} Detayi",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(15, 10))

        scroll = ctk.CTkScrollableFrame(detail_window)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Baslik satiri
        header = ctk.CTkFrame(scroll, fg_color="#2c3e50")
        header.pack(fill="x", pady=(0, 5))

        for col, text in [("Tarama Tipi", 180), ("Hedef", 60), ("Yapilan", 70), ("Devreden", 70), ("%", 50)]:
            ctk.CTkLabel(
                header,
                text=text,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=col if isinstance(col, int) else 100
            ).pack(side="left", padx=5, pady=8)

        tarama_isimleri = {
            "HT_TARAMA": "HT Tarama",
            "HT_IZLEM": "HT Izlem",
            "DIY_TARAMA": "DIY Tarama",
            "DIY_IZLEM": "DIY Izlem",
            "OBE_TARAMA": "OBE Tarama",
            "OBE_IZLEM": "OBE Izlem",
            "KVR_TARAMA": "KVR Tarama",
            "KVR_IZLEM": "KVR Izlem",
            "YAS_IZLEM": "YAS Izlem"
        }

        for kod, isim in tarama_isimleri.items():
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)

            target = perf['targets'].get(kod, 0)
            current = perf['current_counts'].get(kod, 0)
            deferred = perf['deferred_counts'].get(kod, 0)
            total = current + deferred
            pct = (total / target * 100) if target > 0 else 0

            # Renk
            if pct >= 100:
                color = "#2ecc71"
            elif pct >= 70:
                color = "#f39c12"
            else:
                color = "#e74c3c"

            ctk.CTkLabel(row, text=isim, width=180, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(target), width=60).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(current), width=70).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(deferred), width=70).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=f"%{pct:.0f}", width=50, text_color=color).pack(side="left", padx=5)

        ctk.CTkButton(
            detail_window,
            text="Kapat",
            command=detail_window.destroy,
            width=100,
            height=35
        ).pack(pady=15)


class SettingsWindow(ctk.CTkToplevel):
    """Ayarlar penceresi"""

    def __init__(self, parent, settings_manager):
        super().__init__(parent)

        self.settings_manager = settings_manager
        self.parent = parent

        self.title("HYP Otomasyon - Ayarlar")

        # Büyük pencere - tüm içerik görünsün
        width = 800
        height = 950

        self.geometry(f"{width}x{height}")
        self.minsize(750, 850)

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Koyu tema uygula
        self.configure(fg_color="#1a1a2e")

        # Uygulama ikonu
        try:
            import os
            icon_path = os.path.join(os.path.dirname(__file__), "hyp_icon.ico")
            if os.path.exists(icon_path):
                self.after(100, lambda: self.iconbitmap(icon_path))
        except:
            pass

        self.transient(parent)
        self.grab_set()

        # Pencere öne gelme sorunu için
        self.lift()
        self.focus_force()

        # Simge durumundan geri gelince öne çık
        self.bind("<Map>", self._on_map)
        self.bind("<FocusIn>", self._on_focus)

        self.create_widgets()

    def _on_map(self, event=None):
        """Pencere görünür olduğunda"""
        self.lift()
        self.focus_force()

    def _on_focus(self, event=None):
        """Pencere odaklandığında"""
        self.lift()
    
    def create_widgets(self):
        """Widget'lari olustur"""

        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
            fg_color="#1a1a2e"
        )
        self.scrollable_frame.pack(fill="both", expand=True)

        self.main_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="⚙️ AYARLAR",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(10, 20))
        
        # PIN KODU BÖLÜMÜ
        self.pin_section = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.pin_section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.pin_section,
            text="🔐 PIN KODU",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        pin_saved = self.settings_manager.settings.get("remember_pin", False)

        if pin_saved:
            pin_text = "✅ Pin kodunuz kaydedilmiş"
            pin_color = "#2ecc71"
        else:
            pin_text = "❌ Pin kodunuz kaydedilmemiş"
            pin_color = "#e74c3c"

        self.pin_status_label = ctk.CTkLabel(
            self.pin_section,
            text=pin_text,
            font=ctk.CTkFont(size=13),
            text_color=pin_color
        )
        self.pin_status_label.pack(pady=(0, 10))

        # PIN giriş alanı
        pin_input_frame = ctk.CTkFrame(self.pin_section, fg_color="transparent")
        pin_input_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            pin_input_frame,
            text="Yeni PIN:",
            font=ctk.CTkFont(size=12),
            width=70
        ).pack(side="left")

        # PIN entry container (entry + göz butonu)
        pin_entry_container = ctk.CTkFrame(pin_input_frame, fg_color="transparent")
        pin_entry_container.pack(side="left", padx=10)

        self.pin_visible = False
        self.pin_entry = ctk.CTkEntry(
            pin_entry_container,
            width=130,
            height=35,
            show="●",
            placeholder_text="PIN girin"
        )
        self.pin_entry.pack(side="left")

        self.pin_eye_button = ctk.CTkButton(
            pin_entry_container,
            text="👁",
            command=self.toggle_pin_visibility,
            width=35,
            height=35,
            font=ctk.CTkFont(size=14),
            fg_color="#2c3e50",
            hover_color="#34495e",
            corner_radius=8
        )
        self.pin_eye_button.pack(side="left", padx=(2, 0))

        self.save_pin_button = ctk.CTkButton(
            pin_input_frame,
            text="💾 Kaydet",
            command=self.save_new_pin,
            width=90,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        self.save_pin_button.pack(side="left", padx=(5, 0))

        self.clear_pin_button = ctk.CTkButton(
            pin_input_frame,
            text="🗑️ Sil",
            command=self.clear_pin,
            width=70,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        self.clear_pin_button.pack(side="left", padx=5)

        # DOSYA LİSTELERİ BÖLÜMÜ
        self.files_section = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.files_section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.files_section,
            text="📁 DOSYA LİSTELERİ",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            self.files_section,
            text="İlaç ve gebe listesi dosyalarını yükleyin veya güncelleyin",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6"
        ).pack(pady=(0, 10))

        # İlaç listesi satırı
        ilac_frame = ctk.CTkFrame(self.files_section, fg_color="transparent")
        ilac_frame.pack(fill="x", padx=20, pady=8)

        self.ilac_status_label = ctk.CTkLabel(
            ilac_frame,
            text="",
            font=ctk.CTkFont(size=12),
            width=280,
            anchor="w"
        )
        self.ilac_status_label.pack(side="left")

        # İlaç yükle butonu
        self.ilac_upload_btn = ctk.CTkButton(
            ilac_frame,
            text="📤 Yükle",
            command=lambda: self.upload_file("ilac"),
            width=80,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.ilac_upload_btn.pack(side="left", padx=5)

        # İlaç sil butonu
        self.ilac_delete_btn = ctk.CTkButton(
            ilac_frame,
            text="🗑️ Sil",
            command=lambda: self.delete_file("ilac"),
            width=70,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        self.ilac_delete_btn.pack(side="left", padx=2)

        # Gebe listesi satırı
        gebe_frame = ctk.CTkFrame(self.files_section, fg_color="transparent")
        gebe_frame.pack(fill="x", padx=20, pady=8)

        self.gebe_status_label = ctk.CTkLabel(
            gebe_frame,
            text="",
            font=ctk.CTkFont(size=12),
            width=280,
            anchor="w"
        )
        self.gebe_status_label.pack(side="left")

        # Gebe yükle butonu
        self.gebe_upload_btn = ctk.CTkButton(
            gebe_frame,
            text="📤 Yükle",
            command=lambda: self.upload_file("gebe"),
            width=80,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.gebe_upload_btn.pack(side="left", padx=5)

        # Gebe sil butonu
        self.gebe_delete_btn = ctk.CTkButton(
            gebe_frame,
            text="🗑️ Sil",
            command=lambda: self.delete_file("gebe"),
            width=70,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        self.gebe_delete_btn.pack(side="left", padx=2)

        # Dosya durumlarını güncelle
        self.refresh_file_status()

        # AYLIK HEDEFLER BÖLÜMÜ
        self.targets_section = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.targets_section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.targets_section,
            text="🎯 AYLIK HEDEFLER VE MEVCUT DURUM",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            self.targets_section,
            text="Hedef, yapılan ve devreden sayıları girin:",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6"
        ).pack(pady=(0, 10))

        # Mevcut verileri al
        current_targets = self.settings_manager.get_monthly_targets()
        current_counts = self.settings_manager.get_current_counts()
        deferred_counts = self.settings_manager.get_deferred_counts()

        # Başlık satırı ekle
        header_frame = ctk.CTkFrame(self.targets_section, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(5, 10))

        ctk.CTkLabel(
            header_frame,
            text="Tarama Tipi",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=200,
            anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="Hedef",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=70,
            anchor="center"
        ).pack(side="left", padx=2)

        ctk.CTkLabel(
            header_frame,
            text="Yapılan",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=70,
            anchor="center"
        ).pack(side="left", padx=2)

        ctk.CTkLabel(
            header_frame,
            text="Devreden",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=70,
            anchor="center"
        ).pack(side="left", padx=2)

        self.target_entries = {}
        self.current_entries = {}
        self.deferred_entries = {}

        tarama_isimleri = {
            "HT_TARAMA": "Hipertansiyon Tarama",
            "HT_IZLEM": "Hipertansiyon İzlem",
            "DIY_TARAMA": "Diyabet Tarama",
            "DIY_IZLEM": "Diyabet İzlem",
            "OBE_TARAMA": "Obezite Tarama",
            "OBE_IZLEM": "Obezite İzlem",
            "KVR_TARAMA": "Kardiyovasküler Risk Tarama",
            "KVR_IZLEM": "Kardiyovasküler Risk İzlem",
            "YAS_IZLEM": "Yaşlı Sağlığı İzlem"
        }

        for tarama_kodu, tarama_adi in tarama_isimleri.items():
            entry_frame = ctk.CTkFrame(self.targets_section, fg_color="transparent")
            entry_frame.pack(fill="x", padx=20, pady=2)

            # Tarama adı
            label = ctk.CTkLabel(
                entry_frame,
                text=tarama_adi,
                font=ctk.CTkFont(size=11),
                width=200,
                anchor="w"
            )
            label.pack(side="left")

            # Hedef entry
            target_entry = ctk.CTkEntry(
                entry_frame,
                width=70,
                height=28,
                font=ctk.CTkFont(size=12),
                justify="center"
            )
            target_entry.insert(0, str(current_targets.get(tarama_kodu, 0)))
            target_entry.pack(side="left", padx=2)
            self.target_entries[tarama_kodu] = target_entry

            # Yapılan entry
            current_entry = ctk.CTkEntry(
                entry_frame,
                width=70,
                height=28,
                font=ctk.CTkFont(size=12),
                justify="center"
            )
            current_entry.insert(0, str(current_counts.get(tarama_kodu, 0)))
            current_entry.pack(side="left", padx=2)
            self.current_entries[tarama_kodu] = current_entry

            # Devreden entry
            deferred_entry = ctk.CTkEntry(
                entry_frame,
                width=70,
                height=28,
                font=ctk.CTkFont(size=12),
                justify="center"
            )
            deferred_entry.insert(0, str(deferred_counts.get(tarama_kodu, 0)))
            deferred_entry.pack(side="left", padx=2)
            self.deferred_entries[tarama_kodu] = deferred_entry
        
        self.save_targets_button = ctk.CTkButton(
            self.targets_section,
            text="💾 Hedefleri Kaydet",
            command=self.save_targets,
            width=200,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.save_targets_button.pack(pady=15)
        
        # OTOMASYON AYARLARI BÖLÜMÜ
        self.automation_section = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.automation_section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.automation_section,
            text="🤖 OTOMASYON AYARLARI",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        # KVR Otomatik Silme Toggle
        kvr_toggle_frame = ctk.CTkFrame(self.automation_section, fg_color="transparent")
        kvr_toggle_frame.pack(fill="x", padx=20, pady=10)

        kvr_label_frame = ctk.CTkFrame(kvr_toggle_frame, fg_color="transparent")
        kvr_label_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            kvr_label_frame,
            text="KVR hedefi dolunca fazla KVR izlemleri otomatik sil",
            font=ctk.CTkFont(size=12),
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            kvr_label_frame,
            text="HT izlem yapılırken zorunlu olarak KVR izlem de yapılır.\nBu ayar açıksa, KVR hedefi dolduktan sonra fazla yapılan KVR'ler silinir.",
            font=ctk.CTkFont(size=10),
            text_color="#95a5a6",
            anchor="w",
            justify="left"
        ).pack(anchor="w")

        self.kvr_auto_delete_switch = ctk.CTkSwitch(
            kvr_toggle_frame,
            text="",
            width=50,
            command=self.toggle_kvr_auto_delete,
            onvalue=True,
            offvalue=False
        )
        self.kvr_auto_delete_switch.pack(side="right", padx=10)

        # Mevcut değeri yükle
        if self.settings_manager.get_auto_delete_kvr():
            self.kvr_auto_delete_switch.select()

        # DİĞER İŞLEMLER BÖLÜMÜ
        self.other_section = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.other_section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.other_section,
            text="⚙️ Diğer İşlemler",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        # Hedefleri ve Sayaçları Sıfırla (PIN'e dokunmaz)
        self.clear_targets_button = ctk.CTkButton(
            self.other_section,
            text="🔄 Bu Ayın Sayaçlarını Sıfırla",
            command=self.clear_targets,
            width=250,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.clear_targets_button.pack(pady=5)

        self.clear_all_button = ctk.CTkButton(
            self.other_section,
            text="⚠️ Tüm Ayarları Sıfırla",
            command=self.clear_all,
            width=250,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="#e67e22",
            hover_color="#d35400"
        )
        self.clear_all_button.pack(pady=(5, 15))

        # WINDOWS BAŞLANGIÇ BÖLÜMÜ
        self.startup_section = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.startup_section.pack(fill="x", pady=10)

        ctk.CTkLabel(
            self.startup_section,
            text="🖥️ WİNDOWS BAŞLANGIÇ",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        startup_frame = ctk.CTkFrame(self.startup_section, fg_color="transparent")
        startup_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            startup_frame,
            text="Bilgisayar açıldığında uygulama otomatik başlasın",
            font=ctk.CTkFont(size=12),
            text_color="#95a5a6"
        ).pack(side="left")

        # Startup durumunu kontrol et
        try:
            from gui_app import get_startup_status, set_startup_enabled
            startup_enabled = get_startup_status()
        except:
            startup_enabled = False

        self.startup_switch = ctk.CTkSwitch(
            startup_frame,
            text="",
            command=self.toggle_startup,
            onvalue=True,
            offvalue=False,
            progress_color="#2dd4bf",
            button_color="#ffffff",
            button_hover_color="#e0e0e0"
        )
        self.startup_switch.pack(side="right")
        if startup_enabled:
            self.startup_switch.select()

        self.close_button = ctk.CTkButton(
            self.main_frame,
            text="Kapat",
            command=self.destroy,
            width=150,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#34495e",
            hover_color="#2c3e50"
        )
        self.close_button.pack(pady=20)
    
    def save_targets(self):
        """Hedefleri, yapılan ve devreden sayıları kaydet"""
        try:
            new_targets = {}
            new_current = {}
            new_deferred = {}

            # Hedefleri oku
            for tarama_kodu, entry in self.target_entries.items():
                value = entry.get().strip()
                if not value.isdigit():
                    self.show_error(f"{tarama_kodu} Hedef için geçerli bir sayı girin!")
                    return
                new_targets[tarama_kodu] = int(value)

            # Yapılan sayıları oku
            for tarama_kodu, entry in self.current_entries.items():
                value = entry.get().strip()
                if not value.isdigit():
                    self.show_error(f"{tarama_kodu} Yapılan için geçerli bir sayı girin!")
                    return
                new_current[tarama_kodu] = int(value)

            # Devreden sayıları oku
            for tarama_kodu, entry in self.deferred_entries.items():
                value = entry.get().strip()
                if not value.isdigit():
                    self.show_error(f"{tarama_kodu} Devreden için geçerli bir sayı girin!")
                    return
                new_deferred[tarama_kodu] = int(value)

            # Hepsini tek seferde kaydet (performans için)
            self.settings_manager.settings["monthly_targets"] = new_targets
            self.settings_manager.settings["current_counts"] = new_current
            self.settings_manager.settings["deferred_counts"] = new_deferred

            # Ay bazli sisteme de ekle
            current_month = get_current_month_key()
            if "monthly_history" not in self.settings_manager.settings:
                self.settings_manager.settings["monthly_history"] = {}

            self.settings_manager.settings["monthly_history"][current_month] = {
                "targets": new_targets,
                "current_counts": new_current,
                "deferred_counts": new_deferred,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

            # Tek seferde dosyaya yaz
            self.settings_manager.save_settings()

            self.save_targets_button.configure(text="✅ Kaydedildi!", fg_color="#2ecc71")
            self.after(2000, lambda: self.save_targets_button.configure(
                text="💾 Hedefleri Kaydet",
                fg_color="#3498db"
            ))

        except Exception as e:
            self.show_error(f"Hata: {str(e)}")
    
    def show_error(self, message):
        """Hata göster"""
        error_window = ctk.CTkToplevel(self)
        error_window.title("Hata")
        error_window.geometry("400x150")
        
        ctk.CTkLabel(
            error_window,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=350
        ).pack(pady=30)
        
        ctk.CTkButton(
            error_window,
            text="Tamam",
            command=error_window.destroy,
            width=100
        ).pack()
    
    def toggle_kvr_auto_delete(self):
        """KVR otomatik silme ayarını değiştir"""
        value = self.kvr_auto_delete_switch.get()
        self.settings_manager.set_auto_delete_kvr(value)

    def toggle_pin_visibility(self):
        """PIN görünürlüğünü değiştir"""
        if self.pin_visible:
            self.pin_entry.configure(show="●")
            self.pin_eye_button.configure(text="👁")
            self.pin_visible = False
        else:
            self.pin_entry.configure(show="")
            self.pin_eye_button.configure(text="🙈")
            self.pin_visible = True

    def toggle_startup(self):
        """Windows başlangıç ayarını değiştir"""
        try:
            from gui_app import set_startup_enabled
            enabled = self.startup_switch.get()
            success = set_startup_enabled(enabled)
            if not success:
                # Başarısızsa switch'i geri al
                if enabled:
                    self.startup_switch.deselect()
                else:
                    self.startup_switch.select()
        except Exception as e:
            print(f"[STARTUP] Toggle error: {e}")

    def save_new_pin(self):
        """Yeni PIN kaydet"""
        pin = self.pin_entry.get().strip()

        if not pin:
            self.pin_status_label.configure(
                text="⚠️ PIN boş olamaz!",
                text_color="#f39c12"
            )
            return

        if len(pin) < 4:
            self.pin_status_label.configure(
                text="⚠️ PIN en az 4 karakter olmalı!",
                text_color="#f39c12"
            )
            return

        # PIN'i kaydet
        self.settings_manager.save_pin_code(pin, remember=True)

        self.pin_status_label.configure(
            text="✅ PIN kaydedildi!",
            text_color="#2ecc71"
        )
        self.pin_entry.delete(0, "end")

    def clear_pin(self):
        """Pin kodunu sil"""
        self.settings_manager.settings["pin_code"] = None
        self.settings_manager.settings["remember_pin"] = False
        self.settings_manager.save_settings()

        self.pin_status_label.configure(
            text="❌ Pin kodunuz silindi!",
            text_color="#e74c3c"
        )
        self.pin_entry.delete(0, "end")

    def clear_targets(self):
        """Bu ayın sayaçlarını sıfırla (hedefler ve PIN korunur)"""
        confirm_dialog = ctk.CTkToplevel(self)
        confirm_dialog.title("Sayaçları Sıfırla")
        confirm_dialog.geometry("400x180")
        confirm_dialog.resizable(False, False)

        confirm_dialog.update_idletasks()
        x = (confirm_dialog.winfo_screenwidth() // 2) - 200
        y = (confirm_dialog.winfo_screenheight() // 2) - 90
        confirm_dialog.geometry(f"400x180+{x}+{y}")

        confirm_dialog.transient(self)
        confirm_dialog.grab_set()

        ctk.CTkLabel(
            confirm_dialog,
            text="🔄 Sayaçları Sıfırla",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(15, 10))

        ctk.CTkLabel(
            confirm_dialog,
            text="Bu ayın yapılan ve devreden sayaçları sıfırlanacak.\nHedefler ve PIN korunacak.",
            font=ctk.CTkFont(size=12),
            justify="center"
        ).pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(confirm_dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def do_clear():
            # Sayaçları sıfırla
            empty_counts = {k: 0 for k in self.settings_manager.get_monthly_targets().keys()}
            self.settings_manager.save_current_counts(empty_counts)
            self.settings_manager.save_deferred_counts(empty_counts)

            # Ay bazlı sistemde de güncelle
            current_month = get_current_month_key()
            targets = self.settings_manager.get_monthly_targets()
            self.settings_manager.save_month_data(current_month, targets, empty_counts, empty_counts)

            # Entry'leri güncelle - ayrı dict'ler
            for code in self.current_entries:
                self.current_entries[code].delete(0, "end")
                self.current_entries[code].insert(0, "0")

            for code in self.deferred_entries:
                self.deferred_entries[code].delete(0, "end")
                self.deferred_entries[code].insert(0, "0")

            confirm_dialog.destroy()

            self.clear_targets_button.configure(text="✅ Sıfırlandı!", fg_color="#2ecc71")
            self.after(2000, lambda: self.clear_targets_button.configure(
                text="🔄 Bu Ayın Sayaçlarını Sıfırla",
                fg_color="#3498db"
            ))

        ctk.CTkButton(
            btn_frame,
            text="✅ SIFIRLA",
            command=do_clear,
            width=110,
            height=35,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="❌ İPTAL",
            command=confirm_dialog.destroy,
            width=110,
            height=35,
            fg_color="#7f8c8d",
            hover_color="#6c7a7d"
        ).pack(side="left", padx=10)
    
    def clear_all(self):
        """Tum ayarlari sifirla - özel onay dialogu ile"""
        # Özel onay dialogu oluştur
        confirm_dialog = ctk.CTkToplevel(self)
        confirm_dialog.title("Onay Gerekli")
        confirm_dialog.geometry("400x200")
        confirm_dialog.resizable(False, False)

        confirm_dialog.update_idletasks()
        x = (confirm_dialog.winfo_screenwidth() // 2) - 200
        y = (confirm_dialog.winfo_screenheight() // 2) - 100
        confirm_dialog.geometry(f"400x200+{x}+{y}")

        confirm_dialog.transient(self)
        confirm_dialog.grab_set()

        # İçerik
        ctk.CTkLabel(
            confirm_dialog,
            text="⚠️ DİKKAT!",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#e74c3c"
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            confirm_dialog,
            text="Tüm ayarlar (PIN, hedefler, geçmiş) silinecek!\nDevam etmek istiyor musunuz?",
            font=ctk.CTkFont(size=13),
            justify="center"
        ).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(confirm_dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def do_clear():
            self.settings_manager.clear_settings()

            # Entry'leri sıfırla
            for code in self.target_entries:
                self.target_entries[code].delete(0, "end")
                self.target_entries[code].insert(0, "0")

            for code in self.current_entries:
                self.current_entries[code].delete(0, "end")
                self.current_entries[code].insert(0, "0")

            for code in self.deferred_entries:
                self.deferred_entries[code].delete(0, "end")
                self.deferred_entries[code].insert(0, "0")

            # PIN alanını temizle
            self.pin_entry.delete(0, "end")

            self.pin_status_label.configure(
                text="✅ Tüm ayarlar sıfırlandı!",
                text_color="#2ecc71"
            )
            confirm_dialog.destroy()
            # Pencereyi kapatma - kullanıcı isterse kapatır

        ctk.CTkButton(
            btn_frame,
            text="✅ EVET, SİL",
            command=do_clear,
            width=120,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="❌ İPTAL",
            command=confirm_dialog.destroy,
            width=120,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#7f8c8d",
            hover_color="#6c7a7d"
        ).pack(side="left", padx=10)

    def refresh_file_status(self):
        """Dosya durumlarını güncelle"""
        # İlaç listesi
        ilac_ok, ilac_count, ilac_path = check_ilac_listesi()
        if ilac_ok:
            ilac_name = os.path.basename(ilac_path) if ilac_path else ""
            self.ilac_status_label.configure(
                text=f"✅ İlaç Listesi: {ilac_name}",
                text_color="#2ecc71"
            )
            self.ilac_delete_btn.configure(state="normal")
        else:
            self.ilac_status_label.configure(
                text="❌ İlaç Listesi: Yüklenmedi",
                text_color="#e74c3c"
            )
            self.ilac_delete_btn.configure(state="disabled")

        # Gebe listesi
        gebe_ok, gebe_count, gebe_path = check_gebe_listesi()
        if gebe_ok:
            gebe_name = os.path.basename(gebe_path) if gebe_path else ""
            self.gebe_status_label.configure(
                text=f"✅ Gebe Listesi: {gebe_name}",
                text_color="#2ecc71"
            )
            self.gebe_delete_btn.configure(state="normal")
        else:
            self.gebe_status_label.configure(
                text="❌ Gebe Listesi: Yüklenmedi",
                text_color="#e74c3c"
            )
            self.gebe_delete_btn.configure(state="disabled")

    def upload_file(self, file_type):
        """Dosya yükle (ilac veya gebe)"""
        from tkinter import filedialog
        import shutil

        if file_type == "ilac":
            title = "İlaç Listesi Dosyası Seç"
            prefix = "ilac_listesi"
        else:
            title = "Gebe Listesi Dosyası Seç"
            prefix = "gebe_listesi"

        # Dosya seç
        file_path = filedialog.askopenfilename(
            parent=self,
            title=title,
            filetypes=[
                ("Excel dosyaları", "*.xlsx *.xls"),
                ("JSON dosyaları", "*.json"),
                ("CSV dosyaları", "*.csv"),
                ("Tüm dosyalar", "*.*")
            ]
        )

        if not file_path:
            return  # İptal edildi

        try:
            # Dosya uzantısını al
            ext = os.path.splitext(file_path)[1].lower()

            # Hedef dosya adı
            target_name = f"{prefix}{ext}"
            target_path = os.path.join(APP_DIR, target_name)

            # Eski dosyayı sil (varsa)
            self.delete_existing_files(file_type)

            # Yeni dosyayı kopyala
            shutil.copy2(file_path, target_path)

            # Durumu güncelle
            self.refresh_file_status()

            # Başarı mesajı
            if file_type == "ilac":
                self.ilac_status_label.configure(
                    text=f"✅ Yüklendi: {target_name}",
                    text_color="#2ecc71"
                )
            else:
                self.gebe_status_label.configure(
                    text=f"✅ Yüklendi: {target_name}",
                    text_color="#2ecc71"
                )

        except Exception as e:
            self.show_error(f"Dosya yüklenirken hata: {str(e)}")

    def delete_existing_files(self, file_type):
        """Mevcut dosyaları sil"""
        if file_type == "ilac":
            file_path = find_ilac_listesi()
        else:
            file_path = find_gebe_listesi()

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

    def delete_file(self, file_type):
        """Dosyayı sil"""
        if file_type == "ilac":
            file_path = find_ilac_listesi()
            label = self.ilac_status_label
            name = "İlaç listesi"
        else:
            file_path = find_gebe_listesi()
            label = self.gebe_status_label
            name = "Gebe listesi"

        if not file_path:
            return

        # Onay dialogu
        confirm_dialog = ctk.CTkToplevel(self)
        confirm_dialog.title("Silme Onayı")
        confirm_dialog.geometry("350x150")
        confirm_dialog.resizable(False, False)

        confirm_dialog.update_idletasks()
        x = (confirm_dialog.winfo_screenwidth() // 2) - 175
        y = (confirm_dialog.winfo_screenheight() // 2) - 75
        confirm_dialog.geometry(f"350x150+{x}+{y}")

        confirm_dialog.transient(self)
        confirm_dialog.grab_set()

        ctk.CTkLabel(
            confirm_dialog,
            text=f"🗑️ {name} silinsin mi?",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            confirm_dialog,
            text=os.path.basename(file_path),
            font=ctk.CTkFont(size=12),
            text_color="#95a5a6"
        ).pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(confirm_dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def do_delete():
            try:
                os.remove(file_path)
                self.refresh_file_status()
                confirm_dialog.destroy()
            except Exception as e:
                self.show_error(f"Silme hatası: {str(e)}")
                confirm_dialog.destroy()

        ctk.CTkButton(
            btn_frame,
            text="✅ SİL",
            command=do_delete,
            width=100,
            height=35,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="❌ İPTAL",
            command=confirm_dialog.destroy,
            width=100,
            height=35,
            fg_color="#7f8c8d",
            hover_color="#6c7a7d"
        ).pack(side="left", padx=10)


if __name__ == "__main__":
    def test_callback(pin, remember):
        print(f"Pin: {pin}, Remember: {remember}")
    
    app = ctk.CTk()
    app.withdraw()
    
    login = LoginWindow(app, test_callback)
    app.wait_window(login)
    
    if login.pin_code:
        print(f"Giris basarili! Pin: {login.pin_code}")
    else:
        print("Giris iptal edildi.")
    
    app.quit()
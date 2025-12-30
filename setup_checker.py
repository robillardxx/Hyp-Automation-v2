# -*- coding: utf-8 -*-
"""
HYP Otomasyon - Sistem Gereksinim Kontrolü ve Otomatik Kurulum
Uygulama başlatılmadan önce gerekli bileşenleri kontrol eder ve eksikleri giderir.
"""

import subprocess
import sys
import os
import winreg
import shutil
from typing import Tuple, List, Optional
import urllib.request
import tempfile
import ctypes


def is_admin() -> bool:
    """Yönetici yetkisi var mı kontrol et"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def check_chrome_installed() -> Tuple[bool, str]:
    """
    Chrome tarayıcısının kurulu olup olmadığını kontrol et
    Returns: (kurulu_mu, chrome_yolu veya hata mesajı)
    """
    # Olası Chrome yolları
    possible_paths = [
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
    ]

    # Registry'den kontrol
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
        chrome_path, _ = winreg.QueryValueEx(key, "")
        winreg.CloseKey(key)
        if os.path.exists(chrome_path):
            return True, chrome_path
    except:
        pass

    # Dosya yollarından kontrol
    for path in possible_paths:
        if os.path.exists(path):
            return True, path

    # PATH'den kontrol
    chrome_in_path = shutil.which("chrome") or shutil.which("chrome.exe")
    if chrome_in_path:
        return True, chrome_in_path

    return False, "Chrome tarayıcısı bulunamadı"


def get_chrome_version() -> Optional[str]:
    """Chrome versiyonunu al"""
    try:
        is_installed, chrome_path = check_chrome_installed()
        if not is_installed:
            return None

        # Registry'den versiyon al
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            return version
        except:
            pass

        # Alternatif registry yolu
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            return version
        except:
            pass

        return "Bilinmiyor"
    except:
        return None


def download_chrome_installer(progress_callback=None) -> Tuple[bool, str]:
    """
    Chrome kurulum dosyasını indir
    Returns: (başarılı_mı, dosya_yolu veya hata)
    """
    chrome_url = "https://dl.google.com/chrome/install/latest/chrome_installer.exe"

    try:
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, "chrome_installer.exe")

        if progress_callback:
            progress_callback("Chrome indiriliyor...")

        # İndirme
        urllib.request.urlretrieve(chrome_url, installer_path)

        if os.path.exists(installer_path):
            return True, installer_path
        else:
            return False, "İndirme başarısız"

    except Exception as e:
        return False, f"İndirme hatası: {str(e)}"


def install_chrome(installer_path: str, progress_callback=None) -> Tuple[bool, str]:
    """
    Chrome'u sessiz modda kur
    Returns: (başarılı_mı, mesaj)
    """
    try:
        if progress_callback:
            progress_callback("Chrome kuruluyor... (Bu birkaç dakika sürebilir)")

        # Sessiz kurulum
        result = subprocess.run(
            [installer_path, "/silent", "/install"],
            capture_output=True,
            timeout=300  # 5 dakika timeout
        )

        # Kurulum sonrası kontrol
        import time
        time.sleep(5)  # Chrome'un kurulumu tamamlamasını bekle

        is_installed, _ = check_chrome_installed()
        if is_installed:
            return True, "Chrome başarıyla kuruldu!"
        else:
            return False, "Kurulum tamamlandı ancak Chrome bulunamadı"

    except subprocess.TimeoutExpired:
        return False, "Kurulum zaman aşımına uğradı"
    except Exception as e:
        return False, f"Kurulum hatası: {str(e)}"


def check_webdriver_manager() -> bool:
    """webdriver_manager paketi kurulu mu kontrol et"""
    try:
        import webdriver_manager
        return True
    except ImportError:
        return False


def check_all_requirements(progress_callback=None) -> dict:
    """
    Tüm gereksinimleri kontrol et
    Returns: dict with status of each requirement
    """
    results = {
        "chrome": {"installed": False, "version": None, "path": None, "error": None},
        "ready": False,
        "errors": []
    }

    if progress_callback:
        progress_callback("Sistem gereksinimleri kontrol ediliyor...")

    # Chrome kontrolü
    if progress_callback:
        progress_callback("Chrome tarayıcısı kontrol ediliyor...")

    chrome_installed, chrome_info = check_chrome_installed()
    results["chrome"]["installed"] = chrome_installed

    if chrome_installed:
        results["chrome"]["path"] = chrome_info
        results["chrome"]["version"] = get_chrome_version()
    else:
        results["chrome"]["error"] = chrome_info
        results["errors"].append("Chrome tarayıcısı kurulu değil")

    # Sonuç
    results["ready"] = chrome_installed

    return results


def setup_with_auto_install(progress_callback=None, message_callback=None) -> Tuple[bool, str]:
    """
    Gereksinimleri kontrol et ve eksikleri otomatik kur

    Args:
        progress_callback: İlerleme mesajları için callback(text)
        message_callback: Kullanıcıya bilgi mesajı göstermek için callback(title, message)

    Returns: (hazır_mı, mesaj)
    """

    def log(msg):
        if progress_callback:
            progress_callback(msg)
        print(msg)

    log("Sistem gereksinimleri kontrol ediliyor...")

    # Chrome kontrolü
    log("Chrome tarayıcısı kontrol ediliyor...")
    chrome_installed, chrome_info = check_chrome_installed()

    if not chrome_installed:
        log("Chrome bulunamadı. Otomatik kurulum başlatılıyor...")

        # Chrome indir
        success, result = download_chrome_installer(log)
        if not success:
            error_msg = f"Chrome indirilemedi: {result}\n\nLütfen Chrome'u manuel olarak kurun:\nhttps://www.google.com/chrome/"
            return False, error_msg

        # Chrome kur
        success, result = install_chrome(result, log)
        if not success:
            error_msg = f"Chrome kurulamadı: {result}\n\nLütfen Chrome'u manuel olarak kurun:\nhttps://www.google.com/chrome/"
            return False, error_msg

        log("Chrome başarıyla kuruldu!")
    else:
        version = get_chrome_version()
        log(f"Chrome mevcut (v{version})")

    log("Tüm gereksinimler hazır!")
    return True, "Sistem hazır"


def get_system_info() -> dict:
    """Sistem bilgilerini topla (hata raporlama için)"""
    import platform

    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.architecture()[0],
        "python_version": sys.version,
        "chrome_installed": False,
        "chrome_version": None
    }

    chrome_installed, chrome_path = check_chrome_installed()
    info["chrome_installed"] = chrome_installed
    if chrome_installed:
        info["chrome_version"] = get_chrome_version()

    return info


# Test için
if __name__ == "__main__":
    print("=" * 50)
    print("HYP Otomasyon - Sistem Gereksinim Kontrolü")
    print("=" * 50)

    def progress(msg):
        print(f"  → {msg}")

    results = check_all_requirements(progress)

    print("\n" + "=" * 50)
    print("SONUÇ:")
    print("=" * 50)

    print(f"\nChrome: {'✓ Kurulu' if results['chrome']['installed'] else '✗ Kurulu değil'}")
    if results['chrome']['installed']:
        print(f"  Versiyon: {results['chrome']['version']}")
        print(f"  Yol: {results['chrome']['path']}")

    print(f"\nSistem Hazır: {'✓ EVET' if results['ready'] else '✗ HAYIR'}")

    if results['errors']:
        print("\nHatalar:")
        for error in results['errors']:
            print(f"  - {error}")

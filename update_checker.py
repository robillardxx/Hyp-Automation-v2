# -*- coding: utf-8 -*-
"""
HYP Otomasyon - Otomatik Güncelleme Sistemi
GitHub'dan güncelleme kontrolü, indirme ve otomatik kurulum
"""

import json
import os
import sys
import subprocess
import tempfile
import threading
import urllib.request
import urllib.error
from typing import Optional, Callable, Dict, Any

# Mevcut versiyon
CURRENT_VERSION = "7.0.0"

# GitHub ayarları
GITHUB_REPO = "robillardxx/Hyp-Automation-v2"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_app_dir() -> str:
    """Uygulama dizinini döndür (PyInstaller uyumlu)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def parse_version(version_str: str) -> tuple:
    """Versiyon string'ini karşılaştırılabilir tuple'a çevir"""
    try:
        parts = version_str.strip().lstrip('v').split(".")
        return tuple(int(p) for p in parts)
    except:
        return (0, 0, 0)


def compare_versions(current: str, remote: str) -> int:
    """
    İki versiyonu karşılaştır
    Returns:
        -1 if current < remote (güncelleme var)
         0 if current == remote
         1 if current > remote
    """
    current_tuple = parse_version(current)
    remote_tuple = parse_version(remote)

    if current_tuple < remote_tuple:
        return -1
    elif current_tuple > remote_tuple:
        return 1
    return 0


def check_for_updates(timeout: int = 10) -> Dict[str, Any]:
    """
    GitHub'dan güncelleme kontrol et

    Returns:
        Dict with keys:
            - has_update: bool
            - current_version: str
            - remote_version: str
            - changelog: list
            - download_url: str
            - error: str (hata varsa)
    """
    result = {
        "has_update": False,
        "current_version": CURRENT_VERSION,
        "remote_version": None,
        "changelog": [],
        "download_url": None,
        "release_notes": "",
        "error": None
    }

    try:
        # Önce version.json'dan kontrol et
        request = urllib.request.Request(
            VERSION_URL,
            headers={"User-Agent": "HYP-Otomasyon-UpdateChecker/2.0"}
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

        remote_version = data.get("version", "0.0.0")
        result["remote_version"] = remote_version
        result["changelog"] = data.get("changelog", [])
        result["download_url"] = data.get("download_url", "")
        result["release_notes"] = data.get("release_notes", "")

        # Versiyon karşılaştır
        if compare_versions(CURRENT_VERSION, remote_version) < 0:
            result["has_update"] = True

    except urllib.error.HTTPError as e:
        if e.code == 404:
            # version.json yoksa GitHub Releases API'yi dene
            try:
                result = _check_github_releases(timeout)
            except Exception as api_error:
                result["error"] = f"Güncelleme bilgisi bulunamadı: {str(api_error)}"
        else:
            result["error"] = f"HTTP hatası: {e.code}"
    except urllib.error.URLError as e:
        result["error"] = f"Bağlantı hatası: {str(e.reason)}"
    except json.JSONDecodeError:
        result["error"] = "Geçersiz güncelleme verisi"
    except Exception as e:
        result["error"] = f"Beklenmeyen hata: {str(e)}"

    return result


def _check_github_releases(timeout: int = 10) -> Dict[str, Any]:
    """GitHub Releases API'den son sürümü kontrol et"""
    result = {
        "has_update": False,
        "current_version": CURRENT_VERSION,
        "remote_version": None,
        "changelog": [],
        "download_url": None,
        "release_notes": "",
        "error": None
    }

    request = urllib.request.Request(
        RELEASES_API,
        headers={
            "User-Agent": "HYP-Otomasyon-UpdateChecker/2.0",
            "Accept": "application/vnd.github.v3+json"
        }
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))

    remote_version = data.get("tag_name", "0.0.0").lstrip('v')
    result["remote_version"] = remote_version
    result["release_notes"] = data.get("body", "")

    # ZIP asset'i bul
    for asset in data.get("assets", []):
        if asset["name"].endswith(".zip"):
            result["download_url"] = asset["browser_download_url"]
            break

    if compare_versions(CURRENT_VERSION, remote_version) < 0:
        result["has_update"] = True

    return result


def check_for_updates_async(callback: Callable[[Dict[str, Any]], None], timeout: int = 10):
    """
    Arka planda güncelleme kontrolü yap (UI donmasını önler)
    """
    def _check():
        result = check_for_updates(timeout=timeout)
        callback(result)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


def download_update(url: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
    """
    Güncelleme dosyasını indir

    Args:
        url: İndirilecek dosyanın URL'si
        progress_callback: İlerleme callback'i (indirilen_byte, toplam_byte)

    Returns:
        İndirilen dosyanın yolu veya hata durumunda None
    """
    try:
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, "hyp_update.zip")

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "HYP-Otomasyon-Updater/2.0"}
        )

        with urllib.request.urlopen(request) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192

            with open(zip_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total_size)

        return zip_path

    except Exception as e:
        print(f"İndirme hatası: {e}")
        return None


def download_update_async(url: str,
                          progress_callback: Optional[Callable[[int, int], None]] = None,
                          complete_callback: Optional[Callable[[Optional[str]], None]] = None):
    """
    Arka planda güncelleme indir
    """
    def _download():
        result = download_update(url, progress_callback)
        if complete_callback:
            complete_callback(result)

    thread = threading.Thread(target=_download, daemon=True)
    thread.start()
    return thread


def apply_update(zip_path: str) -> bool:
    """
    İndirilen güncellemeyi uygula

    Bu fonksiyon:
    1. Batch script oluşturur
    2. Script'i çalıştırır
    3. Mevcut uygulamadan çıkar
    4. Script: eski dosyaları siler, yenileri kopyalar, uygulamayı yeniden başlatır

    Returns:
        True if başarılı, False if hata
    """
    if not getattr(sys, 'frozen', False):
        print("Güncelleme sadece exe modunda çalışır")
        return False

    try:
        app_dir = get_app_dir()
        exe_name = os.path.basename(sys.executable)
        temp_dir = tempfile.gettempdir()
        extract_dir = os.path.join(temp_dir, "hyp_update_extract")

        # Batch script içeriği
        batch_content = f'''@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════╗
echo ║   HYP Otomasyon Güncelleniyor...       ║
echo ╚════════════════════════════════════════╝
echo.

REM Uygulamanın kapanmasını bekle
echo Uygulama kapatılıyor...
timeout /t 3 /nobreak >nul

REM Eski extract klasörünü temizle
if exist "{extract_dir}" rmdir /s /q "{extract_dir}"
mkdir "{extract_dir}"

REM ZIP dosyasını aç
echo ZIP dosyası açılıyor...
powershell -Command "Expand-Archive -Path '{zip_path}' -DestinationPath '{extract_dir}' -Force"

REM Dosyaları kopyala
echo Dosyalar kopyalanıyor...
xcopy /s /y /q "{extract_dir}\\*" "{app_dir}\\"

REM Temizlik
echo Temizlik yapılıyor...
rmdir /s /q "{extract_dir}"
del "{zip_path}"

REM Uygulamayı yeniden başlat
echo Uygulama yeniden başlatılıyor...
start "" "{os.path.join(app_dir, exe_name)}"

REM Batch dosyasını sil
del "%~f0"
'''

        # Batch dosyasını oluştur
        batch_path = os.path.join(temp_dir, "hyp_updater.bat")
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)

        # Batch'i çalıştır (yeni pencerede)
        subprocess.Popen(
            ['cmd', '/c', 'start', 'cmd', '/c', batch_path],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )

        return True

    except Exception as e:
        print(f"Güncelleme uygulama hatası: {e}")
        return False


def get_current_version() -> str:
    """Mevcut versiyonu döndür"""
    return CURRENT_VERSION


if __name__ == "__main__":
    # Test
    print(f"Mevcut versiyon: {CURRENT_VERSION}")
    print("Güncelleme kontrol ediliyor...")

    result = check_for_updates()

    if result["error"]:
        print(f"Hata: {result['error']}")
    elif result["has_update"]:
        print(f"Yeni versiyon mevcut: {result['remote_version']}")
        print(f"İndirme URL: {result['download_url']}")
        if result['changelog']:
            print(f"Değişiklikler: {result['changelog']}")
    else:
        print("Güncel versiyondasınız!")

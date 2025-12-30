# -*- coding: utf-8 -*-
"""
HYP Otomasyon - Güncelleme Kontrol Sistemi
GitHub'dan version.json kontrol ederek yeni versiyon olup olmadığını kontrol eder
"""

import json
import urllib.request
import urllib.error
import threading
from typing import Optional, Callable, Dict, Any

# Mevcut versiyon
CURRENT_VERSION = "6.9.5"

# GitHub raw URL (private repo için token gerekebilir, public yapılırsa bu çalışır)
VERSION_URL = "https://raw.githubusercontent.com/robillardxx/Hyp-Automation/main/version.json"


def parse_version(version_str: str) -> tuple:
    """Versiyon string'ini karşılaştırılabilir tuple'a çevir"""
    try:
        parts = version_str.strip().split(".")
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


def check_for_updates(callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                      timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    GitHub'dan güncelleme kontrol et

    Args:
        callback: Sonuç geldiğinde çağrılacak fonksiyon (async kullanım için)
        timeout: İstek zaman aşımı (saniye)

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
        "error": None
    }

    try:
        # GitHub'dan version.json çek
        request = urllib.request.Request(
            VERSION_URL,
            headers={"User-Agent": "HYP-Otomasyon-UpdateChecker/1.0"}
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

        remote_version = data.get("version", "0.0.0")
        result["remote_version"] = remote_version
        result["changelog"] = data.get("changelog", [])
        result["download_url"] = data.get("download_url", "")
        result["release_date"] = data.get("release_date", "")

        # Versiyon karşılaştır
        if compare_versions(CURRENT_VERSION, remote_version) < 0:
            result["has_update"] = True

    except urllib.error.URLError as e:
        result["error"] = f"Bağlantı hatası: {str(e.reason)}"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["error"] = "Güncelleme bilgisi bulunamadı"
        else:
            result["error"] = f"HTTP hatası: {e.code}"
    except json.JSONDecodeError:
        result["error"] = "Geçersiz güncelleme verisi"
    except Exception as e:
        result["error"] = f"Beklenmeyen hata: {str(e)}"

    if callback:
        callback(result)

    return result


def check_for_updates_async(callback: Callable[[Dict[str, Any]], None], timeout: int = 10):
    """
    Arka planda güncelleme kontrolü yap (UI donmasını önler)

    Args:
        callback: Sonuç geldiğinde ana thread'de çağrılacak fonksiyon
        timeout: İstek zaman aşımı
    """
    def _check():
        result = check_for_updates(timeout=timeout)
        callback(result)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


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
        print(f"Değişiklikler: {result['changelog']}")
    else:
        print("Güncel versiyondasınız!")

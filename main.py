#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HYP OTOMASYON SISTEMI
Hastalık Yönetim Platformu - Otomatik Tarama/İzlem Sistemi

Kullanim:
    python main.py

Osman Sucioglu - Aile Hekimi
Tekirdağ Kapaklı 26 Nolu Aile Sağlığı Merkezi
"""

import sys
import os

# Windows görev çubuğu ikonu için - TÜM importlardan önce!
import ctypes
try:
    myappid = 'hyp.otomasyon.gui.v6'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

# Encoding ayarla (hata vermeden)
if sys.platform == "win32":
    try:
        import locale
        locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
    except:
        pass  # Locale desteklenmiyorsa, devam et


def show_error_dialog(title: str, message: str):
    """Windows hata dialogu göster"""
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR
    except:
        print(f"\n{title}\n{message}")


def show_info_dialog(title: str, message: str):
    """Windows bilgi dialogu göster"""
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)  # MB_ICONINFORMATION
    except:
        print(f"\n{title}\n{message}")


def check_and_setup_requirements():
    """Sistem gereksinimlerini kontrol et ve eksikleri kur"""
    try:
        from setup_checker import check_chrome_installed, download_chrome_installer, install_chrome, get_chrome_version

        # Chrome kontrolü
        chrome_installed, chrome_info = check_chrome_installed()

        if not chrome_installed:
            # Kullanıcıya sor
            result = ctypes.windll.user32.MessageBoxW(
                0,
                "HYP Otomasyon için Google Chrome tarayıcısı gereklidir.\n\n"
                "Chrome şu anda bilgisayarınızda kurulu değil.\n\n"
                "Chrome'u otomatik olarak indirip kurmak ister misiniz?\n\n"
                "(İnternet bağlantısı gereklidir)",
                "Chrome Gerekli - HYP Otomasyon",
                0x24  # MB_ICONQUESTION | MB_YESNO
            )

            if result == 6:  # IDYES
                # Chrome'u indir ve kur
                show_info_dialog("İndiriliyor", "Chrome indiriliyor...\nBu işlem birkaç dakika sürebilir.\n\nLütfen bekleyin.")

                success, installer_path = download_chrome_installer()
                if not success:
                    show_error_dialog(
                        "İndirme Hatası",
                        f"Chrome indirilemedi:\n{installer_path}\n\n"
                        "Lütfen Chrome'u manuel olarak kurun:\n"
                        "https://www.google.com/chrome/"
                    )
                    return False

                success, msg = install_chrome(installer_path)
                if not success:
                    show_error_dialog(
                        "Kurulum Hatası",
                        f"Chrome kurulamadı:\n{msg}\n\n"
                        "Lütfen Chrome'u manuel olarak kurun:\n"
                        "https://www.google.com/chrome/"
                    )
                    return False

                show_info_dialog("Kurulum Tamamlandı", "Chrome başarıyla kuruldu!\n\nProgram şimdi başlatılacak.")
            else:
                show_error_dialog(
                    "Chrome Gerekli",
                    "HYP Otomasyon çalışmak için Chrome'a ihtiyaç duyar.\n\n"
                    "Lütfen Chrome'u kurun ve programı tekrar başlatın:\n"
                    "https://www.google.com/chrome/"
                )
                return False

        return True

    except ImportError:
        # setup_checker modülü yoksa, direkt devam et
        return True
    except Exception as e:
        # Hata olsa bile devam etmeye çalış
        print(f"Gereksinim kontrolü sırasında hata: {e}")
        return True


def main():
    """Ana fonksiyon"""
    try:
        print("=" * 60)
        print("HYP OTOMASYON SISTEMI")
        print("=" * 60)
        print("Hastalık Yönetim Platformu - Otomatik Tarama/İzlem")
        print("Versiyon: 6.6.2")
        print("=" * 60)
        print()

        # Sistem gereksinimlerini kontrol et
        print("Sistem gereksinimleri kontrol ediliyor...")
        if not check_and_setup_requirements():
            print("Sistem gereksinimleri karşılanamadı. Program kapatılıyor.")
            sys.exit(1)

        print("Sistem hazır. GUI başlatılıyor...")
        print()

        # GUI'yi baslat
        from gui_app import main as gui_main
        gui_main()

    except KeyboardInterrupt:
        print("\n\nProgram kullanici tarafindan durduruldu.")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Beklenmeyen bir hata oluştu:\n\n{str(e)}"
        print(f"\n\nHATA: {str(e)}")

        # Hata detaylarını göster
        import traceback
        traceback.print_exc()

        # Kullanıcıya hata göster
        try:
            ctypes.windll.user32.MessageBoxW(0, error_msg, "HYP Otomasyon - Hata", 0x10)
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()

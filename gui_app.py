# -*- coding: utf-8 -*-
"""
HYP Automation - GUI V6.0
Debug modu, performans takibi, tooltip ve geçmiş aylar sekmesi
"""

# Windows görev çubuğu ikonu için - TÜM importlardan önce olmalı!
import ctypes
import os
try:
    myappid = 'hyp.otomasyon.gui.v6'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

import customtkinter as ctk
from tkinter import scrolledtext
import threading
import json
from datetime import datetime, timedelta
from infi.systray import SysTrayIcon
from PIL import Image, ImageDraw
from config import *
from hyp_automation import HYPAutomation
from login_manager import (
    LoginWindow, SettingsManager, SettingsWindow,
    MonthWarningDialog,
    get_current_month_key, get_month_display_name,
    ILAC_LISTESI_FILE, GEBE_LISTESI_FILE,
    check_ilac_listesi, check_gebe_listesi
)
from update_checker import check_for_updates_async, get_current_version, CURRENT_VERSION
import threading

# Hemsire Entegrasyonu - Paylasimli Klasor
SHARED_FOLDER = r"Z:\Dr Osman"
QUEUE_FILE = "hasta_kuyrugu.json"

# ============================================================
# WINDOWS BAŞLANGIÇ YÖNETİMİ
# ============================================================
import winreg
import sys

def get_startup_status():
    """Windows başlangıcında çalışma durumunu kontrol et"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, "HYP_Otomasyon")
            winreg.CloseKey(key)
            return True
        except WindowsError:
            winreg.CloseKey(key)
            return False
    except:
        return False

def set_startup_enabled(enabled):
    """Windows başlangıcına ekle/kaldır"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )

        if enabled:
            # Exe veya script yolunu bul
            if getattr(sys, 'frozen', False):
                # PyInstaller ile derlenmişse
                app_path = sys.executable
            else:
                # Python script olarak çalışıyorsa
                app_path = f'pythonw "{os.path.abspath(__file__)}"'

            winreg.SetValueEx(key, "HYP_Otomasyon", 0, winreg.REG_SZ, app_path)
            print(f"[STARTUP] Added to startup: {app_path}")
        else:
            try:
                winreg.DeleteValue(key, "HYP_Otomasyon")
                print("[STARTUP] Removed from startup")
            except WindowsError:
                pass  # Zaten yok

        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[STARTUP] Error: {e}")
        return False


# ============================================================
# HEMŞİRE BİLDİRİM SİSTEMİ
# ============================================================
def send_nurse_notification(shared_folder, tc, status, message, hasta_adi="", eksik_tetkikler=None):
    """
    Hemşire uygulamasına bildirim gönder

    Args:
        shared_folder: Paylaşımlı klasör yolu
        tc: Hasta TC numarası
        status: "success", "error", "sms_kapali", "eksik_tetkik"
        message: Bildirim mesajı
        hasta_adi: Hasta adı soyadı
        eksik_tetkikler: Eksik tetkik listesi (varsa)
    """
    try:
        if not os.path.exists(shared_folder):
            return False

        notification = {
            "tc": tc,
            "hasta_adi": hasta_adi,
            "status": status,
            "message": message,
            "eksik_tetkikler": eksik_tetkikler or [],
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "okundu": False
        }

        # Bildirim dosyası oluştur
        notification_file = os.path.join(shared_folder, f"{tc}_{datetime.now().strftime('%H%M%S')}.bildirim")
        with open(notification_file, 'w', encoding='utf-8') as f:
            json.dump(notification, f, ensure_ascii=False, indent=2)

        print(f"[NOTIFICATION] Sent to nurse: {status} - {tc}")
        return True
    except Exception as e:
        print(f"[NOTIFICATION] Error: {e}")
        return False


# ============================================================
# TOOLTIP SİSTEMİ
# ============================================================
class ToolTip:
    """Butonlar için tooltip (ipucu) gösterici"""

    def __init__(self, widget, text, delay=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.scheduled_id = None

        widget.bind("<Enter>", self.on_enter)
        widget.bind("<Leave>", self.on_leave)
        widget.bind("<Button-1>", self.on_leave)

    def on_enter(self, event=None):
        self.scheduled_id = self.widget.after(self.delay, self.show_tooltip)

    def on_leave(self, event=None):
        if self.scheduled_id:
            self.widget.after_cancel(self.scheduled_id)
            self.scheduled_id = None
        self.hide_tooltip()

    def show_tooltip(self):
        if self.tooltip_window:
            return

        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        # Tooltip içeriği
        frame = ctk.CTkFrame(tw, corner_radius=6, fg_color="#2c3e50", border_width=1, border_color="#34495e")
        frame.pack()

        label = ctk.CTkLabel(
            frame,
            text=self.text,
            font=ctk.CTkFont(size=12),
            text_color="#ecf0f1",
            padx=10,
            pady=5
        )
        label.pack()

    def hide_tooltip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def add_tooltip(widget, text):
    """Widget'a tooltip eklemek için yardımcı fonksiyon"""
    return ToolTip(widget, text)


class DatePickerDialog(ctk.CTkToplevel):
    """Coklu tarih secici dialog - Birden fazla tarih secilebilir"""

    def __init__(self, parent):
        super().__init__(parent)

        self.selected_date = None
        self.selected_dates = []
        self.cancelled = False
        self.date_checkboxes = {}

        self.title("Tarih Secimi")
        self.geometry("550x650")
        self.resizable(False, False)

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (550 // 2)
        y = (self.winfo_screenheight() // 2) - (325 // 2)
        self.geometry(f"550x650+{x}+{y}")

        self.configure(fg_color="#1a1a2e")
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        title_frame = ctk.CTkFrame(self, fg_color="#2c3e50", corner_radius=0)
        title_frame.pack(fill="x")

        ctk.CTkLabel(
            title_frame,
            text="📅 COKLU TARIH SECIMI",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#e67e22"
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            title_frame,
            text="Bugun islenecek hasta bulunamadi. Birden fazla tarih secebilirsiniz.",
            font=ctk.CTkFont(size=12),
            text_color="#95a5a6",
            justify="center"
        ).pack(pady=(0, 15))

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        quick_frame = ctk.CTkFrame(content_frame, fg_color="#34495e", corner_radius=10)
        quick_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            quick_frame,
            text="⚡ Hizli Secim:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=15, pady=10)

        ctk.CTkButton(
            quick_frame, text="Son 3 Gun",
            command=lambda: self.quick_select(3),
            width=90, height=30, font=ctk.CTkFont(size=11),
            fg_color="#3498db", hover_color="#2980b9"
        ).pack(side="left", padx=5, pady=10)

        ctk.CTkButton(
            quick_frame, text="Son 1 Hafta",
            command=lambda: self.quick_select(7),
            width=100, height=30, font=ctk.CTkFont(size=11),
            fg_color="#9b59b6", hover_color="#8e44ad"
        ).pack(side="left", padx=5, pady=10)

        ctk.CTkButton(
            quick_frame, text="Hafta Ici",
            command=self.select_weekdays_only,
            width=85, height=30, font=ctk.CTkFont(size=11),
            fg_color="#e67e22", hover_color="#d35400"
        ).pack(side="left", padx=5, pady=10)

        ctk.CTkButton(
            quick_frame, text="Tumunu Sec",
            command=self.select_all,
            width=90, height=30, font=ctk.CTkFont(size=11),
            fg_color="#27ae60", hover_color="#219a52"
        ).pack(side="left", padx=5, pady=10)

        ctk.CTkButton(
            quick_frame, text="Temizle",
            command=self.clear_selection,
            width=70, height=30, font=ctk.CTkFont(size=11),
            fg_color="#7f8c8d", hover_color="#636e72"
        ).pack(side="right", padx=15, pady=10)

        date_list_frame = ctk.CTkFrame(content_frame, fg_color="#2c3e50", corner_radius=10)
        date_list_frame.pack(fill="both", expand=True, pady=5)

        ctk.CTkLabel(
            date_list_frame,
            text="📆 Tarih Secin (birden fazla secebilirsiniz):",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(10, 5))

        self.dates_scroll = ctk.CTkScrollableFrame(
            date_list_frame,
            fg_color="transparent",
            height=200
        )
        self.dates_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        today = datetime.now()
        gun_isimleri = ['Pazartesi', 'Sali', 'Carsamba', 'Persembe', 'Cuma', 'Cumartesi', 'Pazar']

        for i in range(1, 15):
            date = today - timedelta(days=i)
            gun_ismi = gun_isimleri[date.weekday()]
            date_str = date.strftime("%d.%m.%Y")
            display_text = f"{date_str} ({gun_ismi})"

            if i == 1:
                display_text += " - Dun"
            elif i == 2:
                display_text += " - Evvelsi gun"

            var = ctk.BooleanVar(value=False)
            self.date_checkboxes[date] = var

            checkbox_frame = ctk.CTkFrame(self.dates_scroll, fg_color="transparent")
            checkbox_frame.pack(fill="x", pady=2)

            cb = ctk.CTkCheckBox(
                checkbox_frame,
                text=display_text,
                variable=var,
                font=ctk.CTkFont(size=12),
                command=self.update_selection_count,
                checkbox_width=22,
                checkbox_height=22
            )
            cb.pack(anchor="w", padx=10)

        self.selection_label = ctk.CTkLabel(
            content_frame,
            text="📊 Secili: 0 tarih",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f39c12"
        )
        self.selection_label.pack(pady=5)

        self.error_label = ctk.CTkLabel(
            content_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#e74c3c"
        )
        self.error_label.pack()

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(
            button_frame, text="✅ DEVAM ET",
            command=self.confirm_dates,
            height=45, width=150,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2ecc71", hover_color="#27ae60"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame, text="❌ IPTAL",
            command=self.cancel,
            height=45, width=150,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#e74c3c", hover_color="#c0392b"
        ).pack(side="right", padx=10)

    def quick_select(self, days):
        self.clear_selection()
        today = datetime.now()
        for i in range(1, days + 1):
            date = today - timedelta(days=i)
            if date in self.date_checkboxes:
                self.date_checkboxes[date].set(True)
        self.update_selection_count()

    def select_all(self):
        for var in self.date_checkboxes.values():
            var.set(True)
        self.update_selection_count()

    def clear_selection(self):
        for var in self.date_checkboxes.values():
            var.set(False)
        self.update_selection_count()

    def select_weekdays_only(self):
        """Son 1 haftanın sadece hafta içi günlerini seç (Cumartesi-Pazar hariç)"""
        self.clear_selection()
        today = datetime.now()
        for i in range(1, 8):  # Son 7 gün
            date = today - timedelta(days=i)
            # Hafta sonu değilse seç (0=Pazartesi, 6=Pazar)
            if date.weekday() < 5 and date in self.date_checkboxes:  # Pazartesi-Cuma
                self.date_checkboxes[date].set(True)
        self.update_selection_count()

    def update_selection_count(self):
        count = sum(1 for var in self.date_checkboxes.values() if var.get())
        self.selection_label.configure(text=f"📊 Secili: {count} tarih")

    def confirm_dates(self):
        self.selected_dates = [
            date for date, var in self.date_checkboxes.items() if var.get()
        ]

        if not self.selected_dates:
            self.error_label.configure(text="En az bir tarih secmelisiniz!")
            return

        self.selected_dates.sort()
        self.selected_date = self.selected_dates[0]

        self.cancelled = False
        self.destroy()

    def cancel(self):
        self.cancelled = True
        self.destroy()


class HYPApp(ctk.CTk):
    """Ana GUI Uygulaması V6.8 - Modern Dashboard"""

    # Versiyon bilgisi
    VERSION = CURRENT_VERSION
    BUILD_DATE = "16.12.2025"

    # Modern Renk Paleti (Referans tasarima gore)
    COLORS = {
        "bg_dark": "#0f111a",           # Ana arka plan
        "sidebar_bg": "#13151b",        # Sidebar arka plan
        "surface": "#181a24",           # Yüzey rengi
        "surface_highlight": "#1e212b", # Vurgulu yüzey
        "card_bg": "#1e212b",           # Kart arka plan
        "border": "#272a36",            # Border rengi
        "primary": "#2dd4bf",           # Turkuaz accent
        "secondary": "#0ea5e9",         # Mavi
        "success": "#22c55e",           # Yesil
        "warning": "#f59e0b",           # Turuncu
        "danger": "#ef4444",            # Kirmizi
        "text_white": "#ffffff",        # Beyaz metin
        "text_gray": "#9ca3af",         # Gri metin
        "text_dark": "#6b7280",         # Koyu gri
    }

    def __init__(self):
        super().__init__()

        self.settings_manager = SettingsManager()
        self.pin_code = None
        self.debug_mode = ctk.BooleanVar(value=False)

        # Tema ayarı
        saved_theme = self.settings_manager.settings.get("theme", "dark")
        self.current_theme = saved_theme
        ctk.set_appearance_mode(saved_theme)
        ctk.set_default_color_theme("blue")

        self.title(f"HYP Otomasyon V{self.VERSION}")
        self.geometry(GUI_CONFIG["window_size"])

        # Uygulama ikonu
        try:
            import os
            icon_path = os.path.join(os.path.dirname(__file__), "hyp_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
                self.after(100, lambda: self.iconbitmap(icon_path))  # Tekrar uygula
        except Exception as e:
            print(f"Icon error: {e}")

        self.automation = None
        self.automation_thread = None
        self.is_running = False

        # Hemsire kuyruk dinleyici
        self.queue_listener_active = False
        self.queue_listener_thread = None
        self.shared_folder = SHARED_FOLDER
        self.tc_queue = []  # Bekleyen TC'ler
        self.nurse_tc_history = []  # Tamamlanan TC'ler [(tc, tarih, durum), ...]

        # Minimize/Restore düzeltmesi - Windows'ta görev çubuğundan geri getirme
        self._is_minimized = False
        self._setup_windows_restore_fix()

        self.create_widgets()
        self.after(500, self.perform_startup_checks)

        # Hemsire dinleyiciyi otomatik baslat (arka planda)
        self.after(1000, self.start_queue_listener)

        # System Tray (Görev Çubuğu) özelliği
        self.systray = None
        self._is_hidden = False
        self._force_quit = False

        # System tray başlat
        self.setup_system_tray()

        # Pencere kapatma davranışını değiştir - TÜM init bittikten sonra ayarla
        self.after(1000, self._setup_close_protocol)

    def _setup_close_protocol(self):
        """X butonunu minimize to tray olarak ayarla - gecikmeli"""
        self.protocol("WM_DELETE_WINDOW", self._on_close_button)
        print("[TRAY] Close protocol set")

    def _on_close_button(self):
        """X butonuna basıldığında çağrılır"""
        print("[TRAY] X button pressed - minimizing to tray")
        self.minimize_to_tray()

    def setup_system_tray(self):
        """System tray ikonu oluştur - infi.systray ile"""
        # Küçük tray ikonu oluştur (32x32)
        tray_icon_path = os.path.join(os.path.dirname(__file__), "tray_icon.ico")
        try:
            # 32x32 turkuaz ikon oluştur
            img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Turkuaz daire
            draw.ellipse([1, 1, 30, 30], fill='#2dd4bf')
            # Beyaz H harfi
            draw.rectangle([8, 8, 11, 24], fill='white')
            draw.rectangle([21, 8, 24, 24], fill='white')
            draw.rectangle([11, 14, 21, 18], fill='white')
            img.save(tray_icon_path, format='ICO')
            print(f"[TRAY] Icon created: {tray_icon_path}")
        except Exception as e:
            print(f"[TRAY] Icon create error: {e}")
            tray_icon_path = None

        # Menü seçenekleri: (label, icon, callback)
        menu_options = (
            ("Göster", None, self._tray_show),
            ("Gizle", None, self._tray_hide),
        )

        # System tray oluştur
        try:
            self.systray = SysTrayIcon(
                tray_icon_path,
                "HYP Otomasyon",
                menu_options,
                on_quit=self._tray_quit
            )
            self.systray.start()
            print("[TRAY] Systray started successfully")
        except Exception as e:
            print(f"[TRAY] Systray error: {e}")
            import traceback
            traceback.print_exc()

    def _tray_show(self, systray):
        """Tray menüsünden Göster"""
        self.after(0, self.show_window)

    def _tray_hide(self, systray):
        """Tray menüsünden Gizle"""
        self.after(0, self.minimize_to_tray)

    def _tray_quit(self, systray):
        """Tray menüsünden Çıkış"""
        self._force_quit = True
        self.after(0, self._do_quit)

    def minimize_to_tray(self):
        """Pencereyi gizle ve system tray'de çalışmaya devam et"""
        print("[TRAY] minimize_to_tray called")  # DEBUG
        if self._is_hidden:
            print("[TRAY] Already hidden, returning")  # DEBUG
            return
        self._is_hidden = True

        try:
            # withdraw() mainloop'u durduruyor, bunun yerine:
            self._saved_geometry = self.geometry()
            print(f"[TRAY] Saved geometry: {self._saved_geometry}")  # DEBUG

            # Pencereyi ekran dışına taşı ve görev çubuğundan kaldır
            self.overrideredirect(True)
            self.geometry("1x1+-2000+-2000")

            print("[TRAY] Window hidden, starting keep_alive")  # DEBUG
            # Mainloop'u canlı tut
            self._keep_alive()
        except Exception as e:
            print(f"[TRAY] ERROR: {e}")  # DEBUG
            import traceback
            traceback.print_exc()

    def _keep_alive(self):
        """Mainloop'u canlı tut"""
        if self._is_hidden and not self._force_quit:
            self.after(500, self._keep_alive)

    def show_window(self):
        """Pencereyi göster"""
        self._is_hidden = False

        # Pencereyi geri getir
        self.overrideredirect(False)  # Normal pencere
        if hasattr(self, '_saved_geometry') and self._saved_geometry:
            self.geometry(self._saved_geometry)
        else:
            self.geometry(GUI_CONFIG["window_size"])

        self.deiconify()
        self.lift()
        self.focus_force()

        # İkonu tekrar ayarla
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "hyp_icon.ico")
            if os.path.exists(icon_path):
                self.after(100, lambda: self.iconbitmap(icon_path))
        except:
            pass

    def _do_quit(self):
        """Uygulamayı tamamen kapat"""
        # Otomasyonu durdur
        if self.is_running and self.automation:
            self.automation.stop()

        # Systray zaten shutdown oldu (on_quit callback'i çağrıldığında)
        try:
            self.destroy()
        except:
            pass
        os._exit(0)

    def create_widgets(self):
        """Modern Dashboard Arayuzu - Sol Sidebar + Sag Icerik"""

        # Ana pencere arka plan
        self.configure(fg_color=self.COLORS["bg_dark"])

        # ═══════════════════════════════════════════════════════════════
        # ANA LAYOUT: Sidebar (sol) + Icerik (sag)
        # ═══════════════════════════════════════════════════════════════
        self.main_layout = ctk.CTkFrame(self, fg_color="transparent")
        self.main_layout.pack(fill="both", expand=True)
        self.main_layout.grid_columnconfigure(0, weight=0, minsize=240)  # Sidebar
        self.main_layout.grid_columnconfigure(1, weight=1)               # Icerik
        self.main_layout.grid_rowconfigure(0, weight=1)

        # ═══════════════════════════════════════════════════════════════
        # SOL SIDEBAR
        # ═══════════════════════════════════════════════════════════════
        self.sidebar = ctk.CTkFrame(
            self.main_layout,
            width=240,
            corner_radius=0,
            fg_color=self.COLORS["sidebar_bg"],
            border_width=1,
            border_color=self.COLORS["border"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # --- Sidebar Header: Logo + Baslik ---
        sidebar_header = ctk.CTkFrame(
            self.sidebar,
            height=70,
            fg_color="transparent",
            border_width=0
        )
        sidebar_header.pack(fill="x", padx=0, pady=0)
        sidebar_header.pack_propagate(False)

        # Border alt cizgi
        header_border = ctk.CTkFrame(sidebar_header, height=1, fg_color=self.COLORS["border"])
        header_border.pack(side="bottom", fill="x")

        header_content = ctk.CTkFrame(sidebar_header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=16)

        # Logo ikonu (gradient arka plan)
        logo_frame = ctk.CTkFrame(
            header_content,
            width=40,
            height=40,
            corner_radius=10,
            fg_color=self.COLORS["primary"]
        )
        logo_frame.pack(side="left", pady=15)
        logo_frame.pack_propagate(False)

        logo_icon = ctk.CTkLabel(
            logo_frame,
            text="💊",
            font=ctk.CTkFont(size=20),
            text_color=self.COLORS["text_white"]
        )
        logo_icon.place(relx=0.5, rely=0.5, anchor="center")

        # Baslik ve versiyon
        title_container = ctk.CTkFrame(header_content, fg_color="transparent")
        title_container.pack(side="left", padx=12, pady=15)

        app_title = ctk.CTkLabel(
            title_container,
            text="HYP Otomasyon",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLORS["text_white"]
        )
        app_title.pack(anchor="w")

        version_label = ctk.CTkLabel(
            title_container,
            text=f"MEDIKAL v{self.VERSION}",
            font=ctk.CTkFont(size=9, family="Consolas"),
            text_color=self.COLORS["primary"]
        )
        version_label.pack(anchor="w")

        # --- Sidebar Navigation Menu ---
        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(fill="both", expand=True, padx=12, pady=20)

        # Aktif sayfa degiskeni
        self.active_page = ctk.StringVar(value="dashboard")

        # Menu butonlari
        self.nav_buttons = {}

        menu_items = [
            ("dashboard", "📊", "Dashboard"),
            ("hasta_sorgula", "🔍", "Hasta Sorgula"),
            ("hedef_listeleri", "📋", "Hedef Listeleri"),
            ("hesaplamalar", "🧮", "Hesaplamalar"),
        ]

        for page_id, icon, label in menu_items:
            btn = self._create_nav_button(self.nav_frame, page_id, icon, label)
            btn.pack(fill="x", pady=3)
            self.nav_buttons[page_id] = btn

        # Ayirici cizgi
        separator = ctk.CTkFrame(self.nav_frame, height=1, fg_color=self.COLORS["border"])
        separator.pack(fill="x", pady=15)

        # Alt menu
        bottom_menu = [
            ("ayarlar", "⚙️", "Ayarlar"),
            ("yardim", "❓", "Yardım"),
        ]

        for page_id, icon, label in bottom_menu:
            btn = self._create_nav_button(self.nav_frame, page_id, icon, label)
            btn.pack(fill="x", pady=3)
            self.nav_buttons[page_id] = btn

        # --- Sidebar Footer: Kullanici Profili ---
        user_frame = ctk.CTkFrame(
            self.sidebar,
            height=70,
            fg_color=self.COLORS["bg_dark"],
            corner_radius=0
        )
        user_frame.pack(fill="x", side="bottom")
        user_frame.pack_propagate(False)

        # Ust border
        user_border = ctk.CTkFrame(user_frame, height=1, fg_color=self.COLORS["border"])
        user_border.pack(side="top", fill="x")

        user_content = ctk.CTkFrame(user_frame, fg_color="transparent")
        user_content.pack(fill="both", expand=True, padx=16, pady=12)

        # Avatar
        avatar_frame = ctk.CTkFrame(
            user_content,
            width=40,
            height=40,
            corner_radius=20,
            fg_color=self.COLORS["surface_highlight"],
            border_width=1,
            border_color=self.COLORS["border"]
        )
        avatar_frame.pack(side="left")
        avatar_frame.pack_propagate(False)

        avatar_icon = ctk.CTkLabel(
            avatar_frame,
            text="👤",
            font=ctk.CTkFont(size=18)
        )
        avatar_icon.place(relx=0.5, rely=0.5, anchor="center")

        # Yesil durum noktasi
        status_dot = ctk.CTkFrame(
            user_content,
            width=10,
            height=10,
            corner_radius=5,
            fg_color=self.COLORS["success"]
        )
        status_dot.place(relx=0.12, rely=0.7)

        # Kullanici bilgisi
        user_info = ctk.CTkFrame(user_content, fg_color="transparent")
        user_info.pack(side="left", padx=10)

        user_name = ctk.CTkLabel(
            user_info,
            text="Aile Hekimi",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.COLORS["text_white"]
        )
        user_name.pack(anchor="w")

        user_role = ctk.CTkLabel(
            user_info,
            text="Sistem Aktif",
            font=ctk.CTkFont(size=10),
            text_color=self.COLORS["text_dark"]
        )
        user_role.pack(anchor="w")

        # ═══════════════════════════════════════════════════════════════
        # SAG ICERIK ALANI
        # ═══════════════════════════════════════════════════════════════
        self.content_area = ctk.CTkFrame(
            self.main_layout,
            corner_radius=0,
            fg_color=self.COLORS["bg_dark"]
        )
        self.content_area.grid(row=0, column=1, sticky="nsew")

        # --- Header ---
        self.header_frame = ctk.CTkFrame(
            self.content_area,
            height=70,
            corner_radius=0,
            fg_color=self.COLORS["sidebar_bg"],
            border_width=0
        )
        self.header_frame.pack(fill="x")
        self.header_frame.pack_propagate(False)

        # Header border
        header_bottom = ctk.CTkFrame(self.header_frame, height=1, fg_color=self.COLORS["border"])
        header_bottom.pack(side="bottom", fill="x")

        header_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_container.pack(fill="both", expand=True, padx=20)

        # Sol: Sayfa basligi + Sistem durumu
        left_header = ctk.CTkFrame(header_container, fg_color="transparent")
        left_header.pack(side="left", fill="y")

        self.page_title = ctk.CTkLabel(
            left_header,
            text="Genel Bakış",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS["text_white"]
        )
        self.page_title.pack(side="left", pady=20)

        # Dikey ayirici
        divider = ctk.CTkFrame(left_header, width=1, height=24, fg_color=self.COLORS["border"])
        divider.pack(side="left", padx=15, pady=23)

        # Sistem durumu badge
        status_badge = ctk.CTkFrame(
            left_header,
            corner_radius=6,
            fg_color="#1a2e1f",
            border_width=1,
            border_color="#22c55e"
        )
        status_badge.pack(side="left", pady=20)

        status_inner = ctk.CTkFrame(status_badge, fg_color="transparent")
        status_inner.pack(padx=10, pady=5)

        status_dot2 = ctk.CTkFrame(
            status_inner,
            width=6,
            height=6,
            corner_radius=3,
            fg_color=self.COLORS["success"]
        )
        status_dot2.pack(side="left", padx=(0, 6))

        status_text = ctk.CTkLabel(
            status_inner,
            text="Sistem Online",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.COLORS["success"]
        )
        status_text.pack(side="left")

        # Sag: Kontroller
        right_header = ctk.CTkFrame(header_container, fg_color="transparent")
        right_header.pack(side="right", fill="y")

        controls_frame = ctk.CTkFrame(
            right_header,
            corner_radius=20,
            fg_color=self.COLORS["surface_highlight"],
            border_width=1,
            border_color=self.COLORS["border"]
        )
        controls_frame.pack(pady=15)

        controls_inner = ctk.CTkFrame(controls_frame, fg_color="transparent")
        controls_inner.pack(padx=6, pady=6)

        # Tema butonu
        self.theme_button = ctk.CTkButton(
            controls_inner,
            text="🌙" if self.current_theme == "dark" else "☀️",
            command=self.toggle_theme,
            width=32,
            height=32,
            corner_radius=16,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=self.COLORS["surface"],
            text_color=self.COLORS["text_gray"]
        )
        self.theme_button.pack(side="left", padx=2)
        add_tooltip(self.theme_button, "Tema Değiştir")

        # Dikey ayirici
        div2 = ctk.CTkFrame(controls_inner, width=1, height=16, fg_color=self.COLORS["border"])
        div2.pack(side="left", padx=8)

        # Debug switch
        debug_container = ctk.CTkFrame(controls_inner, fg_color="transparent")
        debug_container.pack(side="left", padx=8)

        debug_label = ctk.CTkLabel(
            debug_container,
            text="Debug",
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS["text_dark"]
        )
        debug_label.pack(side="left", padx=(0, 6))

        self.debug_checkbox = ctk.CTkSwitch(
            debug_container,
            text="",
            variable=self.debug_mode,
            command=self.on_debug_toggle,
            width=36,
            height=18,
            progress_color=self.COLORS["primary"],
            button_color=self.COLORS["text_white"],
            fg_color=self.COLORS["border"]
        )
        self.debug_checkbox.pack(side="left")
        add_tooltip(self.debug_checkbox, "Debug modu (Açık Chrome'a bağlan)")

        # Bildirim butonu
        self.notif_button = ctk.CTkButton(
            right_header,
            text="🔔",
            width=36,
            height=36,
            corner_radius=18,
            font=ctk.CTkFont(size=16),
            fg_color="transparent",
            hover_color=self.COLORS["surface_highlight"],
            text_color=self.COLORS["text_gray"],
            command=lambda: None
        )
        self.notif_button.pack(side="right", pady=17, padx=(10, 0))

        # Ayarlar butonu
        self.settings_button = ctk.CTkButton(
            right_header,
            text="⚙️",
            width=36,
            height=36,
            corner_radius=18,
            font=ctk.CTkFont(size=16),
            fg_color="transparent",
            hover_color=self.COLORS["surface_highlight"],
            text_color=self.COLORS["text_gray"],
            command=self.open_settings
        )
        self.settings_button.pack(side="right", pady=17, padx=5)
        add_tooltip(self.settings_button, "Ayarlar")

        # --- Ana Icerik Alani ---
        self.main_content = ctk.CTkFrame(
            self.content_area,
            corner_radius=0,
            fg_color=self.COLORS["bg_dark"]
        )
        self.main_content.pack(fill="both", expand=True)

        self.main_content.grid_columnconfigure(0, weight=1, minsize=280)  # Sol hedefler
        self.main_content.grid_columnconfigure(1, weight=3)               # Sag icerik
        self.main_content.grid_rowconfigure(0, weight=1)

        # SOL PANEL - AYLIK HEDEFLER
        self.quota_frame = ctk.CTkScrollableFrame(
            self.main_content,
            corner_radius=0,
            fg_color=self.COLORS["surface"],
            border_width=1,
            border_color=self.COLORS["border"],
            label_text="  📊 AYLIK HEDEFLER",
            label_font=ctk.CTkFont(size=12, weight="bold"),
            label_text_color=self.COLORS["text_gray"]
        )
        self.quota_frame.grid(row=0, column=0, sticky="nsew", padx=(15, 8), pady=15)

        self.quota_cards = {}
        for tarama_kodu, tarama_adi in TARAMA_TIPLERI.items():
            self.create_quota_card(tarama_kodu, tarama_adi)

        # SAG PANEL - TABVIEW
        self.right_tabview = ctk.CTkTabview(
            self.main_content,
            corner_radius=12,
            border_width=1,
            border_color=self.COLORS["border"],
            fg_color=self.COLORS["surface"],
            segmented_button_fg_color=self.COLORS["surface_highlight"],
            segmented_button_selected_color=self.COLORS["primary"],
            segmented_button_selected_hover_color="#26b8a5",
            segmented_button_unselected_color=self.COLORS["surface_highlight"],
            segmented_button_unselected_hover_color=self.COLORS["card_bg"]
        )
        self.right_tabview.grid(row=0, column=1, sticky="nsew", padx=(8, 15), pady=15)

        # Sekme butonlarini stil
        self.right_tabview._segmented_button.configure(
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36
        )

        # Tab 1: Islem Kayitlari
        self.log_tab = self.right_tabview.add("📋 Kayıtlar")

        # Detaylı logları saklayacak liste
        self.detailed_logs = []
        self.minimal_log_mode = True  # Varsayılan: minimal mod

        # Log text widget
        self.log_text = ctk.CTkTextbox(
            self.log_tab,
            wrap="word",
            font=ctk.CTkFont(size=11, family="Consolas"),
            corner_radius=8,
            border_width=1,
            border_color=self.COLORS["border"],
            fg_color=self.COLORS["bg_dark"],
            text_color=self.COLORS["text_gray"]
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        # Alt buton çerçevesi
        log_btn_frame = ctk.CTkFrame(self.log_tab, fg_color="transparent")
        log_btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Detaylı Log Göster butonu
        self.detail_log_btn = ctk.CTkButton(
            log_btn_frame,
            text="📜 Detaylı Log Göster",
            command=self.show_detailed_log_popup,
            width=150,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#6c5ce7",
            hover_color="#5b4cdb"
        )
        self.detail_log_btn.pack(side="left", padx=5)

        # Log modu toggle
        self.log_mode_var = ctk.BooleanVar(value=True)
        self.log_mode_switch = ctk.CTkSwitch(
            log_btn_frame,
            text="Minimal Log",
            variable=self.log_mode_var,
            command=self.toggle_log_mode,
            font=ctk.CTkFont(size=11),
            onvalue=True,
            offvalue=False
        )
        self.log_mode_switch.pack(side="right", padx=5)

        self._setup_log_tags()

        # Tab 2: Gecmis Aylar
        self.history_tab = self.right_tabview.add("📊 Geçmiş")
        self.create_history_tab()

        # Tab 3: SMS Kapali Hastalar
        self.sms_tab = self.right_tabview.add("📱 SMS Kapalı")
        self.create_sms_kapali_tab()

        # Tab 4: Topluluk
        self.community_tab = self.right_tabview.add("👥 Topluluk")
        self.create_community_tab()

        # Tab 5: Hakkinda
        self.updates_tab = self.right_tabview.add("ℹ️ Hakkında")
        self.create_updates_tab()

        # Tab 6: Hesaplama
        self.calculator_tab = self.right_tabview.add("🧮 Hesaplama")
        self.create_calculator_tab()

        # Tab 7: Eksik Tetkik
        self.eksik_tetkik_tab = self.right_tabview.add("🩸 Eksik Tetkik")
        self.create_eksik_tetkik_tab()

        # ═══════════════════════════════════════════════════════════════
        # ALT FOOTER - KONTROL BUTONLARI
        # ═══════════════════════════════════════════════════════════════
        self.control_frame = ctk.CTkFrame(
            self.content_area,
            height=100,
            corner_radius=0,
            fg_color=self.COLORS["sidebar_bg"],
            border_width=0
        )
        self.control_frame.pack(fill="x", side="bottom")
        self.control_frame.pack_propagate(False)

        # Ust border
        control_border = ctk.CTkFrame(self.control_frame, height=1, fg_color=self.COLORS["border"])
        control_border.pack(side="top", fill="x")

        # Performans gostergesi
        self.perf_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.perf_frame.pack(pady=(12, 8))

        self.perf_label = ctk.CTkLabel(
            self.perf_frame,
            text="📊 Mevcut Oturum: 0 başarılı • 0 başarısız • 0 atlanan",
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS["text_dark"]
        )
        self.perf_label.pack()

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            self.control_frame,
            width=500,
            height=4,
            corner_radius=2,
            progress_color=self.COLORS["primary"],
            fg_color=self.COLORS["border"]
        )
        self.progress.pack(pady=(0, 12))
        self.progress.set(0)

        # Kontrol butonlari
        self.button_container = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.button_container.pack()

        # KUYRUK butonu (Hemsire entegrasyonu) - Dialog açar
        self.queue_btn = ctk.CTkButton(
            self.button_container,
            text="👩‍⚕️ HEMŞİRE",
            command=self.show_nurse_queue_dialog,
            font=ctk.CTkFont(size=13, weight="bold"),
            width=110,
            height=42,
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            corner_radius=10
        )
        self.queue_btn.pack(side="left", padx=8)
        add_tooltip(self.queue_btn, "Hemşire TC kuyruğu ve geçmişi")

        # BASLAT butonu
        self.start_button = ctk.CTkButton(
            self.button_container,
            text="▶  BAŞLAT",
            command=self.start_automation,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=150,
            height=42,
            fg_color=self.COLORS["success"],
            hover_color="#1ea54e",
            corner_radius=10,
            border_width=0
        )
        self.start_button.pack(side="left", padx=8)
        add_tooltip(self.start_button, "Otomasyonu başlat")

        # GEÇMİŞ butonu - Geçmiş tarihlerden başlat
        self.history_button = ctk.CTkButton(
            self.button_container,
            text="📅 GEÇMİŞ",
            command=self.start_automation_with_history,
            font=ctk.CTkFont(size=13, weight="bold"),
            width=110,
            height=42,
            fg_color="#e67e22",
            hover_color="#d35400",
            corner_radius=10
        )
        self.history_button.pack(side="left", padx=8)
        add_tooltip(self.history_button, "Geçmiş tarihlerden otomasyon başlat")

        # DURDUR butonu
        self.stop_button = ctk.CTkButton(
            self.button_container,
            text="◼  DURDUR",
            command=self.stop_automation,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=150,
            height=42,
            fg_color=self.COLORS["danger"],
            hover_color="#dc2626",
            corner_radius=10,
            border_width=0,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=8)
        add_tooltip(self.stop_button, "Otomasyonu durdur")

        # TEMIZLE butonu
        self.clear_button = ctk.CTkButton(
            self.button_container,
            text="🗑  TEMİZLE",
            command=self.clear_logs,
            font=ctk.CTkFont(size=13, weight="bold"),
            width=130,
            height=42,
            fg_color=self.COLORS["surface_highlight"],
            hover_color=self.COLORS["card_bg"],
            corner_radius=10,
            border_width=1,
            border_color=self.COLORS["border"],
            text_color=self.COLORS["text_gray"]
        )
        self.clear_button.pack(side="left", padx=8)
        add_tooltip(self.clear_button, "Logları temizle")

        # ═══════════════════════════════════════════════════════════════
        # HEMŞİRE TC KUYRUĞU GÖSTERİMİ
        # ═══════════════════════════════════════════════════════════════
        self.queue_display_frame = ctk.CTkFrame(
            self.control_frame,
            fg_color=self.COLORS["surface"],
            corner_radius=10,
            border_width=1,
            border_color=self.COLORS["border"]
        )
        self.queue_display_frame.pack(fill="x", pady=(12, 0))
        self.queue_display_frame.pack_forget()  # Başlangıçta gizli

        queue_header = ctk.CTkFrame(self.queue_display_frame, fg_color="transparent")
        queue_header.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            queue_header,
            text="👩‍⚕️ Bekleyen TC'ler",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.COLORS["warning"]
        ).pack(side="left")

        self.queue_count_label = ctk.CTkLabel(
            queue_header,
            text="0",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.COLORS["text_white"],
            fg_color=self.COLORS["warning"],
            corner_radius=10,
            width=24,
            height=20
        )
        self.queue_count_label.pack(side="right")

        self.queue_list_label = ctk.CTkLabel(
            self.queue_display_frame,
            text="",
            font=ctk.CTkFont(size=11, family="Consolas"),
            text_color=self.COLORS["text_gray"],
            justify="left",
            anchor="w"
        )
        self.queue_list_label.pack(fill="x", padx=12, pady=(0, 8))

    def _create_nav_button(self, parent, page_id, icon, label):
        """Sidebar navigasyon butonu olustur"""
        is_active = self.active_page.get() == page_id

        btn_frame = ctk.CTkFrame(
            parent,
            height=44,
            corner_radius=10,
            fg_color=self.COLORS["surface_highlight"] if is_active else "transparent",
            border_width=1 if is_active else 0,
            border_color=self.COLORS["border"]
        )
        btn_frame.pack_propagate(False)

        # Aktif gosterge cizgisi
        if is_active:
            indicator = ctk.CTkFrame(
                btn_frame,
                width=3,
                corner_radius=2,
                fg_color=self.COLORS["primary"]
            )
            indicator.pack(side="left", fill="y", padx=(0, 0), pady=8)

        content = ctk.CTkFrame(btn_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12)

        icon_label = ctk.CTkLabel(
            content,
            text=icon,
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS["primary"] if is_active else self.COLORS["text_dark"]
        )
        icon_label.pack(side="left", pady=10)

        text_label = ctk.CTkLabel(
            content,
            text=label,
            font=ctk.CTkFont(size=13, weight="bold" if is_active else "normal"),
            text_color=self.COLORS["primary"] if is_active else self.COLORS["text_gray"]
        )
        text_label.pack(side="left", padx=12, pady=10)

        # Tiklanabilirlik
        def on_click(e):
            self.navigate_to(page_id)

        btn_frame.bind("<Button-1>", on_click)
        content.bind("<Button-1>", on_click)
        icon_label.bind("<Button-1>", on_click)
        text_label.bind("<Button-1>", on_click)

        # Hover efekti
        def on_enter(e):
            if self.active_page.get() != page_id:
                btn_frame.configure(fg_color=self.COLORS["surface_highlight"])

        def on_leave(e):
            if self.active_page.get() != page_id:
                btn_frame.configure(fg_color="transparent")

        btn_frame.bind("<Enter>", on_enter)
        btn_frame.bind("<Leave>", on_leave)

        return btn_frame

    def navigate_to(self, page_id):
        """Sayfalar arasi navigasyon"""
        self.active_page.set(page_id)

        # Sayfa basligini guncelle
        page_titles = {
            "dashboard": "Genel Bakış",
            "hasta_sorgula": "Hasta Sorgula",
            "hedef_listeleri": "Hedef Listeleri",
            "hesaplamalar": "Hesaplamalar",
            "ayarlar": "Ayarlar",
            "yardim": "Yardım"
        }
        self.page_title.configure(text=page_titles.get(page_id, "Dashboard"))

        # Ozel sayfa aksiyonlari
        if page_id == "ayarlar":
            self.open_settings()
        elif page_id == "hesaplamalar":
            self.right_tabview.set("🧮 Hesaplama")

        # Nav butonlarini yeniden ciz
        self._refresh_nav_buttons()

    def _refresh_nav_buttons(self):
        """Navigasyon butonlarini yeniden olustur"""
        # Mevcut butonlari temizle
        for btn in self.nav_buttons.values():
            btn.destroy()
        self.nav_buttons.clear()

        # Nav frame kontrolu
        if not hasattr(self, 'nav_frame') or not self.nav_frame.winfo_exists():
            return

        # Tum cocuklari temizle
        for child in self.nav_frame.winfo_children():
            child.destroy()

        # Menu butonlarini yeniden olustur
        menu_items = [
            ("dashboard", "📊", "Dashboard"),
            ("hasta_sorgula", "🔍", "Hasta Sorgula"),
            ("hedef_listeleri", "📋", "Hedef Listeleri"),
            ("hesaplamalar", "🧮", "Hesaplamalar"),
        ]

        for page_id, icon, label in menu_items:
            btn = self._create_nav_button(self.nav_frame, page_id, icon, label)
            btn.pack(fill="x", pady=3)
            self.nav_buttons[page_id] = btn

        # Ayirici cizgi
        separator = ctk.CTkFrame(self.nav_frame, height=1, fg_color=self.COLORS["border"])
        separator.pack(fill="x", pady=15)

        # Alt menu
        bottom_menu = [
            ("ayarlar", "⚙️", "Ayarlar"),
            ("yardim", "❓", "Yardım"),
        ]

        for page_id, icon, label in bottom_menu:
            btn = self._create_nav_button(self.nav_frame, page_id, icon, label)
            btn.pack(fill="x", pady=3)
            self.nav_buttons[page_id] = btn

    def create_quota_card(self, tarama_kodu, tarama_adi):
        """Modern kota karti olustur - Referans tasarima gore"""

        # Tarama tiplerine gore ikon ve renk eslestirmesi
        card_styles = {
            "OBE_TARAMA": {"icon": "⚖️", "color": "#3b82f6"},   # Mavi
            "OBE_IZLEM": {"icon": "📊", "color": "#2dd4bf"},    # Turkuaz
            "DIY_TARAMA": {"icon": "🩸", "color": "#a855f7"},   # Mor
            "DIY_IZLEM": {"icon": "💊", "color": "#ec4899"},    # Pembe
            "HT_TARAMA": {"icon": "❤️", "color": "#f97316"},    # Turuncu
            "HT_IZLEM": {"icon": "💓", "color": "#6366f1"},     # Indigo
            "KVR_TARAMA": {"icon": "🫀", "color": "#ef4444"},   # Kirmizi
            "KVR_IZLEM": {"icon": "📈", "color": "#22c55e"},    # Yesil
            "YAS_IZLEM": {"icon": "👴", "color": "#f59e0b"},    # Amber
            "KANSER_SERVIKS": {"icon": "🎀", "color": "#f472b6"}, # Pembe
            "KANSER_MAMO": {"icon": "🩺", "color": "#e879f9"},  # Fuşya
        }

        style = card_styles.get(tarama_kodu, {"icon": "📋", "color": "#6b7280"})

        card = ctk.CTkFrame(
            self.quota_frame,
            corner_radius=12,
            fg_color=self.COLORS["surface_highlight"],
            border_width=1,
            border_color=self.COLORS["border"]
        )
        card.pack(fill="x", padx=8, pady=5)

        # Ust satir: Ikon + Badge
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 6))

        # Sol: Ikon (renkli arka plan)
        icon_bg = ctk.CTkFrame(
            top_row,
            width=32,
            height=32,
            corner_radius=8,
            fg_color=self.COLORS["surface_highlight"]
        )
        icon_bg.pack(side="left")
        icon_bg.pack_propagate(False)

        icon_label = ctk.CTkLabel(
            icon_bg,
            text=style["icon"],
            font=ctk.CTkFont(size=14),
            text_color=style["color"]
        )
        icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Sag: Durum badge (dinamik olarak güncellenecek)
        badge_frame = ctk.CTkFrame(
            top_row,
            corner_radius=4,
            fg_color=self.COLORS["border"],
            border_width=1,
            border_color=self.COLORS["border"]
        )
        badge_frame.pack(side="right")

        badge_label = ctk.CTkLabel(
            badge_frame,
            text="BEKLEMEDE",
            font=ctk.CTkFont(size=8, weight="bold"),
            text_color=self.COLORS["text_dark"]
        )
        badge_label.pack(padx=6, pady=2)

        # Baslik
        title_label = ctk.CTkLabel(
            card,
            text=tarama_adi,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.COLORS["text_gray"]
        )
        title_label.pack(anchor="w", padx=12, pady=(0, 4))

        # Sayilar: Buyuk X / kucuk Y
        saved_targets = self.settings_manager.get_monthly_targets()
        current_counts = self.settings_manager.get_current_counts()
        deferred_counts = self.settings_manager.get_deferred_counts()

        target = saved_targets.get(tarama_kodu, MONTHLY_TARGETS.get(tarama_kodu, 0))
        current = current_counts.get(tarama_kodu, 0)
        deferred = deferred_counts.get(tarama_kodu, 0)
        total_done = current + deferred

        numbers_frame = ctk.CTkFrame(card, fg_color="transparent")
        numbers_frame.pack(anchor="w", padx=12, pady=(0, 6))

        current_label = ctk.CTkLabel(
            numbers_frame,
            text=str(total_done),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS["text_white"]
        )
        current_label.pack(side="left")

        target_label = ctk.CTkLabel(
            numbers_frame,
            text=f" / {target}",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS["text_dark"]
        )
        target_label.pack(side="left", pady=(4, 0))

        # Progress bar
        progress = ctk.CTkProgressBar(
            card,
            height=5,
            corner_radius=3,
            progress_color=style["color"],
            fg_color=self.COLORS["border"]
        )
        progress.pack(fill="x", padx=12, pady=(0, 6))
        percentage = (total_done / target * 100) if target > 0 else 0
        progress.set(min(percentage / 100, 1.0))

        # Alt satir: Ilerleme % ve Kalan
        bottom_row = ctk.CTkFrame(card, fg_color="transparent")
        bottom_row.pack(fill="x", padx=12, pady=(0, 10))

        remaining = max(0, target - total_done)

        progress_pct_label = ctk.CTkLabel(
            bottom_row,
            text=f"İlerleme %{percentage:.0f}",
            font=ctk.CTkFont(size=10),
            text_color=self.COLORS["text_dark"]
        )
        progress_pct_label.pack(side="left")

        remaining_label = ctk.CTkLabel(
            bottom_row,
            text=f"Kalan: {remaining}" if remaining > 0 else "Tamamlandı",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=style["color"]
        )
        remaining_label.pack(side="right")

        # Badge ve renkleri guncelle
        self._update_card_badge(badge_frame, badge_label, percentage)

        self.quota_cards[tarama_kodu] = {
            "frame": card,
            "current_label": current_label,
            "target_label": target_label,
            "progress": progress,
            "progress_pct_label": progress_pct_label,
            "remaining_label": remaining_label,
            "badge_frame": badge_frame,
            "badge_label": badge_label,
            "style": style
        }

    def _update_card_badge(self, badge_frame, badge_label, percentage):
        """Kart badge'ini yuzdeye gore guncelle"""
        if percentage >= 100:
            badge_text = "TAMAM"
            badge_bg = "#1a2e1f"
            badge_border = "#22c55e"
            badge_text_color = "#22c55e"
        elif percentage >= 70:
            badge_text = "İYİ"
            badge_bg = "#1a2e1f"
            badge_border = "#22c55e"
            badge_text_color = "#22c55e"
        elif percentage >= 50:
            badge_text = "NORMAL"
            badge_bg = "#2e2510"
            badge_border = "#f59e0b"
            badge_text_color = "#f59e0b"
        elif percentage >= 25:
            badge_text = "DİKKAT"
            badge_bg = "#2e2510"
            badge_border = "#f59e0b"
            badge_text_color = "#f59e0b"
        elif percentage > 0:
            badge_text = "ALERT"
            badge_bg = "#2e1515"
            badge_border = "#ef4444"
            badge_text_color = "#ef4444"
        else:
            badge_text = "BEKLEMEDE"
            badge_bg = self.COLORS["border"]
            badge_border = self.COLORS["border"]
            badge_text_color = self.COLORS["text_dark"]

        badge_frame.configure(fg_color=badge_bg, border_color=badge_border)
        badge_label.configure(text=badge_text, text_color=badge_text_color)

    def update_quota_card(self, tarama_kodu, current, target, deferred=0):
        """Kota kartini guncelle"""
        if tarama_kodu not in self.quota_cards:
            return
        card = self.quota_cards[tarama_kodu]

        total_done = current + deferred
        remaining = max(0, target - total_done)
        percentage = (total_done / target * 100) if target > 0 else 0

        # Sayilari guncelle
        card["current_label"].configure(text=str(total_done))
        card["target_label"].configure(text=f" / {target}")

        # Progress bar
        card["progress"].set(min(percentage / 100, 1.0))

        # Alt satir
        card["progress_pct_label"].configure(text=f"İlerleme %{percentage:.0f}")
        card["remaining_label"].configure(
            text=f"Kalan: {remaining}" if remaining > 0 else "Tamamlandı",
            text_color=card["style"]["color"]
        )

        # Badge guncelle
        self._update_card_badge(card["badge_frame"], card["badge_label"], percentage)

    def update_all_quota_cards(self, monthly_stats, remaining_targets):
        saved_targets = self.settings_manager.get_monthly_targets()
        deferred_counts = self.settings_manager.get_deferred_counts()

        for tarama_kodu, current_count in monthly_stats.items():
            target = saved_targets.get(tarama_kodu, MONTHLY_TARGETS.get(tarama_kodu, 0))
            deferred = deferred_counts.get(tarama_kodu, 0)
            self.update_quota_card(tarama_kodu, current_count, target, deferred)

    def update_performance(self, stats):
        """Performans göstergesini güncelle"""
        text = f"📊 Bu oturum: {stats.get('basarili', 0)} başarılı | {stats.get('basarisiz', 0)} başarısız | {stats.get('atlanan', 0)} atlanan"
        self.perf_label.configure(text=text)

    def on_hyp_completed(self, hyp_tip: str, hasta_adi: str):
        """
        Bir HYP başarıyla tamamlandığında çağrılır.
        Sol paneldeki ilerlemeyi ANINDA günceller ve kaydeder.
        Thread-safe olarak ana thread'de çalışır.
        """
        def update_ui():
            try:
                # Mevcut sayıları al
                current_counts = self.settings_manager.get_current_counts()
                saved_targets = self.settings_manager.get_monthly_targets()
                deferred_counts = self.settings_manager.get_deferred_counts()

                # Sayıyı artır
                current = current_counts.get(hyp_tip, 0) + 1
                current_counts[hyp_tip] = current

                # Hemen kaydet (zaman kaybı minimumda)
                self.settings_manager.save_current_counts(current_counts)

                # UI'ı güncelle
                target = saved_targets.get(hyp_tip, MONTHLY_TARGETS.get(hyp_tip, 0))
                deferred = deferred_counts.get(hyp_tip, 0)
                self.update_quota_card(hyp_tip, current, target, deferred)

                # Log
                self.log_message(f"✅ {hasta_adi} - {hyp_tip} tamamlandı! ({current}/{target})")

            except Exception as e:
                self.log_message(f"İlerleme güncelleme hatası: {e}", "ERROR")

        # Ana thread'de çalıştır
        self.after(0, update_ui)

    def on_counts_fetched(self, counts: dict):
        """
        HYP'den sayılar çekildiğinde çağrılır.
        Sol paneldeki kota kartlarını HYP'den gelen sayılarla günceller.
        Ayrıca bu sayıları JSON'a kaydeder.
        Thread-safe olarak ana thread'de çalışır.
        """
        def update_ui():
            try:
                # 1. Gelen sayıları JSON'a kaydet
                self.settings_manager.save_current_counts(counts)

                # 2. Sol paneldeki kartları güncelle
                saved_targets = self.settings_manager.get_monthly_targets()
                deferred_counts = self.settings_manager.get_deferred_counts()

                for hyp_tip, current in counts.items():
                    target = saved_targets.get(hyp_tip, MONTHLY_TARGETS.get(hyp_tip, 0))
                    deferred = deferred_counts.get(hyp_tip, 0)
                    self.update_quota_card(hyp_tip, current, target, deferred)

                self.log_message("📊 Sol panel HYP verilerine göre güncellendi.")

            except Exception as e:
                self.log_message(f"GUI güncelleme hatası: {e}", "ERROR")

        # Ana thread'de çalıştır
        self.after(0, update_ui)

    def on_kvr_overflow(self, hasta_adi: str) -> bool:
        """
        KVR hedefi aşıldığında kullanıcıya onay popup'ı göster.

        Bu fonksiyon otomasyon thread'inden çağrılır.
        Thread-safe olmak için Event kullanır ve ana thread'de popup gösterir.

        Args:
            hasta_adi: Mevcut hasta adı (bilgi amaçlı)

        Returns:
            True: Kullanıcı onayladı - fazla KVR'ler silinsin
            False: Kullanıcı reddetti - hiçbir şey silinmesin
        """
        import threading

        # Sonucu saklamak için
        result = {"value": False}
        event = threading.Event()

        def show_popup():
            try:
                popup = ctk.CTkToplevel(self)
                popup.title("KVR Hedef Aşımı")
                popup.geometry("500x280")
                popup.resizable(False, False)

                popup.update_idletasks()
                x = (popup.winfo_screenwidth() // 2) - 250
                y = (popup.winfo_screenheight() // 2) - 140
                popup.geometry(f"500x280+{x}+{y}")

                popup.configure(fg_color="#1a1a2e")
                popup.transient(self)
                popup.grab_set()

                # Uyarı ikonu ve başlık
                ctk.CTkLabel(
                    popup,
                    text="⚠️ KVR_IZLEM HEDEFİ TUTULDU!",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#f39c12"
                ).pack(pady=(20, 10))

                # Açıklama
                ctk.CTkLabel(
                    popup,
                    text="Hipertansiyon İzlem yapılırken Kardiyovasküler Risk İzlem\nzorunlu olarak da yapılıyor.",
                    font=ctk.CTkFont(size=13),
                    text_color="#ecf0f1",
                    justify="center"
                ).pack(pady=(5, 5))

                ctk.CTkLabel(
                    popup,
                    text="Bundan sonraki fazla KVR_IZLEM'ler silinsin mi?",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#3498db"
                ).pack(pady=(10, 5))

                ctk.CTkLabel(
                    popup,
                    text="(Bu seçim oturum boyunca geçerli olacak)",
                    font=ctk.CTkFont(size=11),
                    text_color="#95a5a6"
                ).pack(pady=(0, 15))

                # Butonlar
                btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
                btn_frame.pack(pady=(10, 20))

                def on_yes():
                    result["value"] = True
                    popup.destroy()
                    event.set()

                def on_no():
                    result["value"] = False
                    popup.destroy()
                    event.set()

                ctk.CTkButton(
                    btn_frame,
                    text="✅ Evet, Sil",
                    command=on_yes,
                    width=140,
                    height=40,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    fg_color="#27ae60",
                    hover_color="#2ecc71"
                ).pack(side="left", padx=10)

                ctk.CTkButton(
                    btn_frame,
                    text="❌ Hayır, Silme",
                    command=on_no,
                    width=140,
                    height=40,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    fg_color="#e74c3c",
                    hover_color="#c0392b"
                ).pack(side="left", padx=10)

                # Pencere kapatılırsa "Hayır" olarak kabul et
                popup.protocol("WM_DELETE_WINDOW", on_no)

            except Exception as e:
                self.log_message(f"KVR popup hatası: {e}")
                result["value"] = False
                event.set()

        # Ana thread'de popup göster
        self.after(0, show_popup)

        # Kullanıcı cevap verene kadar bekle (max 60 saniye)
        event.wait(timeout=60)

        return result["value"]

    def on_debug_toggle(self):
        """Debug modu değiştiğinde"""
        if self.debug_mode.get():
            self.log_message("🔧 DEBUG MODU AKTİF")
            self.log_message("   Chrome zaten açıksa ve HYP'ye giriş yapılmışsa,")
            self.log_message("   login atlanacak ve mevcut oturuma bağlanılacak.")
        else:
            self.log_message("🔧 Debug modu kapatıldı.")

    def perform_startup_checks(self):
        """Uygulama başlangıcında 4 temel kontrolü yap ve logla"""
        # Başlık - belirgin kutu
        self.log_message("")
        self.log_message("╔══════════════════════════════════════════════════╗")
        self.log_message("║         🔍 BAŞLANGIÇ KONTROLLERİ                 ║")
        self.log_message("╠══════════════════════════════════════════════════╣")

        # 1. e-İmza Şifresi Kontrolü
        saved_pin = self.settings_manager.get_pin_code()
        if saved_pin:
            self.pin_code = saved_pin
            self.log_message("║  ✅ [1/4] e-İmza Şifresi    → Kayıtlı            ║")
        else:
            self.pin_code = None
            self.log_message("║  ❌ [1/4] e-İmza Şifresi    → Kayıtlı değil      ║")

        # 2. İlaç Listesi Kontrolü
        ilac_ok, ilac_count, ilac_path = check_ilac_listesi()
        if ilac_ok:
            ilac_name = os.path.basename(ilac_path) if ilac_path else ""
            # Dosya adını kısalt
            if len(ilac_name) > 20:
                ilac_name = ilac_name[:17] + "..."
            self.log_message(f"║  ✅ [2/4] İlaç Listesi      → {ilac_name:<18} ║")
        else:
            self.log_message("║  ❌ [2/4] İlaç Listesi      → Bulunamadı         ║")

        # 3. Gebe Listesi Kontrolü
        gebe_ok, gebe_count, gebe_path = check_gebe_listesi()
        if gebe_ok:
            gebe_name = os.path.basename(gebe_path) if gebe_path else ""
            if len(gebe_name) > 20:
                gebe_name = gebe_name[:17] + "..."
            self.log_message(f"║  ✅ [3/4] Gebe Listesi      → {gebe_name:<18} ║")
        else:
            self.log_message("║  ❌ [3/4] Gebe Listesi      → Bulunamadı         ║")

        # 4. Aylık Hedef Veriler Kontrolü
        self.settings_manager.migrate_current_to_month()
        current_month = get_current_month_key()
        month_name = get_month_display_name(current_month)

        if self.settings_manager.is_current_month_configured():
            self.log_message(f"║  ✅ [4/4] Aylık Hedefler    → {month_name:<18} ║")
        else:
            self.log_message(f"║  ❌ [4/4] Aylık Hedefler    → Eksik              ║")

        self.log_message("╠══════════════════════════════════════════════════╣")

        # Eksik kontrolleri say
        eksik_sayisi = sum([
            not saved_pin,
            not ilac_ok,
            not gebe_ok,
            not self.settings_manager.is_current_month_configured()
        ])

        if eksik_sayisi == 0:
            self.log_message("║  🎉 TÜM KONTROLLER BAŞARILI! OTOMASYON HAZIR.    ║")
        else:
            self.log_message(f"║  ⚠️  {eksik_sayisi} EKSİK KONTROL VAR! Ayarlardan düzenleyin. ║")

        self.log_message("╚══════════════════════════════════════════════════╝")
        self.log_message("")

        # Güncelleme kontrolü (arka planda)
        self.check_for_app_updates()

        # Aylık hedefler eksikse uyarı dialogu göster
        if not self.settings_manager.is_current_month_configured():
            dialog = MonthWarningDialog(
                self,
                self.settings_manager,
                on_configure_callback=self.open_settings
            )
            self.wait_window(dialog)

            if dialog.result == "configure":
                pass
            elif dialog.result == "skip":
                self.log_message(f"ℹ️ {month_name} varsayılan hedeflerle başlatıldı.")
                self.refresh_quota_cards()
            elif dialog.result == "cancel":
                self.log_message("❌ Hedef ayarı iptal edildi.")

        # ============================================================
        # AÇILIŞTA İLERLEME DURUMUNU YÜKLE
        # Sol paneldeki kota kartlarını kayıtlı değerlerle güncelle
        # ============================================================
        self.load_saved_progress()

    def load_saved_progress(self):
        """Kayıtlı ilerleme durumunu yükle ve sol paneli güncelle"""
        try:
            current_counts = self.settings_manager.get_current_counts()
            saved_targets = self.settings_manager.get_monthly_targets()
            deferred_counts = self.settings_manager.get_deferred_counts()

            # Her kota kartını güncelle
            for tarama_kodu in MONTHLY_TARGETS.keys():
                current = current_counts.get(tarama_kodu, 0)
                target = saved_targets.get(tarama_kodu, MONTHLY_TARGETS.get(tarama_kodu, 0))
                deferred = deferred_counts.get(tarama_kodu, 0)
                self.update_quota_card(tarama_kodu, current, target, deferred)

            # Toplam ilerlemeyi logla
            total_done = sum(current_counts.values())
            total_target = sum(saved_targets.values()) if saved_targets else sum(MONTHLY_TARGETS.values())
            if total_done > 0:
                self.log_message(f"📊 Kayıtlı ilerleme yüklendi: {total_done} / {total_target}")

        except Exception as e:
            self.log_message(f"İlerleme yükleme hatası: {e}", "ERROR")

    def create_history_tab(self):
        """Geçmiş aylar sekmesini oluştur"""
        # Başlık
        header_frame = ctk.CTkFrame(self.history_tab, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            header_frame,
            text="📊 AYLIK PERFORMANS GEÇMİŞİ",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left")

        # Yenile butonu
        self.refresh_history_btn = ctk.CTkButton(
            header_frame,
            text="🔄 Yenile",
            command=self.refresh_history_tab,
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.refresh_history_btn.pack(side="right")
        add_tooltip(self.refresh_history_btn, "Geçmiş ayları yenile")

        # Scrollable frame
        self.history_scroll = ctk.CTkScrollableFrame(self.history_tab, corner_radius=0)
        self.history_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # İçeriği doldur
        self.refresh_history_tab()

    def refresh_history_tab(self):
        """Geçmiş aylar sekmesini güncelle"""
        # Mevcut içeriği temizle
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        history = self.settings_manager.get_monthly_history()

        if not history:
            ctk.CTkLabel(
                self.history_scroll,
                text="Henüz geçmiş ay verisi yok.\nOtomasyon çalıştıkça veriler burada görünecek.",
                font=ctk.CTkFont(size=14),
                text_color="#95a5a6",
                justify="center"
            ).pack(pady=50, expand=True)
            return

        # Tarihe göre sırala (yeniden eskiye)
        sorted_months = sorted(history.keys(), reverse=True)

        tarama_isimleri = {
            "HT_TARAMA": "HT Tarama", "HT_IZLEM": "HT İzlem",
            "DIY_TARAMA": "DIY Tarama", "DIY_IZLEM": "DIY İzlem",
            "OBE_TARAMA": "OBE Tarama", "OBE_IZLEM": "OBE İzlem",
            "KVR_TARAMA": "KVR Tarama", "KVR_IZLEM": "KVR İzlem",
            "YAS_IZLEM": "YAŞ İzlem"
        }

        for month_key in sorted_months:
            perf = self.settings_manager.calculate_month_performance(month_key)
            if not perf:
                continue

            # Ay kartı
            card = ctk.CTkFrame(self.history_scroll, corner_radius=10)
            card.pack(fill="x", padx=5, pady=8)

            # Başlık satırı
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(10, 5))

            # Ay adı
            ctk.CTkLabel(
                header,
                text=f"📅 {perf['display_name']}",
                font=ctk.CTkFont(size=16, weight="bold")
            ).pack(side="left")

            # Yüzde
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
                header,
                text=pct_text,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=pct_color
            ).pack(side="right")

            # Özet satırı
            ctk.CTkLabel(
                card,
                text=f"Toplam: {perf['total_done']} / {perf['total_target']} hedef tamamlandı",
                font=ctk.CTkFont(size=12),
                text_color="#bdc3c7"
            ).pack(padx=15, pady=(0, 5))

            # Progress bar
            progress = ctk.CTkProgressBar(card, width=400)
            progress.pack(padx=15, pady=(0, 5))
            progress.set(min(percentage / 100, 1.0))

            # Detay frame (genişletilebilir)
            detail_frame = ctk.CTkFrame(card, fg_color="#1a252f", corner_radius=5)
            detail_frame.pack(fill="x", padx=15, pady=(5, 10))

            # Detay grid
            for i, (kod, isim) in enumerate(tarama_isimleri.items()):
                row_frame = ctk.CTkFrame(detail_frame, fg_color="transparent")
                row_frame.pack(fill="x", padx=10, pady=2)

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

                ctk.CTkLabel(row_frame, text=isim, width=100, anchor="w", font=ctk.CTkFont(size=11)).pack(side="left")
                ctk.CTkLabel(row_frame, text=f"{total}/{target}", width=60, font=ctk.CTkFont(size=11)).pack(side="left")
                ctk.CTkLabel(row_frame, text=f"%{pct:.0f}", width=50, text_color=color, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")

    def show_login_window(self):
        def on_login_success(pin, remember):
            self.pin_code = pin
            self.settings_manager.save_pin_code(pin, remember)
            self.log_message(f"✅ PIN {'kaydedildi' if remember else 'girildi'}!")
        
        login_window = LoginWindow(self, on_login_success)
        self.wait_window(login_window)
        
        if not self.pin_code:
            self.log_message("❌ PIN girilmedi. Uygulama kapatılıyor...")
            self.after(2000, self.destroy)
    
    def show_date_picker(self, return_list=False):
        dialog = DatePickerDialog(self)
        self.wait_window(dialog)
        if dialog.cancelled:
            return None
        # Çoklu tarih döndür veya tek tarih
        if return_list:
            return dialog.selected_dates if dialog.selected_dates else None
        return dialog.selected_date

    def start_automation_with_history(self):
        """Geçmiş tarih seçerek otomasyon başlat"""
        if self.is_running:
            return

        # Tarih seçici aç - ÇOKLU TARİH al
        selected_dates = self.show_date_picker(return_list=True)
        if not selected_dates:
            self.log_message("ℹ️ Tarih seçilmedi, otomasyon iptal edildi.")
            return

        # Seçilen TARİHLERİ sakla - start_automation içinde kullanılacak
        self.pre_selected_dates = selected_dates
        self.log_message(f"📅 {len(selected_dates)} tarih seçildi")

        # Normal otomasyon başlat
        self.start_automation()

    def open_settings(self):
        settings_window = SettingsWindow(self, self.settings_manager)
        self.wait_window(settings_window)
        self.refresh_quota_cards()

    def refresh_quota_cards(self):
        saved_targets = self.settings_manager.get_monthly_targets()
        current_counts = self.settings_manager.get_current_counts()
        deferred_counts = self.settings_manager.get_deferred_counts()

        for tarama_kodu in self.quota_cards:
            target = saved_targets.get(tarama_kodu, MONTHLY_TARGETS.get(tarama_kodu, 0))
            current = current_counts.get(tarama_kodu, 0)
            deferred = deferred_counts.get(tarama_kodu, 0)
            self.update_quota_card(tarama_kodu, current, target, deferred)

    def _setup_log_tags(self):
        """Log metin renklendirmesi için tag'leri ayarla"""
        try:
            # CTkTextbox iç Text widget'ına eriş
            inner_text = self.log_text._textbox

            # Renk tag'leri
            inner_text.tag_config("success", foreground="#2ecc71")  # Yeşil
            inner_text.tag_config("error", foreground="#e74c3c")    # Kırmızı
            inner_text.tag_config("warning", foreground="#f39c12")  # Turuncu
            inner_text.tag_config("debug", foreground="#95a5a6")    # Gri
            inner_text.tag_config("patient", foreground="#3498db", font=("Segoe UI", 12, "bold"))  # Mavi, kalın
            inner_text.tag_config("hyp_complete", foreground="#2ecc71", font=("Segoe UI", 12, "bold"))  # Yeşil, kalın
            inner_text.tag_config("header", foreground="#9b59b6", font=("Segoe UI", 12, "bold"))  # Mor, kalın
        except:
            pass  # Tag ayarlanamazsa sessizce devam et

    def log_message(self, message):
        """
        Log mesajı yaz - minimal ve detaylı mod desteği

        Minimal modda sadece önemli mesajlar gösterilir:
        - Hasta başlangıç/bitiş
        - HYP tamamlandı/başarısız
        - Hatalar ve uyarılar
        """
        # Her zaman detaylı loga kaydet
        if hasattr(self, 'detailed_logs'):
            self.detailed_logs.append(message)

        # Minimal modda filtreleme yap
        show_message = True
        if hasattr(self, 'minimal_log_mode') and self.minimal_log_mode:
            # Minimal modda gösterilecek mesajlar
            important_patterns = [
                "HASTA", "ISLENIYOR:", "İŞLENİYOR:",  # Hasta başlangıcı
                "tamamlandı", "TAMAMLANDI",  # Başarılı
                "başarısız", "BASARISIZ", "HATA", "hata",  # Hata
                "✅", "❌", "⚠️",  # Emoji ile işaretli önemli mesajlar
                "OTOMASYON", "OTURUM",  # Özet mesajları
                "==", "──",  # Ayraçlar
                "iptal", "İPTAL", "atlanan", "ATLANAN",  # İptal/atlama
                "Eksik", "eksik",  # Eksik tetkik
                "protokolü başladı", "protokolü tamamlandı",  # Protokol
                "🎯", "📊", "📋", "🏁",  # Önemli emojiler
            ]

            # Debug mesajları her zaman gizle
            if "🔧" in message or "[DEBUG]" in message:
                show_message = False
            # Teknik detaylar gizle
            elif "Adım" in message and "Sayfa=" in message:
                show_message = False
            elif "Bulunan butonlar" in message:
                show_message = False
            elif "xpath" in message.lower() or "element" in message.lower():
                show_message = False
            elif "tiklan" in message.lower() and "buton" not in message.lower():
                show_message = False
            else:
                # Önemli pattern içeriyorsa göster
                show_message = any(p in message for p in important_patterns)

        if not show_message:
            return

        try:
            inner_text = self.log_text._textbox
            start_index = inner_text.index("end-1c")

            # Mesajı ekle
            self.log_text.insert("end", message + "\n")

            # Etiket belirle
            tag = None
            if "✅" in message:
                tag = "success"
                if "tamamlandı" in message.lower():
                    tag = "hyp_complete"
            elif "❌" in message:
                tag = "error"
            elif "⚠️" in message:
                tag = "warning"
            elif "🔧" in message:
                tag = "debug"
            elif "ISLENIYOR:" in message or "İŞLENİYOR:" in message:
                tag = "patient"
            elif "═" in message or "╔" in message or "╠" in message or "╚" in message or "==" in message:
                tag = "header"

            # Tag uygula
            if tag:
                end_index = inner_text.index("end-1c")
                inner_text.tag_add(tag, start_index, end_index)

        except:
            self.log_text.insert("end", message + "\n")

        self.log_text.see("end")
        self.update_idletasks()
    
    def clear_logs(self):
        self.log_text.delete("1.0", "end")
        if hasattr(self, 'detailed_logs'):
            self.detailed_logs.clear()
        self.log_message("Log ekranı temizlendi.")

    def toggle_log_mode(self):
        """Log modunu değiştir (minimal/detaylı)"""
        self.minimal_log_mode = self.log_mode_var.get()
        mode_text = "Minimal" if self.minimal_log_mode else "Detaylı"
        self.log_message(f"📋 Log modu: {mode_text}")

    def show_detailed_log_popup(self):
        """Detaylı logları popup pencerede göster"""
        popup = ctk.CTkToplevel(self)
        popup.title("Detaylı Log Kayıtları")
        popup.geometry("800x600")

        # Ortala
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - 400
        y = (popup.winfo_screenheight() // 2) - 300
        popup.geometry(f"800x600+{x}+{y}")

        popup.configure(fg_color="#1a1a2e")
        popup.transient(self)

        # Başlık
        header = ctk.CTkFrame(popup, fg_color="#2c3e50", corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="📜 Detaylı Log Kayıtları",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ecf0f1"
        ).pack(pady=15)

        ctk.CTkLabel(
            header,
            text=f"Toplam {len(self.detailed_logs) if hasattr(self, 'detailed_logs') else 0} kayıt",
            font=ctk.CTkFont(size=12),
            text_color="#95a5a6"
        ).pack(pady=(0, 10))

        # Log text
        log_frame = ctk.CTkFrame(popup, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=15, pady=10)

        detail_text = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            font=ctk.CTkFont(size=10, family="Consolas"),
            corner_radius=8,
            fg_color="#0d1117",
            text_color="#c9d1d9"
        )
        detail_text.pack(fill="both", expand=True)

        # Logları ekle
        if hasattr(self, 'detailed_logs') and self.detailed_logs:
            for log in self.detailed_logs:
                detail_text.insert("end", log + "\n")
        else:
            detail_text.insert("end", "Henüz log kaydı yok.")

        # Alt butonlar
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="📋 Panoya Kopyala",
            command=lambda: self.copy_detailed_logs_to_clipboard(popup),
            width=130,
            height=35,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="💾 Dosyaya Kaydet",
            command=lambda: self.save_detailed_logs_to_file(),
            width=130,
            height=35,
            fg_color="#27ae60",
            hover_color="#219a52"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Kapat",
            command=popup.destroy,
            width=100,
            height=35,
            fg_color="#7f8c8d",
            hover_color="#636e72"
        ).pack(side="right", padx=5)

    def copy_detailed_logs_to_clipboard(self, popup=None):
        """Detaylı logları panoya kopyala"""
        if hasattr(self, 'detailed_logs') and self.detailed_logs:
            log_text = "\n".join(self.detailed_logs)
            self.clipboard_clear()
            self.clipboard_append(log_text)
            self.log_message("📋 Detaylı loglar panoya kopyalandı.")
        else:
            self.log_message("Kopyalanacak log yok.", "WARNING")

    def save_detailed_logs_to_file(self):
        """Detaylı logları dosyaya kaydet"""
        import os
        from datetime import datetime

        if not hasattr(self, 'detailed_logs') or not self.detailed_logs:
            self.log_message("Kaydedilecek log yok.", "WARNING")
            return

        # Dosya adı oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        filename = os.path.join(log_dir, f"hyp_log_{timestamp}.txt")

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("HYP Otomasyon Log Kaydı\n")
                f.write(f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                f.write("\n".join(self.detailed_logs))

            self.log_message(f"💾 Log dosyası kaydedildi: {filename}")
        except Exception as e:
            self.log_message(f"Log kaydetme hatası: {e}", "ERROR")

    # ============================================================
    # HEMSIRE DINLEYICI (Dosya Tabanli - Hizli)
    # ============================================================
    def toggle_queue_listener(self):
        """Hemsire dinleyiciyi ac/kapat"""
        if self.queue_listener_active:
            self.stop_queue_listener()
        else:
            self.start_queue_listener()

    def start_queue_listener(self):
        """Hemsire dinleyiciyi baslat"""
        self.queue_listener_active = True
        if hasattr(self, 'queue_btn'):
            self.queue_btn.configure(
                text="📡 DINLIYOR",
                fg_color="#27ae60"
            )
        self.log_message("📡 Hemsire dinleyici aktif")
        self.log_message(f"   Klasor: {self.shared_folder}")

        # Arka plan thread'i baslat
        self.queue_listener_thread = threading.Thread(
            target=self._nurse_listener_loop,
            daemon=True
        )
        self.queue_listener_thread.start()

    def stop_queue_listener(self):
        """Hemsire dinleyiciyi durdur"""
        self.queue_listener_active = False
        self.log_message("📡 Hemsire dinleyici durduruldu.")

    def show_nurse_queue_dialog(self):
        """Hemşire TC kuyruğu ve geçmişi dialogu"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Hemşire TC Takibi")
        dialog.geometry("500x600")
        dialog.resizable(False, False)

        # Ekran ortasına konumla
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 300
        dialog.geometry(f"500x600+{x}+{y}")

        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=self.COLORS["bg_dark"])

        # Başlık
        header = ctk.CTkFrame(dialog, fg_color=self.COLORS["surface"], corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="👩‍⚕️ Hemşire TC Takibi",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS["primary"]
        ).pack(pady=15)

        # Dinleyici durumu
        status_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=10)

        status_color = self.COLORS["success"] if self.queue_listener_active else self.COLORS["danger"]
        status_text = "● Dinleyici Aktif" if self.queue_listener_active else "● Dinleyici Kapalı"

        self.listener_status_label = ctk.CTkLabel(
            status_frame,
            text=status_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=status_color
        )
        self.listener_status_label.pack(side="left")

        # Dinleyici aç/kapa butonu
        toggle_btn = ctk.CTkButton(
            status_frame,
            text="Kapat" if self.queue_listener_active else "Başlat",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=self.COLORS["danger"] if self.queue_listener_active else self.COLORS["success"],
            command=lambda: self._toggle_listener_from_dialog(dialog, toggle_btn)
        )
        toggle_btn.pack(side="right")

        # ═══════════════════════════════════════════════════════════════
        # KUYRUKTA BEKLEYENLER
        # ═══════════════════════════════════════════════════════════════
        queue_section = ctk.CTkFrame(dialog, fg_color=self.COLORS["surface"], corner_radius=10)
        queue_section.pack(fill="x", padx=20, pady=(10, 5))

        queue_header = ctk.CTkFrame(queue_section, fg_color="transparent")
        queue_header.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            queue_header,
            text="⏳ Kuyrukta Bekleyenler",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS["warning"]
        ).pack(side="left")

        queue_count = ctk.CTkLabel(
            queue_header,
            text=str(len(self.tc_queue)),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.COLORS["text_white"],
            fg_color=self.COLORS["warning"],
            corner_radius=10,
            width=30,
            height=22
        )
        queue_count.pack(side="right")

        # Kuyruk listesi
        queue_list_frame = ctk.CTkFrame(queue_section, fg_color=self.COLORS["bg_dark"], corner_radius=8)
        queue_list_frame.pack(fill="x", padx=15, pady=(5, 15))

        if self.tc_queue:
            for tc in self.tc_queue:
                tc_row = ctk.CTkFrame(queue_list_frame, fg_color="transparent")
                tc_row.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(
                    tc_row,
                    text=f"📋 {tc}",
                    font=ctk.CTkFont(size=12, family="Consolas"),
                    text_color=self.COLORS["text_gray"]
                ).pack(side="left")
        else:
            ctk.CTkLabel(
                queue_list_frame,
                text="Kuyruk boş",
                font=ctk.CTkFont(size=11),
                text_color=self.COLORS["text_dark"]
            ).pack(pady=10)

        # ═══════════════════════════════════════════════════════════════
        # TAMAMLANAN İŞLEMLER
        # ═══════════════════════════════════════════════════════════════
        history_section = ctk.CTkFrame(dialog, fg_color=self.COLORS["surface"], corner_radius=10)
        history_section.pack(fill="both", expand=True, padx=20, pady=(5, 10))

        history_header = ctk.CTkFrame(history_section, fg_color="transparent")
        history_header.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            history_header,
            text="✅ Tamamlanan İşlemler",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS["success"]
        ).pack(side="left")

        history_count = ctk.CTkLabel(
            history_header,
            text=str(len(self.nurse_tc_history)),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.COLORS["text_white"],
            fg_color=self.COLORS["success"],
            corner_radius=10,
            width=30,
            height=22
        )
        history_count.pack(side="right")

        # Geçmiş listesi (scrollable)
        history_scroll = ctk.CTkScrollableFrame(
            history_section,
            fg_color=self.COLORS["bg_dark"],
            corner_radius=8,
            height=250
        )
        history_scroll.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        if self.nurse_tc_history:
            for tc, tarih, durum in reversed(self.nurse_tc_history):  # En son en üstte
                row = ctk.CTkFrame(history_scroll, fg_color=self.COLORS["surface_highlight"], corner_radius=6)
                row.pack(fill="x", pady=2)

                status_icon = "✅" if durum == "success" else "⚠️"
                status_color = self.COLORS["success"] if durum == "success" else self.COLORS["warning"]

                ctk.CTkLabel(
                    row,
                    text=f"{status_icon} {tc}",
                    font=ctk.CTkFont(size=12, family="Consolas", weight="bold"),
                    text_color=status_color
                ).pack(side="left", padx=10, pady=8)

                ctk.CTkLabel(
                    row,
                    text=tarih,
                    font=ctk.CTkFont(size=10),
                    text_color=self.COLORS["text_dark"]
                ).pack(side="right", padx=10, pady=8)
        else:
            ctk.CTkLabel(
                history_scroll,
                text="Henüz işlem yapılmadı",
                font=ctk.CTkFont(size=11),
                text_color=self.COLORS["text_dark"]
            ).pack(pady=20)

        # Alt butonlar
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="🗑️ Geçmişi Temizle",
            width=140,
            height=36,
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS["surface_highlight"],
            hover_color=self.COLORS["card_bg"],
            text_color=self.COLORS["text_gray"],
            command=lambda: self._clear_nurse_history(dialog)
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Kapat",
            width=100,
            height=36,
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS["primary"],
            command=dialog.destroy
        ).pack(side="right")

    def _toggle_listener_from_dialog(self, dialog, btn):
        """Dialog içinden dinleyiciyi aç/kapat"""
        if self.queue_listener_active:
            self.stop_queue_listener()
            btn.configure(text="Başlat", fg_color=self.COLORS["success"])
            self.listener_status_label.configure(
                text="● Dinleyici Kapalı",
                text_color=self.COLORS["danger"]
            )
        else:
            self.start_queue_listener()
            btn.configure(text="Kapat", fg_color=self.COLORS["danger"])
            self.listener_status_label.configure(
                text="● Dinleyici Aktif",
                text_color=self.COLORS["success"]
            )

    def _clear_nurse_history(self, dialog):
        """Hemşire geçmişini temizle"""
        self.nurse_tc_history = []
        dialog.destroy()
        self.show_nurse_queue_dialog()  # Dialogu yeniden aç

    def _nurse_listener_loop(self):
        """Hemsire TC dosyalarini dinle (her 200ms)"""
        import time
        import os

        while self.queue_listener_active:
            try:
                # Klasor var mi?
                if not os.path.exists(self.shared_folder):
                    time.sleep(1)
                    continue

                # Önce kuyrukta bekleyen TC'leri topla
                pending_tcs = []
                for filename in os.listdir(self.shared_folder):
                    if filename.endswith('.tc'):
                        tc = filename[:-3]
                        if len(tc) == 11 and tc.isdigit():
                            pending_tcs.append(tc)

                # Kuyruk değiştiyse GUI'yi güncelle
                if pending_tcs != self.tc_queue:
                    self.tc_queue = pending_tcs.copy()
                    self.after(0, self._update_queue_display)

                # Otomasyon çalışmıyorsa ve kuyrukta TC varsa - KUYRUK OTOMASYONU BASLAT
                if pending_tcs and not self.is_running:
                    # Kuyruk otomasyonunu başlat (tek Chrome oturumunda tüm kuyruğu işler)
                    self.after(0, self._start_queue_automation)

                    # İşlem bitene kadar bekle
                    time.sleep(1)  # İşlemin başlamasını bekle
                    while self.automation_thread and self.automation_thread.is_alive():
                        time.sleep(0.5)
                        if not self.queue_listener_active:
                            break

            except Exception as e:
                pass  # Sessizce devam et

            # 200ms bekle (hizli polling)
            time.sleep(0.2)

    def _update_queue_display(self):
        """Kuyruk gösterimini güncelle"""
        try:
            count = len(self.tc_queue)

            if count == 0:
                # Kuyruk boşsa gizle
                self.queue_display_frame.pack_forget()
            else:
                # Kuyruk doluysa göster
                self.queue_display_frame.pack(fill="x", pady=(12, 0))
                self.queue_count_label.configure(text=str(count))

                # TC listesini göster (max 5 tane)
                if count <= 5:
                    tc_list = "\n".join([f"• {tc}" for tc in self.tc_queue])
                else:
                    tc_list = "\n".join([f"• {tc}" for tc in self.tc_queue[:5]])
                    tc_list += f"\n... ve {count - 5} tane daha"

                self.queue_list_label.configure(text=tc_list)
        except Exception as e:
            print(f"[QUEUE] Display update error: {e}")

    def _start_queue_automation(self):
        """Kuyruk otomasyonunu baslat - TEK CHROME OTURUMUNDA TUM KUYRUGU ISLE"""
        if self.is_running:
            return  # Zaten calisiyor

        # Otomasyon baslat
        self.is_running = True
        self.start_button.configure(state="disabled")
        self.history_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        def run_queue_automation():
            try:
                import config as cfg
                cfg.PIN_CODE = self.pin_code

                # Otomasyon nesnesi olustur
                self.automation = HYPAutomation(
                    log_callback=self.log_message,
                    stats_callback=self.update_all_quota_cards
                )

                # Canli ilerleme callback
                self.automation.on_hyp_success_callback = self.on_hyp_completed
                self.automation.on_counts_fetched_callback = self.on_counts_fetched

                # Driver baslat
                self.log_message("🌐 Chrome başlatılıyor...")
                if not self.automation.setup_driver(debug_mode=self.debug_mode.get()):
                    self.log_message("❌ Chrome başlatılamadı!")
                    return

                # Login
                self.log_message("🔐 HYP'ye giriş yapılıyor...")
                has_saved_pin = self.pin_code is not None and len(self.pin_code) > 0

                if not self.automation.login(auto_pin=has_saved_pin):
                    self.log_message("❌ Login başarısız! Lütfen manuel giriş yapın.")
                    return

                self.log_message("✅ HYP'ye giriş başarılı!")

                # ============================================================
                # KUYRUK DONGUSU - Kuyruk bosalana kadar devam et
                # ============================================================
                processed_count = 0
                while self.queue_listener_active:
                    # Kuyruktan TC al
                    tc = self._get_next_tc_from_queue()
                    if not tc:
                        # Kuyruk bos, biraz bekle belki yeni TC gelir
                        import time
                        time.sleep(2)
                        tc = self._get_next_tc_from_queue()
                        if not tc:
                            # Hala bos, donguden cik
                            break

                    # TC'yi isle
                    self.log_message(f"")
                    self.log_message(f"{'='*50}")
                    self.log_message(f"📋 TC: {tc}")
                    self.log_message(f"{'='*50}")

                    success = self.automation.process_patient(tc)
                    processed_count += 1

                    # Hasta adini al
                    hasta_adi = getattr(self.automation, 'current_patient_name', '') or tc

                    # Gecmise kaydet
                    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
                    durum = "success" if success else "warning"
                    self.nurse_tc_history.append((tc, tarih, durum))

                    # Hemsireye bildirim gonder
                    if success:
                        self.log_message(f"✅ TC {tc} - HYP'ler tamamlandı!")
                        send_nurse_notification(
                            self.shared_folder, tc, "success",
                            f"{hasta_adi} hastanın HYP'leri başarıyla yapıldı!",
                            hasta_adi=hasta_adi
                        )
                    else:
                        # Basarisizlik nedenini belirle
                        cancelled_hyps = self.automation.get_cancelled_hyps() if hasattr(self.automation, 'get_cancelled_hyps') else []
                        sms_kapali = False
                        eksik_tetkikler = []

                        for hyp in cancelled_hyps:
                            if hyp.get('sms_gerekli'):
                                sms_kapali = True
                            if hyp.get('eksik_tetkikler'):
                                eksik_tetkikler.extend(hyp.get('eksik_tetkikler', []))

                        if sms_kapali:
                            self.log_message(f"⚠️ TC {tc} - SMS onayı kapalı!")
                            send_nurse_notification(
                                self.shared_folder, tc, "sms_kapali",
                                f"{hasta_adi} hastanın HYP'leri yapılamadı çünkü SMS onayı kapalı!",
                                hasta_adi=hasta_adi
                            )
                        elif eksik_tetkikler:
                            eksik_tetkikler = list(set(eksik_tetkikler))
                            tetkik_listesi = ", ".join(eksik_tetkikler[:5])
                            if len(eksik_tetkikler) > 5:
                                tetkik_listesi += f" ve {len(eksik_tetkikler)-5} tane daha"
                            self.log_message(f"⚠️ TC {tc} - Eksik tetkikler: {tetkik_listesi}")
                            send_nurse_notification(
                                self.shared_folder, tc, "eksik_tetkik",
                                f"{hasta_adi} hastanın HYP'leri yapılamadı çünkü şu tetkikler eksik: {tetkik_listesi}",
                                hasta_adi=hasta_adi,
                                eksik_tetkikler=eksik_tetkikler
                            )
                        else:
                            self.log_message(f"⚠️ TC {tc} - İşlem tamamlanamadı")
                            send_nurse_notification(
                                self.shared_folder, tc, "error",
                                f"{hasta_adi} hastanın HYP'leri yapılamadı!",
                                hasta_adi=hasta_adi
                            )

                # Kuyruk bitti
                self.log_message(f"🏁 Kuyruk tamamlandı! ({processed_count} hasta işlendi)")

                # Chrome'u kapat
                try:
                    if self.automation and self.automation.driver:
                        self.automation.driver.quit()
                        self.log_message("🔒 Chrome kapatıldı")
                except Exception as e:
                    print(f"Chrome kapatma hatasi (normal): {e}")

            except Exception as e:
                self.log_message(f"❌ Hata: {e}")
                import traceback
                traceback.print_exc()

                # Hata durumunda Chrome'u kapat
                try:
                    if self.automation and self.automation.driver:
                        self.automation.driver.quit()
                except Exception as e:
                    print(f"Chrome kapatma hatasi (hata durumu): {e}")

            finally:
                self.is_running = False
                self.automation = None
                self.after(0, lambda: self.start_button.configure(state="normal"))
                self.after(0, lambda: self.history_button.configure(state="normal"))
                self.after(0, lambda: self.stop_button.configure(state="disabled"))

        self.automation_thread = threading.Thread(target=run_queue_automation, daemon=True)
        self.automation_thread.start()

    def _get_next_tc_from_queue(self):
        """Kuyruktan siradaki TC'yi al ve dosyasini sil"""
        import os
        try:
            if not os.path.exists(self.shared_folder):
                return None

            for filename in os.listdir(self.shared_folder):
                if filename.endswith('.tc'):
                    tc = filename[:-3]
                    if len(tc) == 11 and tc.isdigit():
                        # Dosyayi sil
                        tc_file = os.path.join(self.shared_folder, filename)
                        try:
                            os.remove(tc_file)
                        except:
                            continue

                        # Kuyruktan cikar ve GUI guncelle
                        if tc in self.tc_queue:
                            self.tc_queue.remove(tc)
                        self.after(0, self._update_queue_display)
                        return tc
        except:
            pass
        return None

    def _process_nurse_tc(self, tc):
        """Hemsireden gelen TC'yi isle"""
        self.log_message(f"")
        self.log_message(f"{'='*50}")
        self.log_message(f"👩‍⚕️ HEMŞİRE FİZİKİ BULGU GİRDİ!")
        self.log_message(f"📋 TC: {tc}")
        self.log_message(f"🚀 HYP'ler yapılıyor...")
        self.log_message(f"{'='*50}")

        # TC ile otomasyon baslat
        self._start_tc_automation(tc)

    def _start_tc_automation(self, tc):
        """TC ile tek hasta otomasyonu baslat - Normal otomasyon akışı gibi"""
        if not tc or len(tc) != 11:
            self.log_message(f"❌ Geçersiz TC: {tc}")
            return

        # Otomasyon zaten çalışıyor mu?
        if self.is_running:
            self.log_message(f"⏳ Otomasyon çalışıyor, TC kuyruğa alındı: {tc}")
            # Dosyayı tekrar oluştur (kuyrukta kalsın)
            try:
                tc_file = os.path.join(self.shared_folder, f"{tc}.tc")
                with open(tc_file, 'w') as f:
                    f.write("")
            except:
                pass
            return

        # Otomasyon başlat
        self.is_running = True
        self.start_button.configure(state="disabled")
        self.history_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        def run_tc_automation():
            try:
                import config as cfg
                cfg.PIN_CODE = self.pin_code

                # Otomasyon nesnesi oluştur
                self.automation = HYPAutomation(
                    log_callback=self.log_message,
                    stats_callback=self.update_all_quota_cards
                )

                # Canlı ilerleme callback
                self.automation.on_hyp_success_callback = self.on_hyp_completed
                self.automation.on_counts_fetched_callback = self.on_counts_fetched

                # Driver başlat (debug modda açık Chrome'a bağlan veya yeni aç)
                self.log_message("🌐 Chrome başlatılıyor...")
                if not self.automation.setup_driver(debug_mode=self.debug_mode.get()):
                    self.log_message("❌ Chrome başlatılamadı!")
                    return

                # Login kontrolü ve login işlemi
                self.log_message("🔐 HYP'ye giriş yapılıyor...")
                has_saved_pin = self.pin_code is not None and len(self.pin_code) > 0

                if not self.automation.login(auto_pin=has_saved_pin):
                    self.log_message("❌ Login başarısız! Lütfen manuel giriş yapın.")
                    return

                self.log_message("✅ HYP'ye giriş başarılı!")
                self.log_message(f"🔍 Hasta aranıyor: TC {tc}")

                # TC ile hasta işle
                success = self.automation.process_patient(tc)

                # Hasta adını al
                hasta_adi = getattr(self.automation, 'current_patient_name', '') or tc

                # Geçmişe kaydet
                tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
                durum = "success" if success else "warning"
                self.nurse_tc_history.append((tc, tarih, durum))

                # Hemşireye bildirim gönder
                if success:
                    self.log_message(f"✅ TC {tc} - HYP'ler tamamlandı!")
                    send_nurse_notification(
                        self.shared_folder, tc, "success",
                        f"{hasta_adi} hastanın HYP'leri başarıyla yapıldı!",
                        hasta_adi=hasta_adi
                    )
                else:
                    # Başarısızlık nedenini belirle
                    cancelled_hyps = self.automation.get_cancelled_hyps() if hasattr(self.automation, 'get_cancelled_hyps') else []

                    # Son iptal edilen HYP'yi kontrol et
                    sms_kapali = False
                    eksik_tetkikler = []

                    for hyp in cancelled_hyps:
                        if hyp.get('sms_gerekli'):
                            sms_kapali = True
                        if hyp.get('eksik_tetkikler'):
                            eksik_tetkikler.extend(hyp.get('eksik_tetkikler', []))

                    # SMS kapalı mı kontrol et
                    if sms_kapali or (hasattr(self.automation, '_is_sms_kapali_hasta') and
                                      self.automation._is_sms_kapali_hasta(tc)):
                        self.log_message(f"⚠️ TC {tc} - SMS onayı kapalı!")
                        send_nurse_notification(
                            self.shared_folder, tc, "sms_kapali",
                            f"{hasta_adi} hastanın HYP'leri yapılamadı çünkü SMS onayı kapalı!",
                            hasta_adi=hasta_adi
                        )
                    elif eksik_tetkikler:
                        # Tekrar eden tetkikleri kaldır
                        eksik_tetkikler = list(set(eksik_tetkikler))
                        tetkik_listesi = ", ".join(eksik_tetkikler[:5])  # Max 5 tane göster
                        if len(eksik_tetkikler) > 5:
                            tetkik_listesi += f" ve {len(eksik_tetkikler)-5} tane daha"

                        self.log_message(f"⚠️ TC {tc} - Eksik tetkikler: {tetkik_listesi}")
                        send_nurse_notification(
                            self.shared_folder, tc, "eksik_tetkik",
                            f"{hasta_adi} hastanın HYP'leri yapılamadı çünkü şu tetkikler eksik: {tetkik_listesi}",
                            hasta_adi=hasta_adi,
                            eksik_tetkikler=eksik_tetkikler
                        )
                    else:
                        self.log_message(f"⚠️ TC {tc} - İşlem tamamlanamadı")
                        send_nurse_notification(
                            self.shared_folder, tc, "error",
                            f"{hasta_adi} hastanın HYP'leri yapılamadı!",
                            hasta_adi=hasta_adi
                        )

                self.log_message("🏁 Hemşire TC işlemi tamamlandı!")

                # Chrome'u kapat (hemşire TC'leri için)
                try:
                    if self.automation and self.automation.driver:
                        self.automation.driver.quit()
                        self.log_message("🔒 Chrome kapatıldı")
                except Exception as e:
                    print(f"Chrome kapatma hatasi (hemsire TC): {e}")

            except Exception as e:
                self.log_message(f"❌ Hata: {e}")
                import traceback
                traceback.print_exc()
                # Hata durumunda da geçmişe ekle
                tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
                self.nurse_tc_history.append((tc, tarih, "error"))

                # Hata bildirimini hemşireye gönder
                send_nurse_notification(
                    self.shared_folder, tc, "error",
                    f"TC {tc} için sistem hatası oluştu!",
                    hasta_adi=tc
                )

                # Hata durumunda da Chrome'u kapat
                try:
                    if self.automation and self.automation.driver:
                        self.automation.driver.quit()
                except Exception as e:
                    print(f"Chrome kapatma hatasi (hemsire TC hata): {e}")

            finally:
                self.is_running = False
                self.automation = None  # Referansı temizle
                self.after(0, lambda: self.start_button.configure(state="normal"))
                self.after(0, lambda: self.history_button.configure(state="normal"))
                self.after(0, lambda: self.stop_button.configure(state="disabled"))

        self.automation_thread = threading.Thread(target=run_tc_automation, daemon=True)
        self.automation_thread.start()

    def show_target_selection_dialog(self):
        """
        Hedef yüzdesi ve HYP tipi seçim dialogu göster.
        Returns: dict {"percentage": 70/100, "enabled_hyp_types": list} veya None
        """
        result = {"value": None}

        dialog = ctk.CTkToplevel(self)
        dialog.title("Otomasyon Ayarları")
        dialog.geometry("550x680")
        dialog.resizable(False, False)

        # Ekran ortasına konumla
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 275
        y = (dialog.winfo_screenheight() // 2) - 340
        dialog.geometry(f"550x680+{x}+{y}")

        dialog.transient(self)
        dialog.grab_set()

        # Ana frame
        main_frame = ctk.CTkFrame(dialog, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # ========== BÖLÜM 1: HEDEF YÜZDESİ ==========
        ctk.CTkLabel(
            main_frame,
            text="🎯 Hedef Yüzdesi Seçin",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            main_frame,
            text="Bir yüzde seçin - otomasyon hemen başlayacak",
            font=ctk.CTkFont(size=13),
            text_color="#95a5a6"
        ).pack(pady=(0, 10))

        # Yüzde seçim değişkeni
        selected_percentage = ctk.IntVar(value=100)

        # Buton frame
        percentage_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        percentage_frame.pack(pady=10)

        def start_with_percentage(percentage):
            """Yüzde seçilince otomatik başlat"""
            selected_percentage.set(percentage)
            # Seçili HYP tiplerini al
            enabled_types = [code for code, var in hyp_vars.items() if var.get()]
            if not enabled_types:
                # En az bir HYP tipi seçilmeli - hepsini seç
                for var in hyp_vars.values():
                    var.set(True)
                enabled_types = list(hyp_vars.keys())

            result["value"] = {
                "percentage": percentage,
                "enabled_hyp_types": enabled_types
            }
            dialog.destroy()

        def select_70():
            start_with_percentage(70)

        def select_100():
            start_with_percentage(100)

        def update_percentage_buttons():
            pass  # Artık kullanılmıyor

        # %70 Butonu - Tıklayınca başlar
        btn_70 = ctk.CTkButton(
            percentage_frame,
            text="🟡 %70 BAŞLAT",
            command=select_70,
            width=160,
            height=55,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#f39c12",
            hover_color="#e67e22",
            corner_radius=12
        )
        btn_70.pack(side="left", padx=10)

        # %100 Butonu - Tıklayınca başlar
        btn_100 = ctk.CTkButton(
            percentage_frame,
            text="🟢 %100 BAŞLAT",
            command=select_100,
            width=160,
            height=55,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            corner_radius=12
        )
        btn_100.pack(side="left", padx=10)

        # Ayırıcı çizgi
        separator = ctk.CTkFrame(main_frame, height=2, fg_color="#3d5a80")
        separator.pack(fill="x", padx=20, pady=15)

        # ========== BÖLÜM 2: HYP TİPİ SEÇİMİ ==========
        ctk.CTkLabel(
            main_frame,
            text="📋 Yapılacak HYP Tiplerini Seçin",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(5, 5))

        ctk.CTkLabel(
            main_frame,
            text="İstemediğiniz HYP tiplerinin tikini kaldırabilirsiniz",
            font=ctk.CTkFont(size=12),
            text_color="#95a5a6"
        ).pack(pady=(0, 10))

        # Tümünü Seç / Tümünü Kaldır butonları
        select_buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        select_buttons_frame.pack(pady=(0, 10))

        # HYP tipi checkbox'ları için değişkenler (varsayılan hepsi seçili)
        hyp_checkboxes = {}
        hyp_vars = {}

        for hyp_code in TARAMA_TIPLERI.keys():
            hyp_vars[hyp_code] = ctk.BooleanVar(value=True)

        def select_all():
            for var in hyp_vars.values():
                var.set(True)

        def deselect_all():
            for var in hyp_vars.values():
                var.set(False)

        ctk.CTkButton(
            select_buttons_frame,
            text="✅ Tümünü Seç",
            command=select_all,
            width=120,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            corner_radius=8
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            select_buttons_frame,
            text="❌ Tümünü Kaldır",
            command=deselect_all,
            width=120,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#e74c3c",
            hover_color="#c0392b",
            corner_radius=8
        ).pack(side="left", padx=5)

        # Scrollable frame for checkboxes
        checkbox_frame = ctk.CTkScrollableFrame(
            main_frame,
            height=280,
            corner_radius=10,
            fg_color="#1a1a2e"
        )
        checkbox_frame.pack(fill="x", padx=20, pady=5)

        # 2 sütunlu grid layout
        checkbox_frame.grid_columnconfigure(0, weight=1)
        checkbox_frame.grid_columnconfigure(1, weight=1)

        # HYP tiplerini kategorilere ayır
        hyp_categories = {
            "Obezite": ["OBE_TARAMA", "OBE_IZLEM"],
            "Diyabet": ["DIY_TARAMA", "DIY_IZLEM"],
            "Hipertansiyon": ["HT_TARAMA", "HT_IZLEM"],
            "Kardiyovasküler": ["KVR_TARAMA", "KVR_IZLEM"],
            "Yaşlı Sağlığı": ["YAS_IZLEM"],
            "Kanser Tarama": ["KANSER_SERVIKS", "KANSER_MAMO"]
        }

        row_idx = 0
        for category, hyp_codes in hyp_categories.items():
            # Kategori başlığı
            category_label = ctk.CTkLabel(
                checkbox_frame,
                text=f"━━ {category} ━━",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#00d4aa"
            )
            category_label.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
            row_idx += 1

            # Bu kategorideki HYP tipleri
            col = 0
            for hyp_code in hyp_codes:
                if hyp_code in TARAMA_TIPLERI:
                    hyp_name = TARAMA_TIPLERI[hyp_code]

                    cb = ctk.CTkCheckBox(
                        checkbox_frame,
                        text=hyp_name,
                        variable=hyp_vars[hyp_code],
                        font=ctk.CTkFont(size=13),
                        checkbox_width=22,
                        checkbox_height=22,
                        corner_radius=5,
                        border_width=2,
                        fg_color="#27ae60",
                        hover_color="#2ecc71",
                        border_color="#3d5a80"
                    )
                    cb.grid(row=row_idx, column=col, sticky="w", padx=15, pady=3)
                    hyp_checkboxes[hyp_code] = cb

                    col += 1
                    if col >= 2:
                        col = 0
                        row_idx += 1

            if col != 0:
                row_idx += 1

        # Uyarı metni
        warning_label = ctk.CTkLabel(
            main_frame,
            text="⚠️ Seçili olmayan HYP tipleri bu oturumda atlanacaktır",
            font=ctk.CTkFont(size=11),
            text_color="#f39c12"
        )
        warning_label.pack(pady=(10, 5))

        # ========== ALT BUTONLAR ==========
        bottom_button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        bottom_button_frame.pack(pady=(15, 10))

        def cancel():
            result["value"] = None
            dialog.destroy()

        # İPTAL butonu (ortada)
        ctk.CTkButton(
            bottom_button_frame,
            text="❌ İPTAL",
            command=cancel,
            width=150,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#7f8c8d",
            hover_color="#95a5a6",
            corner_radius=12
        ).pack()

        # Dialog kapanana kadar bekle
        dialog.wait_window()

        return result["value"]

    def start_automation(self):
        if self.is_running:
            return

        # Hedef yüzdesi ve HYP tipi seçimi dialogunu göster
        dialog_result = self.show_target_selection_dialog()
        if dialog_result is None:
            self.log_message("ℹ️ Otomasyon iptal edildi.")
            return

        # Dialog sonuçlarını al
        target_percentage = dialog_result["percentage"]
        enabled_hyp_types = dialog_result["enabled_hyp_types"]

        self.target_percentage = target_percentage
        self.enabled_hyp_types = enabled_hyp_types

        # PIN yoksa manuel mod - sorun değil, devam et
        if not self.pin_code:
            self.log_message("ℹ️ PIN kaydedilmemiş - e-İmza ekranında manuel girilecek")

        self.is_running = True
        self.start_button.configure(state="disabled")
        self.history_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress.set(0)

        # GUI güncelleme timer'ını başlat
        self._start_gui_refresh_timer()

        self.log_message("=" * 50)
        self.log_message("🚀 OTOMASYON BAŞLATILIYOR...")
        self.log_message(f"🎯 Hedef Yüzdesi: %{target_percentage}")

        # Seçili HYP tiplerini logla
        disabled_types = [t for t in TARAMA_TIPLERI.keys() if t not in enabled_hyp_types]
        if disabled_types:
            self.log_message(f"📋 Aktif HYP Tipleri: {len(enabled_hyp_types)}/{len(TARAMA_TIPLERI)}")
            disabled_names = [TARAMA_TIPLERI.get(t, t) for t in disabled_types]
            self.log_message(f"⏭️ Devre Dışı: {', '.join(disabled_names)}")
        else:
            self.log_message("📋 Tüm HYP Tipleri Aktif")

        if self.debug_mode.get():
            self.log_message("🔧 DEBUG MODU: Login atlanabilir")
        self.log_message("=" * 50)

        def run_thread():
            try:
                import config as cfg
                cfg.PIN_CODE = self.pin_code

                self.automation = HYPAutomation(
                    log_callback=self.log_message,
                    date_picker_callback=self.show_date_picker,
                    stats_callback=self.update_all_quota_cards
                )

                # Eğer GEÇMİŞ butonundan seçilmiş TARİHLER varsa ayarla
                if hasattr(self, 'pre_selected_dates') and self.pre_selected_dates:
                    self.automation.selected_dates = self.pre_selected_dates
                    self.log_message(f"📅 Seçilen Tarihler: {len(self.pre_selected_dates)} gün")
                    for d in self.pre_selected_dates:
                        self.log_message(f"   - {d.strftime('%d.%m.%Y')}")
                    self.pre_selected_dates = None  # Temizle

                # Hedef yüzdesini ayarla
                self.automation.target_percentage = self.target_percentage

                # Aktif HYP tiplerini ayarla
                self.automation.enabled_hyp_types = self.enabled_hyp_types

                # Canlı ilerleme callback'ini ayarla
                self.automation.on_hyp_success_callback = self.on_hyp_completed

                # HYP'den sayılar çekildiğinde GUI güncelleme callback
                self.automation.on_counts_fetched_callback = self.on_counts_fetched

                # KVR otomatik silme ayarı callback'i (Ayarlar > Otomasyon Ayarları'ndan kontrol edilir)
                self.automation.get_kvr_decision_callback = self.settings_manager.get_auto_delete_kvr

                # PIN kaydedilmiş mi kontrol et
                # PIN varsa otomatik girilir, yoksa manuel beklenir
                has_saved_pin = self.pin_code is not None and len(self.pin_code) > 0

                # Debug modunu geç
                self.automation.run_automation(
                    debug_mode=self.debug_mode.get(),
                    auto_pin=has_saved_pin
                )
                
                # Performans güncelle
                if hasattr(self.automation, 'session_stats'):
                    self.after(0, lambda: self.update_performance(self.automation.session_stats))
                
                # Kota kartlarını güncelle
                if self.automation.monthly_stats:
                    saved_targets = self.settings_manager.get_monthly_targets()
                    deferred_counts = self.settings_manager.get_deferred_counts()
                    for tarama_kodu, current_count in self.automation.monthly_stats.items():
                        target = saved_targets.get(tarama_kodu, MONTHLY_TARGETS.get(tarama_kodu, 0))
                        deferred = deferred_counts.get(tarama_kodu, 0)
                        self.after(0, lambda tk=tarama_kodu, cc=current_count, t=target, d=deferred: 
                                   self.update_quota_card(tk, cc, t, d))
                
                self.progress.set(1.0)
                self.log_message("🏁 OTOMASYON TAMAMLANDI!")

                # Oturum özeti ve iptal edilen/atlanan/başarısız HYP'leri popup ile göster
                cancelled = self.automation.get_cancelled_hyps()
                skipped = self.automation.get_skipped_notifications() if hasattr(self.automation, 'get_skipped_notifications') else []
                failed = self.automation.get_failed_hyps() if hasattr(self.automation, 'get_failed_hyps') else []
                stats = self.automation.session_stats.copy() if hasattr(self.automation, 'session_stats') else {}
                self.after(0, lambda: self.show_completion_popup(stats, cancelled, skipped, failed))

            except Exception as e:
                self.log_message(f"❌ HATA: {str(e)}")
                import traceback
                traceback.print_exc()
            
            finally:
                self.is_running = False
                self.after(0, self._stop_gui_refresh_timer)
                self.after(0, lambda: self.start_button.configure(state="normal"))
                self.after(0, lambda: self.history_button.configure(state="normal"))
                self.after(0, lambda: self.stop_button.configure(state="disabled"))

        threading.Thread(target=run_thread, daemon=True).start()

    def _start_gui_refresh_timer(self):
        """GUI'nin donmaması için periyodik güncelleme başlat"""
        self._gui_refresh_id = None

        def refresh():
            if self.is_running:
                self.update_idletasks()
                self._gui_refresh_id = self.after(150, refresh)  # Her 150ms'de bir

        refresh()

    def _stop_gui_refresh_timer(self):
        """GUI güncelleme timer'ını durdur"""
        if hasattr(self, '_gui_refresh_id') and self._gui_refresh_id:
            self.after_cancel(self._gui_refresh_id)
            self._gui_refresh_id = None

    def stop_automation(self):
        if not self.is_running or not self.automation:
            return
        self.log_message("=" * 50)
        self.log_message("🛑 OTOMASYON DURDURULUYOR...")
        self.automation.stop()
        self.is_running = False
        self._stop_gui_refresh_timer()
        self.start_button.configure(state="normal")
        self.history_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def show_completion_popup(self, stats: dict, cancelled_list: list, skipped_list: list = None, failed_list: list = None):
        """
        Otomasyon tamamlandığında özet popup göster.
        Başarılı, başarısız, atlanan sayıları ve iptal edilen/atlanan/başarısız HYP'leri gösterir.
        """
        # Eksik tetkik kayitlarini dosyaya kaydet
        if cancelled_list:
            self.save_eksik_tetkik_from_automation(cancelled_list)
            self.refresh_eksik_tetkik_list()

        basarili = stats.get('basarili', 0)
        basarisiz = stats.get('basarisiz', 0)
        atlanan = stats.get('atlanan', 0)
        toplam_sure = stats.get('toplam_sure', 0)
        iptal_sayisi = len(cancelled_list) if cancelled_list else 0
        atlanan_detay_sayisi = len(skipped_list) if skipped_list else 0
        basarisiz_detay_sayisi = len(failed_list) if failed_list else 0

        popup = ctk.CTkToplevel(self)
        popup.title("Otomasyon Tamamlandı")
        popup.geometry("450x450")
        popup.resizable(False, False)

        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - 225
        y = (popup.winfo_screenheight() // 2) - 200
        popup.geometry(f"450x400+{x}+{y}")

        popup.configure(fg_color="#1a1a2e")
        popup.transient(self)
        popup.grab_set()

        # Başlık
        ctk.CTkLabel(
            popup,
            text="🏁 OTOMASYON TAMAMLANDI",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#2ecc71"
        ).pack(pady=(20, 15))

        # Ana bilgi çerçevesi
        info_frame = ctk.CTkFrame(popup, fg_color="#2c3e50", corner_radius=12)
        info_frame.pack(fill="x", padx=25, pady=10)

        # Başarılı
        row1 = ctk.CTkFrame(info_frame, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(row1, text="✅ Başarılı:", font=ctk.CTkFont(size=14), text_color="#ecf0f1", anchor="w").pack(side="left")
        ctk.CTkLabel(row1, text=str(basarili), font=ctk.CTkFont(size=16, weight="bold"), text_color="#2ecc71", anchor="e").pack(side="right")

        # Başarısız
        row2 = ctk.CTkFrame(info_frame, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row2, text="❌ Başarısız:", font=ctk.CTkFont(size=14), text_color="#ecf0f1", anchor="w").pack(side="left")
        ctk.CTkLabel(row2, text=str(basarisiz), font=ctk.CTkFont(size=16, weight="bold"), text_color="#e74c3c" if basarisiz > 0 else "#95a5a6", anchor="e").pack(side="right")

        # Atlanan
        row3 = ctk.CTkFrame(info_frame, fg_color="transparent")
        row3.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row3, text="⏭️ Atlanan:", font=ctk.CTkFont(size=14), text_color="#ecf0f1", anchor="w").pack(side="left")
        ctk.CTkLabel(row3, text=str(atlanan), font=ctk.CTkFont(size=16, weight="bold"), text_color="#f39c12" if atlanan > 0 else "#95a5a6", anchor="e").pack(side="right")

        # İptal Edilen
        if iptal_sayisi > 0:
            row4 = ctk.CTkFrame(info_frame, fg_color="transparent")
            row4.pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(row4, text="⚠️ İptal Edilen:", font=ctk.CTkFont(size=14), text_color="#ecf0f1", anchor="w").pack(side="left")
            ctk.CTkLabel(row4, text=str(iptal_sayisi), font=ctk.CTkFont(size=16, weight="bold"), text_color="#e67e22", anchor="e").pack(side="right")

        # Süre
        row5 = ctk.CTkFrame(info_frame, fg_color="transparent")
        row5.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkLabel(row5, text="⏱️ Toplam Süre:", font=ctk.CTkFont(size=14), text_color="#ecf0f1", anchor="w").pack(side="left")
        if toplam_sure > 0:
            dakika = int(toplam_sure // 60)
            saniye = int(toplam_sure % 60)
            sure_text = f"{dakika}dk {saniye}sn" if dakika > 0 else f"{saniye}sn"
        else:
            sure_text = "-"
        ctk.CTkLabel(row5, text=sure_text, font=ctk.CTkFont(size=16, weight="bold"), text_color="#3498db", anchor="e").pack(side="right")

        # Başarı oranı
        toplam = basarili + basarisiz
        if toplam > 0:
            oran = (basarili / toplam) * 100
            oran_renk = "#2ecc71" if oran >= 90 else "#f39c12" if oran >= 70 else "#e74c3c"
            ctk.CTkLabel(
                popup,
                text=f"Başarı Oranı: %{oran:.0f}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=oran_renk
            ).pack(pady=(15, 5))

        # Butonlar
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=(20, 15))

        # İptal edilen HYP'leri göster butonu (varsa)
        if iptal_sayisi > 0:
            ctk.CTkButton(
                btn_frame,
                text="⚠️ İptal Edilenleri Gör",
                command=lambda: [popup.destroy(), self.show_cancelled_hyps_popup(cancelled_list)],
                width=150,
                height=35,
                font=ctk.CTkFont(size=13),
                fg_color="#e67e22",
                hover_color="#d35400"
            ).pack(side="left", padx=5)

        # Atlanan HYP'leri göster butonu (varsa)
        if atlanan_detay_sayisi > 0:
            ctk.CTkButton(
                btn_frame,
                text="📋 Atlanan Sebepleri Gör",
                command=lambda: [popup.destroy(), self.show_skipped_hyps_popup(skipped_list)],
                width=170,
                height=35,
                font=ctk.CTkFont(size=13),
                fg_color="#9b59b6",
                hover_color="#8e44ad"
            ).pack(side="left", padx=5)

        # Başarısız HYP'leri göster butonu (varsa)
        if basarisiz_detay_sayisi > 0:
            ctk.CTkButton(
                btn_frame,
                text="❌ Başarısız Detayları",
                command=lambda: [popup.destroy(), self.show_failed_hyps_popup(failed_list)],
                width=160,
                height=35,
                font=ctk.CTkFont(size=13),
                fg_color="#e74c3c",
                hover_color="#c0392b"
            ).pack(side="left", padx=5)

        # Tamam butonu
        ctk.CTkButton(
            btn_frame,
            text="Tamam",
            command=popup.destroy,
            width=120,
            height=35,
            font=ctk.CTkFont(size=13),
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)

    def show_cancelled_hyps_popup(self, cancelled_list):
        """
        İptal edilen HYP'leri popup pencerede göster.
        Eksik tetkik detayları ve SMS onayı bilgisi dahil.
        """
        if not cancelled_list:
            return

        # SMS gereken ve tetkik eksik olanları ayır
        sms_gerekli_sayisi = sum(1 for x in cancelled_list if x.get('sms_gerekli', False))
        tetkik_eksik_sayisi = sum(1 for x in cancelled_list if x.get('eksik_tetkikler'))

        popup = ctk.CTkToplevel(self)
        popup.title("İptal Edilen HYP'ler")
        popup.geometry("600x500")
        popup.resizable(True, True)

        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - 300
        y = (popup.winfo_screenheight() // 2) - 250
        popup.geometry(f"600x500+{x}+{y}")

        popup.configure(fg_color="#1a1a2e")
        popup.transient(self)
        popup.grab_set()

        # Başlık
        ctk.CTkLabel(
            popup,
            text="⚠️ İPTAL EDİLEN HYP'LER",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e74c3c"
        ).pack(pady=(15, 5))

        # Alt başlık - özet bilgi
        ozet_text = f"Toplam {len(cancelled_list)} HYP iptal edildi"
        if tetkik_eksik_sayisi > 0:
            ozet_text += f" • {tetkik_eksik_sayisi} eksik tetkik"
        if sms_gerekli_sayisi > 0:
            ozet_text += f" • {sms_gerekli_sayisi} SMS onayı gerekli"

        ctk.CTkLabel(
            popup,
            text=ozet_text,
            font=ctk.CTkFont(size=12),
            text_color="#95a5a6"
        ).pack(pady=(0, 10))

        # Liste
        scroll_frame = ctk.CTkScrollableFrame(popup, fg_color="#2c3e50", corner_radius=10)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=10)

        for i, item in enumerate(cancelled_list):
            # SMS gerekliyse farklı renk
            sms_gerekli = item.get('sms_gerekli', False)
            bg_color = "#4a3728" if sms_gerekli else "#34495e"

            item_frame = ctk.CTkFrame(scroll_frame, fg_color=bg_color, corner_radius=8)
            item_frame.pack(fill="x", pady=5, padx=5)

            # Hasta adı
            hasta_text = f"👤 {item.get('hasta', 'Bilinmiyor')}"
            if sms_gerekli:
                hasta_text += " 📱"  # SMS ikonu

            ctk.CTkLabel(
                item_frame,
                text=hasta_text,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#3498db"
            ).pack(anchor="w", padx=10, pady=(8, 2))

            # HYP tipi
            hyp_tipi = item.get('hyp_tipi', 'Bilinmiyor')
            ctk.CTkLabel(
                item_frame,
                text=f"📋 HYP: {hyp_tipi}",
                font=ctk.CTkFont(size=12),
                text_color="#ecf0f1"
            ).pack(anchor="w", padx=10, pady=1)

            # Neden
            neden = item.get('neden', 'Bilinmiyor')
            ctk.CTkLabel(
                item_frame,
                text=f"❌ Neden: {neden}",
                font=ctk.CTkFont(size=11),
                text_color="#e74c3c"
            ).pack(anchor="w", padx=10, pady=1)

            # Eksik tetkikler (varsa ayrı satırda göster)
            eksik_tetkikler = item.get('eksik_tetkikler', [])
            if eksik_tetkikler:
                tetkik_text = ", ".join(eksik_tetkikler)
                ctk.CTkLabel(
                    item_frame,
                    text=f"🔬 Eksik Tetkikler: {tetkik_text}",
                    font=ctk.CTkFont(size=11),
                    text_color="#f39c12"
                ).pack(anchor="w", padx=10, pady=1)

            # SMS onayı gerekli uyarısı
            if sms_gerekli:
                ctk.CTkLabel(
                    item_frame,
                    text="📱 SMS ONAYI GEREKLİ - Manuel işlem yapılmalı!",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#9b59b6"
                ).pack(anchor="w", padx=10, pady=(1, 8))
            else:
                # Padding için boş alan
                ctk.CTkLabel(item_frame, text="", height=5).pack()

        # Alt bilgi
        ctk.CTkLabel(
            popup,
            text="Bu hastaların tetkiklerini ve SMS onaylarını kontrol edin.",
            font=ctk.CTkFont(size=11),
            text_color="#f39c12"
        ).pack(pady=(5, 10))

        # Kapat butonu
        ctk.CTkButton(
            popup,
            text="Tamam",
            command=popup.destroy,
            width=120,
            height=35,
            font=ctk.CTkFont(size=13),
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(pady=(0, 15))

    def show_skipped_hyps_popup(self, skipped_list):
        """
        Atlanan/başarısız HYP'leri sebepleriyle birlikte popup pencerede göster.
        """
        if not skipped_list:
            return

        popup = ctk.CTkToplevel(self)
        popup.title("Atlanan HYP Sebepleri")
        popup.geometry("550x450")
        popup.resizable(True, True)

        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - 275
        y = (popup.winfo_screenheight() // 2) - 225
        popup.geometry(f"550x450+{x}+{y}")

        popup.configure(fg_color="#1a1a2e")
        popup.transient(self)
        popup.grab_set()

        # Baslik
        ctk.CTkLabel(
            popup,
            text="📋 ATLANAN HYP SEBEPLERİ",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#9b59b6"
        ).pack(pady=(15, 5))

        # Alt baslik
        ctk.CTkLabel(
            popup,
            text=f"Toplam {len(skipped_list)} HYP atlandı/başarısız oldu",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7"
        ).pack(pady=(0, 10))

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(
            popup,
            fg_color="#2c3e50",
            corner_radius=10,
            height=280
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Her bir atlanan HYP için bilgi göster
        for idx, item in enumerate(skipped_list, 1):
            item_frame = ctk.CTkFrame(scroll_frame, fg_color="#34495e", corner_radius=8)
            item_frame.pack(fill="x", padx=5, pady=5)

            # Hasta adı ve HYP tipi
            hasta = item.get('hasta', 'Bilinmiyor')
            hyp_tip = item.get('hyp_tip', 'Bilinmiyor')
            tarih = item.get('tarih', '')

            ctk.CTkLabel(
                item_frame,
                text=f"{idx}. {hasta} - {hyp_tip}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ecf0f1"
            ).pack(anchor="w", padx=10, pady=(8, 2))

            # Sebep
            sebep = item.get('sebep', 'Bilinmiyor')
            ctk.CTkLabel(
                item_frame,
                text=f"Sebep: {sebep}",
                font=ctk.CTkFont(size=12),
                text_color="#e74c3c"
            ).pack(anchor="w", padx=10, pady=2)

            # Tarih
            if tarih:
                ctk.CTkLabel(
                    item_frame,
                    text=f"Tarih: {tarih}",
                    font=ctk.CTkFont(size=11),
                    text_color="#7f8c8d"
                ).pack(anchor="w", padx=10, pady=(2, 8))

        # Alt bilgi
        ctk.CTkLabel(
            popup,
            text="Bu HYP'leri manuel olarak kontrol etmeniz gerekebilir.",
            font=ctk.CTkFont(size=11),
            text_color="#f39c12"
        ).pack(pady=(5, 10))

        # Kapat butonu
        ctk.CTkButton(
            popup,
            text="Tamam",
            command=popup.destroy,
            width=120,
            height=35,
            font=ctk.CTkFont(size=13),
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(pady=(0, 15))

    def show_failed_hyps_popup(self, failed_list):
        """
        Başarısız HYP'leri nedenleriyle birlikte popup pencerede göster.
        """
        if not failed_list:
            return

        popup = ctk.CTkToplevel(self)
        popup.title("Başarısız HYP Detayları")
        popup.geometry("550x450")
        popup.resizable(True, True)

        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - 275
        y = (popup.winfo_screenheight() // 2) - 225
        popup.geometry(f"550x450+{x}+{y}")

        popup.configure(fg_color="#1a1a2e")
        popup.transient(self)
        popup.grab_set()

        # Başlık
        ctk.CTkLabel(
            popup,
            text="❌ BAŞARISIZ HYP'LER",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e74c3c"
        ).pack(pady=(15, 5))

        # Alt başlık
        ctk.CTkLabel(
            popup,
            text=f"Toplam {len(failed_list)} HYP tamamlanamadı",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7"
        ).pack(pady=(0, 10))

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(
            popup,
            fg_color="#2c3e50",
            corner_radius=10,
            height=280
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Her bir başarısız HYP için bilgi göster
        for idx, item in enumerate(failed_list, 1):
            item_frame = ctk.CTkFrame(scroll_frame, fg_color="#34495e", corner_radius=8)
            item_frame.pack(fill="x", padx=5, pady=5)

            # Hasta adı ve HYP tipi
            hasta = item.get('hasta', 'Bilinmiyor')
            hyp_ad = item.get('hyp_ad', item.get('hyp_tip', 'Bilinmiyor'))

            ctk.CTkLabel(
                item_frame,
                text=f"{idx}. {hasta} - {hyp_ad}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ecf0f1"
            ).pack(anchor="w", padx=10, pady=(8, 2))

            # Neden
            neden = item.get('neden', 'Bilinmiyor')
            ctk.CTkLabel(
                item_frame,
                text=f"Neden: {neden}",
                font=ctk.CTkFont(size=12),
                text_color="#e74c3c"
            ).pack(anchor="w", padx=10, pady=(2, 8))

        # Alt bilgi
        ctk.CTkLabel(
            popup,
            text="Bu HYP'leri manuel olarak tekrar deneyebilirsiniz.",
            font=ctk.CTkFont(size=11),
            text_color="#f39c12"
        ).pack(pady=(5, 10))

        # Kapat butonu
        ctk.CTkButton(
            popup,
            text="Tamam",
            command=popup.destroy,
            width=120,
            height=35,
            font=ctk.CTkFont(size=13),
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(pady=(0, 15))

    def toggle_theme(self):
        """Light/Dark tema değiştir - smooth geçiş"""
        # Pencereyi geçici olarak gizle (titreme önleme)
        self.withdraw()

        if self.current_theme == "dark":
            # LIGHT MODE
            self.current_theme = "light"
            ctk.set_appearance_mode("light")

            self.theme_button.configure(
                text="🌙",
                fg_color="#2c3e50",
                hover_color="#34495e"
            )

            self.configure(fg_color="#f5f6fa")
            self.header_frame.configure(fg_color="#2c3e50")
            self.control_frame.configure(fg_color="#2c3e50")
            self.main_container.configure(fg_color="#dcdde1")
            self.title_label.configure(text_color="#ffffff")
            self.perf_label.configure(text_color="#bdc3c7")

        else:
            # DARK MODE
            self.current_theme = "dark"
            ctk.set_appearance_mode("dark")

            self.theme_button.configure(
                text="☀️",
                fg_color="#f39c12",
                hover_color="#e67e22"
            )

            self.configure(fg_color="#1a1a2e")
            self.header_frame.configure(fg_color="#0f0f23")
            self.control_frame.configure(fg_color="#0f0f23")
            self.main_container.configure(fg_color="#16213e")
            self.title_label.configure(text_color="#e0e0e0")
            self.perf_label.configure(text_color="#a0a0a0")

        # Ayarı kaydet
        self.settings_manager.settings["theme"] = self.current_theme
        self.settings_manager.save_settings()

        # Pencereyi tekrar göster
        self.after(50, self.deiconify)

    def create_sms_kapali_tab(self):
        """SMS onayı kapalı hastalar sekmesi"""
        import json
        import os

        # Ana container
        main_frame = ctk.CTkFrame(self.sms_tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Başlık
        header_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e", corner_radius=10)
        header_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header_frame,
            text="📱 SMS Onayı Kapalı Hastalar",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#e74c3c"
        ).pack(pady=10)

        ctk.CTkLabel(
            header_frame,
            text="Bu listedeki hastalara HYP yapılmaz, otomatik atlanır.",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6"
        ).pack(pady=(0, 10))

        # Liste frame
        self.sms_list_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="#2c3e50",
            corner_radius=10
        )
        self.sms_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Alt butonlar
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text="🔄 Yenile",
            command=self.refresh_sms_kapali_list,
            width=100,
            height=32,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="🗑 Tümünü Temizle",
            command=self.clear_sms_kapali_list,
            width=120,
            height=32,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="right", padx=5)

        # Listeyi yükle
        self.refresh_sms_kapali_list()

    def refresh_sms_kapali_list(self):
        """SMS kapalı hastalar listesini yenile"""
        import json
        import os

        # Mevcut widget'ları temizle
        for widget in self.sms_list_frame.winfo_children():
            widget.destroy()

        # Dosyayı oku
        sms_file = os.path.join(os.path.dirname(__file__), 'sms_kapali_hastalar.json')
        data = []

        if os.path.exists(sms_file):
            try:
                with open(sms_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError, OSError) as e:
                print(f"SMS dosyasi okuma hatasi: {e}")
                data = []

        if not data:
            ctk.CTkLabel(
                self.sms_list_frame,
                text="📭 Henüz SMS kapalı hasta yok.\n\nOtomasyon sırasında SMS onayı gereken\nhastalar buraya otomatik eklenir.",
                font=ctk.CTkFont(size=12),
                text_color="#7f8c8d"
            ).pack(pady=30)
            return

        # Sayaç
        ctk.CTkLabel(
            self.sms_list_frame,
            text=f"Toplam {len(data)} hasta",
            font=ctk.CTkFont(size=11),
            text_color="#f39c12"
        ).pack(pady=(5, 10))

        # Her hasta için kart
        for i, hasta in enumerate(data):
            item_frame = ctk.CTkFrame(self.sms_list_frame, fg_color="#34495e", corner_radius=8)
            item_frame.pack(fill="x", pady=3, padx=5)

            # Sol: Bilgiler
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            ad_soyad = hasta.get('ad_soyad', 'Bilinmiyor')
            tc = hasta.get('tc', '')
            yas = hasta.get('yas', '')
            tarih = hasta.get('ekleme_tarihi', '')

            ctk.CTkLabel(
                info_frame,
                text=f"👤 {ad_soyad}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#ecf0f1"
            ).pack(anchor="w")

            detay_text = f"TC: {tc}"
            if yas:
                detay_text += f" • Yaş: {yas}"
            if tarih:
                detay_text += f" • Eklenme: {tarih}"

            ctk.CTkLabel(
                info_frame,
                text=detay_text,
                font=ctk.CTkFont(size=10),
                text_color="#95a5a6"
            ).pack(anchor="w")

            # Sağ: Sil butonu
            ctk.CTkButton(
                item_frame,
                text="🗑",
                width=30,
                height=30,
                fg_color="#c0392b",
                hover_color="#e74c3c",
                command=lambda t=tc: self.remove_sms_kapali_hasta(t)
            ).pack(side="right", padx=10, pady=8)

    def remove_sms_kapali_hasta(self, tc: str):
        """Bir hastayı SMS kapalı listesinden çıkar"""
        import json
        import os

        sms_file = os.path.join(os.path.dirname(__file__), 'sms_kapali_hastalar.json')

        if not os.path.exists(sms_file):
            return

        try:
            with open(sms_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # TC'yi sil
            data = [h for h in data if h.get('tc') != tc]

            with open(sms_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.refresh_sms_kapali_list()
            self.log_message(f"SMS kapalı listesinden silindi: {tc}")
        except Exception as e:
            self.log_message(f"Silme hatası: {e}", "ERROR")

    def clear_sms_kapali_list(self):
        """Tüm SMS kapalı hastaları temizle"""
        import os

        sms_file = os.path.join(os.path.dirname(__file__), 'sms_kapali_hastalar.json')

        if os.path.exists(sms_file):
            # Onay iste
            confirm = ctk.CTkInputDialog(
                text="Tüm listeyi silmek için 'SİL' yazın:",
                title="Onay Gerekli"
            )
            result = confirm.get_input()

            if result and result.upper() == "SİL":
                try:
                    os.remove(sms_file)
                    self.refresh_sms_kapali_list()
                    self.log_message("SMS kapalı hastalar listesi temizlendi.")
                except Exception as e:
                    self.log_message(f"Temizleme hatası: {e}", "ERROR")

    # ============================================================
    # EKSIK TETKIK SEKMESI
    # ============================================================
    def create_eksik_tetkik_tab(self):
        """Eksik tetkik nedeniyle atlanan hastalar sekmesi"""
        import json
        import os

        # Ana container
        main_frame = ctk.CTkFrame(self.eksik_tetkik_tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Baslik
        header_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e", corner_radius=10)
        header_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header_frame,
            text="🩸 Eksik Tetkik Nedeniyle Atlanan Hastalar",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#e67e22"
        ).pack(pady=10)

        ctk.CTkLabel(
            header_frame,
            text="Bu listedeki hastalarin eksik tetkiklerini hemsireye bildirin.",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6"
        ).pack(pady=(0, 10))

        # Liste frame
        self.eksik_tetkik_list_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="#2c3e50",
            corner_radius=10
        )
        self.eksik_tetkik_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Alt butonlar
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text="🔄 Yenile",
            command=self.refresh_eksik_tetkik_list,
            width=100,
            height=32,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="📋 Panoya Kopyala",
            command=self.copy_eksik_tetkik_to_clipboard,
            width=130,
            height=32,
            fg_color="#9b59b6",
            hover_color="#8e44ad"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="🗑 Tümünü Temizle",
            command=self.clear_eksik_tetkik_list,
            width=120,
            height=32,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="right", padx=5)

        # Listeyi yukle
        self.refresh_eksik_tetkik_list()

    def refresh_eksik_tetkik_list(self):
        """Eksik tetkik listesini yenile"""
        import json
        import os

        # Mevcut widget'lari temizle
        for widget in self.eksik_tetkik_list_frame.winfo_children():
            widget.destroy()

        # Dosyayi oku
        eksik_file = os.path.join(os.path.dirname(__file__), 'eksik_tetkik_hastalar.json')
        data = []

        if os.path.exists(eksik_file):
            try:
                with open(eksik_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError, OSError) as e:
                print(f"Eksik tetkik dosyasi okuma hatasi: {e}")
                data = []

        if not data:
            ctk.CTkLabel(
                self.eksik_tetkik_list_frame,
                text="📭 Eksik tetkik kaydı yok.\n\nOtomasyon sırasında tetkik eksikliği\nnedeniyle atlanan hastalar buraya eklenir.",
                font=ctk.CTkFont(size=12),
                text_color="#7f8c8d"
            ).pack(pady=30)
            return

        # Sayac
        ctk.CTkLabel(
            self.eksik_tetkik_list_frame,
            text=f"Toplam {len(data)} hasta",
            font=ctk.CTkFont(size=11),
            text_color="#f39c12"
        ).pack(pady=(5, 10))

        # Her hasta icin kart
        for item in data:
            card = ctk.CTkFrame(self.eksik_tetkik_list_frame, fg_color="#34495e", corner_radius=8)
            card.pack(fill="x", padx=5, pady=3)

            # Sol: Hasta bilgisi
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            # Hasta adi ve HYP tipi
            ctk.CTkLabel(
                info_frame,
                text=f"👤 {item.get('hasta', 'Bilinmiyor')}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ecf0f1"
            ).pack(anchor="w")

            # HYP tipi ve zaman
            hyp_tipi = item.get('hyp_tipi', 'Bilinmiyor')
            zaman = item.get('zaman', '')
            ctk.CTkLabel(
                info_frame,
                text=f"🏥 {hyp_tipi}  •  ⏰ {zaman}",
                font=ctk.CTkFont(size=10),
                text_color="#95a5a6"
            ).pack(anchor="w")

            # Eksik tetkikler
            eksik_tetkikler = item.get('eksik_tetkikler', [])
            if eksik_tetkikler:
                tetkik_text = ", ".join(eksik_tetkikler)
                ctk.CTkLabel(
                    info_frame,
                    text=f"🩸 Eksik: {tetkik_text}",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#e74c3c"
                ).pack(anchor="w", pady=(3, 0))

            # Sag: Sil butonu
            ctk.CTkButton(
                card,
                text="✕",
                width=30,
                height=30,
                fg_color="#c0392b",
                hover_color="#a93226",
                command=lambda i=item: self.remove_eksik_tetkik_item(i)
            ).pack(side="right", padx=10)

    def copy_eksik_tetkik_to_clipboard(self):
        """Eksik tetkik listesini panoya kopyala"""
        import json
        import os

        eksik_file = os.path.join(os.path.dirname(__file__), 'eksik_tetkik_hastalar.json')
        data = []

        if os.path.exists(eksik_file):
            try:
                with open(eksik_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = []

        if not data:
            self.log_message("Kopyalanacak kayıt yok.", "WARNING")
            return

        # Metin olustur
        text_lines = ["EKSIK TETKIK OLAN HASTALAR", "=" * 40, ""]

        for item in data:
            hasta = item.get('hasta', 'Bilinmiyor')
            hyp_tipi = item.get('hyp_tipi', '')
            eksik = item.get('eksik_tetkikler', [])
            zaman = item.get('zaman', '')

            text_lines.append(f"Hasta: {hasta}")
            text_lines.append(f"HYP: {hyp_tipi}")
            if eksik:
                text_lines.append(f"Eksik Tetkik: {', '.join(eksik)}")
            text_lines.append(f"Tarih: {zaman}")
            text_lines.append("-" * 30)
            text_lines.append("")

        clipboard_text = "\n".join(text_lines)

        # Panoya kopyala
        self.clipboard_clear()
        self.clipboard_append(clipboard_text)
        self.log_message(f"{len(data)} hasta bilgisi panoya kopyalandı.", "SUCCESS")

    def remove_eksik_tetkik_item(self, item_to_remove):
        """Tek bir eksik tetkik kaydini sil + cache'den de sil"""
        import json
        import os

        eksik_file = os.path.join(os.path.dirname(__file__), 'eksik_tetkik_hastalar.json')
        data = []

        if os.path.exists(eksik_file):
            try:
                with open(eksik_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = []

        # Kaydi bul ve sil
        new_data = [item for item in data if not (
            item.get('hasta') == item_to_remove.get('hasta') and
            item.get('zaman') == item_to_remove.get('zaman')
        )]

        # Dosyaya yaz
        try:
            with open(eksik_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            # Cache'den de sil (tekrar denenebilsin diye)
            tc = item_to_remove.get('tc', '')
            hyp_tipi = item_to_remove.get('hyp_tipi', '')
            if tc and hyp_tipi and hasattr(self, 'automation') and self.automation:
                self.automation.remove_from_cache(tc, hyp_tipi)
                self.log_message(f"Cache'den silindi: {item_to_remove.get('hasta')} - {hyp_tipi}")

            self.refresh_eksik_tetkik_list()
        except Exception as e:
            self.log_message(f"Silme hatası: {e}", "ERROR")

    def clear_eksik_tetkik_list(self):
        """Tum eksik tetkik kayitlarini temizle"""
        import os

        eksik_file = os.path.join(os.path.dirname(__file__), 'eksik_tetkik_hastalar.json')

        if os.path.exists(eksik_file):
            confirm = ctk.CTkInputDialog(
                text="Tüm listeyi silmek için 'SİL' yazın:",
                title="Onay Gerekli"
            )
            result = confirm.get_input()

            if result and result.upper() == "SİL":
                try:
                    os.remove(eksik_file)
                    self.refresh_eksik_tetkik_list()
                    self.log_message("Eksik tetkik listesi temizlendi.")
                except Exception as e:
                    self.log_message(f"Temizleme hatası: {e}", "ERROR")

    def save_eksik_tetkik_from_automation(self, cancelled_list):
        """Otomasyon sonunda eksik tetkik kayitlarini dosyaya kaydet"""
        import json
        import os

        if not cancelled_list:
            return

        eksik_file = os.path.join(os.path.dirname(__file__), 'eksik_tetkik_hastalar.json')
        data = []

        # Mevcut veriyi oku
        if os.path.exists(eksik_file):
            try:
                with open(eksik_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = []

        # Yeni kayitlari ekle (eksik tetkik nedeniyle iptal edilen tum HYP'ler)
        for item in cancelled_list:
            # Eksik tetkik listesi VEYA nedende 'Eksik' geciyorsa ekle
            has_eksik = item.get('eksik_tetkikler') and len(item.get('eksik_tetkikler', [])) > 0
            neden = item.get('neden', '')
            has_reason = 'Eksik' in neden or 'Dis lab' in neden
            
            if has_eksik or has_reason:
                # Ayni kayit var mi kontrol et
                is_duplicate = any(
                    d.get('hasta') == item.get('hasta') and
                    d.get('hyp_tipi') == item.get('hyp_tipi') and
                    d.get('zaman') == item.get('zaman')
                    for d in data
                )
                if not is_duplicate:
                    data.append(item)

        # Dosyaya yaz
        try:
            with open(eksik_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"Eksik tetkik kaydetme hatası: {e}", "ERROR")

    def create_community_tab(self):
        """Topluluk sekmesi - Modern tasarım"""
        # Ana container
        main_frame = ctk.CTkFrame(self.community_tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Başlık kartı
        header_card = ctk.CTkFrame(main_frame, corner_radius=15)
        header_card.pack(fill="x", pady=(0, 15))

        header_inner = ctk.CTkFrame(header_card, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            header_inner,
            text="👥 ASM TOPLULUK PANELİ",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_inner,
            text="Aynı ASM'deki hekimlerle ilerleme paylaşımı",
            font=ctk.CTkFont(size=13),
            text_color="#95a5a6"
        ).pack(anchor="w", pady=(5, 0))

        # Durum kartı
        status_card = ctk.CTkFrame(main_frame, corner_radius=12)
        status_card.pack(fill="x", pady=10)

        status_inner = ctk.CTkFrame(status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=20, pady=20)

        # İkon ve metin
        icon_frame = ctk.CTkFrame(status_inner, fg_color="#2c3e50", width=60, height=60, corner_radius=30)
        icon_frame.pack(side="left")
        icon_frame.pack_propagate(False)

        ctk.CTkLabel(
            icon_frame,
            text="🔒",
            font=ctk.CTkFont(size=28)
        ).place(relx=0.5, rely=0.5, anchor="center")

        text_frame = ctk.CTkFrame(status_inner, fg_color="transparent")
        text_frame.pack(side="left", padx=20, fill="x", expand=True)

        ctk.CTkLabel(
            text_frame,
            text="Çok Yakında!",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_frame,
            text="Bu özellik geliştirme aşamasındadır",
            font=ctk.CTkFont(size=12),
            text_color="#7f8c8d"
        ).pack(anchor="w")

        # Özellik listesi
        features_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        features_frame.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            features_frame,
            text="📋 Gelecek Özellikler",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        features = [
            ("📊", "Aylık performans karşılaştırması", "ASM'deki tüm hekimlerin ilerlemesini görün"),
            ("🏆", "Liderlik tablosu", "En çok HYP tamamlayan hekimler"),
            ("💬", "Mesajlaşma", "ASM içi iletişim"),
            ("🔔", "Bildirimler", "Hedef hatırlatmaları ve güncellemeler"),
        ]

        for icon, title, desc in features:
            row = ctk.CTkFrame(features_frame, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=8)

            ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=20), width=35).pack(side="left")

            text_container = ctk.CTkFrame(row, fg_color="transparent")
            text_container.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                text_container,
                text=title,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w"
            ).pack(anchor="w")

            ctk.CTkLabel(
                text_container,
                text=desc,
                font=ctk.CTkFont(size=11),
                text_color="#7f8c8d",
                anchor="w"
            ).pack(anchor="w")

    def create_updates_tab(self):
        """Güncellemeler sekmesi - Modern tasarım"""
        main_frame = ctk.CTkFrame(self.updates_tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Versiyon kartı
        version_card = ctk.CTkFrame(main_frame, corner_radius=15)
        version_card.pack(fill="x", pady=(0, 15))

        version_inner = ctk.CTkFrame(version_card, fg_color="transparent")
        version_inner.pack(fill="x", padx=20, pady=20)

        # Sol: İkon
        icon_frame = ctk.CTkFrame(version_inner, fg_color="#27ae60", width=70, height=70, corner_radius=15)
        icon_frame.pack(side="left")
        icon_frame.pack_propagate(False)

        ctk.CTkLabel(
            icon_frame,
            text="🏥",
            font=ctk.CTkFont(size=32)
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Sağ: Versiyon bilgisi
        info_frame = ctk.CTkFrame(version_inner, fg_color="transparent")
        info_frame.pack(side="left", padx=20, fill="x", expand=True)

        ctk.CTkLabel(
            info_frame,
            text="HYP Otomasyon",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame,
            text=f"Versiyon {self.VERSION}",
            font=ctk.CTkFont(size=14),
            text_color="#2ecc71"
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame,
            text=f"Build: {self.BUILD_DATE}",
            font=ctk.CTkFont(size=11),
            text_color="#7f8c8d"
        ).pack(anchor="w")

        # Güncelleme butonu
        self.check_update_btn = ctk.CTkButton(
            version_inner,
            text="🔍 Güncelleme Denetle",
            command=self.check_for_updates,
            width=160,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.check_update_btn.pack(side="right")
        add_tooltip(self.check_update_btn, "Yeni sürüm kontrolü yap")

        # Güncelleme durumu
        self.update_status_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        self.update_status_frame.pack(fill="x", pady=10)

        self.update_status_label = ctk.CTkLabel(
            self.update_status_frame,
            text="✅ Güncel sürümü kullanıyorsunuz",
            font=ctk.CTkFont(size=14),
            text_color="#2ecc71"
        )
        self.update_status_label.pack(pady=15)

        # Değişiklik günlüğü
        changelog_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        changelog_frame.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            changelog_frame,
            text="📝 Değişiklik Günlüğü",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        changelog_scroll = ctk.CTkScrollableFrame(changelog_frame, corner_radius=0)
        changelog_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        changes = [
            ("v6.8.0", "16.12.2025", [
                "🧮 HYP Katsayı Hesaplama sekmesi eklendi",
                "📋 Başlat'ta HYP tipi seçimi (checkbox)",
                "⏭️ İstenen HYP tiplerini devre dışı bırakma",
                "📊 Resmi yönetmeliğe uygun hesaplama modülü",
                "🎯 Kategorize edilmiş HYP tipi seçim ekranı"
            ]),
            ("v6.7.0", "15.12.2025", [
                "🎯 Hedef yüzdesi seçimi (%70 veya %100)",
                "🚀 Hızlı başlatma - anında splash ekranı",
                "🔧 Minimize/restore sorunu düzeltildi",
                "⏹️ Durdur butonu artık tarayıcıyı kapatmıyor",
                "⚡ Lazy loading ile açılış optimizasyonu"
            ]),
            ("v6.6.0", "05.12.2025", [
                "🔄 Otomatik güncelleme kontrol sistemi",
                "📦 EXE olarak dağıtım desteği",
                "🔒 PIN şifreleme güvenliği artırıldı"
            ]),
            ("v6.0.0", "03.12.2025", [
                "🎨 Light/Dark tema desteği",
                "📊 Geçmiş Aylar sekmesi (pencere yerine)",
                "👥 Topluluk sekmesi eklendi",
                "🔄 Güncellemeler sekmesi eklendi",
                "💡 Tooltip (ipucu) sistemi",
                "🐛 Ayar sıfırlama bug'ı düzeltildi"
            ]),
            ("v5.0.0", "27.11.2025", [
                "🎯 Ay bazlı hedef sistemi",
                "📊 Geçmiş aylar penceresi",
                "🔧 Debug modu iyileştirmeleri",
                "⚡ Performans optimizasyonları"
            ]),
            ("v4.0.0", "25.11.2025", [
                "🔧 Debug modu eklendi",
                "💊 İlaç analiz modülü",
                "👴 Yaşlı izlem desteği"
            ]),
        ]

        for version, date, items in changes:
            # Versiyon başlığı
            ver_header = ctk.CTkFrame(changelog_scroll, fg_color="transparent")
            ver_header.pack(fill="x", pady=(10, 5))

            ctk.CTkLabel(
                ver_header,
                text=version,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#3498db"
            ).pack(side="left")

            ctk.CTkLabel(
                ver_header,
                text=f"  •  {date}",
                font=ctk.CTkFont(size=12),
                text_color="#7f8c8d"
            ).pack(side="left")

            # Değişiklik listesi
            for item in items:
                ctk.CTkLabel(
                    changelog_scroll,
                    text=f"    {item}",
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                ).pack(anchor="w", pady=1)

    def create_calculator_tab(self):
        """HYP Katsayı Hesaplama sekmesi"""
        main_frame = ctk.CTkFrame(self.calculator_tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Başlık
        header_frame = ctk.CTkFrame(main_frame, corner_radius=12, fg_color="#1a3a4a")
        header_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            header_frame,
            text="🧮 HYP Katsayı Hesaplayıcı",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#00d4aa"
        ).pack(pady=15)

        ctk.CTkLabel(
            header_frame,
            text="Aile Hekimliği Tarama ve Takip Katsayısı hesaplama aracı",
            font=ctk.CTkFont(size=12),
            text_color="#95a5a6"
        ).pack(pady=(0, 15))

        # Scrollable content
        content_frame = ctk.CTkScrollableFrame(main_frame, corner_radius=10)
        content_frame.pack(fill="both", expand=True)

        # Birim Bilgileri
        birim_frame = ctk.CTkFrame(content_frame, corner_radius=10)
        birim_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            birim_frame,
            text="📋 Birim Bilgileri",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        birim_grid = ctk.CTkFrame(birim_frame, fg_color="transparent")
        birim_grid.pack(fill="x", padx=15, pady=10)

        # Nüfus
        ctk.CTkLabel(birim_grid, text="Kayıtlı Nüfus:", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=5)
        self.calc_nufus = ctk.CTkEntry(birim_grid, width=120, placeholder_text="3500")
        self.calc_nufus.grid(row=0, column=1, padx=10, pady=5)
        self.calc_nufus.insert(0, "3500")

        # Birim Türü
        ctk.CTkLabel(birim_grid, text="Birim Türü:", font=ctk.CTkFont(size=12)).grid(row=0, column=2, sticky="w", padx=(20, 0), pady=5)
        self.calc_birim_turu = ctk.CTkComboBox(
            birim_grid,
            values=["Normal", "Entegre", "Zorunlu Düşük Nüfus"],
            width=180
        )
        self.calc_birim_turu.grid(row=0, column=3, padx=10, pady=5)
        self.calc_birim_turu.set("Normal")

        # Kriter Girişleri
        kriter_frame = ctk.CTkFrame(content_frame, corner_radius=10)
        kriter_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            kriter_frame,
            text="📊 Kriter Verileri (Gereken / Yapılan)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        kriter_grid = ctk.CTkFrame(kriter_frame, fg_color="transparent")
        kriter_grid.pack(fill="x", padx=15, pady=10)

        # Kriter giriş alanları
        self.calc_kriterler = {}
        kriterler = [
            ("HT Tarama", "ht_tarama", 40),
            ("HT İzlem", "ht_izlem", 50),
            ("DM Tarama", "dm_tarama", 40),
            ("DM İzlem", "dm_izlem", 50),
            ("Obezite Tarama", "obezite_tarama", 40),
            ("Obezite İzlem", "obezite_izlem", 50),
            ("KVR Tarama", "kvr_tarama", 40),
            ("KVR İzlem", "kvr_izlem", 50),
        ]

        for i, (label, key, asgari) in enumerate(kriterler):
            row = i // 2
            col_offset = (i % 2) * 4

            ctk.CTkLabel(
                kriter_grid,
                text=f"{label}:",
                font=ctk.CTkFont(size=11)
            ).grid(row=row, column=col_offset, sticky="w", pady=3)

            gereken = ctk.CTkEntry(kriter_grid, width=60, placeholder_text="100")
            gereken.grid(row=row, column=col_offset + 1, padx=2, pady=3)

            ctk.CTkLabel(kriter_grid, text="/", font=ctk.CTkFont(size=11)).grid(row=row, column=col_offset + 2)

            yapilan = ctk.CTkEntry(kriter_grid, width=60, placeholder_text="85")
            yapilan.grid(row=row, column=col_offset + 3, padx=(2, 15), pady=3)

            self.calc_kriterler[key] = {"gereken": gereken, "yapilan": yapilan, "asgari": asgari}

        # Buton Frame
        btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=15)

        # Kendi Verilerimle Güncelle Butonu
        self.calc_update_btn = ctk.CTkButton(
            btn_frame,
            text="📊 Kendi Verilerimle Güncelle",
            command=self.update_calculator_with_my_data,
            width=220,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#3498db",
            hover_color="#2980b9",
            corner_radius=12
        )
        self.calc_update_btn.pack(side="left", padx=(50, 10))

        # Hesapla Butonu
        self.calc_btn = ctk.CTkButton(
            btn_frame,
            text="🧮 HESAPLA",
            command=self.calculate_hyp_katsayi,
            width=200,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            corner_radius=12
        )
        self.calc_btn.pack(side="left", padx=10)

        # Sonuç Alanı
        sonuc_frame = ctk.CTkFrame(content_frame, corner_radius=10, fg_color="#1a252f")
        sonuc_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            sonuc_frame,
            text="📈 Hesaplama Sonucu",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.calc_sonuc_text = ctk.CTkTextbox(
            sonuc_frame,
            height=200,
            font=ctk.CTkFont(size=12, family="Consolas"),
            corner_radius=8
        )
        self.calc_sonuc_text.pack(fill="x", padx=15, pady=(5, 15))

        # Varsayılan açıklama
        self.calc_sonuc_text.insert("1.0", """
╔══════════════════════════════════════════════════╗
║  HYP KATSAYI HESAPLAYICI                          ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  Kriter verilerini girin ve HESAPLA butonuna     ║
║  tıklayın.                                       ║
║                                                  ║
║  📋 Formül:                                      ║
║  Tarama Takip Katsayısı = Kriter₁ × Kriter₂ × ...║
║                                                  ║
║  📊 Katsayı Aralığı: 0.90 - 1.50                 ║
║                                                  ║
╚══════════════════════════════════════════════════╝
""")

    def update_calculator_with_my_data(self):
        """Hesaplama formunu kendi verilerimle doldur"""
        try:
            # Ayarlardan verileri al
            current_counts = self.settings_manager.get_current_counts()
            saved_targets = self.settings_manager.get_monthly_targets()
            deferred_counts = self.settings_manager.get_deferred_counts()

            # HYP tiplerini hesaplama alanlarına eşle
            mapping = {
                "HIPERTANSIYON": "ht_tarama",
                "HT_IZLEM": "ht_izlem",
                "DIYABET": "dm_tarama",
                "DM_IZLEM": "dm_izlem",
                "OBEZITE": "obezite_tarama",
                "OBE_IZLEM": "obezite_izlem",
                "KVR": "kvr_tarama",
                "KVR_IZLEM": "kvr_izlem",
            }

            # Alanları güncelle
            updated_count = 0
            for hyp_tip, calc_key in mapping.items():
                if calc_key in self.calc_kriterler:
                    fields = self.calc_kriterler[calc_key]

                    # Hedef (gereken)
                    hedef = saved_targets.get(hyp_tip, 0)
                    # Yapılan + Devreden
                    yapilan = current_counts.get(hyp_tip, 0)
                    devreden = deferred_counts.get(hyp_tip, 0)
                    toplam_yapilan = yapilan + devreden

                    # Alanları temizle ve doldur
                    fields["gereken"].delete(0, "end")
                    fields["gereken"].insert(0, str(hedef))

                    fields["yapilan"].delete(0, "end")
                    fields["yapilan"].insert(0, str(toplam_yapilan))

                    updated_count += 1

            # Başarı mesajı
            self.calc_sonuc_text.delete("1.0", "end")
            self.calc_sonuc_text.insert("1.0", f"""
╔══════════════════════════════════════════════════╗
║  ✅ VERİLER GÜNCELLENDİ                           ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  {updated_count} kriter verilerinizle güncellendi.           ║
║                                                  ║
║  Şimdi HESAPLA butonuna tıklayarak              ║
║  katsayınızı hesaplayabilirsiniz.               ║
║                                                  ║
╚══════════════════════════════════════════════════╝
""")

            self.log_message("📊 Hesaplama verileri güncellendi")

        except Exception as e:
            self.calc_sonuc_text.delete("1.0", "end")
            self.calc_sonuc_text.insert("1.0", f"❌ Hata: {str(e)}")

    def calculate_hyp_katsayi(self):
        """HYP katsayısını hesapla"""
        try:
            from hyp_calculator import (
                hesapla_hyp, HYPGirdi, KriterVerisi,
                get_kriter_ismi, get_durum_renk_kodu
            )

            # Nüfus al
            nufus = int(self.calc_nufus.get() or 3500)

            # Birim türü
            birim_turu_map = {
                "Normal": "normal",
                "Entegre": "entegre",
                "Zorunlu Düşük Nüfus": "zorunlu_dusuk_nufus"
            }
            birim_turu = birim_turu_map.get(self.calc_birim_turu.get(), "normal")

            # Kriterleri topla
            kriterler = []
            for key, fields in self.calc_kriterler.items():
                gereken_str = fields["gereken"].get()
                yapilan_str = fields["yapilan"].get()

                if gereken_str and yapilan_str:
                    gereken = int(gereken_str)
                    yapilan = int(yapilan_str)
                    kriterler.append(KriterVerisi(
                        tur=key,
                        gereken=gereken,
                        yapilan=yapilan,
                        gecen_ay_devir=0
                    ))

            if not kriterler:
                self.calc_sonuc_text.delete("1.0", "end")
                self.calc_sonuc_text.insert("1.0", "❌ En az bir kriter girmelisiniz!")
                return

            # Hesapla
            girdi = HYPGirdi(
                birim_id="Hesaplama",
                donem="2025-12",
                nufus=nufus,
                birim_turu=birim_turu,
                kriterler=kriterler
            )

            sonuc = hesapla_hyp(girdi)

            # Sonucu göster
            self.calc_sonuc_text.delete("1.0", "end")

            output = f"""
╔══════════════════════════════════════════════════╗
║  HYP HESAPLAMA SONUCU                             ║
╠══════════════════════════════════════════════════╣

📊 BİRİM BİLGİLERİ
   Nüfus: {sonuc.toplam_nufus}
   Birim Türü: {sonuc.birim_turu.upper()}

📈 KATSAYILAR
   ├─ Tavan Katsayısı: {sonuc.tavan_katsayisi:.4f}
   ├─ Kriterler Çarpımı: {sonuc.kriterler_carpimi:.4f}
   └─ Tarama Takip Katsayısı: {sonuc.tarama_takip_katsayisi:.4f}

"""

            if sonuc.tarama_takip_katsayisi < 1.0:
                output += f"   ⚠️ UYARI: Katsayı 1'in altında!\n\n"

            output += "📋 KRİTER DETAYLARI\n"
            output += "─" * 50 + "\n"

            for ks in sonuc.kriter_sonuclari:
                durum_emoji = "🔴" if ks.durum == "kirmizi" else "🟢" if ks.durum == "yesil" else "🟡" if ks.durum == "sari" else "🟠"
                output += f"""
   {get_kriter_ismi(ks.tur)}:
   {durum_emoji} Başarı: %{ks.basari_yuzdesi:.1f} | Katsayı: {ks.kriter_katsayisi:.4f}
      Gereken: {ks.gereken} | Yapılan: {ks.yapilan} | Kalan: {ks.kalan}
      {ks.aciklama}
"""

            output += "\n" + "═" * 50

            self.calc_sonuc_text.insert("1.0", output)

        except Exception as e:
            self.calc_sonuc_text.delete("1.0", "end")
            self.calc_sonuc_text.insert("1.0", f"❌ Hata: {str(e)}")
            import traceback
            traceback.print_exc()

    def check_for_updates(self):
        """Güncelleme sekmesindeki butonla güncelleme kontrolü"""
        self.check_update_btn.configure(text="⏳ Denetleniyor...", state="disabled")
        self.update_idletasks()

        def on_update_result(result):
            def update_ui():
                self.check_update_btn.configure(
                    text="🔍 Güncelleme Denetle",
                    state="normal"
                )

                if result.get("error"):
                    self.update_status_label.configure(
                        text=f"⚠️ Kontrol başarısız: {result['error']}",
                        text_color="#e74c3c"
                    )
                elif result.get("has_update"):
                    new_version = result.get("remote_version", "?")
                    self.update_status_label.configure(
                        text=f"🎉 Yeni versiyon mevcut: v{new_version}",
                        text_color="#f39c12"
                    )
                    # Güncelleme popup'ı göster
                    self.show_update_available_popup(result)
                else:
                    self.update_status_label.configure(
                        text=f"✅ Güncel sürümü kullanıyorsunuz (v{self.VERSION})",
                        text_color="#2ecc71"
                    )

            self.after(0, update_ui)

        check_for_updates_async(on_update_result)

    def check_for_app_updates(self):
        """Uygulama başlangıcında otomatik güncelleme kontrolü"""
        def on_startup_update_result(result):
            def show_update():
                if result.get("has_update") and not result.get("error"):
                    self.log_message(f"🆕 Yeni versiyon mevcut: v{result.get('remote_version')}")
                    self.show_update_available_popup(result)
                elif result.get("error"):
                    # Hata varsa sessizce logla, kullanıcıyı rahatsız etme
                    if self.debug_mode.get():
                        self.log_message(f"[DEBUG] Güncelleme kontrolü: {result['error']}")

            self.after(0, show_update)

        check_for_updates_async(on_startup_update_result)

    def show_update_available_popup(self, update_info: dict):
        """Yeni güncelleme mevcut popup'ı"""
        popup = ctk.CTkToplevel(self)
        popup.title("Güncelleme Mevcut")
        popup.geometry("450x350")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        # Popup'ı ortala
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 450) // 2
        y = self.winfo_y() + (self.winfo_height() - 350) // 2
        popup.geometry(f"+{x}+{y}")

        # Ana frame
        main_frame = ctk.CTkFrame(popup, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=25, pady=20)

        # Başlık
        ctk.CTkLabel(
            main_frame,
            text="🎉 Yeni Güncelleme Mevcut!",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(0, 15))

        # Versiyon bilgisi
        version_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        version_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            version_frame,
            text=f"Mevcut: v{self.VERSION}  →  Yeni: v{update_info.get('remote_version', '?')}",
            font=ctk.CTkFont(size=14),
            text_color="#00d4aa"
        ).pack(pady=12)

        # Değişiklikler
        changelog = update_info.get("changelog", [])
        if changelog:
            ctk.CTkLabel(
                main_frame,
                text="📋 Değişiklikler:",
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w"
            ).pack(fill="x", pady=(10, 5))

            changelog_text = "\n".join([f"  • {item}" for item in changelog[:5]])
            ctk.CTkLabel(
                main_frame,
                text=changelog_text,
                font=ctk.CTkFont(size=12),
                anchor="w",
                justify="left",
                text_color="#bdc3c7"
            ).pack(fill="x", padx=10)

        # Butonlar
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        download_url = update_info.get("download_url", "")

        def open_download():
            import webbrowser
            if download_url:
                webbrowser.open(download_url)
            popup.destroy()

        ctk.CTkButton(
            btn_frame,
            text="📥 İndir",
            command=open_download,
            width=120,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#27ae60",
            hover_color="#2ecc71"
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="Sonra",
            command=popup.destroy,
            width=100,
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color="#7f8c8d",
            hover_color="#95a5a6"
        ).pack(side="left")

    # ============================================================
    # MINIMIZE/RESTORE DÜZELTMESİ (Windows API ile)
    # ============================================================
    def _setup_windows_restore_fix(self):
        """Windows'ta minimize/restore sorununu çöz"""
        import ctypes
        from ctypes import wintypes

        # Windows API sabitleri
        self._SW_RESTORE = 9
        self._SW_SHOW = 5
        self._SW_SHOWNORMAL = 1

        # Bind events
        self.bind("<Map>", self._on_window_map)
        self.bind("<Unmap>", self._on_window_unmap)
        self.bind("<FocusIn>", self._on_focus_in)

        # Pencere durumu kontrolü için timer
        self._check_window_state()

    def _on_window_map(self, event=None):
        """Pencere görünür olduğunda"""
        if event and event.widget == self:
            self._is_minimized = False

    def _on_window_unmap(self, event=None):
        """Pencere minimize edildiğinde"""
        if event and event.widget == self:
            self._is_minimized = True

    def _on_focus_in(self, event=None):
        """Pencere focus aldığında - restore işlemi"""
        if event and event.widget == self:
            if self._is_minimized or self.state() == 'iconic':
                self._force_restore_window()

    def _check_window_state(self):
        """Periyodik pencere durumu kontrolü"""
        try:
            # Eğer pencere iconic (minimize) ama focus alıyorsa, restore et
            if self.focus_get() and self.state() == 'iconic':
                self._force_restore_window()
        except:
            pass
        # Her 500ms kontrol et
        self.after(500, self._check_window_state)

    def _force_restore_window(self):
        """Windows API kullanarak pencereyi zorla restore et"""
        try:
            import ctypes

            # Pencere handle'ını al
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()

            # ShowWindow ile restore et
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE

            # Pencereyi öne getir
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.BringWindowToTop(hwnd)

            # Tkinter tarafında da güncelle
            self.deiconify()
            self.lift()
            self.focus_force()
            self.update()

            self._is_minimized = False
        except Exception as e:
            # Fallback: sadece tkinter metodları
            try:
                self.deiconify()
                self.lift()
                self.focus_force()
                self.attributes('-topmost', True)
                self.after(100, lambda: self.attributes('-topmost', False))
            except:
                pass

    def on_closing(self):
        """Uygulama kapatılırken GUI'yi temizle (Chrome açık kalır)"""
        try:
            # Otomasyon çalışıyorsa durdur (Chrome açık kalır)
            if self.is_running:
                self.is_running = False
                if hasattr(self, 'automation') and self.automation:
                    self.automation.should_stop = True

            # Tüm açık popup/toplevel pencerelerini kapat
            for widget in self.winfo_children():
                if isinstance(widget, ctk.CTkToplevel):
                    try:
                        widget.grab_release()
                        widget.destroy()
                    except:
                        pass
        except:
            pass

        # GUI'yi kapat ve Python process'i sonlandır
        try:
            self.quit()
            self.destroy()
        except:
            pass

        # Zorla çıkış - GUI kapansın ama Chrome açık kalsın
        import os
        os._exit(0)


# ============================================================
# VIDEO SPLASH SCREEN + MAIN
# ============================================================
import tkinter as tk


def main():
    video_path = os.path.join(os.path.dirname(__file__), "splash_video.mp4")

    # Video yoksa veya cv2 yoksa direkt uygulamayı aç
    if not os.path.exists(video_path):
        app = HYPApp()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
        return

    try:
        import cv2
        from PIL import Image, ImageTk
    except ImportError:
        app = HYPApp()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
        return

    # Ana uygulama - gizli olarak oluştur
    app = HYPApp()
    app.withdraw()  # Gizle
    app.protocol("WM_DELETE_WINDOW", app.on_closing)

    # Splash penceresi
    splash = tk.Toplevel(app)
    splash.title("")
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    splash.configure(bg="#000000")

    width, height = 600, 600
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    splash.geometry(f"{width}x{height}+{x}+{y}")

    video_label = tk.Label(splash, bg="#000000")
    video_label.pack(fill="both", expand=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        splash.destroy()
        app.deiconify()
        app.mainloop()
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_delay = int(1000 / fps) if fps > 0 else 33
    max_duration_ms = 3000
    start_time = datetime.now()
    is_closed = [False]

    def play_frame():
        if is_closed[0]:
            return

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        if elapsed >= max_duration_ms:
            close_splash()
            return

        ret, frame = cap.read()
        if not ret:
            close_splash()
            return

        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame.shape[:2]
            scale = min(width / w, height / h)
            new_w, new_h = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image)
            video_label.configure(image=photo)
            video_label.image = photo

            splash.after(frame_delay, play_frame)
        except:
            close_splash()

    def close_splash():
        if is_closed[0]:
            return
        is_closed[0] = True
        cap.release()
        splash.destroy()
        # Ana uygulamayı hemen göster
        app.deiconify()
        app.lift()
        app.focus_force()

    splash.after(max_duration_ms, close_splash)
    splash.after(50, play_frame)
    app.mainloop()


if __name__ == "__main__":
    main()

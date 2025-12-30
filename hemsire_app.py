# -*- coding: utf-8 -*-
"""
HYP Hemsire Paneli v3.0 (Bildirimli)
====================================
TC gonder, bildirim al, gecmisi gor.
"""

import customtkinter as ctk
import os
import json
from datetime import datetime
import threading
import time

# ============================================================
# YAPILANDIRMA
# ============================================================
SHARED_FOLDER = r"Z:\Dr Osman"
SETTINGS_FILE = "hemsire_ayarlar.json"
NOTIFICATIONS_FILE = "hemsire_bildirimler.json"

# Tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class HemsireApp(ctk.CTk):
    """Hemsire Paneli - TC Gonder + Bildirim Al"""

    def __init__(self):
        super().__init__()

        self.title("HYP Hemsire")
        self.geometry("400x350")
        self.resizable(False, False)
        self.configure(fg_color="#1a1a2e")

        # Ortala
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 200
        y = (self.winfo_screenheight() // 2) - 175
        self.geometry(f"400x350+{x}+{y}")

        # Ayarlari yukle
        self.load_settings()

        # Bildirimler
        self.notifications = []
        self.unread_count = 0
        self.load_notifications()

        # Arayuz
        self.create_widgets()

        # Bildirim dinleyici baslat
        self.notification_listener_active = True
        self.start_notification_listener()

        # Enter tusu ile gonder
        self.bind('<Return>', lambda e: self.send_tc())

        # Kapatirken dinleyiciyi durdur
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_settings(self):
        """Ayarlari yukle"""
        self.shared_folder = SHARED_FOLDER
        settings_path = os.path.join(os.path.dirname(__file__), SETTINGS_FILE)

        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.shared_folder = settings.get('shared_folder', SHARED_FOLDER)
            except:
                pass

    def save_settings(self):
        """Ayarlari kaydet"""
        settings_path = os.path.join(os.path.dirname(__file__), SETTINGS_FILE)
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump({'shared_folder': self.shared_folder}, f, ensure_ascii=False)
        except:
            pass

    def load_notifications(self):
        """Bildirimleri dosyadan yukle"""
        notifications_path = os.path.join(os.path.dirname(__file__), NOTIFICATIONS_FILE)
        if os.path.exists(notifications_path):
            try:
                with open(notifications_path, 'r', encoding='utf-8') as f:
                    self.notifications = json.load(f)
                    # Okunmamis bildirimleri say
                    self.unread_count = sum(1 for n in self.notifications if not n.get('okundu', True))
            except:
                self.notifications = []

    def save_notifications(self):
        """Bildirimleri dosyaya kaydet"""
        notifications_path = os.path.join(os.path.dirname(__file__), NOTIFICATIONS_FILE)
        try:
            with open(notifications_path, 'w', encoding='utf-8') as f:
                json.dump(self.notifications, f, ensure_ascii=False, indent=2)
        except:
            pass

    def create_widgets(self):
        """Arayuz olustur"""

        # Baslik
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(20, 5))

        ctk.CTkLabel(
            header_frame,
            text="HYP HEMSIRE",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#00d4ff"
        ).pack(side="left", padx=30)

        # Gecmis butonu (sag ustte)
        self.history_btn = ctk.CTkButton(
            header_frame,
            text="📋 Geçmiş",
            width=90,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            command=self.show_history
        )
        self.history_btn.pack(side="right", padx=30)

        # Bildirim badge
        self.badge_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="white",
            fg_color="#e74c3c",
            corner_radius=10,
            width=20,
            height=20
        )
        # Badge gizli baslasin
        if self.unread_count > 0:
            self.badge_label.configure(text=str(self.unread_count))
            self.badge_label.place(relx=0.82, rely=0.3)

        ctk.CTkLabel(
            self,
            text="TC girin, doktora otomatik iletilir",
            font=ctk.CTkFont(size=12),
            text_color="#888888"
        ).pack(pady=(0, 15))

        # TC Girisi
        self.tc_entry = ctk.CTkEntry(
            self,
            width=280,
            height=50,
            font=ctk.CTkFont(size=20),
            placeholder_text="TC Kimlik No",
            justify="center"
        )
        self.tc_entry.pack(pady=(0, 15))
        self.tc_entry.focus()

        # Gonder Butonu
        self.send_btn = ctk.CTkButton(
            self,
            text="📤 GÖNDER",
            width=280,
            height=50,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#00d4ff",
            hover_color="#00a8cc",
            command=self.send_tc
        )
        self.send_btn.pack(pady=(0, 15))

        # Durum
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="#888888"
        )
        self.status_label.pack()

        # Son bildirim gosterimi
        self.last_notification_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            wraplength=350
        )
        self.last_notification_label.pack(pady=(10, 0))

        # Alt kisim - Ayarlar
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", pady=10)

        ctk.CTkButton(
            bottom_frame,
            text="⚙️",
            width=35,
            height=25,
            font=ctk.CTkFont(size=12),
            fg_color="#333333",
            hover_color="#444444",
            command=self.show_settings
        ).pack(side="right", padx=20)

    def send_tc(self):
        """TC'yi doktora gonder"""
        tc = self.tc_entry.get().strip()

        # Validasyon
        if not tc:
            self.show_status("TC giriniz!", "error")
            return

        if not tc.isdigit():
            self.show_status("TC sadece rakam olmalı!", "error")
            return

        if len(tc) != 11:
            self.show_status("TC 11 haneli olmalı!", "error")
            return

        # Klasor kontrolu
        if not os.path.exists(self.shared_folder):
            try:
                os.makedirs(self.shared_folder, exist_ok=True)
            except:
                self.show_status("Paylaşım klasörü bulunamadı!", "error")
                return

        # TC dosyasi olustur
        try:
            tc_file = os.path.join(self.shared_folder, f"{tc}.tc")

            # Zaten varsa uyar
            if os.path.exists(tc_file):
                self.show_status("Bu TC zaten kuyrukta!", "warning")
                return

            # Dosya olustur
            with open(tc_file, 'w', encoding='utf-8') as f:
                f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            self.show_status("✓ Gönderildi!", "success")
            self.tc_entry.delete(0, 'end')
            self.tc_entry.focus()

            # 2 saniye sonra durumu temizle
            self.after(2000, lambda: self.status_label.configure(text=""))

        except Exception as e:
            self.show_status(f"Hata: {e}", "error")

    def show_status(self, message, status_type="info"):
        """Durum mesaji goster"""
        colors = {
            "success": "#00ff88",
            "error": "#ff4444",
            "warning": "#ffaa00",
            "info": "#888888"
        }
        color = colors.get(status_type, "#888888")
        self.status_label.configure(text=message, text_color=color)

    def start_notification_listener(self):
        """Bildirim dinleyiciyi baslat"""
        def listen():
            while self.notification_listener_active:
                try:
                    self.check_new_notifications()
                except:
                    pass
                time.sleep(1)  # Her saniye kontrol et

        thread = threading.Thread(target=listen, daemon=True)
        thread.start()

    def check_new_notifications(self):
        """Yeni bildirimleri kontrol et"""
        if not os.path.exists(self.shared_folder):
            return

        try:
            # .bildirim dosyalarini ara
            for filename in os.listdir(self.shared_folder):
                if filename.endswith('.bildirim'):
                    filepath = os.path.join(self.shared_folder, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            notification = json.load(f)

                        # Listeye ekle
                        notification['okundu'] = False
                        self.notifications.insert(0, notification)  # En basa ekle
                        self.unread_count += 1

                        # Dosyayi sil
                        os.remove(filepath)

                        # GUI'yi guncelle
                        self.after(0, self.update_notification_ui)
                        self.after(0, lambda n=notification: self.show_notification_popup(n))

                    except Exception as e:
                        print(f"Bildirim okuma hatasi: {e}")
                        try:
                            os.remove(filepath)  # Bozuk dosyayi sil
                        except:
                            pass

            # Bildirimleri kaydet
            self.save_notifications()

        except Exception as e:
            print(f"Bildirim kontrol hatasi: {e}")

    def update_notification_ui(self):
        """Bildirim UI'ini guncelle"""
        if self.unread_count > 0:
            self.badge_label.configure(text=str(self.unread_count))
            self.badge_label.place(relx=0.82, rely=0.3)
        else:
            self.badge_label.place_forget()

    def show_notification_popup(self, notification):
        """Yeni bildirim popup'u goster"""
        status = notification.get('status', 'info')
        message = notification.get('message', '')

        # Durum ikonlari ve renkleri
        icons = {
            "success": "✅",
            "error": "❌",
            "sms_kapali": "📵",
            "eksik_tetkik": "🔬"
        }
        colors = {
            "success": "#00ff88",
            "error": "#ff4444",
            "sms_kapali": "#ffaa00",
            "eksik_tetkik": "#ff8800"
        }

        icon = icons.get(status, "📋")
        color = colors.get(status, "#888888")

        # Son bildirim label'ini guncelle
        short_msg = message[:60] + "..." if len(message) > 60 else message
        self.last_notification_label.configure(
            text=f"{icon} {short_msg}",
            text_color=color
        )

        # Popup penceresi goster
        popup = ctk.CTkToplevel(self)
        popup.title("Bildirim")
        popup.geometry("400x200")
        popup.resizable(False, False)
        popup.configure(fg_color="#1a1a2e")

        # Ortala
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - 200
        y = (popup.winfo_screenheight() // 2) - 100
        popup.geometry(f"400x200+{x}+{y}")

        popup.transient(self)
        popup.grab_set()

        # Ikon
        ctk.CTkLabel(
            popup,
            text=icon,
            font=ctk.CTkFont(size=48)
        ).pack(pady=(20, 10))

        # Mesaj
        ctk.CTkLabel(
            popup,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=color,
            wraplength=360
        ).pack(pady=10)

        # Tamam butonu
        ctk.CTkButton(
            popup,
            text="Tamam",
            width=100,
            height=35,
            command=popup.destroy
        ).pack(pady=10)

        # 5 saniye sonra otomatik kapat
        popup.after(5000, popup.destroy)

    def show_history(self):
        """Gecmis bildirimleri goster"""
        # Tum bildirimleri okundu olarak isaretle
        for n in self.notifications:
            n['okundu'] = True
        self.unread_count = 0
        self.update_notification_ui()
        self.save_notifications()

        # Dialog olustur
        dialog = ctk.CTkToplevel(self)
        dialog.title("Bildirim Geçmişi")
        dialog.geometry("500x600")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#1a1a2e")

        # Ortala
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 300
        dialog.geometry(f"500x600+{x}+{y}")

        dialog.transient(self)
        dialog.grab_set()

        # Baslik
        ctk.CTkLabel(
            dialog,
            text="📋 Bildirim Geçmişi",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#00d4ff"
        ).pack(pady=20)

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color="#13151b",
            corner_radius=10,
            height=450
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        if self.notifications:
            for notification in self.notifications:
                self.create_notification_card(scroll_frame, notification)
        else:
            ctk.CTkLabel(
                scroll_frame,
                text="Henüz bildirim yok",
                font=ctk.CTkFont(size=13),
                text_color="#666666"
            ).pack(pady=50)

        # Alt butonlar
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="🗑️ Tümünü Temizle",
            width=130,
            height=35,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=lambda: self.clear_history(dialog)
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Kapat",
            width=100,
            height=35,
            fg_color="#34495e",
            hover_color="#2c3e50",
            command=dialog.destroy
        ).pack(side="right")

    def create_notification_card(self, parent, notification):
        """Bildirim karti olustur"""
        status = notification.get('status', 'info')
        message = notification.get('message', '')
        tarih = notification.get('tarih', '')
        hasta_adi = notification.get('hasta_adi', '')
        eksik_tetkikler = notification.get('eksik_tetkikler', [])

        # Durum renkleri ve ikonlari
        status_config = {
            "success": {"icon": "✅", "color": "#00ff88", "bg": "#1a3d1a"},
            "error": {"icon": "❌", "color": "#ff4444", "bg": "#3d1a1a"},
            "sms_kapali": {"icon": "📵", "color": "#ffaa00", "bg": "#3d3d1a"},
            "eksik_tetkik": {"icon": "🔬", "color": "#ff8800", "bg": "#3d2a1a"}
        }

        config = status_config.get(status, {"icon": "📋", "color": "#888888", "bg": "#2a2a2a"})

        # Kart frame
        card = ctk.CTkFrame(parent, fg_color=config["bg"], corner_radius=10)
        card.pack(fill="x", pady=5, padx=5)

        # Ust kisim - ikon, hasta adi, tarih
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text=f"{config['icon']} {hasta_adi}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=config["color"]
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=tarih,
            font=ctk.CTkFont(size=10),
            text_color="#666666"
        ).pack(side="right")

        # Mesaj
        ctk.CTkLabel(
            card,
            text=message,
            font=ctk.CTkFont(size=12),
            text_color="#cccccc",
            wraplength=440,
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=10, pady=(0, 10))

        # Eksik tetkikler varsa goster
        if eksik_tetkikler:
            tetkik_text = "Eksik: " + ", ".join(eksik_tetkikler[:3])
            if len(eksik_tetkikler) > 3:
                tetkik_text += f" (+{len(eksik_tetkikler)-3})"

            ctk.CTkLabel(
                card,
                text=tetkik_text,
                font=ctk.CTkFont(size=10),
                text_color="#ff8800"
            ).pack(fill="x", padx=10, pady=(0, 10))

    def clear_history(self, dialog):
        """Gecmisi temizle"""
        self.notifications = []
        self.unread_count = 0
        self.save_notifications()
        self.update_notification_ui()
        self.last_notification_label.configure(text="")
        dialog.destroy()
        self.show_history()  # Yeniden ac (bos gosterecek)

    def show_settings(self):
        """Ayarlar penceresi"""
        dialog = ctk.CTkInputDialog(
            text=f"Paylaşım klasörü:\n(Mevcut: {self.shared_folder})",
            title="Ayarlar"
        )
        result = dialog.get_input()

        if result and result.strip():
            self.shared_folder = result.strip()
            self.save_settings()
            self.show_status("Ayarlar kaydedildi", "success")

    def on_close(self):
        """Uygulama kapatilirken"""
        self.notification_listener_active = False
        self.save_notifications()
        self.destroy()


if __name__ == "__main__":
    app = HemsireApp()
    app.mainloop()

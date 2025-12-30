#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HYP OTOMASYON SISTEMI - Hızlı Başlatıcı
Anında splash gösterir, arka planda modülleri yükler.
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

# Çalışma dizinini ayarla
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Encoding ayarla
if sys.platform == "win32":
    try:
        import locale
        locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
    except:
        pass


def show_quick_splash_and_load():
    """Hızlı splash göster, arka planda yükle"""
    import tkinter as tk
    import threading

    # Splash penceresi - ANINDA açılır
    splash = tk.Tk()
    splash.title("")
    splash.overrideredirect(True)
    splash.configure(bg="#0f0f23")
    splash.attributes("-topmost", True)

    # Ekran ortasına konumla
    width, height = 400, 200
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    splash.geometry(f"{width}x{height}+{x}+{y}")

    # İkon ayarla
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "hyp_icon.ico")
        if os.path.exists(icon_path):
            splash.iconbitmap(icon_path)
    except:
        pass

    # Başlık
    title_label = tk.Label(
        splash,
        text="🏥 HYP Otomasyon",
        font=("Segoe UI", 24, "bold"),
        bg="#0f0f23",
        fg="#e0e0e0"
    )
    title_label.pack(pady=(30, 10))

    # Yükleniyor mesajı
    loading_label = tk.Label(
        splash,
        text="Yükleniyor...",
        font=("Segoe UI", 12),
        bg="#0f0f23",
        fg="#00d4aa"
    )
    loading_label.pack(pady=(5, 10))

    # Progress bar benzeri animasyon
    progress_frame = tk.Frame(splash, bg="#1a1a3a", height=6, width=300)
    progress_frame.pack(pady=(10, 0))
    progress_frame.pack_propagate(False)

    progress_bar = tk.Frame(progress_frame, bg="#00d4aa", height=6, width=0)
    progress_bar.place(x=0, y=0)

    # Yükleme durumu
    load_state = {"done": False, "app": None, "error": None, "progress": 0}

    def animate_progress():
        """Progress bar animasyonu"""
        if load_state["done"]:
            return

        # Yükleme tamamlanana kadar yavaş ilerle, sonra hızla tamamla
        if load_state["progress"] < 280:
            if load_state["app"] is not None:
                # Yükleme bitti, hızlı tamamla
                load_state["progress"] += 20
            else:
                # Henüz yükleniyor, yavaş ilerle
                load_state["progress"] += 3

            progress_bar.configure(width=load_state["progress"])

        splash.after(30, animate_progress)

    def load_modules():
        """Ağır modülleri arka planda yükle"""
        try:
            # Ağır importlar burada yapılıyor
            from gui_app import HYPApp
            load_state["app"] = HYPApp
        except Exception as e:
            load_state["error"] = str(e)
        finally:
            load_state["done"] = True

    def check_load_complete():
        """Yükleme tamamlandı mı kontrol et"""
        if load_state["done"]:
            if load_state["error"]:
                # Hata durumu
                splash.destroy()
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("HYP Otomasyon Hatası",
                    f"Uygulama başlatılamadı:\n\n{load_state['error']}")
                root.destroy()
                return

            # Başarılı - Ana uygulamayı başlat
            splash.destroy()

            # Ana uygulamayı oluştur
            app = load_state["app"]()
            app.protocol("WM_DELETE_WINDOW", app.on_closing)

            # Video splash'ı göster (gui_app içindeki main yerine)
            show_video_splash(app)

            app.mainloop()
        else:
            splash.after(50, check_load_complete)

    # Yükleme thread'ini başlat
    load_thread = threading.Thread(target=load_modules, daemon=True)
    load_thread.start()

    # Animasyonu başlat
    splash.after(10, animate_progress)

    # Yükleme kontrolünü başlat
    splash.after(100, check_load_complete)

    splash.mainloop()


def show_video_splash(app):
    """Video splash göster (opsiyonel)"""
    import tkinter as tk
    from datetime import datetime

    video_path = os.path.join(os.path.dirname(__file__), "splash_video.mp4")

    # Video yoksa direkt göster
    if not os.path.exists(video_path):
        app.deiconify()
        app.lift()
        app.focus_force()
        return

    try:
        import cv2
        from PIL import Image, ImageTk
    except ImportError:
        app.deiconify()
        app.lift()
        app.focus_force()
        return

    # Ana uygulamayı gizle
    app.withdraw()

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
        app.lift()
        app.focus_force()
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
        app.deiconify()
        app.lift()
        app.focus_force()

    splash.after(max_duration_ms, close_splash)
    splash.after(50, play_frame)


def main():
    """Ana fonksiyon"""
    try:
        show_quick_splash_and_load()
    except Exception as e:
        # Hata durumunda messagebox göster
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("HYP Otomasyon Hatası", f"Uygulama başlatılamadı:\n\n{str(e)}")
        root.destroy()


if __name__ == "__main__":
    main()

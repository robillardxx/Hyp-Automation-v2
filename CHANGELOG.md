# HYP Otomasyon - Guncelleme Gunlugu

## [v6.9.7] - 2026-01-05

### Kuyruk Sistemi Iyilestirmesi
- **Tek Chrome Oturumu:** Kuyruktaki tum hastalar artik tek Chrome oturumunda isleniyor
- **Performans:** Her hasta icin Chrome acilip kapanmasi sorunu giderildi
- **Kararlilik:** Chrome crash sorunu cozuldu

### Sonsuz Dongu Duzeltmesi
- **Diyabet Protokolu:** Ayni sayfada 3 kez takilinca HYP atlanip sonrakine geciliyor
- **Hipertansiyon Protokolu:** Ayni kontrol eklendi
- **Log Mesaji:** 'X sayfasinda 3 kez takili kaldi, HYP atlaniyor' uyarisi

### Gebelik Sorusu Duzeltmesi
- **KAN_SEKERI Sayfasi:** Diyabet taramada gebelik sorusu artik cevaplanıyor
- **Gebe Listesi Kontrolu:** Hasta gebe listesindeyse EVET, degilse HAYIR seciliyor
- **Onceki Sorun:** Gebelik sorusu cevaplanmadigi icin sayfa ilerlemiyordu

---

## [v6.9.6] - 2025-12-30

### Performans Iyilestirmeleri

#### Super Hizli Coklu Tarih Sorgulama
- **Bellek Tabanli Filtreleme:** 100 hasta satirini tek seferde okur, bellekte tarih filtreleme yapar
- **Tarih Basi Sorgu YOK:** Her tarih icin ayri sayfa yuklemesi yerine tek okuma
- **Performans Kazanci:** ~100 saniyeden ~3 saniyeye dustu (30x hizlanma)

#### GUI Donma Onleme
- **Periyodik Guncelleme:** 150ms arayla GUI refresh timer
- **Arka Plan Islemleri:** Otomasyon calisirken GUI donmuyor

### Hata Duzeltmeleri

#### Turkce Karakter Arama Sorunu
- **normalize_tr() Fonksiyonu:** Hasta isimlerinde Turkce karakter uyumsuzlugu giderildi
- **Ornek:** "MECBURE CAKMAK" artik "MECBURE CAKMAK" ile eslesiyor

#### KVR Protokol Takilma Sorunu
- **Ayni Sayfa Tespiti:** Ayni URL'de 4+ kez kalma durumu algilaniyor
- **Otomatik Iptal:** Protokol takildiginda HYP iptal edilip sonrakine geciyor

#### DEVAM EDIYOR Durumu
- **Baslat Butonu Eksikligi:** "Baslat butonu bulunamadi" hatasi duzeltildi
- **Protokol Algilama:** Sayfa zaten protokol icindeyse devam ediliyor

### HYP Bakanlik Sistemi Guncellemeleri (v2.7.0 - v2.7.14)

#### Bizi Etkileyen Degisiklikler
- **v2.7.10:** Devam eden islemler durumunda yeni islemlere baslayamama kurallari
- **v2.7.9:** Edmonton evrelemesi kontrolu (Obezite izlem) - izlenmeli
- **v2.7.8:** Hasta popup validasyonu kaldirildi - test edilmeli

#### Gelecek Potansiyeli (v2.7.0)
- Koroner Arter, Inme, Kronik Bobrek, KOAH, Astim modulleri

---

## [v6.9.5] - 2025-12-30

### Yeni Ozellikler

#### Kendi Verilerimle Hesapla Butonu
- **Yeni Buton:** Hesaplama sekmesinde "📊 Kendi Verilerimle Güncelle" butonu
- **Otomatik Doldurma:** Uygulamadaki hedef ve yapilan degerleri otomatik doldurur
- **Tek Tikla Hesaplama:** Verileri doldurup hemen HESAPLA butonuna basabilirsiniz

---

## [v6.9.4] - 2025-12-30

### Yeni Ozellikler

#### Hemsire Bildirim Sistemi
- **Anlik Bildirim:** TC islendikten sonra hemsireye otomatik bildirim gider
- **Basarili Islem:** "X hastanin HYP'leri basariyla yapildi!"
- **SMS Kapali:** "X hastanin HYP'leri yapilamadi cunku SMS onayi kapali!"
- **Eksik Tetkik:** "X hastanin HYP'leri yapilamadi cunku su tetkikler eksik: ..."
- **Popup Bildirimi:** Hemsire uygulamasinda anlik popup gosterimi
- **Gecmis Butonu:** Tum bildirimler "Gecmis" butonunda saklanir

#### Hemsire Uygulamasi v3.0
- **Bildirim Dinleyici:** Paylasimli klasorden bildirimleri okur
- **Bildirim Kartlari:** Renkli kartlarla basari/hata/uyari gosterimi
- **Badge Sayaci:** Okunmamis bildirim sayisi gosterimi
- **Gecmis Temizleme:** Tum bildirimleri temizleme secenegi

---

## [v6.9.3] - 2025-12-30

### Yeni Ozellikler

#### Hemsire TC Takip Penceresi
- **Yeni Buton:** "👩‍⚕️ HEMŞİRE" butonu ile takip penceresi aciliyor
- **Kuyrukta Bekleyenler:** Hemsirenin gonderdigi bekleyen TC'ler listeleniyor
- **Tamamlanan Islemler:** Yapilan HYP'ler tarih ve durum ile gosteriliyor
- **Dinleyici Kontrolu:** Pencereden dinleyiciyi acip kapatabilirsiniz
- **Gecmis Temizleme:** Tamamlanan islemler listesi temizlenebilir

#### Windows Baslangic Destegi
- **Otomatik Baslama:** Bilgisayar acildiginda uygulama otomatik baslar
- **Ayarlar Menusu:** Ayarlar > Windows Baslangic bolumunden acilip kapatilabilir
- **Registry Tabanli:** Windows Registry kullanilarak stabil calisma

#### Hemsire TC Chrome Kapatma
- **Otomatik Kapanma:** Her TC islemi bittikten sonra Chrome otomatik kapaniyor
- **Kaynak Tasarrufu:** 50 TC gonderildiginde 50 Chrome acik kalmaz

---

## [v6.9.2] - 2025-12-30

### Yeni Ozellikler

#### Hemsire TC Kuyrugu Gosterimi
- **Anlik Takip:** Hemsirenin gonderdigi TC'ler arayuzde anlik gorunuyor
- **Kuyruk Sayaci:** Kac TC bekliyor badge olarak gosteriliyor
- **TC Listesi:** Bekleyen TC numaralari liste halinde goruntuleniyor
- **Otomatik Gizleme:** Kuyruk bosaldigi anda gorunum gizleniyor

#### Hemsire TC Isleme Akisi
- **Normal Otomasyon Akisi:** Hemsire TC gonderdginde normal BASLAT butonu gibi calisiyor
- **Tam Login:** Chrome aciliyor -> HYP giris -> Dashboard -> Hasta arama -> HYP yapma
- **Senkron Islem:** Kuyrukta birden fazla TC varsa sirayla isleniyor

---

## [v6.9.1] - 2025-12-30

### Yeni Ozellikler

#### System Tray (Gorev Cubugu) Destegi
- **Arka Planda Calisma:** Pencere kapatildiginda (X butonu) uygulama kapanmaz, system tray'e kuculur
- **Tray Ikonu:** Gorev cubugu gizli simgeler alaninda turkuaz HYP ikonu gorunur
- **Sag Tik Menusu:**
  - Goster - Pencereyi tekrar acar
  - Gizle - Pencereyi gizler
  - Cikis - Uygulamayi tamamen kapatir
- **Bagimsiz Calisma:** Otomasyon tray'de arka planda calismaya devam eder
- **Windows Native:** `infi.systray` kutuphanesi ile stabil calisma

#### Fizik Muayene Sayfa Boyutu
- **100 Hasta:** Fizik Muayene Kayitlari sayfasinda artik 100 hasta gosteriliyor (onceki: 50)

### Hata Duzeltmeleri

#### Coklu Tarih Secimi Dialogi
- **Buton Gorunurlugu:** "DEVAM ET" ve "IPTAL" butonlari artik gorunuyor
- **Pencere Boyutu:** Dialog boyutu 550x550'den 550x650'ye cikarildi
- **Sorun:** Onceden butonlar pencere disinda kaliyordu

#### Sol Panel Navigasyon Sorunu
- **Navigasyon Butonlari:** Dashboard, Hasta Sorgula, Ayarlar vb. butonlar artik kaybolmuyor
- **nav_frame Duzeltmesi:** Navigasyon frame'i instance degiskeni olarak saklaniyor
- **_refresh_nav_buttons:** Fonksiyon artik dogru sekilde nav_frame'e erisiyor

### Teknik Degisiklikler
- `infi.systray` kutuphanesi eklendi (Windows native system tray)
- `gui_app.py` - System tray metodlari, dialog boyutu, nav_frame duzeltmesi
- `hyp_automation.py` - Fizik Muayene sayfa boyutu 50 -> 100

---

## [v6.9.0] - 2025-12-26

### Kritik Hata Duzeltmeleri
- **Loop Sorunu Cozuldu:** HYP iptal edildikten sonra ayni HYP'nin tekrar denenmesi sorunu giderildi
  - `_process_hipertansiyon()` TETKIK sayfasi kontrolu duzeltildi
  - `_process_diyabet()` KAN_SEKERI ve TETKIK sayfalari kontrolu duzeltildi
  - HYP iptalinde fonksiyon artik `False` donduruyor ve sonraki HYP'ye geciyor

### Yeni Ozellikler

#### Cache Sistemi (Islenmis Hasta Takibi)
- **1 Ay Cache:** Yapilan HYP'ler 1 ay boyunca hatirlanir
- **Tekrar Isleme Engeli:** Ayni hasta ayni HYP icin tekrar islenmez
- **Performans:** Coklu tarih seciminde sadece yeni hastalar islenir
- **Cache Temizleme:** Eksik tetkik listesinden silince cache'den de silinir
- **Dosya:** `processed_patients.json`

#### Log Sistemi Yenilendi
- **Minimal Log Modu:** Sadece onemli loglar gosteriliyor (hasta adi, HYP sonucu, hatalar)
- **Detayli Log Butonu:** "Detayli Log Goster" butonuyla tum loglara erisim
- **Log Filtreleme:** Gereksiz teknik loglar gizleniyor
- **Kaydet ve Kopyala:** Detayli loglari dosyaya kaydetme ve panoya kopyalama

#### Coklu Tarih Secimi
- **Checkbox Listesi:** Son 14 gun icin coklu secim
- **Hizli Secim Butonlari:** "Son 3 Gun", "Son 1 Hafta", "Tumunu Sec"
- **Secim Sayaci:** Kac tarih secildigini gosteren badge
- **Toplu Islem:** Birden fazla tarihi tek seferde isleme

#### Eksik Tetkik Takip Sekmesi
- **Yeni Sekme:** "Eksik Tetkik" sekmesi eklendi
- **Hasta Listesi:** Tetkik eksik oldugu icin atlanan hastalar listeleniyor
- **Panoya Kopyala:** Liste hemsirelere kolayca aktarilabilir
- **Silme + Cache:** Listeden silince cache'den de silinir (tekrar denenebilir)
- **Otomatik Kayit:** Otomasyon bitiminde liste otomatik kaydediliyor

#### Hemsire Entegrasyonu v2
- **Basit Arayuz:** Sadece TC girisi ve Gonder butonu
- **Exe Uygulama:** `HYP_Hemsire.exe` - Python kurulumu gerektirmez
- **Paylasimli Klasor:** `Z:\Dr Osman` uzerinden iletisim
- **Dosya Tabanli:** `.tc` dosyalari ile hizli haberlesme (200ms polling)
- **Otomatik Dinleyici:** Uygulama acildiginda otomatik baslar
- **Anlik Islem:** Hemsire TC gonderince otomasyon hemen baslar

### Dosya Degisiklikleri
- `hyp_automation.py` - Loop duzeltmeleri, cache sistemi
- `gui_app.py` - Log sistemi, tarih secici, eksik tetkik, hemsire dinleyici
- `hemsire_app/` - Yeni klasor (Hemsire uygulamasi)
  - `HYP_Hemsire.exe` - Hemsire icin bagimsiz uygulama
  - `BENIOKU.txt` - Kurulum talimatlari

---

## [v6.8.0] - 2025-12-16

### Yeni Ozellikler - Modern Dashboard Tasarimi

#### Login Ekrani (login_manager.py)
- **Yeni:** Modern numpad PIN girisi
- **Yeni:** 6 haneli PIN gosterge noktalari (turkuaz parlak efekt)
- **Yeni:** Yuvarlak butonlu 3x4 keypad tasarimi
- **Yeni:** "HYP Automation" + "SECURE ACCESS" basliklari
- **Yeni:** Remember Me toggle switch
- **Yeni:** Gradient LOGIN butonu
- **Yeni:** "Forgot PIN?" ve "Support" linkleri
- **Yeni:** System ID ve versiyon badge'i
- **Yeni:** Klavye destegi (rakam tuslari + backspace + enter)
- **Yeni:** 6 hane dolunca otomatik giris

#### Ana Dashboard (gui_app.py)
- **Yeni:** Sol sidebar navigasyon menusu
  - Logo + "HYP Otomasyon" basligi
  - Dashboard, Hasta Sorgula, Hedef Listeleri, Hesaplamalar
  - Ayarlar, Yardim
  - Aktif sayfa gostergesi (turkuaz cizgi)
  - Kullanici profili bolumu + yesil durum noktasi
- **Yeni:** Modern header
  - Sayfa basligi ("Genel Bakis")
  - "Sistem Online" badge'i
  - Debug toggle (pill style)
  - Tema ve ayar butonlari
- **Yeni:** COLORS sinif degiskeni (renk paleti merkezi yonetim)

#### Kota Kartlari
- **Yeni:** Her tarama tipine ozel ikon ve renk
- **Yeni:** Durum badge'leri (TAMAM, IYI, NORMAL, DIKKAT, ALERT, BEKLEMEDE)
- **Yeni:** Buyuk sayi gosterimi (X / Y formati)
- **Yeni:** Renkli progress bar (tarama tipine gore)
- **Yeni:** Ilerleme yuzdesi ve kalan sayisi alt satirda

### Renk Paleti (Referans Tasarim)
```
bg_dark:          #0f111a   (Ana arka plan)
sidebar_bg:       #13151b   (Sidebar arka plan)
surface:          #181a24   (Yuzey rengi)
surface_highlight: #1e212b  (Vurgulu yuzey)
card_bg:          #1e212b   (Kart arka plan)
border:           #272a36   (Border rengi)
primary:          #2dd4bf   (Turkuaz accent)
secondary:        #0ea5e9   (Mavi)
success:          #22c55e   (Yesil)
warning:          #f59e0b   (Turuncu)
danger:           #ef4444   (Kirmizi)
```

### Teknik Degisiklikler
- `HYPApp.COLORS` dictionary eklendi
- `create_widgets()` tamamen yeniden yazildi
- `_create_nav_button()` fonksiyonu eklendi
- `_refresh_nav_buttons()` fonksiyonu eklendi
- `navigate_to()` fonksiyonu eklendi
- `create_quota_card()` modernlestirildi
- `_update_card_badge()` fonksiyonu eklendi
- `update_quota_card()` yeni kart yapisina uyumlandi
- `LoginWindow` sinifi tamamen yeniden yazildi

---

## [v6.6.1] - 2025-12-15

### Guncelleme Sistemi
- Otomatik guncelleme kontrolu eklendi
- GitHub uzerinden versiyon kontrolu

---

## [v6.6.0] - 2025-12-14

### Temel Ozellikler
- Aylik hedef takip sistemi
- Gecmis ay performans raporu
- SMS kapali hasta listesi
- HYP hesaplama modulu
- Pin kodu kaydetme ozelligi
- Debug modu (acik Chrome'a baglanma)

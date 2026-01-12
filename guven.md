# HYP Otomasyon - Yasal Uyumluluk ve Guvenlik Belgesi

**Versiyon:** 1.0
**Tarih:** 12 Ocak 2026
**Son Guncelleme:** 12 Ocak 2026

---

## ONEMLI UYARI

**Bu belge yalnizca bilgilendirme amaciyla hazirlanmistir ve hukuki tavsiye niteliginde degildir.**

Kesin hukuki degerlendirme icin bir saglik hukuku veya bilisim hukuku uzmanina danisilmasi sart ile tavsiye edilir. Mevzuat degisiklikleri nedeniyle bu belgedeki bilgiler guncelligini yitirebilir.

---

## Yonetici Ozeti

HYP Otomasyon, aile hekimlerinin **kendi yetkileri dahilindeki** rutin tarama ve izlem islemlerini hizlandirmak icin tasarlanmis bir aractir. Yazilim:

- Hekimin yetkili oldugu HYP sistemine erisir
- Hekimin giris bilgileriyle calisir
- Sadece hekimin zaten yapabilecegi islemleri otomatiklestirir
- Yetkisiz veri erisimi veya sistem mudahalesi yapmaz

---

## 1. Yasal Dayanak

### 1.1 Aile Hekimligi Mevzuati

**5258 Sayili Aile Hekimligi Kanunu** (Kabul: 24.11.2004, RG: 09.12.2004/25665)

Ilgili hukumler:
- **Madde 3:** Aile hekimleri, kayitli kisilerin saglik kayitlarini tutmakla yukumludur
- **Madde 5:** Kayit ve belgeler resmi evrak niteeligindedir
- **Madde 8:** Denetim Bakanlik, mulki idare ve saglik idaresi tarafindan yapilir

**Aile Hekimligi Sozlesme ve Odeme Yonetmeligi** (2025 Guncellemesi)

- Hipertansiyon, diyabet, kanser, obezite tarama/takip islemleri performans katsayisini (0,90-1,50) etkiler
- Hekimlerin bu islemleri yapmasi ZORUNLUDUR
- Otomasyon, bu zorunlu gorevlerin yerine getirilmesini kolaylastirir

**Kaynak:** [5258 Sayili Kanun - Resmi Gazete](https://www.mevzuat.gov.tr/MevzuatMetin/1.5.5258.pdf)

### 1.2 HYP Platformu Hakkinda

HYP (Hastalik Yonetim Platformu), Saglik Bakanligi tarafindan aile hekimlerinin kullanimi icin sunulan resmi bir web platformudur.

**Platform ozellikleri:**
- Hekimler e-Devlet/e-Imza ile giris yapar
- Her hekim sadece kendi kayitli hastalarini gorebilir
- Islemler hekimin kendi yetki alanindadir

**Onemli not:** HYP platformunun kullanim sartlari (Terms of Service) resmi olarak yayinlanmamistir. Bot/otomasyon kullanimina dair acik bir yasak bulunmamaktadir. Ancak Bakanlik bu konuda politikasini degistirebilir.

### 1.3 KVKK Uyumlulugu

**6698 Sayili Kisisel Verilerin Korunmasi Kanunu**

**Madde 6/3 - Saglik Verilerinin Islenmesi:**
> "Saglik verileri, kamu sagliginin korunmasi, koruyucu hekimlik, tibbi teshis, tedavi ve bakim hizmetlerinin yurutulmesi amaciyla, sir saklama yukumlulugu altinda bulunan kisiler tarafindan ilgilinin acik rizasi aranmaksizin islenebilir."

**Aile hekiminin konumu:**
- Kayitli hastalarinin saglik verilerine **suresiz erisim hakki** vardir
- Sir saklama yukumlulugu altindadir
- KVKK kapsaminda "yetkili kisi" konumundadir

**Otomasyon ve KVKK:**
- Otomasyon, hekimin KVKK kapsamindaki yetkilerini ASMIYOR
- Erisilebilen veriler zaten hekimin gorebilecegi veriler
- Veri isleme amaci: Koruyucu hekimlik, tarama/takip

**Kaynak:** [KVKK Resmi Sitesi](https://www.kvkk.gov.tr/)

### 1.4 Turk Ceza Kanunu - Bilisim Suclari

**TCK Madde 243 - Bilisim Sistemine Girme:**
> "Bir bilisim sisteminin butunune veya bir kismina, **hukuka aykiri olarak** giren kimseye bir yila kadar hapis cezasi verilir."

**Anahtar kavram: "Hukuka Aykiri"**

HYP Otomasyon kullanimi hukuka aykiri DEGILDIR cunku:
1. Hekim, sisteme **kendi yetkisiyle** giris yapar
2. e-Imza sifresi hekim tarafindan girilir
3. Erisilen veriler hekimin zaten gorebilecegi verilerdir
4. Sistem zarar gormez, veri degistirilmez/silinmez

**TCK Madde 244 - Sistemi Engelleme/Bozma:**
Bu madde otomasyon ile ILGISIZDIR cunku:
- Sistem engellenmez/bozulmaz
- Veriler yok edilmez/degistirilmez
- Normal kullanici akisi simule edilir

**Kaynak:** [Bilisim Suclari - BTK](https://internet.btk.gov.tr/turkiye-de-bilisim-hukuku)

---

## 2. Bu Yazilim Ne Yapar / Ne Yapmaz

### 2.1 YAPAR

| Islem | Aciklama |
|-------|----------|
| Oturum acma | Hekimin kendi e-Imza sifresiyle |
| Hasta listesi goruntuleme | Sadece kayitli hastalar |
| Form doldurma | Tarama/izlem formlarini otomatik doldurma |
| Buton tiklama | "Ilerle", "Kaydet" gibi standart islemler |
| Veri okuma | Hekimin zaten gorebilecegi bilgiler |

### 2.2 YAPMAZ

| Islem | Aciklama |
|-------|----------|
| Yetkisiz erisim | Baska hekimlerin hastlarina erismez |
| Veri silme | Hasta kayitlarini silmez |
| Veri degistirme | Mevcut verileri bozmaz |
| Sistem saldirisi | DDoS, brute-force vb. yapmaz |
| Veri cikartma | Toplu veri export etmez |
| Sifre kaydetme | PIN bellekte tutulur, diske **guvenli sifrelenm**is olarak kaydedilir |

---

## 3. Risk Analizi

### 3.1 Teknik Riskler

| Risk | Olasilik | Etki | Onlem |
|------|----------|------|-------|
| Yanlis veri girisi | Dusuk | Orta | Manuel dogrulama onerilir |
| Oturum zaman asimi | Orta | Dusuk | Otomatik yeniden baglanti |
| Platform degisikligi | Orta | Yuksek | Duzeltmelerin guncellemeler ile giderilmesi ongoruluyor |

### 3.2 Hukuki Riskler

| Risk | Deger | Aciklama |
|------|----------|----------|
| TCK 243 ihlali | **Cok Dusuk** | Yetkili kullanim, hukuka aykiri degil |
| KVKK ihlali | **Cok Dusuk** | Hekim zaten yetkili, veri aktarimi yok |
| Meslek etigi ihlali | **Dusuk** | Islem hala hekim adinadir |
| Bakanlik yaptirimi | **Belirsiz** | Acik mevzuat yok, politika degisebilir |

### 3.3 En Kotu Senaryo

Bakanlik, otomasyon kullanimini yasaklayan bir genelge yayinlarsa:
- Yazilim kullanimi durdurulmalidir
- Gecmise donuk ceza uygulanmasi BEKLENMEZ (kanunilik ilkesi)
- Disiplin soru strmasi OLASI DEGILDIR (mevcut yasak yok)

---

## 4. Sikca Sorulan Sorular

### S1: "Bakanlik bunu ogrenirse sorun cikarir mi?"

**C:** Su an icin HYP'de otomasyon kullanimini yasaklayan bir mevzuat bulunmamaktadir. Ancak:
- Bakanlik politikasini degistirebilir
- Guncellemeleri takip etmeniz onerilir
- Dikkat cekici olmayan kullanim (normal hizda) tavsiye edilir

### S2: "Bu yasal mi?"

**C:** Mevcut mevzuata gore:
- TCK 243 kapsaminda suc YOKTUR (yetkili erisim)
- KVKK ihlali YOKTUR (hekim zaten yetkili)
- Acik bir yasak YOKTUR

Ancak "yasal" ve "Bakanlik tarafindan onaylanmis" farkli seylerdir. Resmi onay yoktur.

### S3: "Verilerim guvenli mi?"

**C:**
- PIN sifreli saklanir (PBKDF2 + makine-bagli anahtar)
- Hasta verileri yerel olarak SAKLANMAZ
- Veriler sadece HYP oturumu boyunca bellekte tutulur

### S4: "Diger hekimler de kullaniyor mu?"

**C:**
- Bu tur araclar yaygin olarak kullanilmaktadir
- Resmi istatistik bulunmamaktadir
- Her hekimin kendi risk degerlendirmesi yapmasi onerilir

### S5: "Ne zaman kullanmamam gerekir?"

**C:**
- Bakanlik acik yasak yayinlarsa
- Platform kullanim sartlari degisirse
- Mesleki sorumluluk sigortaniz bunu kapsamamorsa

---

## 5. Sonuc ve Tavsiyeler

### 5.1 Genel Degerlendirme

HYP Otomasyon, **mevcut mevzuat cercevesinde** kullanimi sakincali gorunmeyen bir aractir. Ancak:

1. **Kesin hukuki guvence yoktur** - Resmi onay bulunmamaktadir
2. **Politika degisebilir** - Bakanlik yeni duzenleme yapabilir
3. **Sorumluluk hekimindir** - Yapilan islemler hekim adina yapilir

### 5.2 Kullanim Onerileri

1. **Manuel dogrulama:** Kritik islemleri manuel kontrol edin
2. **Guncellemeleri takip edin:** Mevzuat degisikliklerini izleyin
3. **Dikkatli kullanim:** Asiri hizli/yogun kullanim dikkat cekebilir
4. **Yedek plan:** Otomasyon calismazsa manuel islem yapabilmelisiniz
5. **Hukuki danismanlik:** Supheniz varsa uzman gorusu alin

### 5.3 Sorumluluk Reddi

Bu yazilimin gelistiricileri:
- Hukuki tavsiye vermemektedir
- Kullanim sonuclarindan sorumlu degildir
- Mevzuat uyumlulugun takibini kullaniciya birakmaktadir

---

## Kaynakca

1. [5258 Sayili Aile Hekimligi Kanunu](https://www.mevzuat.gov.tr/MevzuatMetin/1.5.5258.pdf) - T.C. Resmi Gazete
2. [Aile Hekimligi Rehberi 2025](https://hsgm.saglik.gov.tr/depo/Yayinlarimiz/Rehberler/AILE_HEKIMLIGI_REHBERI_2025.pdf) - Saglik Bakanligi
3. [KVKK Resmi Web Sitesi](https://www.kvkk.gov.tr/) - Kisisel Verileri Koruma Kurumu
4. [Kisisel Saglik Verileri Yonetmeligi](https://kisiselveri.saglik.gov.tr/) - Saglik Bakanligi
5. [Bilisim Hukuku - BTK](https://internet.btk.gov.tr/turkiye-de-bilisim-hukuku) - Bilgi Teknolojileri ve Iletisim Kurumu
6. [TCK 243-245 Bilisim Suclari](https://www.gaissecurity.com/blog/turk-ceza-kanununda-tck-bilisim-suclari-ve-ornek-senaryolarla-incelenmesi) - Hukuk Analizi
7. [RPA ve Saglik Sektoru](https://hukukvebilisim.org/robotik-surec-otomasyonu-rpa-nedir/) - Hukuk ve Bilisim Dergisi

---

**Belge Sonu**

*Bu belge HYP Otomasyon v6.9.9 ile birlikte dagitilmaktadir.*
*Sorulariniz icin: [Gelistirici iletisim bilgileri eklenebilir]*

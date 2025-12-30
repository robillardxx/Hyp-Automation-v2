# HYP Katsayı Hesaplama Sistemi - Teknik Dokümantasyon

> **Yasal Dayanak:**  
> - Aile Hekimliği Sözleşme ve Ödeme Yönetmeliği (Madde 18, 20, 21)
> - Aile Hekimliği Tarama ve Takip Katsayısına İlişkin Yönerge
> - HYP Tarama ve Takip Kılavuzu (01.06.2025 yürürlük)
>
> **Kaynak Site:** [hyp.camlicaasm.gov.tr](https://hyp.camlicaasm.gov.tr)  
> **Versiyon:** 2.0 | **Tarih:** 2025-12-15

---

## 1. Sistem Genel Bakışı

### 1.1 HYP Nedir?

HYP (Hastalık Yönetim Platformu), aile hekimliği birimlerinin kronik hastalık tarama, takip ve izlem performanslarını ölçen Sağlık Bakanlığı sistemidir. Bu performans **maaşa esas puan** hesaplamasında doğrudan çarpan olarak kullanılır.

### 1.2 Temel Formül

```
Maaşa Esas Puan = Ara Puan × Tarama ve Takip Katsayısı

Tarama ve Takip Katsayısı = Kriter₁ × Kriter₂ × Kriter₃ × ... × KriterN
```

### 1.3 Katsayı Sınırları

| Durum | Katsayı Aralığı |
|-------|-----------------|
| Normal Birimler | 0.90 - 1.50 |
| Sevk Sistemi Uygulanan | 0.90 - 2.00 |
| Hiç HYP Yapılmamış | 0.90 (sabit) |

---

## 2. EK-1: Asgari ve Azami Başarı Oranları

### 2.1 Aile Hekimliği Birimi İçin

| Kriter | Alt Tür | Asgari (%) | Azami (%) |
|--------|---------|------------|-----------|
| **Hipertansiyon** | Tarama | 40 | 90 |
| | İzlem | 50 | 90 |
| | Sonuç | 40 | 90 |
| **Diyabet** | Tarama | 40 | 90 |
| | İzlem | 50 | 90 |
| | Sonuç | 40 | 90 |
| **Obezite** | Tarama | 40 | 90 |
| | İzlem | 50 | 90 |
| | Sonuç | 40 | 90 |
| **Kardiyovasküler Risk** | Tarama | 40 | 90 |
| | İzlem | 50 | 90 |
| | Sonuç | 40 | 90 |
| **Yaşlı Sağlığı** | Tarama | 40 | 90 |
| | İzlem | 50 | 90 |
| | Sonuç | 40 | 90 |
| **Serviks Kanseri** | Tarama | 50 | 90 |
| **Kolorektal Kanser** | Tarama | 50 | 90 |
| **Meme Kanseri** | Tarama | 40 | 90 |
| **Süreç Yönetimi** | - | 50 | **80** ⚠️ |

> ⚠️ **DİKKAT:** Süreç Yönetimi kriteri için azami başarı %80'dir (diğerlerinden farklı!)

### 2.2 Aile Sağlığı Çalışanları İçin (01.06.2025 sonrası)

| Kriter | Asgari (%) | Azami (%) | Asgari Altı Katsayı | Asgari Katsayı | Azami Katsayı |
|--------|------------|-----------|---------------------|----------------|---------------|
| **Vital Bulgular** | 50 | 90 | 0.93 | 1.00 | 1.06 |
| **Yaşlı Değerlendirme** | 50 | 90 | 0.97 | 1.00 | 1.13 |

> **Maksimum ASÇ Katsayısı:** 1.06 × 1.13 = **1.1978** (her iki parametrede %90 başarı ile)

---

## 3. EK-2: Kriter Katsayısı Hesaplama

### 3.1 Hesaplama Prensibi

Yönetmelik ifadesi: *"Başarı oranları ile **doğru orantılı** olarak asgari ve azami değerler arasında belirlenen kriter katsayılarının değerleri"*

### 3.2 Katsayı Belirleme Algoritması

```
Eğer başarı = 0:
    katsayı = 0.90

Eğer başarı < asgari:
    katsayı = 0.90 + (başarı / asgari) × 0.10  // Lineer interpolasyon
    // Sonuç: 0.90 - 0.9999 arası

Eğer asgari ≤ başarı ≤ azami:
    katsayı = 1.00  // İdeal aralık

Eğer başarı > azami:
    katsayı = 1.00  // Fazlası devredilir
```

### 3.3 Durum Renk Kodları

| Renk | Durum | Katsayı | Açıklama |
|------|-------|---------|----------|
| 🔴 Kırmızı | Asgari Altı | < 1.00 | Tamamlayınız! |
| 🟢 Yeşil | İdeal Aralık | 1.00 | Sorun yok |
| 🟡 Sarı | Azami Üstü (%90-100) | 1.00 | Devir %10 kayıplı |
| 🟠 Turuncu | %100 Üstü | 1.00 | Sonraki aya devir |

---

## 4. Tavan Katsayısı

### 4.1 Birim Türüne Göre Limitler

| Birim Türü | Azami Nüfus | Birim Katsayısı | Özel Kurallar |
|------------|-------------|-----------------|---------------|
| Normal | 4000 | 1.00 | - |
| Entegre | 2400 | 1.65 | Aylık 96 saat nöbet zorunlu |
| Zorunlu Düşük Nüfus | 2400 | 1.65 | Aylık 96 saat nöbet zorunlu |
| Tutuklu/Hükümlü >2000 | 2000 | 1.00 | Asgari üstünde ise katsayı=1 |
| Tutuklu/Hükümlü >1700 | 1700 | - | Tavan: 1.176471 |
| Tutuklu/Hükümlü 1500-1700 | 1500 | - | Tavan: 1.333334 |

### 4.2 Tavan Katsayısı Formülü

```javascript
function tavanKatsayisi(nufus, birimTuru, sevkSistemi) {
    const azamiNufus = birimTuru === 'normal' ? 4000 : 2400;
    
    if (nufus >= azamiNufus) {
        return 1.0;  // Tavan nüfusu aşanlar için max 1
    }
    
    const maksimum = sevkSistemi ? 2.0 : 1.5;
    return Math.min(azamiNufus / nufus, maksimum);
}
```

### 4.3 Entegre Birim Nöbet Kesintisi

```javascript
// Her tutulmayan 8 saat için %8 kesinti
const kesinti = Math.floor((96 - tutulanNobetSaati) / 8) * 0.08;
const birimKatsayisi = 1.65 * (1 - kesinti);
```

---

## 5. Devir (Carry-Over) Sistemi

### 5.1 Devir Kuralları

1. **Devir Koşulu:** Gerçekleşme yüzdesi %100'ü aştığında fazla işlemler devredilir
2. **Maksimum Süre:** En fazla 2 ay ileriye devir yapılabilir
3. **Kullanım Şartı:** Devreden sayının kullanılabilmesi için o ay en az **%10** işlem yapılmalı
4. **%10 Kaybı:** Azami başarı (%90) üstündeki devirler %10 kayıpla kullanılır

### 5.2 Devir Algoritması

```javascript
function hesaplaDevir(yapilan, gereken, mevcutDevir) {
    const basari = (yapilan / gereken) * 100;
    const asgariIslem = gereken * 0.10;
    
    // Devir kullanım kontrolü
    if (yapilan >= asgariIslem && mevcutDevir > 0) {
        const devirliBasari = ((yapilan + mevcutDevir) / gereken) * 100;
        return { devirKullanildi: true, yeniBasari: devirliBasari };
    }
    
    // %100 üstü yeni devir
    if (basari > 100) {
        return { yeniDevir: yapilan - gereken };
    }
    
    return { devirKullanildi: false, yeniBasari: basari };
}
```

### 5.3 Devir Kullanılmazsa (<%10 Yapılmışsa)

| Devir Miktarı | Durum | Uygulanan Katsayı |
|---------------|-------|-------------------|
| < Azami başarı oranı | İlk devreden ay | Asgari altı katsayısı |
| ≥ Azami başarı oranı | İlk devreden ay | 1.00 |
| ≥ Azami başarı oranı | Sonraki aylar | Asgari altı katsayısı |

---

## 6. Aile Sağlığı Çalışanı Hesaplama Kuralları

### 6.1 ASÇ Katsayı Belirleme

ASÇ için **iki bağımsız kriter** vardır:
- Vital Bulgular
- Yaşlı Sağlığı Değerlendirmesi

```
ASÇ Tarama Takip Katsayısı = Vital Katsayı × Yaşlı Katsayı
```

### 6.2 Birim Katsayısından Faydalanma

```javascript
function ascSonKatsayi(ascKatsayi, birimKatsayisi) {
    const birimYuzde75 = birimKatsayisi * 0.75;
    
    // Katsayı 1'in altında ise kendi katsayısı
    if (ascKatsayi < 1.0) {
        return ascKatsayi;
    }
    
    // 1 ve üstü ama birim %75'inin altında
    if (ascKatsayi < birimYuzde75) {
        return ascKatsayi;
    }
    
    // Birim veya ASÇ'den yüksek olanı
    return Math.max(ascKatsayi, birimKatsayi);
}
```

### 6.3 Örnek Senaryolar

| Birim Katsayısı | ASÇ Katsayısı | %75 Eşiği | Sonuç |
|-----------------|---------------|-----------|-------|
| 1.50 | 0.95 | 1.125 | 0.95 (kendi) |
| 1.50 | 1.10 | 1.125 | 1.10 (kendi) |
| 1.50 | 1.20 | 1.125 | 1.50 (birim) |
| 1.40 | 1.05 | 1.05 | 1.40 (birim) |
| 1.40 | 1.00 | 1.05 | 1.00 (kendi) |

---

## 7. Özel Durumlar ve İstisnalar

### 7.1 Otomatik Katsayı = 1 Durumları

| Durum | Açıklama |
|-------|----------|
| Maaşa esas puan < 1000 | Otomatik katsayı = 1 |
| Yeni birim (ilk 18 ay) | 6. ayda 500 nüfusa ulaşmışsa, ilk 2000 puan için katsayı = 1 |
| Hedef nüfus = 0 | İlgili kriter için katsayı = 1 |
| Yüksek nüfus + Asgari üstü | Nüfus > azami ve başarı ≥ asgari ise katsayı = 1 |

### 7.2 Yüksek Nüfuslu Birim İstisnası

```javascript
// Yönetmelik Madde 7(4)
if (nufus > azamiNufus && basariOrani >= asgariBasari) {
    kriterKatsayisi = 1.0;
}
```

---

## 8. Maaş Hesaplaması

### 8.1 Maaş Formülü

```
Maaşa Esas Puan = Ara Puan × Tarama Takip Katsayısı

Brüt Maaş = İlk 1000 Puan Ücreti + Kalan Puan Ücreti
```

### 8.2 İlk 1000 Puan Ücreti

| Hekim Türü | Oran |
|------------|------|
| Uzman Tabip / Tabip | Tavan ücretin %78.5'i |
| Aile Hekimliği Uzmanı | Tavan ücretin %113.5'i |

### 8.3 Kalan Puan Ücreti

```
Kalan Puan Ücreti = (Maaşa Esas Puan - 1000) × Tavan Ücret × 0.000522
```

### 8.4 Örnek Maaş Hesabı

```
Girdi:
- Ara Puan: 3200
- Tarama Takip Katsayısı: 1.15
- Tavan Ücret: 50.000 TL
- Hekim Türü: Aile Hekimliği Uzmanı

Hesaplama:
- Maaşa Esas Puan = 3200 × 1.15 = 3680
- İlk 1000 Puan = 50.000 × 1.135 = 56.750 TL
- Kalan Puan = (3680 - 1000) × 50.000 × 0.000522 = 69.948 TL
- Toplam Brüt = 56.750 + 69.948 = 126.698 TL
```

---

## 9. Entegrasyon Rehberi

### 9.1 Dosya Yapısı

```
/hyp-otomasyon/
├── src/
│   ├── hyp-hesaplama-modulu.ts    # Ana hesaplama modülü
│   ├── types.ts                    # Tip tanımları
│   └── constants.ts                # Sabit değerler
├── tests/
│   └── hyp.test.ts                 # Test dosyaları
└── README.md
```

### 9.2 Temel Kullanım

```typescript
import { hesaplaHYP, hesaplaASCHYP, HYPGirdi } from './hyp-hesaplama-modulu';

// Aile Hekimi Hesaplaması
const birimVerisi: HYPGirdi = {
  birimId: 'ASM-001-01',
  donem: '2025-12',
  nufus: 3500,
  birimTuru: 'normal',
  kriterler: [
    { tur: 'dm_tarama', gereken: 100, yapilan: 85, gecenAyDevir: 10 },
    { tur: 'dm_izlem', gereken: 50, yapilan: 45 },
    { tur: 'ht_tarama', gereken: 120, yapilan: 110 },
    { tur: 'ht_izlem', gereken: 60, yapilan: 55 },
    // ... diğer kriterler
  ]
};

const sonuc = hesaplaHYP(birimVerisi);
console.log('Tarama Takip Katsayısı:', sonuc.taramaTakipKatsayisi);
```

### 9.3 Validasyon Kontrolleri

```typescript
function validateGirdi(girdi: HYPGirdi): string[] {
  const hatalar: string[] = [];
  
  if (girdi.nufus <= 0) {
    hatalar.push('Nüfus 0\'dan büyük olmalı');
  }
  
  if (!girdi.donem.match(/^\d{4}-\d{2}$/)) {
    hatalar.push('Dönem formatı YYYY-MM olmalı');
  }
  
  for (const kriter of girdi.kriterler) {
    if (kriter.yapilan < 0 || kriter.gereken < 0) {
      hatalar.push(`${kriter.tur}: Negatif değer olamaz`);
    }
  }
  
  return hatalar;
}
```

---

## 10. Site ile Korelasyon Kontrolü

### 10.1 hyp.camlicaasm.gov.tr ile Uyum

| Özellik | Site | Bu Modül | Durum |
|---------|------|----------|-------|
| Asgari/Azami Oranlar | EK-1 tablosu | `KRITER_BASARI_ORANLARI` | ✅ Uyumlu |
| Katsayı Hesaplama | Doğru orantılı | Lineer interpolasyon | ✅ Uyumlu |
| Devir Sistemi | %10 kuralı | Aynı mantık | ✅ Uyumlu |
| Tavan Katsayısı | 4000/nüfus | Aynı formül | ✅ Uyumlu |
| Süreç Yönetimi Azami | %80 | `surec_yonetimi: {azami: 80}` | ✅ Uyumlu |
| Renk Kodları | 4 renk | Aynı mantık | ✅ Uyumlu |

### 10.2 Farklılıklar ve Dikkat Edilecekler

1. **Site dinamik JavaScript kullanıyor** - Bizim modül statik hesaplama yapar
2. **Site kullanıcı oturumu tutuyor** - Modül stateless
3. **Site görsel geri bildirim veriyor** - Modül sadece veri döndürür

---

## 11. Sürüm Notları

### v2.0.0 (2025-12-15)
- ✅ ASÇ hesaplama desteği eklendi (01.06.2025 yönergesi)
- ✅ Tutuklu/hükümlü birim katsayıları eklendi
- ✅ Entegre birim nöbet kesintisi hesaplaması
- ✅ Maaş hesaplama fonksiyonu eklendi
- ✅ Resmi kaynaklara göre tüm formüller doğrulandı

### v1.0.0 (İlk sürüm)
- Temel HYP hesaplama
- Kriter katsayıları
- Devir sistemi

---

## 12. Kaynaklar

1. [Aile Hekimliği Sözleşme ve Ödeme Yönetmeliği](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=4198&MevzuatTur=21&MevzuatTertip=5)
2. [Aile Hekimliği Tarama ve Takip Katsayısına İlişkin Yönerge](https://hsgm.saglik.gov.tr/depo/Mevzuat/Yonergeler/Aile_Hekimligi_Tarama_ve_Takip_Katsayisina_Iliskin_Yonerge.pdf)
3. [HYP Tarama ve Takip Kılavuzu](https://hsgm.saglik.gov.tr/depo/birimler/aile-hekimligi-uygulama-ve-gelistirme-db/Dokumanlar/Yonerge/Ek_Hastalik_Yonetim_Platformu_HYP_Tarama_ve_Takip_Kilavuzu_1.pdf)
4. [HYP Hesaplama Modülü (Çamlıca ASM)](https://hyp.camlicaasm.gov.tr)

---

*Bu dokümantasyon resmi Sağlık Bakanlığı kaynakları esas alınarak hazırlanmıştır.*

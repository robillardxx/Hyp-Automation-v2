/**
 * HYP (Hastalık Yönetim Platformu) Katsayı Hesaplama Modülü
 * 
 * Kaynak: Aile Hekimliği Tarama ve Takip Katsayısına İlişkin Yönerge
 *         HYP Tarama ve Takip Kılavuzu (01.06.2025 tarihinde yürürlüğe girdi)
 *         Aile Hekimliği Sözleşme ve Ödeme Yönetmeliği (Madde 18)
 * 
 * @version 2.0.0
 * @date 2025-12-15
 */

// =====================================================
// TİP TANIMLARI
// =====================================================

/** Birim türleri */
export type BirimTuru = 'normal' | 'entegre' | 'zorunlu_dusuk_nufus' | 'tutuklu_hukumlu';

/** Kriter türleri */
export type KriterTuru = 
  | 'ht_tarama' | 'ht_izlem' | 'ht_sonuc'
  | 'dm_tarama' | 'dm_izlem' | 'dm_sonuc'
  | 'obezite_tarama' | 'obezite_izlem' | 'obezite_sonuc'
  | 'kvr_tarama' | 'kvr_izlem' | 'kvr_sonuc'
  | 'yasli_tarama' | 'yasli_izlem' | 'yasli_sonuc'
  | 'serviks_tarama'
  | 'kolorektal_tarama'
  | 'meme_tarama'
  | 'surec_yonetimi';

/** ASÇ (Aile Sağlığı Çalışanı) kriter türleri */
export type ASCKriterTuru = 'vital_bulgular' | 'yasli_degerlendirme';

/** Durum renk kodları */
export type DurumRengi = 'kirmizi' | 'yesil' | 'sari' | 'turuncu';

// =====================================================
// SABİT DEĞERLER - YÖNETMELIK VE YÖNERGEYE GÖRE
// =====================================================

/**
 * EK-1: Kriter Katsayısına Esas Asgari ve Azami Başarı Oranları
 * Kaynak: Aile Hekimliği Tarama ve Takip Katsayısına İlişkin Yönerge
 */
export const KRITER_BASARI_ORANLARI: Record<KriterTuru, { asgari: number; azami: number }> = {
  // Hipertansiyon
  ht_tarama: { asgari: 40, azami: 90 },
  ht_izlem: { asgari: 50, azami: 90 },
  ht_sonuc: { asgari: 40, azami: 90 },
  
  // Diyabet
  dm_tarama: { asgari: 40, azami: 90 },
  dm_izlem: { asgari: 50, azami: 90 },
  dm_sonuc: { asgari: 40, azami: 90 },
  
  // Obezite
  obezite_tarama: { asgari: 40, azami: 90 },
  obezite_izlem: { asgari: 50, azami: 90 },
  obezite_sonuc: { asgari: 40, azami: 90 },
  
  // Kardiyovasküler Risk
  kvr_tarama: { asgari: 40, azami: 90 },
  kvr_izlem: { asgari: 50, azami: 90 },
  kvr_sonuc: { asgari: 40, azami: 90 },
  
  // Yaşlı Sağlığı
  yasli_tarama: { asgari: 40, azami: 90 },
  yasli_izlem: { asgari: 50, azami: 90 },
  yasli_sonuc: { asgari: 40, azami: 90 },
  
  // Kanser Taramaları
  serviks_tarama: { asgari: 50, azami: 90 },
  kolorektal_tarama: { asgari: 50, azami: 90 },
  meme_tarama: { asgari: 40, azami: 90 },
  
  // Süreç Yönetimi (DİKKAT: Azami %80, diğerlerinden farklı!)
  surec_yonetimi: { asgari: 50, azami: 80 }
};

/**
 * EK-2: Başarı Oranlarına Göre Kriter Katsayıları
 * NOT: Yönetmeliğe göre başarı oranları ile "doğru orantılı" olarak hesaplanır
 * Asgari altı için ceza katsayısı, asgari-azami arası 1.0, azami üstü 1.0
 */
export const KATSAYI_SINIRLAR = {
  /** Tarama ve takip katsayısı minimum değeri */
  MINIMUM_KATSAYI: 0.90,
  /** Tarama ve takip katsayısı maksimum değeri (normal birimler) */
  MAKSIMUM_KATSAYI: 1.50,
  /** Sevk sistemi uygulanan yerlerde maksimum katsayı */
  MAKSIMUM_KATSAYI_SEVK: 2.00,
  /** Hiç HYP yapılmadığında uygulanan katsayı */
  HIC_HYP_YAPILMADI: 0.90,
  /** Asgari başarının altında kalan için ceza katsayısı aralığı */
  ASGARI_ALTI_KATSAYI_MIN: 0.90,
  ASGARI_ALTI_KATSAYI_MAX: 0.99
};

/**
 * Aile Sağlığı Çalışanları için Kriter Katsayıları
 * Kaynak: HYP Tarama ve Takip Kılavuzu (01.06.2025)
 */
export const ASC_KRITER_KATSAYILARI = {
  vital_bulgular: {
    asgari: 50,
    azami: 90,
    katsayilar: {
      asgari_alti: 0.93,
      asgari: 1.00,
      azami: 1.06
    }
  },
  yasli_degerlendirme: {
    asgari: 50,
    azami: 90,
    katsayilar: {
      asgari_alti: 0.97,
      asgari: 1.00,
      azami: 1.13
    }
  }
};

/**
 * Birim türüne göre nüfus limitleri ve katsayılar
 */
export const BIRIM_AYARLARI = {
  normal: {
    azamiNufus: 4000,
    birimKatsayisi: 1.00,
    nobetZorunlu: false
  },
  entegre: {
    azamiNufus: 2400,
    birimKatsayisi: 1.65,
    nobetZorunlu: true,
    nobetSaati: 96, // aylık minimum
    nobetKesintisi: 0.08 // her tutulmayan 8 saat için %8 azalma
  },
  zorunlu_dusuk_nufus: {
    azamiNufus: 2400,
    birimKatsayisi: 1.65,
    nobetZorunlu: true,
    nobetSaati: 96,
    nobetKesintisi: 0.08
  },
  tutuklu_hukumlu: {
    azamiNufus: 2000,
    tavanKatsayisi_1700_ustu: 1.176471,
    tavanKatsayisi_1500_1700: 1.333334
  }
};

// =====================================================
// ARAYÜZ TANIMLARI
// =====================================================

/** Kriter verisi girişi */
export interface KriterVerisi {
  tur: KriterTuru;
  gereken: number;
  yapilan: number;
  gecenAyDevir?: number;
}

/** ASÇ kriter verisi */
export interface ASCKriterVerisi {
  tur: ASCKriterTuru;
  gereken: number;
  yapilan: number;
}

/** HYP hesaplama girişi */
export interface HYPGirdi {
  birimId: string;
  donem: string; // "YYYY-MM" formatında
  nufus: number;
  birimTuru: BirimTuru;
  maasaEsasPuan?: number;
  birimYasiAy?: number;
  altiAydaNufus?: number;
  nobetSaati?: number; // Entegre birimler için tutulan nöbet saati
  sevkSistemiAktif?: boolean;
  kriterler: KriterVerisi[];
}

/** ASÇ için HYP hesaplama girişi */
export interface ASCHYPGirdi {
  birimId: string;
  donem: string;
  birimTaramaTakipKatsayisi: number;
  kriterler: ASCKriterVerisi[];
}

/** Kriter sonucu */
export interface KriterSonucu {
  tur: KriterTuru;
  gereken: number;
  yapilan: number;
  gecenAyDevir: number;
  basariYuzdesi: number;
  devirliBasariYuzdesi: number;
  kriterKatsayisi: number;
  kalan: number;
  sonrakiAyaDevir: number;
  durum: DurumRengi;
  aciklama: string;
}

/** HYP hesaplama sonucu */
export interface HYPSonuc {
  donem: string;
  birimId: string;
  toplamNufus: number;
  birimTuru: BirimTuru;
  
  // Katsayılar
  tavanKatsayisi: number;
  kriterlerCarpimi: number;
  taramaTakipKatsayisi: number;
  birimKatsayisi: number;
  
  // Detaylar
  kriterSonuclari: KriterSonucu[];
  
  // Özel durumlar
  istisnaDurumu?: string;
  uyarilar: string[];
}

/** ASÇ HYP sonucu */
export interface ASCHYPSonuc {
  donem: string;
  birimId: string;
  vitalBulgularKatsayisi: number;
  yasliDegerlendirmeKatsayisi: number;
  ascTaramaTakipKatsayisi: number;
  birimKatsayisiKullanildiMi: boolean;
  sonKatsayi: number;
  aciklama: string;
}

// =====================================================
// HESAPLAMA FONKSİYONLARI
// =====================================================

/**
 * Başarı yüzdesini hesaplar
 */
export function hesaplaBasariYuzdesi(yapilan: number, gereken: number): number {
  if (gereken === 0) return 100;
  return (yapilan / gereken) * 100;
}

/**
 * Devirli başarı yüzdesini hesaplar
 * DİKKAT: Devir kullanılabilmesi için o ay en az %10 işlem yapılmış olmalı
 */
export function hesaplaDevirliBasariYuzdesi(
  yapilan: number, 
  gereken: number, 
  devir: number
): { devirliBasari: number; devirKullanildiMi: boolean } {
  if (gereken === 0) return { devirliBasari: 100, devirKullanildiMi: false };
  
  const asgariIslem = gereken * 0.10;
  
  if (yapilan >= asgariIslem && devir > 0) {
    return {
      devirliBasari: ((yapilan + devir) / gereken) * 100,
      devirKullanildiMi: true
    };
  }
  
  return {
    devirliBasari: (yapilan / gereken) * 100,
    devirKullanildiMi: false
  };
}

/**
 * EK-2'ye göre kriter katsayısını hesaplar
 * Yönetmelik: "Başarı oranları ile doğru orantılı olarak asgari ve azami değerler 
 * arasında belirlenen kriter katsayılarının değerleri"
 */
export function hesaplaKriterKatsayisi(
  basariOrani: number,
  asgariBasari: number,
  azamiBasari: number
): { katsayi: number; durum: DurumRengi } {
  
  // Başarı oranı %0 ise (hiç yapılmadı)
  if (basariOrani === 0) {
    return { katsayi: KATSAYI_SINIRLAR.HIC_HYP_YAPILMADI, durum: 'kirmizi' };
  }
  
  // Asgari başarı altında - ceza uygulanır
  if (basariOrani < asgariBasari) {
    // Lineer interpolasyon: 0% -> 0.90, asgari% -> 1.00
    const katsayi = KATSAYI_SINIRLAR.ASGARI_ALTI_KATSAYI_MIN + 
      (basariOrani / asgariBasari) * 
      (1.0 - KATSAYI_SINIRLAR.ASGARI_ALTI_KATSAYI_MIN);
    
    return { 
      katsayi: Math.max(KATSAYI_SINIRLAR.ASGARI_ALTI_KATSAYI_MIN, Math.min(katsayi, 0.9999)),
      durum: 'kirmizi' 
    };
  }
  
  // Asgari-azami arası - ideal aralık, katsayı 1.0
  if (basariOrani >= asgariBasari && basariOrani <= azamiBasari) {
    return { katsayi: 1.0, durum: 'yesil' };
  }
  
  // Azami üstü - %100'e kadar
  if (basariOrani > azamiBasari && basariOrani <= 100) {
    return { katsayi: 1.0, durum: 'sari' };
  }
  
  // %100 üstü - devir olacak
  return { katsayi: 1.0, durum: 'turuncu' };
}

/**
 * Tavan katsayısını hesaplar
 * Yönetmelik Madde 7(5): "azami nüfusun aile hekimliği biriminin mevcut nüfusuna oranını geçemez"
 */
export function hesaplaTavanKatsayisi(
  nufus: number, 
  birimTuru: BirimTuru,
  sevkSistemiAktif: boolean = false
): number {
  const ayarlar = BIRIM_AYARLARI[birimTuru === 'tutuklu_hukumlu' ? 'normal' : birimTuru];
  const azamiNufus = 'azamiNufus' in ayarlar ? ayarlar.azamiNufus : 4000;
  
  // Tutuklu/hükümlü birimleri için özel limitler
  if (birimTuru === 'tutuklu_hukumlu') {
    const thAyarlar = BIRIM_AYARLARI.tutuklu_hukumlu;
    if (nufus > 1700) return thAyarlar.tavanKatsayisi_1700_ustu;
    if (nufus >= 1500) return thAyarlar.tavanKatsayisi_1500_1700;
  }
  
  // Azami nüfus üstünde ise tavan = 1
  if (nufus >= azamiNufus) {
    return 1.0;
  }
  
  // Normal hesaplama
  const maksimum = sevkSistemiAktif ? 
    KATSAYI_SINIRLAR.MAKSIMUM_KATSAYI_SEVK : 
    KATSAYI_SINIRLAR.MAKSIMUM_KATSAYI;
  
  return Math.min(azamiNufus / nufus, maksimum);
}

/**
 * Entegre birim katsayısını nöbet durumuna göre hesaplar
 */
export function hesaplaEntegreBirimKatsayisi(nobetSaati: number): number {
  const ayarlar = BIRIM_AYARLARI.entegre;
  const tabanKatsayi = ayarlar.birimKatsayisi;
  
  if (nobetSaati >= ayarlar.nobetSaati) {
    return tabanKatsayi;
  }
  
  // Her tutulmayan 8 saat için %8 kesinti
  const tutulmayanSaat = ayarlar.nobetSaati - nobetSaati;
  const kesinti = Math.floor(tutulmayanSaat / 8) * ayarlar.nobetKesintisi;
  
  return tabanKatsayi * (1 - kesinti);
}

/**
 * Sonraki aya devredecek miktarı hesaplar
 */
export function hesaplaSonrakiAyaDevir(
  yapilan: number,
  gereken: number,
  mevcutDevir: number,
  devirKullanildiMi: boolean
): number {
  const basariYuzdesi = hesaplaBasariYuzdesi(yapilan, gereken);
  
  // %100'ü aşan kısım devredilir (en fazla 2 ay)
  let yeniDevir = 0;
  if (basariYuzdesi > 100) {
    yeniDevir = yapilan - gereken;
  }
  
  // Eğer devir kullanıldıysa, kullanılan miktarı düş
  if (devirKullanildiMi && mevcutDevir > 0) {
    // Mevcut devir zaten kullanıldı, yeni devir kaldı
    return yeniDevir;
  }
  
  return yeniDevir;
}

/**
 * Ana HYP hesaplama fonksiyonu
 */
export function hesaplaHYP(girdi: HYPGirdi): HYPSonuc {
  const uyarilar: string[] = [];
  let istisnaDurumu: string | undefined;
  
  // Birim ayarlarını al
  const birimAyarlari = BIRIM_AYARLARI[
    girdi.birimTuru === 'tutuklu_hukumlu' ? 'normal' : girdi.birimTuru
  ];
  const azamiNufus = 'azamiNufus' in birimAyarlari ? birimAyarlari.azamiNufus : 4000;
  
  // =====================================================
  // ÖZEL DURUM KONTROLLERİ
  // =====================================================
  
  // 1. Maaşa esas puan < 1000 ise katsayı = 1
  if (girdi.maasaEsasPuan !== undefined && girdi.maasaEsasPuan < 1000) {
    istisnaDurumu = 'Maaşa esas puan 1000\'in altında, tarama takip katsayısı otomatik 1';
    return {
      donem: girdi.donem,
      birimId: girdi.birimId,
      toplamNufus: girdi.nufus,
      birimTuru: girdi.birimTuru,
      tavanKatsayisi: 1.0,
      kriterlerCarpimi: 1.0,
      taramaTakipKatsayisi: 1.0,
      birimKatsayisi: 'birimKatsayisi' in birimAyarlari ? birimAyarlari.birimKatsayisi : 1.0,
      kriterSonuclari: [],
      istisnaDurumu,
      uyarilar
    };
  }
  
  // 2. Yeni açılan birimler (ilk 18 ay, 6. ayda 500 nüfusa ulaşılmışsa)
  if (girdi.birimYasiAy !== undefined && girdi.birimYasiAy <= 18) {
    if (girdi.altiAydaNufus !== undefined && girdi.altiAydaNufus >= 500) {
      istisnaDurumu = 'Yeni açılan birim (ilk 18 ay), ilk 2000 puan için katsayı 1';
      uyarilar.push('Yeni birim istisnası uygulandı');
    }
  }
  
  // =====================================================
  // KRİTER HESAPLAMALARI
  // =====================================================
  
  const kriterSonuclari: KriterSonucu[] = [];
  let kriterlerCarpimi = 1.0;
  
  for (const kriter of girdi.kriterler) {
    const oranlar = KRITER_BASARI_ORANLARI[kriter.tur];
    
    // Hedef nüfus sıfır kontrolü
    if (kriter.gereken === 0) {
      kriterSonuclari.push({
        tur: kriter.tur,
        gereken: 0,
        yapilan: kriter.yapilan,
        gecenAyDevir: kriter.gecenAyDevir || 0,
        basariYuzdesi: 100,
        devirliBasariYuzdesi: 100,
        kriterKatsayisi: 1.0,
        kalan: 0,
        sonrakiAyaDevir: 0,
        durum: 'yesil',
        aciklama: 'Hedef nüfus sıfır, katsayı otomatik 1'
      });
      continue;
    }
    
    // Başarı hesaplamaları
    const basariYuzdesi = hesaplaBasariYuzdesi(kriter.yapilan, kriter.gereken);
    const { devirliBasari, devirKullanildiMi } = hesaplaDevirliBasariYuzdesi(
      kriter.yapilan,
      kriter.gereken,
      kriter.gecenAyDevir || 0
    );
    
    // Katsayı hesaplama
    let kriterKatsayisi: number;
    let durum: DurumRengi;
    
    // Yüksek nüfuslu birim istisnası
    if (girdi.nufus > azamiNufus && devirliBasari >= oranlar.asgari) {
      kriterKatsayisi = 1.0;
      durum = 'yesil';
    } else {
      const sonuc = hesaplaKriterKatsayisi(devirliBasari, oranlar.asgari, oranlar.azami);
      kriterKatsayisi = sonuc.katsayi;
      durum = sonuc.durum;
    }
    
    // Kalan ve devir hesaplama
    const kalan = Math.max(0, kriter.gereken - kriter.yapilan);
    const sonrakiAyaDevir = hesaplaSonrakiAyaDevir(
      kriter.yapilan,
      kriter.gereken,
      kriter.gecenAyDevir || 0,
      devirKullanildiMi
    );
    
    // Açıklama oluştur
    let aciklama = '';
    if (durum === 'kirmizi') {
      aciklama = `Asgari başarı (%${oranlar.asgari}) altında`;
    } else if (durum === 'yesil') {
      aciklama = 'İdeal aralıkta';
    } else if (durum === 'sari') {
      aciklama = 'Azami başarı üstünde (devir kaybı olabilir)';
    } else if (durum === 'turuncu') {
      aciklama = '%100 üstünde, sonraki aya devredecek';
    }
    
    kriterSonuclari.push({
      tur: kriter.tur,
      gereken: kriter.gereken,
      yapilan: kriter.yapilan,
      gecenAyDevir: kriter.gecenAyDevir || 0,
      basariYuzdesi: Math.round(basariYuzdesi * 100) / 100,
      devirliBasariYuzdesi: Math.round(devirliBasari * 100) / 100,
      kriterKatsayisi: Math.round(kriterKatsayisi * 10000) / 10000,
      kalan,
      sonrakiAyaDevir,
      durum,
      aciklama
    });
    
    kriterlerCarpimi *= kriterKatsayisi;
  }
  
  // =====================================================
  // FİNAL HESAPLAMALAR
  // =====================================================
  
  // Tavan katsayısı
  const tavanKatsayisi = hesaplaTavanKatsayisi(
    girdi.nufus, 
    girdi.birimTuru,
    girdi.sevkSistemiAktif
  );
  
  // Birim katsayısı (entegre için nöbet durumuna göre)
  let birimKatsayisi = 1.0;
  if (girdi.birimTuru === 'entegre' || girdi.birimTuru === 'zorunlu_dusuk_nufus') {
    birimKatsayisi = hesaplaEntegreBirimKatsayisi(girdi.nobetSaati || 0);
  }
  
  // Tarama ve takip katsayısı (tavan ile sınırla)
  const taramaTakipKatsayisi = Math.min(
    Math.max(kriterlerCarpimi, KATSAYI_SINIRLAR.MINIMUM_KATSAYI),
    tavanKatsayisi
  );
  
  return {
    donem: girdi.donem,
    birimId: girdi.birimId,
    toplamNufus: girdi.nufus,
    birimTuru: girdi.birimTuru,
    tavanKatsayisi: Math.round(tavanKatsayisi * 10000) / 10000,
    kriterlerCarpimi: Math.round(kriterlerCarpimi * 10000) / 10000,
    taramaTakipKatsayisi: Math.round(taramaTakipKatsayisi * 10000) / 10000,
    birimKatsayisi: Math.round(birimKatsayisi * 10000) / 10000,
    kriterSonuclari,
    istisnaDurumu,
    uyarilar
  };
}

/**
 * Aile Sağlığı Çalışanı için HYP hesaplama
 * Kaynak: HYP Tarama ve Takip Kılavuzu, Yönerge Madde 7
 */
export function hesaplaASCHYP(girdi: ASCHYPGirdi): ASCHYPSonuc {
  let vitalKatsayi = 1.0;
  let yasliKatsayi = 1.0;
  
  for (const kriter of girdi.kriterler) {
    const ayarlar = ASC_KRITER_KATSAYILARI[kriter.tur];
    const basari = hesaplaBasariYuzdesi(kriter.yapilan, kriter.gereken);
    
    let katsayi: number;
    if (basari < ayarlar.asgari) {
      katsayi = ayarlar.katsayilar.asgari_alti;
    } else if (basari >= ayarlar.azami) {
      katsayi = ayarlar.katsayilar.azami;
    } else {
      // Lineer interpolasyon asgari ile azami arasında
      const oran = (basari - ayarlar.asgari) / (ayarlar.azami - ayarlar.asgari);
      katsayi = ayarlar.katsayilar.asgari + oran * (ayarlar.katsayilar.azami - ayarlar.katsayilar.asgari);
    }
    
    if (kriter.tur === 'vital_bulgular') {
      vitalKatsayi = katsayi;
    } else {
      yasliKatsayi = katsayi;
    }
  }
  
  // ASÇ tarama takip katsayısı = vital × yaşlı
  const ascKatsayisi = vitalKatsayi * yasliKatsayi;
  
  // Birim katsayısından faydalanma kuralları
  let sonKatsayi: number;
  let birimKatsayisiKullanildiMi = false;
  let aciklama = '';
  
  const birimKatsayisi = girdi.birimTaramaTakipKatsayisi;
  const birimKatsayisiYuzde75 = birimKatsayisi * 0.75;
  
  if (ascKatsayisi < 1.0) {
    // ASÇ katsayısı 1'in altında ise kendi katsayısı kullanılır
    sonKatsayi = ascKatsayisi;
    aciklama = 'ASÇ katsayısı 1\'in altında, kendi katsayısı uygulandı';
  } else if (ascKatsayisi >= 1.0 && ascKatsayisi < birimKatsayisiYuzde75) {
    // 1 ve üstü ama birim katsayısının %75'inin altında
    sonKatsayi = ascKatsayisi;
    aciklama = `ASÇ katsayısı birim katsayısının %75'inin (${birimKatsayisiYuzde75.toFixed(4)}) altında, kendi katsayısı uygulandı`;
  } else {
    // Birim veya ASÇ katsayısından yüksek olanı
    if (ascKatsayisi >= birimKatsayisi) {
      sonKatsayi = ascKatsayisi;
      aciklama = 'ASÇ katsayısı birim katsayısından yüksek, ASÇ katsayısı uygulandı';
    } else {
      sonKatsayi = birimKatsayisi;
      birimKatsayisiKullanildiMi = true;
      aciklama = 'Birim katsayısı daha yüksek, birim katsayısı uygulandı';
    }
  }
  
  return {
    donem: girdi.donem,
    birimId: girdi.birimId,
    vitalBulgularKatsayisi: Math.round(vitalKatsayi * 10000) / 10000,
    yasliDegerlendirmeKatsayisi: Math.round(yasliKatsayi * 10000) / 10000,
    ascTaramaTakipKatsayisi: Math.round(ascKatsayisi * 10000) / 10000,
    birimKatsayisiKullanildiMi,
    sonKatsayi: Math.round(sonKatsayi * 10000) / 10000,
    aciklama
  };
}

// =====================================================
// MAAŞ HESAPLAMA FONKSİYONLARI
// =====================================================

/**
 * Maaşa esas puanı hesaplar
 * Yönetmelik Madde 18(2)(a)(6): ara puan × tarama takip katsayısı
 */
export interface MaasHesaplamaGirdi {
  araPuan: number;
  taramaTakipKatsayisi: number;
  birimKatsayisi: number;
  tavanUcret: number; // Bakanlıkça belirlenen güncel tavan ücret
  uzmanMi: boolean;
  aileHekimligiUzmaniMi: boolean;
}

export interface MaasHesaplamaSonucu {
  araPuan: number;
  maasaEsasPuan: number;
  ilk1000PuanUcreti: number;
  kalanPuanUcreti: number;
  toplamBrutMaas: number;
}

export function hesaplaMaas(girdi: MaasHesaplamaGirdi): MaasHesaplamaSonucu {
  // Maaşa esas puan = Ara puan × Tarama Takip Katsayısı
  const maasaEsasPuan = girdi.araPuan * girdi.taramaTakipKatsayisi;
  
  // İlk 1000 puan için sabit ücret oranları
  let ilk1000Oran: number;
  if (girdi.aileHekimligiUzmaniMi) {
    ilk1000Oran = 1.135; // %113.5
  } else {
    ilk1000Oran = 0.785; // %78.5 (uzman veya tabip)
  }
  
  const ilk1000PuanUcreti = girdi.tavanUcret * ilk1000Oran;
  
  // 1000 üstü puanlar için
  const kalanPuan = Math.max(0, maasaEsasPuan - 1000);
  const puanBasiOran = 0.000522; // Tavan ücretin onbinde 5.22'si
  const kalanPuanUcreti = kalanPuan * girdi.tavanUcret * puanBasiOran;
  
  return {
    araPuan: Math.round(girdi.araPuan * 100) / 100,
    maasaEsasPuan: Math.round(maasaEsasPuan * 100) / 100,
    ilk1000PuanUcreti: Math.round(ilk1000PuanUcreti * 100) / 100,
    kalanPuanUcreti: Math.round(kalanPuanUcreti * 100) / 100,
    toplamBrutMaas: Math.round((ilk1000PuanUcreti + kalanPuanUcreti) * 100) / 100
  };
}

// =====================================================
// YARDIMCI FONKSİYONLAR
// =====================================================

/**
 * Durum rengine göre açıklama döndürür
 */
export function getDurumAciklamasi(durum: DurumRengi): string {
  switch (durum) {
    case 'kirmizi':
      return 'Asgari Başarı Yüzdesine ulaşılamadı - Katsayı düşük, tamamlayınız!';
    case 'yesil':
      return 'İdeal aralıkta';
    case 'sari':
      return 'Azami Başarı Yüzdesi Geçildi! (Devrederken %10 kaybınız olur)';
    case 'turuncu':
      return '%100 değeri geçildi! Gelecek aya devir olacak!';
    default:
      return '';
  }
}

/**
 * Kalan hesabı için gereken başarı yüzdelerini döndürür (KHT %40, %70, %90)
 */
export function hesaplaKalanlar(gereken: number, yapilan: number): {
  kalanYuzde40: number;
  kalanYuzde70: number;
  kalanYuzde90: number;
} {
  return {
    kalanYuzde40: Math.max(0, Math.ceil(gereken * 0.40) - yapilan),
    kalanYuzde70: Math.max(0, Math.ceil(gereken * 0.70) - yapilan),
    kalanYuzde90: Math.max(0, Math.ceil(gereken * 0.90) - yapilan)
  };
}

/**
 * Kriter ismini Türkçe döndürür
 */
export function getKriterIsmi(tur: KriterTuru): string {
  const isimler: Record<KriterTuru, string> = {
    ht_tarama: 'HT Tarama',
    ht_izlem: 'HT İzlem',
    ht_sonuc: 'HT Sonuç',
    dm_tarama: 'DM Tarama',
    dm_izlem: 'DM İzlem',
    dm_sonuc: 'DM Sonuç',
    obezite_tarama: 'Obezite Tarama',
    obezite_izlem: 'Obezite İzlem',
    obezite_sonuc: 'Obezite Sonuç',
    kvr_tarama: 'KVR Tarama',
    kvr_izlem: 'KVR İzlem',
    kvr_sonuc: 'KVR Sonuç',
    yasli_tarama: 'Yaşlı Tarama',
    yasli_izlem: 'Yaşlı İzlem',
    yasli_sonuc: 'Yaşlı Sonuç',
    serviks_tarama: 'Serviks',
    kolorektal_tarama: 'Kolorektal',
    meme_tarama: 'Mamografi',
    surec_yonetimi: 'Süreç Yönetimi'
  };
  return isimler[tur];
}

// =====================================================
// ÖRNEK KULLANIM
// =====================================================

/*
// Örnek: Aile Hekimi HYP Hesaplama
const ornek: HYPGirdi = {
  birimId: 'ASM-001-01',
  donem: '2025-12',
  nufus: 3500,
  birimTuru: 'normal',
  sevkSistemiAktif: false,
  kriterler: [
    { tur: 'dm_tarama', gereken: 100, yapilan: 85, gecenAyDevir: 10 },
    { tur: 'dm_izlem', gereken: 50, yapilan: 45, gecenAyDevir: 0 },
    { tur: 'ht_tarama', gereken: 120, yapilan: 110, gecenAyDevir: 5 },
    { tur: 'ht_izlem', gereken: 60, yapilan: 55, gecenAyDevir: 0 },
    // ... diğer kriterler
  ]
};

const sonuc = hesaplaHYP(ornek);
console.log('Tarama Takip Katsayısı:', sonuc.taramaTakipKatsayisi);

// Örnek: ASÇ HYP Hesaplama
const ascOrnek: ASCHYPGirdi = {
  birimId: 'ASM-001-01',
  donem: '2025-12',
  birimTaramaTakipKatsayisi: 1.40,
  kriterler: [
    { tur: 'vital_bulgular', gereken: 100, yapilan: 90 },
    { tur: 'yasli_degerlendirme', gereken: 50, yapilan: 45 }
  ]
};

const ascSonuc = hesaplaASCHYP(ascOrnek);
console.log('ASÇ Son Katsayısı:', ascSonuc.sonKatsayi);
*/

export default {
  hesaplaHYP,
  hesaplaASCHYP,
  hesaplaMaas,
  hesaplaBasariYuzdesi,
  hesaplaKriterKatsayisi,
  hesaplaTavanKatsayisi,
  hesaplaKalanlar,
  getKriterIsmi,
  getDurumAciklamasi,
  KRITER_BASARI_ORANLARI,
  ASC_KRITER_KATSAYILARI,
  BIRIM_AYARLARI,
  KATSAYI_SINIRLAR
};

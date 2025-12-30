# -*- coding: utf-8 -*-
"""
HYP (Hastalık Yönetim Platformu) Katsayı Hesaplama Modülü

Kaynak: Aile Hekimliği Tarama ve Takip Katsayısına İlişkin Yönerge
        HYP Tarama ve Takip Kılavuzu (01.06.2025 tarihinde yürürlüğe girdi)
        Aile Hekimliği Sözleşme ve Ödeme Yönetmeliği (Madde 18)

@version 2.0.0
@date 2025-12-15
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


# =====================================================
# TİP TANIMLARI
# =====================================================

class BirimTuru(Enum):
    """Birim türleri"""
    NORMAL = "normal"
    ENTEGRE = "entegre"
    ZORUNLU_DUSUK_NUFUS = "zorunlu_dusuk_nufus"
    TUTUKLU_HUKUMLU = "tutuklu_hukumlu"


class KriterTuru(Enum):
    """Kriter türleri"""
    HT_TARAMA = "ht_tarama"
    HT_IZLEM = "ht_izlem"
    HT_SONUC = "ht_sonuc"
    DM_TARAMA = "dm_tarama"
    DM_IZLEM = "dm_izlem"
    DM_SONUC = "dm_sonuc"
    OBEZITE_TARAMA = "obezite_tarama"
    OBEZITE_IZLEM = "obezite_izlem"
    OBEZITE_SONUC = "obezite_sonuc"
    KVR_TARAMA = "kvr_tarama"
    KVR_IZLEM = "kvr_izlem"
    KVR_SONUC = "kvr_sonuc"
    YASLI_TARAMA = "yasli_tarama"
    YASLI_IZLEM = "yasli_izlem"
    YASLI_SONUC = "yasli_sonuc"
    SERVIKS_TARAMA = "serviks_tarama"
    KOLOREKTAL_TARAMA = "kolorektal_tarama"
    MEME_TARAMA = "meme_tarama"
    SUREC_YONETIMI = "surec_yonetimi"


class ASCKriterTuru(Enum):
    """ASÇ (Aile Sağlığı Çalışanı) kriter türleri"""
    VITAL_BULGULAR = "vital_bulgular"
    YASLI_DEGERLENDIRME = "yasli_degerlendirme"


class DurumRengi(Enum):
    """Durum renk kodları"""
    KIRMIZI = "kirmizi"  # Asgari altı
    YESIL = "yesil"      # İdeal aralık
    SARI = "sari"        # Azami üstü (%90-100)
    TURUNCU = "turuncu"  # %100 üstü


# =====================================================
# SABİT DEĞERLER - YÖNETMELIK VE YÖNERGEYE GÖRE
# =====================================================

# EK-1: Kriter Katsayısına Esas Asgari ve Azami Başarı Oranları
KRITER_BASARI_ORANLARI: Dict[str, Dict[str, int]] = {
    # Hipertansiyon
    "ht_tarama": {"asgari": 40, "azami": 90},
    "ht_izlem": {"asgari": 50, "azami": 90},
    "ht_sonuc": {"asgari": 40, "azami": 90},

    # Diyabet
    "dm_tarama": {"asgari": 40, "azami": 90},
    "dm_izlem": {"asgari": 50, "azami": 90},
    "dm_sonuc": {"asgari": 40, "azami": 90},

    # Obezite
    "obezite_tarama": {"asgari": 40, "azami": 90},
    "obezite_izlem": {"asgari": 50, "azami": 90},
    "obezite_sonuc": {"asgari": 40, "azami": 90},

    # Kardiyovasküler Risk
    "kvr_tarama": {"asgari": 40, "azami": 90},
    "kvr_izlem": {"asgari": 50, "azami": 90},
    "kvr_sonuc": {"asgari": 40, "azami": 90},

    # Yaşlı Sağlığı
    "yasli_tarama": {"asgari": 40, "azami": 90},
    "yasli_izlem": {"asgari": 50, "azami": 90},
    "yasli_sonuc": {"asgari": 40, "azami": 90},

    # Kanser Taramaları
    "serviks_tarama": {"asgari": 50, "azami": 90},
    "kolorektal_tarama": {"asgari": 50, "azami": 90},
    "meme_tarama": {"asgari": 40, "azami": 90},

    # Süreç Yönetimi (DİKKAT: Azami %80, diğerlerinden farklı!)
    "surec_yonetimi": {"asgari": 50, "azami": 80}
}

# EK-2: Başarı Oranlarına Göre Katsayı Sınırları
KATSAYI_SINIRLAR = {
    "MINIMUM_KATSAYI": 0.90,
    "MAKSIMUM_KATSAYI": 1.50,
    "MAKSIMUM_KATSAYI_SEVK": 2.00,
    "HIC_HYP_YAPILMADI": 0.90,
    "ASGARI_ALTI_KATSAYI_MIN": 0.90,
    "ASGARI_ALTI_KATSAYI_MAX": 0.99
}

# Aile Sağlığı Çalışanları için Kriter Katsayıları
ASC_KRITER_KATSAYILARI = {
    "vital_bulgular": {
        "asgari": 50,
        "azami": 90,
        "katsayilar": {
            "asgari_alti": 0.93,
            "asgari": 1.00,
            "azami": 1.06
        }
    },
    "yasli_degerlendirme": {
        "asgari": 50,
        "azami": 90,
        "katsayilar": {
            "asgari_alti": 0.97,
            "asgari": 1.00,
            "azami": 1.13
        }
    }
}

# Birim türüne göre nüfus limitleri ve katsayılar
BIRIM_AYARLARI = {
    "normal": {
        "azami_nufus": 4000,
        "birim_katsayisi": 1.00,
        "nobet_zorunlu": False
    },
    "entegre": {
        "azami_nufus": 2400,
        "birim_katsayisi": 1.65,
        "nobet_zorunlu": True,
        "nobet_saati": 96,  # aylık minimum
        "nobet_kesintisi": 0.08  # her tutulmayan 8 saat için %8 azalma
    },
    "zorunlu_dusuk_nufus": {
        "azami_nufus": 2400,
        "birim_katsayisi": 1.65,
        "nobet_zorunlu": True,
        "nobet_saati": 96,
        "nobet_kesintisi": 0.08
    },
    "tutuklu_hukumlu": {
        "azami_nufus": 2000,
        "tavan_katsayisi_1700_ustu": 1.176471,
        "tavan_katsayisi_1500_1700": 1.333334
    }
}


# =====================================================
# VERİ SINIFLARI
# =====================================================

@dataclass
class KriterVerisi:
    """Kriter verisi girişi"""
    tur: str
    gereken: int
    yapilan: int
    gecen_ay_devir: int = 0


@dataclass
class ASCKriterVerisi:
    """ASÇ kriter verisi"""
    tur: str
    gereken: int
    yapilan: int


@dataclass
class HYPGirdi:
    """HYP hesaplama girişi"""
    birim_id: str
    donem: str  # "YYYY-MM" formatında
    nufus: int
    birim_turu: str = "normal"
    maasa_esas_puan: Optional[int] = None
    birim_yasi_ay: Optional[int] = None
    alti_ayda_nufus: Optional[int] = None
    nobet_saati: Optional[int] = None
    sevk_sistemi_aktif: bool = False
    kriterler: List[KriterVerisi] = field(default_factory=list)


@dataclass
class ASCHYPGirdi:
    """ASÇ için HYP hesaplama girişi"""
    birim_id: str
    donem: str
    birim_tarama_takip_katsayisi: float
    kriterler: List[ASCKriterVerisi] = field(default_factory=list)


@dataclass
class KriterSonucu:
    """Kriter sonucu"""
    tur: str
    gereken: int
    yapilan: int
    gecen_ay_devir: int
    basari_yuzdesi: float
    devirli_basari_yuzdesi: float
    kriter_katsayisi: float
    kalan: int
    sonraki_aya_devir: int
    durum: str  # DurumRengi değeri
    aciklama: str


@dataclass
class HYPSonuc:
    """HYP hesaplama sonucu"""
    donem: str
    birim_id: str
    toplam_nufus: int
    birim_turu: str
    tavan_katsayisi: float
    kriterler_carpimi: float
    tarama_takip_katsayisi: float
    birim_katsayisi: float
    kriter_sonuclari: List[KriterSonucu] = field(default_factory=list)
    istisna_durumu: Optional[str] = None
    uyarilar: List[str] = field(default_factory=list)


@dataclass
class ASCHYPSonuc:
    """ASÇ HYP sonucu"""
    donem: str
    birim_id: str
    vital_bulgular_katsayisi: float
    yasli_degerlendirme_katsayisi: float
    asc_tarama_takip_katsayisi: float
    birim_katsayisi_kullanildi_mi: bool
    son_katsayi: float
    aciklama: str


@dataclass
class MaasHesaplamaSonucu:
    """Maaş hesaplama sonucu"""
    ara_puan: float
    maasa_esas_puan: float
    ilk_1000_puan_ucreti: float
    kalan_puan_ucreti: float
    toplam_brut_maas: float


# =====================================================
# HESAPLAMA FONKSİYONLARI
# =====================================================

def hesapla_basari_yuzdesi(yapilan: int, gereken: int) -> float:
    """Başarı yüzdesini hesaplar"""
    if gereken == 0:
        return 100.0
    return (yapilan / gereken) * 100


def hesapla_devirli_basari_yuzdesi(
    yapilan: int,
    gereken: int,
    devir: int
) -> Tuple[float, bool]:
    """
    Devirli başarı yüzdesini hesaplar
    DİKKAT: Devir kullanılabilmesi için o ay en az %10 işlem yapılmış olmalı

    Returns:
        (devirli_basari, devir_kullanildi_mi)
    """
    if gereken == 0:
        return (100.0, False)

    asgari_islem = gereken * 0.10

    if yapilan >= asgari_islem and devir > 0:
        return (((yapilan + devir) / gereken) * 100, True)

    return ((yapilan / gereken) * 100, False)


def hesapla_kriter_katsayisi(
    basari_orani: float,
    asgari_basari: int,
    azami_basari: int
) -> Tuple[float, str]:
    """
    EK-2'ye göre kriter katsayısını hesaplar
    Yönetmelik: "Başarı oranları ile doğru orantılı olarak asgari ve azami değerler
    arasında belirlenen kriter katsayılarının değerleri"

    Returns:
        (katsayi, durum_rengi)
    """
    # Başarı oranı %0 ise (hiç yapılmadı)
    if basari_orani == 0:
        return (KATSAYI_SINIRLAR["HIC_HYP_YAPILMADI"], DurumRengi.KIRMIZI.value)

    # Asgari başarı altında - ceza uygulanır
    if basari_orani < asgari_basari:
        # Lineer interpolasyon: 0% -> 0.90, asgari% -> 1.00
        katsayi = KATSAYI_SINIRLAR["ASGARI_ALTI_KATSAYI_MIN"] + \
            (basari_orani / asgari_basari) * \
            (1.0 - KATSAYI_SINIRLAR["ASGARI_ALTI_KATSAYI_MIN"])

        katsayi = max(KATSAYI_SINIRLAR["ASGARI_ALTI_KATSAYI_MIN"],
                      min(katsayi, 0.9999))
        return (katsayi, DurumRengi.KIRMIZI.value)

    # Asgari-azami arası - ideal aralık, katsayı 1.0
    if asgari_basari <= basari_orani <= azami_basari:
        return (1.0, DurumRengi.YESIL.value)

    # Azami üstü - %100'e kadar
    if basari_orani > azami_basari and basari_orani <= 100:
        return (1.0, DurumRengi.SARI.value)

    # %100 üstü - devir olacak
    return (1.0, DurumRengi.TURUNCU.value)


def hesapla_tavan_katsayisi(
    nufus: int,
    birim_turu: str,
    sevk_sistemi_aktif: bool = False
) -> float:
    """
    Tavan katsayısını hesaplar
    Yönetmelik Madde 7(5): "azami nüfusun aile hekimliği biriminin mevcut nüfusuna oranını geçemez"
    """
    ayarlar_key = birim_turu if birim_turu != "tutuklu_hukumlu" else "normal"
    ayarlar = BIRIM_AYARLARI.get(ayarlar_key, BIRIM_AYARLARI["normal"])
    azami_nufus = ayarlar.get("azami_nufus", 4000)

    # Tutuklu/hükümlü birimleri için özel limitler
    if birim_turu == "tutuklu_hukumlu":
        th_ayarlar = BIRIM_AYARLARI["tutuklu_hukumlu"]
        if nufus > 1700:
            return th_ayarlar["tavan_katsayisi_1700_ustu"]
        if nufus >= 1500:
            return th_ayarlar["tavan_katsayisi_1500_1700"]

    # Azami nüfus üstünde ise tavan = 1
    if nufus >= azami_nufus:
        return 1.0

    # Normal hesaplama
    maksimum = KATSAYI_SINIRLAR["MAKSIMUM_KATSAYI_SEVK"] if sevk_sistemi_aktif \
        else KATSAYI_SINIRLAR["MAKSIMUM_KATSAYI"]

    return min(azami_nufus / nufus, maksimum)


def hesapla_entegre_birim_katsayisi(nobet_saati: int) -> float:
    """Entegre birim katsayısını nöbet durumuna göre hesaplar"""
    ayarlar = BIRIM_AYARLARI["entegre"]
    taban_katsayi = ayarlar["birim_katsayisi"]

    if nobet_saati >= ayarlar["nobet_saati"]:
        return taban_katsayi

    # Her tutulmayan 8 saat için %8 kesinti
    tutulmayan_saat = ayarlar["nobet_saati"] - nobet_saati
    kesinti = (tutulmayan_saat // 8) * ayarlar["nobet_kesintisi"]

    return taban_katsayi * (1 - kesinti)


def hesapla_sonraki_aya_devir(
    yapilan: int,
    gereken: int,
    mevcut_devir: int,
    devir_kullanildi_mi: bool
) -> int:
    """Sonraki aya devredecek miktarı hesaplar"""
    basari_yuzdesi = hesapla_basari_yuzdesi(yapilan, gereken)

    # %100'ü aşan kısım devredilir (en fazla 2 ay)
    yeni_devir = 0
    if basari_yuzdesi > 100:
        yeni_devir = yapilan - gereken

    # Eğer devir kullanıldıysa, kullanılan miktarı düş
    if devir_kullanildi_mi and mevcut_devir > 0:
        # Mevcut devir zaten kullanıldı, yeni devir kaldı
        return yeni_devir

    return yeni_devir


def hesapla_hyp(girdi: HYPGirdi) -> HYPSonuc:
    """Ana HYP hesaplama fonksiyonu"""
    uyarilar: List[str] = []
    istisna_durumu: Optional[str] = None

    # Birim ayarlarını al
    ayarlar_key = girdi.birim_turu if girdi.birim_turu != "tutuklu_hukumlu" else "normal"
    birim_ayarlari = BIRIM_AYARLARI.get(ayarlar_key, BIRIM_AYARLARI["normal"])
    azami_nufus = birim_ayarlari.get("azami_nufus", 4000)

    # =====================================================
    # ÖZEL DURUM KONTROLLERİ
    # =====================================================

    # 1. Maaşa esas puan < 1000 ise katsayı = 1
    if girdi.maasa_esas_puan is not None and girdi.maasa_esas_puan < 1000:
        istisna_durumu = "Maaşa esas puan 1000'in altında, tarama takip katsayısı otomatik 1"
        return HYPSonuc(
            donem=girdi.donem,
            birim_id=girdi.birim_id,
            toplam_nufus=girdi.nufus,
            birim_turu=girdi.birim_turu,
            tavan_katsayisi=1.0,
            kriterler_carpimi=1.0,
            tarama_takip_katsayisi=1.0,
            birim_katsayisi=birim_ayarlari.get("birim_katsayisi", 1.0),
            kriter_sonuclari=[],
            istisna_durumu=istisna_durumu,
            uyarilar=uyarilar
        )

    # 2. Yeni açılan birimler (ilk 18 ay, 6. ayda 500 nüfusa ulaşılmışsa)
    if girdi.birim_yasi_ay is not None and girdi.birim_yasi_ay <= 18:
        if girdi.alti_ayda_nufus is not None and girdi.alti_ayda_nufus >= 500:
            istisna_durumu = "Yeni açılan birim (ilk 18 ay), ilk 2000 puan için katsayı 1"
            uyarilar.append("Yeni birim istisnası uygulandı")

    # =====================================================
    # KRİTER HESAPLAMALARI
    # =====================================================

    kriter_sonuclari: List[KriterSonucu] = []
    kriterler_carpimi = 1.0

    for kriter in girdi.kriterler:
        oranlar = KRITER_BASARI_ORANLARI.get(kriter.tur)

        if not oranlar:
            continue

        # Hedef nüfus sıfır kontrolü
        if kriter.gereken == 0:
            kriter_sonuclari.append(KriterSonucu(
                tur=kriter.tur,
                gereken=0,
                yapilan=kriter.yapilan,
                gecen_ay_devir=kriter.gecen_ay_devir,
                basari_yuzdesi=100,
                devirli_basari_yuzdesi=100,
                kriter_katsayisi=1.0,
                kalan=0,
                sonraki_aya_devir=0,
                durum=DurumRengi.YESIL.value,
                aciklama="Hedef nüfus sıfır, katsayı otomatik 1"
            ))
            continue

        # Başarı hesaplamaları
        basari_yuzdesi = hesapla_basari_yuzdesi(kriter.yapilan, kriter.gereken)
        devirli_basari, devir_kullanildi_mi = hesapla_devirli_basari_yuzdesi(
            kriter.yapilan,
            kriter.gereken,
            kriter.gecen_ay_devir
        )

        # Katsayı hesaplama
        # Yüksek nüfuslu birim istisnası
        if girdi.nufus > azami_nufus and devirli_basari >= oranlar["asgari"]:
            kriter_katsayisi = 1.0
            durum = DurumRengi.YESIL.value
        else:
            kriter_katsayisi, durum = hesapla_kriter_katsayisi(
                devirli_basari,
                oranlar["asgari"],
                oranlar["azami"]
            )

        # Kalan ve devir hesaplama
        kalan = max(0, kriter.gereken - kriter.yapilan)
        sonraki_aya_devir = hesapla_sonraki_aya_devir(
            kriter.yapilan,
            kriter.gereken,
            kriter.gecen_ay_devir,
            devir_kullanildi_mi
        )

        # Açıklama oluştur
        aciklama = ""
        if durum == DurumRengi.KIRMIZI.value:
            aciklama = f"Asgari başarı (%{oranlar['asgari']}) altında"
        elif durum == DurumRengi.YESIL.value:
            aciklama = "İdeal aralıkta"
        elif durum == DurumRengi.SARI.value:
            aciklama = "Azami başarı üstünde (devir kaybı olabilir)"
        elif durum == DurumRengi.TURUNCU.value:
            aciklama = "%100 üstünde, sonraki aya devredecek"

        kriter_sonuclari.append(KriterSonucu(
            tur=kriter.tur,
            gereken=kriter.gereken,
            yapilan=kriter.yapilan,
            gecen_ay_devir=kriter.gecen_ay_devir,
            basari_yuzdesi=round(basari_yuzdesi, 2),
            devirli_basari_yuzdesi=round(devirli_basari, 2),
            kriter_katsayisi=round(kriter_katsayisi, 4),
            kalan=kalan,
            sonraki_aya_devir=sonraki_aya_devir,
            durum=durum,
            aciklama=aciklama
        ))

        kriterler_carpimi *= kriter_katsayisi

    # =====================================================
    # FİNAL HESAPLAMALAR
    # =====================================================

    # Tavan katsayısı
    tavan_katsayisi = hesapla_tavan_katsayisi(
        girdi.nufus,
        girdi.birim_turu,
        girdi.sevk_sistemi_aktif
    )

    # Birim katsayısı (entegre için nöbet durumuna göre)
    birim_katsayisi = 1.0
    if girdi.birim_turu in ("entegre", "zorunlu_dusuk_nufus"):
        birim_katsayisi = hesapla_entegre_birim_katsayisi(girdi.nobet_saati or 0)

    # Tarama ve takip katsayısı (tavan ile sınırla)
    tarama_takip_katsayisi = min(
        max(kriterler_carpimi, KATSAYI_SINIRLAR["MINIMUM_KATSAYI"]),
        tavan_katsayisi
    )

    return HYPSonuc(
        donem=girdi.donem,
        birim_id=girdi.birim_id,
        toplam_nufus=girdi.nufus,
        birim_turu=girdi.birim_turu,
        tavan_katsayisi=round(tavan_katsayisi, 4),
        kriterler_carpimi=round(kriterler_carpimi, 4),
        tarama_takip_katsayisi=round(tarama_takip_katsayisi, 4),
        birim_katsayisi=round(birim_katsayisi, 4),
        kriter_sonuclari=kriter_sonuclari,
        istisna_durumu=istisna_durumu,
        uyarilar=uyarilar
    )


def hesapla_asc_hyp(girdi: ASCHYPGirdi) -> ASCHYPSonuc:
    """
    Aile Sağlığı Çalışanı için HYP hesaplama
    Kaynak: HYP Tarama ve Takip Kılavuzu, Yönerge Madde 7
    """
    vital_katsayi = 1.0
    yasli_katsayi = 1.0

    for kriter in girdi.kriterler:
        ayarlar = ASC_KRITER_KATSAYILARI.get(kriter.tur)
        if not ayarlar:
            continue

        basari = hesapla_basari_yuzdesi(kriter.yapilan, kriter.gereken)

        if basari < ayarlar["asgari"]:
            katsayi = ayarlar["katsayilar"]["asgari_alti"]
        elif basari >= ayarlar["azami"]:
            katsayi = ayarlar["katsayilar"]["azami"]
        else:
            # Lineer interpolasyon asgari ile azami arasında
            oran = (basari - ayarlar["asgari"]) / (ayarlar["azami"] - ayarlar["asgari"])
            katsayi = ayarlar["katsayilar"]["asgari"] + \
                oran * (ayarlar["katsayilar"]["azami"] - ayarlar["katsayilar"]["asgari"])

        if kriter.tur == "vital_bulgular":
            vital_katsayi = katsayi
        else:
            yasli_katsayi = katsayi

    # ASÇ tarama takip katsayısı = vital × yaşlı
    asc_katsayisi = vital_katsayi * yasli_katsayi

    # Birim katsayısından faydalanma kuralları
    birim_katsayisi = girdi.birim_tarama_takip_katsayisi
    birim_katsayisi_yuzde75 = birim_katsayisi * 0.75

    birim_katsayisi_kullanildi_mi = False

    if asc_katsayisi < 1.0:
        # ASÇ katsayısı 1'in altında ise kendi katsayısı kullanılır
        son_katsayi = asc_katsayisi
        aciklama = "ASÇ katsayısı 1'in altında, kendi katsayısı uygulandı"
    elif asc_katsayisi >= 1.0 and asc_katsayisi < birim_katsayisi_yuzde75:
        # 1 ve üstü ama birim katsayısının %75'inin altında
        son_katsayi = asc_katsayisi
        aciklama = f"ASÇ katsayısı birim katsayısının %75'inin ({birim_katsayisi_yuzde75:.4f}) altında, kendi katsayısı uygulandı"
    else:
        # Birim veya ASÇ katsayısından yüksek olanı
        if asc_katsayisi >= birim_katsayisi:
            son_katsayi = asc_katsayisi
            aciklama = "ASÇ katsayısı birim katsayısından yüksek, ASÇ katsayısı uygulandı"
        else:
            son_katsayi = birim_katsayisi
            birim_katsayisi_kullanildi_mi = True
            aciklama = "Birim katsayısı daha yüksek, birim katsayısı uygulandı"

    return ASCHYPSonuc(
        donem=girdi.donem,
        birim_id=girdi.birim_id,
        vital_bulgular_katsayisi=round(vital_katsayi, 4),
        yasli_degerlendirme_katsayisi=round(yasli_katsayi, 4),
        asc_tarama_takip_katsayisi=round(asc_katsayisi, 4),
        birim_katsayisi_kullanildi_mi=birim_katsayisi_kullanildi_mi,
        son_katsayi=round(son_katsayi, 4),
        aciklama=aciklama
    )


# =====================================================
# MAAŞ HESAPLAMA FONKSİYONLARI
# =====================================================

def hesapla_maas(
    ara_puan: float,
    tarama_takip_katsayisi: float,
    tavan_ucret: float,
    aile_hekimligi_uzmani_mi: bool = False
) -> MaasHesaplamaSonucu:
    """
    Maaşa esas puanı hesaplar
    Yönetmelik Madde 18(2)(a)(6): ara puan × tarama takip katsayısı
    """
    # Maaşa esas puan = Ara puan × Tarama Takip Katsayısı
    maasa_esas_puan = ara_puan * tarama_takip_katsayisi

    # İlk 1000 puan için sabit ücret oranları
    if aile_hekimligi_uzmani_mi:
        ilk_1000_oran = 1.135  # %113.5
    else:
        ilk_1000_oran = 0.785  # %78.5 (uzman veya tabip)

    ilk_1000_puan_ucreti = tavan_ucret * ilk_1000_oran

    # 1000 üstü puanlar için
    kalan_puan = max(0, maasa_esas_puan - 1000)
    puan_basi_oran = 0.000522  # Tavan ücretin onbinde 5.22'si
    kalan_puan_ucreti = kalan_puan * tavan_ucret * puan_basi_oran

    return MaasHesaplamaSonucu(
        ara_puan=round(ara_puan, 2),
        maasa_esas_puan=round(maasa_esas_puan, 2),
        ilk_1000_puan_ucreti=round(ilk_1000_puan_ucreti, 2),
        kalan_puan_ucreti=round(kalan_puan_ucreti, 2),
        toplam_brut_maas=round(ilk_1000_puan_ucreti + kalan_puan_ucreti, 2)
    )


# =====================================================
# YARDIMCI FONKSİYONLAR
# =====================================================

def get_durum_aciklamasi(durum: str) -> str:
    """Durum rengine göre açıklama döndürür"""
    aciklamalar = {
        DurumRengi.KIRMIZI.value: "Asgari Başarı Yüzdesine ulaşılamadı - Katsayı düşük, tamamlayınız!",
        DurumRengi.YESIL.value: "İdeal aralıkta",
        DurumRengi.SARI.value: "Azami Başarı Yüzdesi Geçildi! (Devrederken %10 kaybınız olur)",
        DurumRengi.TURUNCU.value: "%100 değeri geçildi! Gelecek aya devir olacak!"
    }
    return aciklamalar.get(durum, "")


def hesapla_kalanlar(gereken: int, yapilan: int) -> Dict[str, int]:
    """Kalan hesabı için gereken başarı yüzdelerini döndürür (KHT %40, %70, %90)"""
    return {
        "kalan_yuzde_40": max(0, int(gereken * 0.40 + 0.5) - yapilan),
        "kalan_yuzde_70": max(0, int(gereken * 0.70 + 0.5) - yapilan),
        "kalan_yuzde_90": max(0, int(gereken * 0.90 + 0.5) - yapilan)
    }


def get_kriter_ismi(tur: str) -> str:
    """Kriter ismini Türkçe döndürür"""
    isimler = {
        "ht_tarama": "HT Tarama",
        "ht_izlem": "HT İzlem",
        "ht_sonuc": "HT Sonuç",
        "dm_tarama": "DM Tarama",
        "dm_izlem": "DM İzlem",
        "dm_sonuc": "DM Sonuç",
        "obezite_tarama": "Obezite Tarama",
        "obezite_izlem": "Obezite İzlem",
        "obezite_sonuc": "Obezite Sonuç",
        "kvr_tarama": "KVR Tarama",
        "kvr_izlem": "KVR İzlem",
        "kvr_sonuc": "KVR Sonuç",
        "yasli_tarama": "Yaşlı Tarama",
        "yasli_izlem": "Yaşlı İzlem",
        "yasli_sonuc": "Yaşlı Sonuç",
        "serviks_tarama": "Serviks",
        "kolorektal_tarama": "Kolorektal",
        "meme_tarama": "Mamografi",
        "surec_yonetimi": "Süreç Yönetimi"
    }
    return isimler.get(tur, tur)


def get_durum_renk_kodu(durum: str) -> str:
    """Durum için HTML renk kodu döndürür"""
    renk_kodlari = {
        DurumRengi.KIRMIZI.value: "#e74c3c",
        DurumRengi.YESIL.value: "#2ecc71",
        DurumRengi.SARI.value: "#f1c40f",
        DurumRengi.TURUNCU.value: "#e67e22"
    }
    return renk_kodlari.get(durum, "#95a5a6")


# =====================================================
# ÖRNEK KULLANIM
# =====================================================

if __name__ == "__main__":
    # Örnek: Aile Hekimi HYP Hesaplama
    ornek_kriterler = [
        KriterVerisi(tur="dm_tarama", gereken=100, yapilan=85, gecen_ay_devir=10),
        KriterVerisi(tur="dm_izlem", gereken=50, yapilan=45, gecen_ay_devir=0),
        KriterVerisi(tur="ht_tarama", gereken=120, yapilan=110, gecen_ay_devir=5),
        KriterVerisi(tur="ht_izlem", gereken=60, yapilan=55, gecen_ay_devir=0),
    ]

    ornek_girdi = HYPGirdi(
        birim_id="ASM-001-01",
        donem="2025-12",
        nufus=3500,
        birim_turu="normal",
        sevk_sistemi_aktif=False,
        kriterler=ornek_kriterler
    )

    sonuc = hesapla_hyp(ornek_girdi)

    print("=" * 50)
    print("HYP HESAPLAMA SONUCU")
    print("=" * 50)
    print(f"Birim: {sonuc.birim_id}")
    print(f"Dönem: {sonuc.donem}")
    print(f"Nüfus: {sonuc.toplam_nufus}")
    print(f"Tavan Katsayısı: {sonuc.tavan_katsayisi}")
    print(f"Kriterler Çarpımı: {sonuc.kriterler_carpimi}")
    print(f"Tarama Takip Katsayısı: {sonuc.tarama_takip_katsayisi}")
    print()

    print("KRİTER DETAYLARI:")
    print("-" * 50)
    for ks in sonuc.kriter_sonuclari:
        print(f"  {get_kriter_ismi(ks.tur)}:")
        print(f"    Gereken: {ks.gereken}, Yapılan: {ks.yapilan}")
        print(f"    Başarı: %{ks.basari_yuzdesi:.1f}")
        print(f"    Katsayı: {ks.kriter_katsayisi}")
        print(f"    Durum: {ks.durum} - {ks.aciklama}")
        print()

    # Örnek: Maaş hesaplama
    print("=" * 50)
    print("MAAŞ HESAPLAMA")
    print("=" * 50)
    maas = hesapla_maas(
        ara_puan=3200,
        tarama_takip_katsayisi=sonuc.tarama_takip_katsayisi,
        tavan_ucret=50000,
        aile_hekimligi_uzmani_mi=True
    )
    print(f"Ara Puan: {maas.ara_puan}")
    print(f"Maaşa Esas Puan: {maas.maasa_esas_puan}")
    print(f"İlk 1000 Puan Ücreti: {maas.ilk_1000_puan_ucreti:,.2f} TL")
    print(f"Kalan Puan Ücreti: {maas.kalan_puan_ucreti:,.2f} TL")
    print(f"Toplam Brüt Maaş: {maas.toplam_brut_maas:,.2f} TL")

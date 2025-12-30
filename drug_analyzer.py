# -*- coding: utf-8 -*-
"""
ILAC ANALIZ MODULU
==================
Polifarmasi tespiti ve yasli izlem icin akilli ilac analizi.

ATC Kodlari Rehberi:
- A: Sindirim sistemi ve metabolizma (A10: Diyabet ilaclari)
- B: Kan ve kan yapici organlar (B01: Antitrombotikler)
- C: Kardiyovaskuler sistem (Kalp-damar ilaclari)
- D: Dermatolojikler (Cilt ilaclari - genelde kronik degil)
- G: Genitoüriner sistem (Uroloji ilaclari)
- H: Sistemik hormonal preparatlar (H02: Kortikosteroidler)
- J: Enfeksiyon (Antibiyotikler - kisa sureli)
- L: Antineoplastik ve immunmodulatör ajanlar
- M: Kas-iskelet sistemi (M01: Antiinflamatuar - genelde kisa)
- N: Sinir sistemi (N05: Psikotrop, N06: Antidepresan)
- P: Antiparaziter urunler
- R: Solunum sistemi (R03: Astim/KOAH)
- S: Duyu organlari (Goz/kulak damlasi)
- V: Cesitli
"""

import os
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

# Excel icin opsiyonel import
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class DrugAnalyzer:
    """Ilac analizi ve polifarmasi tespiti"""

    # KRONIK ILAC ATC KODLARI (ilk karakterler veya tam kodlar)
    CHRONIC_ATC_PREFIXES = {
        # Kardiyovaskuler (C) - HEPSI KRONIK
        'C01': 'Kardiyak glikozidler',
        'C02': 'Antihipertansifler',
        'C03': 'Diuretikler',
        'C07': 'Beta blokerler',
        'C08': 'Kalsiyum kanal blokerleri',
        'C09': 'RAA sistemi ilaclari (ACE/ARB)',
        'C10': 'Lipid duzenleyiciler (Statinler)',

        # Diyabet (A10) - HEPSI KRONIK
        'A10A': 'Insulinler',
        'A10B': 'Oral antidiyabetikler',

        # Sinir sistemi (N) - COGU KRONIK
        'N02A': 'Opioidler (kronik agri)',
        'N03': 'Antiepileptikler',
        'N04': 'Antiparkinson',
        'N05A': 'Antipsikotikler',
        'N05B': 'Anksiyolitikler',
        'N05C': 'Hipnotik/Sedatifler',
        'N06A': 'Antidepresanlar',
        'N06D': 'Demans ilaclari',

        # Solunum (R03) - KRONIK
        'R03': 'Astim/KOAH ilaclari',

        # Endokrin (H) - COGU KRONIK
        'H01': 'Hipofiz hormonlari',
        'H02': 'Sistemik kortikosteroidler',
        'H03': 'Tiroid ilaclari',

        # Kan (B01) - KRONIK
        'B01A': 'Antitrombotikler (Aspirin, Warfarin)',
        'B03': 'Antianemikler',

        # Genitoüriner (G04) - COGU KRONIK
        'G04B': 'Urolojikler',
        'G04C': 'BPH ilaclari',

        # Immun sistem (L04)
        'L04': 'Immunsupresanlar',

        # Kemik (M05)
        'M05B': 'Osteoporoz ilaclari',

        # Goz (S01E) - Glokom kronik
        'S01E': 'Glokom ilaclari',
    }

    # KISA SURELI ILAC ATC KODLARI (polifarmasiden haric tutulacak)
    SHORT_TERM_ATC_PREFIXES = {
        'J01': 'Antibiyotikler',
        'J02': 'Antifungaller (sistemik)',
        'J05': 'Antiviraller',
        'D01': 'Topikal antifungaller',
        'D06': 'Topikal antibiyotikler',
        'D07': 'Topikal kortikosteroidler',
        'M01A': 'NSAID (agri kesici)',
        'M02': 'Topikal agri kesiciler',
        'N02B': 'Analjezikler (Parasetamol vb)',
        'R05': 'Oksuruk/soguk alginligi',
        'A02': 'Antasitler (kisa sureli)',
        'A03': 'GI spazmolitikler',
        'A07': 'Antidiyareikler',
    }

    # YASLI ICIN POTANSIYEL UYGUNSUZ ILACLAR (Beers Kriterleri bazli)
    POTENTIALLY_INAPPROPRIATE_DRUGS = {
        # Antikolinerjikler
        'N05BB01': 'Difenhidramin - Yaslida kacinilmali',
        'R06AA02': 'Difenhidramin - Antikolinerjik etki',
        'A03B': 'Belladonna alkaloidleri - Antikolinerjik',

        # Uzun etkili benzodiazepinler
        'N05BA01': 'Diazepam - Uzun etkili, dusme riski',
        'N05BA05': 'Klordiazepoksit - Uzun etkili',
        'N05CD02': 'Nitrazepam - Uzun etkili',

        # Birinci kuşak antihistaminikler
        'R06AA': 'Birinci kusak antihistaminikler',
        'R06AB': 'Birinci kusak antihistaminikler',

        # GI antispazmotikler
        'A03BA': 'Atropin turevleri',
        'A03BB': 'Skopolamin turevleri',

        # NSAIDler (uzun sureli)
        'M01AB05': 'Diklofenak - GI kanama riski',
        'M01AE01': 'Ibuprofen - uzun sureli kullanımda risk',
        'M01AC01': 'Piroksikam - Uzun yari omur',

        # Kas gevsetici
        'M03BX': 'Merkezi etkili kas gevseticiler',

        # Digoksin yuksek doz
        'C01AA05': 'Digoksin - Doz kontrolu gerekli',

        # Alfa blokerler (hipertansiyon icin)
        'C02CA': 'Alfa blokerler - Ortostatik hipotansiyon',

        # Sliding scale insulin
        'A10AB': 'Kisa etkili insulin - Sliding scale riskli',
    }

    def __init__(self, excel_path: str = None):
        """
        Args:
            excel_path: Ilac listesi Excel dosyasi yolu
        """
        self.excel_path = excel_path
        self.drug_database = {}

        if excel_path and os.path.exists(excel_path):
            self._load_drug_database()

    def _load_drug_database(self):
        """Excel'den ilac veritabanini yukle"""
        if not PANDAS_AVAILABLE:
            print("[!] Pandas yuklu degil, Excel okunamiyor")
            return

        try:
            df = pd.read_excel(self.excel_path, header=1)
            # Sutun isimlerini duzelt
            df.columns = ['ilac_adi', 'barkod', 'atc_kodu', 'atc_adi', 'firma',
                         'recete_turu', 'durum', 'aciklama', 'temel_ilac',
                         'cocuk_temel', 'yenidogan_temel', 'aktif_tarih']

            # Veritabanini olustur (ilac adi -> bilgiler)
            for _, row in df.iterrows():
                ilac_adi = str(row['ilac_adi']).upper().strip()
                if ilac_adi and ilac_adi != 'NAN':
                    self.drug_database[ilac_adi] = {
                        'atc_kodu': str(row['atc_kodu']).strip() if pd.notna(row['atc_kodu']) else '',
                        'atc_adi': str(row['atc_adi']).strip() if pd.notna(row['atc_adi']) else '',
                        'barkod': str(row['barkod']).strip() if pd.notna(row['barkod']) else '',
                    }

            print(f"[OK] {len(self.drug_database)} ilac yuklendi")
        except Exception as e:
            print(f"[!] Excel okuma hatasi: {e}")

    def get_atc_code(self, drug_name: str) -> str:
        """Ilac adindan ATC kodunu bul"""
        drug_name_upper = drug_name.upper().strip()

        # Tam esleme
        if drug_name_upper in self.drug_database:
            return self.drug_database[drug_name_upper].get('atc_kodu', '')

        # Kismi esleme (ilac adi baslangici)
        for db_name, info in self.drug_database.items():
            if db_name.startswith(drug_name_upper.split()[0]):
                return info.get('atc_kodu', '')

        return ''

    def is_chronic_drug(self, atc_code: str) -> Tuple[bool, str]:
        """
        ATC koduna gore ilacin kronik olup olmadigini belirle.

        Returns:
            (is_chronic, category_name)
        """
        if not atc_code:
            return False, ''

        atc_code = atc_code.upper().strip()

        # Kronik ilac kontrolu
        for prefix, category in self.CHRONIC_ATC_PREFIXES.items():
            if atc_code.startswith(prefix):
                return True, category

        return False, ''

    def is_short_term_drug(self, atc_code: str) -> Tuple[bool, str]:
        """
        ATC koduna gore ilacin kisa sureli olup olmadigini belirle.

        Returns:
            (is_short_term, category_name)
        """
        if not atc_code:
            return False, ''

        atc_code = atc_code.upper().strip()

        for prefix, category in self.SHORT_TERM_ATC_PREFIXES.items():
            if atc_code.startswith(prefix):
                return True, category

        return False, ''

    def is_potentially_inappropriate(self, atc_code: str) -> Tuple[bool, str]:
        """
        Yaslilarda potansiyel uygunsuz ilac kontrolu (Beers kriterleri).

        Returns:
            (is_inappropriate, warning_message)
        """
        if not atc_code:
            return False, ''

        atc_code = atc_code.upper().strip()

        for prefix, warning in self.POTENTIALLY_INAPPROPRIATE_DRUGS.items():
            if atc_code.startswith(prefix):
                return True, warning

        return False, ''

    def analyze_drug_list(self, drugs: List[Dict]) -> Dict:
        """
        Hasta ilac listesini analiz et.

        Args:
            drugs: [{'name': 'Ilac Adi', 'atc': 'ATC kodu (opsiyonel)',
                    'start_date': 'baslangic tarihi', 'dose': 'doz'}]

        Returns:
            {
                'chronic_count': int,
                'chronic_drugs': [...],
                'short_term_drugs': [...],
                'inappropriate_drugs': [...],
                'polypharmacy': bool,
                'polypharmacy_level': str,
                'recommendations': [...]
            }
        """
        result = {
            'chronic_count': 0,
            'chronic_drugs': [],
            'short_term_drugs': [],
            'inappropriate_drugs': [],
            'polypharmacy': False,
            'polypharmacy_level': 'YOK',
            'recommendations': []
        }

        for drug in drugs:
            drug_name = drug.get('name', '')
            atc_code = drug.get('atc', '') or self.get_atc_code(drug_name)

            # Kronik ilac mi?
            is_chronic, chronic_category = self.is_chronic_drug(atc_code)

            if is_chronic:
                result['chronic_count'] += 1
                result['chronic_drugs'].append({
                    'name': drug_name,
                    'atc': atc_code,
                    'category': chronic_category
                })
            else:
                # Kisa sureli mi?
                is_short, short_category = self.is_short_term_drug(atc_code)
                if is_short:
                    result['short_term_drugs'].append({
                        'name': drug_name,
                        'atc': atc_code,
                        'category': short_category
                    })

            # Yasli icin uygunsuz mu?
            is_inappropriate, warning = self.is_potentially_inappropriate(atc_code)
            if is_inappropriate:
                result['inappropriate_drugs'].append({
                    'name': drug_name,
                    'atc': atc_code,
                    'warning': warning
                })

        # Polifarmasi degerlendirmesi
        chronic_count = result['chronic_count']

        if chronic_count >= 10:
            result['polypharmacy'] = True
            result['polypharmacy_level'] = 'ASIRI'
            result['recommendations'].append('Asiri polifarmasi (10+ ilac) - Acil ilac gozden gecirmesi gerekli')
        elif chronic_count >= 5:
            result['polypharmacy'] = True
            result['polypharmacy_level'] = 'MEVCUT'
            result['recommendations'].append('Polifarmasi (5+ kronik ilac) - Ilac etkilesimlerini degerlendirin')
        elif chronic_count >= 3:
            result['polypharmacy_level'] = 'RISK'
            result['recommendations'].append('Polifarmasi riski (3-4 kronik ilac) - Takip edin')

        # Uygunsuz ilac uyarilari
        if result['inappropriate_drugs']:
            result['recommendations'].append(
                f"{len(result['inappropriate_drugs'])} potansiyel uygunsuz ilac tespit edildi"
            )

        return result

    def calculate_polypharmacy_answer(self, drugs: List[Dict]) -> str:
        """
        HYP Yasli Izlem icin polifarmasi sorusunun cevabini hesapla.

        Args:
            drugs: Hasta ilac listesi

        Returns:
            'EVET' veya 'HAYIR'
        """
        analysis = self.analyze_drug_list(drugs)
        return 'EVET' if analysis['polypharmacy'] else 'HAYIR'

    def calculate_inappropriate_drug_answer(self, drugs: List[Dict]) -> Tuple[str, List[str]]:
        """
        HYP Yasli Izlem icin uygunsuz ilac sorusunun cevabini hesapla.

        Returns:
            ('EVET'/'HAYIR', [uyari listesi])
        """
        analysis = self.analyze_drug_list(drugs)

        if analysis['inappropriate_drugs']:
            warnings = [d['warning'] for d in analysis['inappropriate_drugs']]
            return 'EVET', warnings

        return 'HAYIR', []


class ElderlyAssessmentHelper:
    """Yasli Izlem icin otomatik degerlendirme yardimcisi"""

    # Geriatrik degerlendirme sorulari ve varsayilan cevaplar
    GERIATRIC_QUESTIONS = {
        # Fonksiyonel Durum (Katz ADL bazli)
        'banyo': {'default': 'HAYIR', 'description': 'Banyoda yardima ihtiyac duyuyor mu?'},
        'giyinme': {'default': 'HAYIR', 'description': 'Giyinmede yardima ihtiyac duyuyor mu?'},
        'tuvalet': {'default': 'HAYIR', 'description': 'Tuvalette yardima ihtiyac duyuyor mu?'},
        'transfer': {'default': 'HAYIR', 'description': 'Yatak/sandalyeden kalkmada yardima ihtiyac duyuyor mu?'},
        'kontinans': {'default': 'HAYIR', 'description': 'Idrar/gaita inkontinansi var mi?'},
        'beslenme': {'default': 'HAYIR', 'description': 'Beslenmede yardima ihtiyac duyuyor mu?'},

        # SARC-F (Sarkopeni taramasi)
        'guc': {'default': 'HAYIR', 'description': '4.5 kg agirlik kaldirmada zorluk?'},
        'yurume': {'default': 'HAYIR', 'description': 'Oda icinde yurumede zorluk?'},
        'sandalye': {'default': 'HAYIR', 'description': 'Sandalyeden kalkmada zorluk?'},
        'merdiven': {'default': 'HAYIR', 'description': '10 basamak merdivenr cikmada zorluk?'},
        'dusme': {'default': 'HAYIR', 'description': 'Son 1 yilda dusme?'},

        # Kognitif durum
        'bellek': {'default': 'HAYIR', 'description': 'Bellek problemi var mi?'},
        'oryantasyon': {'default': 'HAYIR', 'description': 'Yer/zaman oryantasyon bozuklugu?'},

        # Duygudurum
        'depresyon': {'default': 'HAYIR', 'description': 'Depresyon belirtileri?'},
        'anksiyete': {'default': 'HAYIR', 'description': 'Anksiyete belirtileri?'},

        # Beslenme
        'kilo_kaybi': {'default': 'HAYIR', 'description': 'Son 3 ayda istemsiz kilo kaybi?'},
        'istahsizlik': {'default': 'HAYIR', 'description': 'Istahsizlik var mi?'},

        # Duyu
        'gorme': {'default': 'HAYIR', 'description': 'Gorme problemi var mi?'},
        'isitme': {'default': 'HAYIR', 'description': 'Isitme problemi var mi?'},
    }

    def __init__(self):
        self.patient_data = {}

    def set_patient_data(self, data: Dict):
        """
        Hasta verilerini ayarla.

        Args:
            data: {
                'age': int,
                'drugs': [...],
                'katz_score': int (0-6),
                'sarc_f_score': int (0-10),
                'mmse_score': int (0-30),
                'gds_score': int (0-15),
                'mna_score': float,
                'recent_falls': int,
                'hospitalizations': int,
                ...
            }
        """
        self.patient_data = data

    def calculate_katz_score(self, answers: Dict[str, str]) -> int:
        """
        Katz ADL skorunu hesapla.

        Args:
            answers: {'banyo': 'EVET/HAYIR', 'giyinme': 'EVET/HAYIR', ...}

        Returns:
            0-6 arasi skor (6 = bagimsiz)
        """
        adl_items = ['banyo', 'giyinme', 'tuvalet', 'transfer', 'kontinans', 'beslenme']
        score = 0

        for item in adl_items:
            # HAYIR = bagimsiz = 1 puan
            if answers.get(item, 'HAYIR').upper() == 'HAYIR':
                score += 1

        return score

    def calculate_sarc_f_score(self, answers: Dict[str, str]) -> int:
        """
        SARC-F skorunu hesapla (sarkopeni taramasi).

        Args:
            answers: {'guc': 'EVET/HAYIR', 'yurume': 'EVET/HAYIR', ...}

        Returns:
            0-10 arasi skor (4+ = sarkopeni riski)
        """
        sarc_items = ['guc', 'yurume', 'sandalye', 'merdiven', 'dusme']
        score = 0

        for item in sarc_items:
            # EVET = sorun var = 2 puan
            if answers.get(item, 'HAYIR').upper() == 'EVET':
                score += 2

        return score

    def get_smart_answers(self) -> Dict[str, str]:
        """
        Hasta verilerine gore akilli cevaplar uret.

        Returns:
            {soru_adi: 'EVET'/'HAYIR'}
        """
        answers = {}
        data = self.patient_data

        # Katz skoru varsa
        katz = data.get('katz_score')
        if katz is not None:
            if katz <= 2:  # Ciddi bagimlilik
                for item in ['banyo', 'giyinme', 'tuvalet', 'transfer', 'beslenme']:
                    answers[item] = 'EVET'
            elif katz <= 4:  # Orta bagimlilik
                answers['banyo'] = 'EVET'
                answers['giyinme'] = 'EVET'

        # SARC-F skoru varsa
        sarc_f = data.get('sarc_f_score')
        if sarc_f is not None and sarc_f >= 4:
            answers['guc'] = 'EVET'
            answers['sandalye'] = 'EVET'

        # MMSE skoru varsa (kognitif)
        mmse = data.get('mmse_score')
        if mmse is not None:
            if mmse < 24:  # Kognitif bozukluk
                answers['bellek'] = 'EVET'
            if mmse < 18:  # Ciddi
                answers['oryantasyon'] = 'EVET'

        # GDS skoru varsa (depresyon)
        gds = data.get('gds_score')
        if gds is not None and gds >= 5:
            answers['depresyon'] = 'EVET'

        # Son dusme
        if data.get('recent_falls', 0) > 0:
            answers['dusme'] = 'EVET'

        # Kilo kaybi
        if data.get('weight_loss_3m', 0) > 3:  # 3 kg'dan fazla
            answers['kilo_kaybi'] = 'EVET'

        # MNA skoru (beslenme)
        mna = data.get('mna_score')
        if mna is not None and mna < 17:
            answers['istahsizlik'] = 'EVET'
            answers['kilo_kaybi'] = 'EVET'

        # Varsayilanlari ekle
        for question, config in self.GERIATRIC_QUESTIONS.items():
            if question not in answers:
                answers[question] = config['default']

        return answers

    def calculate_frailty_index(self) -> Tuple[int, str]:
        """
        Kirilganlik indeksini hesapla (1-9).

        Returns:
            (skor, aciklama)
        """
        data = self.patient_data
        score = 3  # Varsayilan orta

        # Yas etkisi
        age = data.get('age', 65)
        if age >= 85:
            score += 2
        elif age >= 75:
            score += 1

        # Katz ADL
        katz = data.get('katz_score', 6)
        if katz <= 2:
            score += 3
        elif katz <= 4:
            score += 2
        elif katz <= 5:
            score += 1

        # Polifarmasi
        drug_count = len(data.get('drugs', []))
        if drug_count >= 10:
            score += 2
        elif drug_count >= 5:
            score += 1

        # Hospitalizasyon
        if data.get('hospitalizations', 0) >= 2:
            score += 1

        # Dusme
        if data.get('recent_falls', 0) >= 2:
            score += 1

        # Sinirla 1-9
        score = max(1, min(9, score))

        # Aciklama
        if score <= 3:
            desc = 'Dusuk kirilganlik'
        elif score <= 5:
            desc = 'Orta kirilganlik'
        elif score <= 7:
            desc = 'Yuksek kirilganlik'
        else:
            desc = 'Cok yuksek kirilganlik'

        return score, desc

    def get_follow_up_interval(self) -> str:
        """
        Onerilen izlem araligini hesapla.

        Returns:
            '3 Ay', '6 Ay', veya '1 Yil'
        """
        frailty_score, _ = self.calculate_frailty_index()

        if frailty_score >= 7:
            return '3 Ay'
        elif frailty_score >= 4:
            return '6 Ay'
        else:
            return '1 Yil'


# Test fonksiyonu
def test_drug_analyzer():
    """Modulu test et"""
    print("=" * 60)
    print("ILAC ANALIZ MODULU TESTI")
    print("=" * 60)

    # Excel dosyasi varsa yukle
    excel_path = os.path.join(os.path.dirname(__file__), 'İlaç Listesi.xlsx')
    analyzer = DrugAnalyzer(excel_path if os.path.exists(excel_path) else None)

    # Ornek hasta ilac listesi
    test_drugs = [
        {'name': 'Metformin 1000mg', 'atc': 'A10BA02'},
        {'name': 'Ramipril 5mg', 'atc': 'C09AA05'},
        {'name': 'Atorvastatin 20mg', 'atc': 'C10AA05'},
        {'name': 'Aspirin 100mg', 'atc': 'B01AC06'},
        {'name': 'Metoprolol 50mg', 'atc': 'C07AB02'},
        {'name': 'Omeprazol 20mg', 'atc': 'A02BC01'},  # Kisa sureli
        {'name': 'Amoksisilin 1000mg', 'atc': 'J01CA04'},  # Antibiyotik
        {'name': 'Diazepam 5mg', 'atc': 'N05BA01'},  # Uygunsuz
    ]

    print("\n[1] Ilac Analizi:")
    result = analyzer.analyze_drug_list(test_drugs)

    print(f"\n    Kronik ilac sayisi: {result['chronic_count']}")
    print(f"    Polifarmasi: {result['polypharmacy_level']}")

    print("\n    Kronik ilaclar:")
    for drug in result['chronic_drugs']:
        print(f"      - {drug['name']} ({drug['category']})")

    print("\n    Kisa sureli ilaclar:")
    for drug in result['short_term_drugs']:
        print(f"      - {drug['name']} ({drug['category']})")

    if result['inappropriate_drugs']:
        print("\n    [!] Potansiyel uygunsuz ilaclar:")
        for drug in result['inappropriate_drugs']:
            print(f"      - {drug['name']}: {drug['warning']}")

    print("\n    Oneriler:")
    for rec in result['recommendations']:
        print(f"      - {rec}")

    # Yasli degerlendirme testi
    print("\n" + "=" * 60)
    print("[2] Yasli Izlem Degerlendirmesi:")
    print("=" * 60)

    helper = ElderlyAssessmentHelper()
    helper.set_patient_data({
        'age': 78,
        'drugs': test_drugs,
        'katz_score': 4,
        'sarc_f_score': 6,
        'mmse_score': 22,
        'gds_score': 7,
        'recent_falls': 1,
    })

    smart_answers = helper.get_smart_answers()
    frailty, frailty_desc = helper.calculate_frailty_index()
    follow_up = helper.get_follow_up_interval()

    print(f"\n    Kirilganlik skoru: {frailty}/9 ({frailty_desc})")
    print(f"    Onerilen izlem araligi: {follow_up}")

    print("\n    Akilli cevaplar:")
    evet_count = sum(1 for v in smart_answers.values() if v == 'EVET')
    print(f"      EVET cevabi: {evet_count}/{len(smart_answers)}")
    for q, a in smart_answers.items():
        if a == 'EVET':
            print(f"      - {q}: {a}")

    print("\n" + "=" * 60)
    print("TEST TAMAMLANDI")
    print("=" * 60)


if __name__ == '__main__':
    test_drug_analyzer()


class PregnancyChecker:
    """Gebe listesi kontrolu"""
    
    def __init__(self, excel_path: str = None):
        self.pregnant_patients = {}  # TC -> hasta bilgileri
        
        if excel_path and os.path.exists(excel_path):
            self._load_pregnancy_list(excel_path)
        else:
            # Varsayilan yol
            default_paths = [
                'Gebe Listesi (27.11.2025).xls',
                'Gebe Listesi.xls',
                'Gebe Listesi.xlsx',
            ]
            for path in default_paths:
                full_path = os.path.join(os.path.dirname(__file__), path)
                if os.path.exists(full_path):
                    self._load_pregnancy_list(full_path)
                    break
    
    def _load_pregnancy_list(self, excel_path: str):
        """Excel'den gebe listesini yukle"""
        if not PANDAS_AVAILABLE:
            print('[!] Pandas yuklu degil, gebe listesi okunamiyor')
            return

        try:
            df = pd.read_excel(excel_path, engine="xlrd")

            # Kolon isimlerini bul (encoding sorunlari icin)
            columns = df.columns.tolist()

            # TC kolonu
            tc_col = None
            for col in columns:
                if 'T.C.' in col or 'Kimlik' in col or 'TC' in col.upper():
                    tc_col = col
                    break

            # Ad kolonu (encoding varyantlari: Adi, Ad, Ad�)
            ad_col = None
            for col in columns:
                col_lower = col.lower()
                if 'ad' in col_lower and 'soyad' not in col_lower:
                    ad_col = col
                    break

            # Soyad kolonu (encoding varyantlari: Soyadi, Soyad, Soyad�)
            soyad_col = None
            for col in columns:
                col_lower = col.lower()
                if 'soyad' in col_lower:
                    soyad_col = col
                    break

            for _, row in df.iterrows():
                tc = str(row.get(tc_col, '') if tc_col else '').strip()
                if tc and tc != 'nan':
                    ad = str(row.get(ad_col, '') if ad_col else '').strip()
                    soyad = str(row.get(soyad_col, '') if soyad_col else '').strip()

                    # nan kontrolu
                    if ad.lower() == 'nan':
                        ad = ''
                    if soyad.lower() == 'nan':
                        soyad = ''

                    self.pregnant_patients[tc] = {
                        'tc': tc,
                        'ad': ad,
                        'soyad': soyad,
                        'ad_soyad': f'{ad} {soyad}'.strip(),
                    }

            print(f'[OK] {len(self.pregnant_patients)} gebe yuklendi')
        except Exception as e:
            print(f'[!] Gebe listesi okuma hatasi: {e}')
    
    def is_pregnant(self, tc: str = None, ad_soyad: str = None) -> bool:
        """
        Hastanin gebe olup olmadigini kontrol et.
        
        Args:
            tc: TC Kimlik No
            ad_soyad: Ad Soyad (TC yoksa isim ile eslestir)
        
        Returns:
            True if pregnant
        """
        if not self.pregnant_patients:
            return False
        
        # TC ile kontrol
        if tc:
            tc = str(tc).strip()
            if tc in self.pregnant_patients:
                return True
        
        # Ad soyad ile kontrol
        if ad_soyad:
            ad_soyad_upper = ad_soyad.upper().strip()
            for patient in self.pregnant_patients.values():
                patient_name = patient.get('ad_soyad', '').upper()
                if patient_name and patient_name in ad_soyad_upper:
                    return True
                if patient_name and ad_soyad_upper in patient_name:
                    return True
        
        return False
    
    def get_pregnancy_answer(self, tc: str = None, ad_soyad: str = None) -> str:
        """
        HYP icin gebelik sorusunun cevabini dondur.
        
        Returns:
            'EVET' veya 'HAYIR'
        """
        return 'EVET' if self.is_pregnant(tc, ad_soyad) else 'HAYIR'

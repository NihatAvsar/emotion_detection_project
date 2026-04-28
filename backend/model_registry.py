"""
Model Registry — Coklu Model Yonetimi
=======================================
backend/models/ dizinindeki tum .pth model dosyalarini tarar,
kaydeder ve lazy-loading ile yukler.

Ozellikler:
- Otomatik dizin tarama (alt klasorler + kok .pth dosyalari)
- Klasor adindan timm model ismi cikarma
- Lazy loading: model ilk kullanimda yuklenir, sonra cache'den doner
- Thread-safe model erisimi

Kullanim:
    kayit_defteri = ModelRegistry("backend/models")
    kayit_defteri.tara()
    modeller = kayit_defteri.modelleri_listele()
    tahminleyici = kayit_defteri.model_getir("resnet18")
    sonuc = tahminleyici.predict(yuz_goruntusu)
"""

import os
import glob
import threading
from model import EmotionPredictor

# ─────────────────────────────────────────────
# Klasor adi → timm model ismi eslestirmesi
# ─────────────────────────────────────────────
FOLDER_TO_TIMM = {
    "resnet18":              "resnet18",
    "VGG16":                 "vgg16",
    "VGG19":                 "vgg19",
    "cait_xxs24_224":        "cait_xxs24_224",
    "convnext_tiny":         "convnext_tiny",
    "deit_tiny_patch16_224": "deit_tiny_patch16_224",
    "densenet121":           "densenet121",
    "effectnet_b0":          "efficientnet_b0",
    "effectnet_b3":          "efficientnet_b3",
    "mnasnet_100":           "mnasnet_100",
    "mobilenetv3_large_100": "mobilenetv3_large_100",
    "pit_ti_224":            "pit_ti_224",
    "resnet101":             "resnet101",
    "resnext50_32x4d":       "resnext50_32x4d",
    "visformer_tiny":        "visformer_tiny",
    "vit_base_16_224":       "vit_base_patch16_224",
    "vit_small_16_224":      "vit_small_patch16_224",
    "vit_tiny_16_224":       "vit_tiny_patch16_224",
    "xception":              "xception",
}

# ─────────────────────────────────────────────
# timm model ismi → giris boyutu eslestirmesi
# ─────────────────────────────────────────────
TIMM_INPUT_SIZES = {
    "xception":        299,
    "efficientnet_b3": 300,
}
VARSAYILAN_GIRIS_BOYUTU = 224


def _klasor_adi_normalize_et(ad: str) -> str:
    """
    Klasor veya dosya adini normalize et.
    Ornek: 'Resnet18' → 'resnet18', 'convnext_tiny_best' → 'convnext_tiny'
    """
    normalize_edilmis = ad.strip()

    # '_best' suffix'ini kaldir
    if normalize_edilmis.endswith("_best"):
        normalize_edilmis = normalize_edilmis[:-5]

    return normalize_edilmis


def _timm_adi_getir(klasor_adi: str) -> str:
    """
    Klasor adindan timm model ismini cikar.
    Once eslestirme tablosunu kontrol eder, bulamazsa adi oldugu gibi dondurur.
    """
    # Once tablodan dene (orijinal ad)
    if klasor_adi in FOLDER_TO_TIMM:
        return FOLDER_TO_TIMM[klasor_adi]

    # Normalize edip tekrar dene
    normalize_edilmis = _klasor_adi_normalize_et(klasor_adi)
    if normalize_edilmis in FOLDER_TO_TIMM:
        return FOLDER_TO_TIMM[normalize_edilmis]

    # Kucuk harfe cevirip dene
    kucuk_harf = normalize_edilmis.lower()
    for anahtar, deger in FOLDER_TO_TIMM.items():
        if anahtar.lower() == kucuk_harf:
            return deger

    # Tabloda bulunamadi — adi dondur (timm'in kendisi deneyecek)
    return normalize_edilmis.lower()


def _giris_boyutu_getir(timm_adi: str) -> int:
    """timm model ismine gore giris boyutu dondur."""
    return TIMM_INPUT_SIZES.get(timm_adi, VARSAYILAN_GIRIS_BOYUTU)


class ModelRegistry:
    """
    Coklu model kayit ve lazy-loading yoneticisi.

    Kullanim:
        kayit_defteri = ModelRegistry("/path/to/models")
        kayit_defteri.tara()
        tahminleyici = kayit_defteri.model_getir("resnet18")
    """

    def __init__(self, modeller_dizini: str):
        """
        Args:
            modeller_dizini: Model klasorlerinin bulundugu dizin (or. backend/models/)
        """
        self.modeller_dizini = os.path.abspath(modeller_dizini)

        # ─── Kayit defteri: { gorunen_ad: { timm_name, pth_path, input_size } } ───
        self._kayit_defteri: dict = {}

        # ─── Onbellek: { gorunen_ad: EmotionPredictor instance } ───
        self._onbellek: dict = {}

        # ─── Thread-safe yukleme ───
        self._kilit = threading.Lock()

    def tara(self) -> int:
        """
        modeller_dizini'ni tara, tum model dosyalarini bul ve kayit defterine ekle.

        Returns:
            int: Bulunan model sayisi
        """
        if not os.path.isdir(self.modeller_dizini):
            print(f"[KayitDefteri] Uyari: {self.modeller_dizini} dizini bulunamadi")
            return 0

        self._kayit_defteri.clear()

        # ─── 1. Alt klasorlerdeki .pth dosyalarini tara ───
        for girdi in os.listdir(self.modeller_dizini):
            girdi_yolu = os.path.join(self.modeller_dizini, girdi)

            if os.path.isdir(girdi_yolu):
                # Klasor icindeki ilk .pth dosyasini bul
                pth_dosyalari = glob.glob(os.path.join(girdi_yolu, "*.pth"))
                if pth_dosyalari:
                    pth_yolu = pth_dosyalari[0]
                    timm_adi = _timm_adi_getir(girdi)
                    giris_boyutu = _giris_boyutu_getir(timm_adi)

                    self._kayit_defteri[girdi] = {
                        "display_name": girdi,
                        "timm_name": timm_adi,
                        "pth_path": pth_yolu,
                        "input_size": giris_boyutu,
                        "loaded": False,
                    }

            elif girdi.endswith(".pth"):
                # Kok dizindeki .pth dosyasi
                temel_ad = girdi.replace(".pth", "")
                timm_adi = _timm_adi_getir(temel_ad)
                giris_boyutu = _giris_boyutu_getir(timm_adi)

                self._kayit_defteri[temel_ad] = {
                    "display_name": temel_ad,
                    "timm_name": timm_adi,
                    "pth_path": girdi_yolu,
                    "input_size": giris_boyutu,
                    "loaded": False,
                }

        print(f"[KayitDefteri] {len(self._kayit_defteri)} model bulundu:")
        for ad, bilgi in sorted(self._kayit_defteri.items()):
            print(f"  - {ad} -> timm:{bilgi['timm_name']} ({bilgi['input_size']}px)")

        return len(self._kayit_defteri)

    def modelleri_listele(self) -> list:
        """
        Kayitli model bilgilerini dondur.

        Returns:
            list: [ { name, timm_name, input_size, loaded }, ... ]
        """
        return [
            {
                "name": ad,
                "timm_name": bilgi["timm_name"],
                "input_size": bilgi["input_size"],
                "loaded": bilgi["loaded"],
            }
            for ad, bilgi in sorted(self._kayit_defteri.items())
        ]

    def model_getir(self, ad: str) -> EmotionPredictor:
        """
        Isme gore model dondur. Ilk cagirida lazy loading yapilir.

        Args:
            ad: Model adi (kayit defterindeki display_name)

        Returns:
            EmotionPredictor: Yuklenmis ve kullanima hazir model

        Raises:
            KeyError: Model kayit defterinde bulunamazsa
        """
        if ad not in self._kayit_defteri:
            raise KeyError(
                f"Model bulunamadi: '{ad}'\n"
                f"Mevcut modeller: {list(self._kayit_defteri.keys())}"
            )

        # ─── Onbellekte varsa direkt dondur ───
        if ad in self._onbellek:
            return self._onbellek[ad]

        # ─── Thread-safe lazy loading ───
        with self._kilit:
            # Double-check (baska thread yuklenmis olabilir)
            if ad in self._onbellek:
                return self._onbellek[ad]

            bilgi = self._kayit_defteri[ad]
            print(f"[KayitDefteri] Model yukleniyor: {ad} (timm:{bilgi['timm_name']})")

            # ─── EmotionPredictor olustur ───
            tahminleyici = EmotionPredictor(
                model_yolu=bilgi["pth_path"],
                timm_model_name=bilgi["timm_name"],
                giris_boyutu=bilgi["input_size"],
            )

            # Onbellege kaydet
            self._onbellek[ad] = tahminleyici
            bilgi["loaded"] = True

            print(f"[KayitDefteri] ✅ {ad} yuklendi ve onbelleklendi")
            return tahminleyici

    def varsayilan_model_adi_getir(self) -> str:
        """Kayit defterindeki ilk modelin adini dondur (varsayilan model)."""
        if not self._kayit_defteri:
            return None
        return sorted(self._kayit_defteri.keys())[0]

"""
ConvNeXt Tiny Duygu Tanima Modeli
==================================
Bu modul, ConvNeXt Tiny mimarisini kullanarak yuz ifadelerinden
duygu tahmini (inference) yapar.

Model detaylari:
- Mimari: ConvNeXt Tiny (timm kutuphanesi ile)
- Giris: 640x640 RGB goruntu
- Cikis: 5 duygu sinifi (angry, happy, neutral, sad, surprised)
- Dogruluk: ~%89
"""

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms
import timm
import os

# ─── Duygu siniflari (alfabetik sirada, egitim ile uyumlu) ───
EMOTION_CLASSES = ["angry", "happy", "neutral", "sad", "surprised"]

# ─── Turkce etiketler ───
DUYGU_ETIKETLERI_TR = {
    "angry": "Kızgın",
    "happy": "Mutlu",
    "neutral": "Nötr",
    "sad": "Üzgün",
    "surprised": "Şaşkın",
}

# ─── Emoji eslestirme ───
DUYGU_EMOJILERI = {
    "angry": "😠",
    "happy": "😊",
    "neutral": "😐",
    "sad": "😢",
    "surprised": "😲",
}

# ─── ImageNet normalizasyon parametreleri ───
IMAGENET_ORTALAMA = [0.485, 0.456, 0.406]
IMAGENET_STD_SAPMA = [0.229, 0.224, 0.225]

def _donusum_olustur(giris_boyutu: int = 224):
    """Belirtilen giris boyutuna gore transform pipeline olustur."""
    return transforms.Compose([
        transforms.Resize((giris_boyutu, giris_boyutu)),  # Model giris boyutuna olcekle
        transforms.ToTensor(),                             # [0,255] → [0,1] tensor
        transforms.Normalize(                              # ImageNet normalize
            mean=IMAGENET_ORTALAMA,
            std=IMAGENET_STD_SAPMA
        ),
    ])

# ─── Geriye uyumluluk: varsayilan transform ───
cikarsama_donusumu = _donusum_olustur(224)


class EmotionPredictor:
    """
    ConvNeXt Tiny tabanli duygu tahmin sinifi.

    Kullanim:
        tahminleyici = EmotionPredictor("convnext_tiny_best.pth")
        sonuc = tahminleyici.predict(yuz_goruntusu_np)
    """

    def __init__(self, model_yolu: str, timm_model_name: str = "convnext_tiny",
                 giris_boyutu: int = 224, device: str = None):
        """
        Model yukleme ve hazirlik.

        Args:
            model_yolu: .pth model dosyasinin yolu
            timm_model_name: timm kutuphanesindeki model adi (varsayilan: convnext_tiny)
            giris_boyutu: Model giris boyutu (varsayilan: 224)
            device: "cuda" veya "cpu" (None ise otomatik secim)
        """
        self.timm_model_name = timm_model_name
        self.giris_boyutu = giris_boyutu

        # ─── Giris boyutuna gore transform olustur ───
        self.transform = _donusum_olustur(giris_boyutu)

        # ─── Cihaz secimi (GPU varsa GPU, yoksa CPU) ───
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        print(f"[Model] Cihaz: {self.device}")

        # ─── timm model olustur (5 sinif) ───
        self.model = timm.create_model(
            timm_model_name,
            pretrained=False,  # Agirliklari dosyadan yukleyecegiz
            num_classes=len(EMOTION_CLASSES),
        )

        # ─── Egitilmis agirliklari yukle ───
        if not os.path.exists(model_yolu):
            raise FileNotFoundError(
                f"Model dosyasi bulunamadi: {model_yolu}\n"
                f"Lutfen 'convnext_tiny_best.pth' dosyasini proje kok dizinine kopyalayin."
            )

        agirlik_sozlugu = torch.load(model_yolu, map_location=self.device, weights_only=True)
        self.model.load_state_dict(agirlik_sozlugu)
        print(f"[Model] Agirliklar yuklendi: {model_yolu}")

        # ─── Eval moduna gec (dropout / batchnorm kapatir) ───
        self.model.eval()
        self.model.to(self.device)
        print(f"[Model] Hazir - {len(EMOTION_CLASSES)} sinif: {EMOTION_CLASSES}")

    def predict(self, yuz_goruntusu: np.ndarray) -> dict:
        """
        Kirpilmis yuz goruntusunden duygu tahmini yap.

        Args:
            yuz_goruntusu: BGR veya RGB numpy array (OpenCV formati)

        Returns:
            dict: {
                "emotion": str,        # Tahmin edilen duygu (Ingilizce)
                "emotion_tr": str,     # Turkce etiket
                "emoji": str,          # Emoji
                "confidence": float,   # Guven skoru (0-1)
                "probabilities": dict  # Her sinif icin olasilik
            }
        """
        # ─── BGR → RGB donusumu (OpenCV BGR kullanir) ───
        if len(yuz_goruntusu.shape) == 3 and yuz_goruntusu.shape[2] == 3:
            rgb_goruntu = yuz_goruntusu[:, :, ::-1]  # BGR → RGB
        else:
            rgb_goruntu = yuz_goruntusu

        # ─── NumPy → PIL Image ───
        pil_goruntu = Image.fromarray(rgb_goruntu.astype(np.uint8))

        # ─── Transform uygula: resize, normalize, tensor ───
        giris_tensoru = self.transform(pil_goruntu)
        giris_grubu = giris_tensoru.unsqueeze(0).to(self.device)  # Batch boyutu ekle

        # ─── Inference (gradient hesaplamasi kapali — hiz + bellek) ───
        with torch.no_grad():
            ham_ciktilar = self.model(giris_grubu)                    # Ham cikis
            olasiliklar = F.softmax(ham_ciktilar, dim=1)[0]          # Olasikliklara donustur

        # ─── En yuksek olasilikli sinifi bul ───
        guven_skoru, tahmin_indeksi = torch.max(olasiliklar, dim=0)
        tahmin_edilen_duygu = EMOTION_CLASSES[tahmin_indeksi.item()]

        # ─── Tum sinif olasiliklirini dict'e cevir ───
        olasilik_sozlugu = {
            cls: round(olasiliklar[i].item(), 4)
            for i, cls in enumerate(EMOTION_CLASSES)
        }

        return {
            "emotion": tahmin_edilen_duygu,
            "emotion_tr": DUYGU_ETIKETLERI_TR[tahmin_edilen_duygu],
            "emoji": DUYGU_EMOJILERI[tahmin_edilen_duygu],
            "confidence": round(guven_skoru.item(), 4),
            "probabilities": olasilik_sozlugu,
        }

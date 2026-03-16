"""
ConvNeXt Tiny Duygu Tanıma Modeli
==================================
Bu modül, ConvNeXt Tiny mimarisini kullanarak yüz ifadelerinden
duygu tahmini (inference) yapar.

Model detayları:
- Mimari: ConvNeXt Tiny (timm kütüphanesi ile)
- Giriş: 640x640 RGB görüntü
- Çıkış: 5 duygu sınıfı (angry, happy, neutral, sad, surprised)
- Doğruluk: ~%89
"""

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms
import timm
import os

# ─── Duygu sınıfları (alfabetik sırada, eğitim ile uyumlu) ───
EMOTION_CLASSES = ["angry", "happy", "neutral", "sad", "surprised"]

# ─── Türkçe etiketler ───
EMOTION_LABELS_TR = {
    "angry": "Kızgın",
    "happy": "Mutlu",
    "neutral": "Nötr",
    "sad": "Üzgün",
    "surprised": "Şaşkın",
}

# ─── Emoji eşleştirme ───
EMOTION_EMOJIS = {
    "angry": "😠",
    "happy": "😊",
    "neutral": "😐",
    "sad": "😢",
    "surprised": "😲",
}

# ─── ImageNet normalizasyon parametreleri ───
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

def _build_transform(input_size: int = 224):
    """Belirtilen giriş boyutuna göre transform pipeline oluştur."""
    return transforms.Compose([
        transforms.Resize((input_size, input_size)),  # Model giriş boyutuna ölçekle
        transforms.ToTensor(),                         # [0,255] → [0,1] tensor
        transforms.Normalize(                          # ImageNet normalize
            mean=IMAGENET_MEAN,
            std=IMAGENET_STD
        ),
    ])

# ─── Geriye uyumluluk: varsayılan transform ───
inference_transform = _build_transform(224)


class EmotionPredictor:
    """
    ConvNeXt Tiny tabanlı duygu tahmin sınıfı.

    Kullanım:
        predictor = EmotionPredictor("convnext_tiny_best.pth")
        result = predictor.predict(face_image_np)
    """

    def __init__(self, model_path: str, timm_model_name: str = "convnext_tiny",
                 input_size: int = 224, device: str = None):
        """
        Model yükleme ve hazırlık.

        Args:
            model_path: .pth model dosyasının yolu
            timm_model_name: timm kütüphanesindeki model adı (varsayılan: convnext_tiny)
            input_size: Model giriş boyutu (varsayılan: 224)
            device: "cuda" veya "cpu" (None ise otomatik seçim)
        """
        self.timm_model_name = timm_model_name
        self.input_size = input_size

        # ─── Giriş boyutuna göre transform oluştur ───
        self.transform = _build_transform(input_size)

        # ─── Cihaz seçimi (GPU varsa GPU, yoksa CPU) ───
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        print(f"[Model] Cihaz: {self.device}")

        # ─── timm model oluştur (5 sınıf) ───
        self.model = timm.create_model(
            timm_model_name,
            pretrained=False,  # Ağırlıkları dosyadan yükleyeceğiz
            num_classes=len(EMOTION_CLASSES),
        )

        # ─── Eğitilmiş ağırlıkları yükle ───
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model dosyası bulunamadı: {model_path}\n"
                f"Lütfen 'convnext_tiny_best.pth' dosyasını proje kök dizinine kopyalayın."
            )

        state_dict = torch.load(model_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state_dict)
        print(f"[Model] Ağırlıklar yüklendi: {model_path}")

        # ─── Eval moduna geç (dropout / batchnorm kapatır) ───
        self.model.eval()
        self.model.to(self.device)
        print(f"[Model] Hazır — {len(EMOTION_CLASSES)} sınıf: {EMOTION_CLASSES}")

    def predict(self, face_image: np.ndarray) -> dict:
        """
        Kırpılmış yüz görüntüsünden duygu tahmini yap.

        Args:
            face_image: BGR veya RGB numpy array (OpenCV formatı)

        Returns:
            dict: {
                "emotion": str,        # Tahmin edilen duygu (İngilizce)
                "emotion_tr": str,     # Türkçe etiket
                "emoji": str,          # Emoji
                "confidence": float,   # Güven skoru (0-1)
                "probabilities": dict  # Her sınıf için olasılık
            }
        """
        # ─── BGR → RGB dönüşümü (OpenCV BGR kullanır) ───
        if len(face_image.shape) == 3 and face_image.shape[2] == 3:
            rgb_image = face_image[:, :, ::-1]  # BGR → RGB
        else:
            rgb_image = face_image

        # ─── NumPy → PIL Image ───
        pil_image = Image.fromarray(rgb_image.astype(np.uint8))

        # ─── Transform uygula: resize, normalize, tensor ───
        input_tensor = self.transform(pil_image)
        input_batch = input_tensor.unsqueeze(0).to(self.device)  # Batch boyutu ekle

        # ─── Inference (gradient hesaplaması kapalı — hız + bellek) ───
        with torch.no_grad():
            logits = self.model(input_batch)               # Ham çıkış
            probabilities = F.softmax(logits, dim=1)[0]    # Olasılıklara dönüştür

        # ─── En yüksek olasılıklı sınıfı bul ───
        confidence, predicted_idx = torch.max(probabilities, dim=0)
        predicted_emotion = EMOTION_CLASSES[predicted_idx.item()]

        # ─── Tüm sınıf olasılıklarını dict'e çevir ───
        prob_dict = {
            cls: round(probabilities[i].item(), 4)
            for i, cls in enumerate(EMOTION_CLASSES)
        }

        return {
            "emotion": predicted_emotion,
            "emotion_tr": EMOTION_LABELS_TR[predicted_emotion],
            "emoji": EMOTION_EMOJIS[predicted_emotion],
            "confidence": round(confidence.item(), 4),
            "probabilities": prob_dict,
        }

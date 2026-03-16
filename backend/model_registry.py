"""
Model Registry — Çoklu Model Yönetimi
=======================================
backend/models/ dizinindeki tüm .pth model dosyalarını tarar,
kaydeder ve lazy-loading ile yükler.

Özellikler:
- Otomatik dizin tarama (alt klasörler + kök .pth dosyaları)
- Klasör adından timm model ismi çıkarma
- Lazy loading: model ilk kullanımda yüklenir, sonra cache'den döner
- Thread-safe model erişimi

Kullanım:
    registry = ModelRegistry("backend/models")
    registry.scan()
    models = registry.list_models()
    predictor = registry.get_model("resnet18")
    result = predictor.predict(face_image)
"""

import os
import glob
import threading
from model import EmotionPredictor

# ─────────────────────────────────────────────
# Klasör adı → timm model ismi eşleştirmesi
# ─────────────────────────────────────────────
# Bazı klasör/dosya adları timm isimleriyle eşleşmez.
# Bu tablo özel durumları ele alır.
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
# timm model ismi → giriş boyutu eşleştirmesi
# ─────────────────────────────────────────────
TIMM_INPUT_SIZES = {
    "xception":        299,
    "efficientnet_b3": 300,
}
DEFAULT_INPUT_SIZE = 224


def _normalize_folder_name(name: str) -> str:
    """
    Klasör veya dosya adını normalize et.
    Örnek: 'Resnet18' → 'resnet18', 'convnext_tiny_best' → 'convnext_tiny'
    """
    # Büyük/küçük harf normalize
    normalized = name.strip()

    # '_best' suffix'ini kaldır
    if normalized.endswith("_best"):
        normalized = normalized[:-5]

    return normalized


def _get_timm_name(folder_name: str) -> str:
    """
    Klasör adından timm model ismini çıkar.
    Önce eşleştirme tablosunu kontrol eder, bulamazsa adı olduğu gibi döndürür.
    """
    # Önce tablodan dene (orijinal ad)
    if folder_name in FOLDER_TO_TIMM:
        return FOLDER_TO_TIMM[folder_name]

    # Normalize edip tekrar dene
    normalized = _normalize_folder_name(folder_name)
    if normalized in FOLDER_TO_TIMM:
        return FOLDER_TO_TIMM[normalized]

    # Küçük harfe çevirip dene
    lower = normalized.lower()
    for key, value in FOLDER_TO_TIMM.items():
        if key.lower() == lower:
            return value

    # Tabloda bulunamadı — adı döndür (timm'in kendisi deneyecek)
    return normalized.lower()


def _get_input_size(timm_name: str) -> int:
    """timm model ismine göre giriş boyutu döndür."""
    return TIMM_INPUT_SIZES.get(timm_name, DEFAULT_INPUT_SIZE)


class ModelRegistry:
    """
    Çoklu model kayıt ve lazy-loading yöneticisi.

    Kullanım:
        registry = ModelRegistry("/path/to/models")
        registry.scan()
        predictor = registry.get_model("resnet18")
    """

    def __init__(self, models_dir: str):
        """
        Args:
            models_dir: Model klasörlerinin bulunduğu dizin (ör. backend/models/)
        """
        self.models_dir = os.path.abspath(models_dir)

        # ─── Registry: { display_name: { timm_name, pth_path, input_size } } ───
        self._registry: dict = {}

        # ─── Cache: { display_name: EmotionPredictor instance } ───
        self._cache: dict = {}

        # ─── Thread-safe loading ───
        self._lock = threading.Lock()

    def scan(self) -> int:
        """
        models_dir'i tara, tüm model dosyalarını bul ve registry'ye ekle.

        Returns:
            int: Bulunan model sayısı
        """
        if not os.path.isdir(self.models_dir):
            print(f"[Registry] Uyarı: {self.models_dir} dizini bulunamadı")
            return 0

        self._registry.clear()

        # ─── 1. Alt klasörlerdeki .pth dosyalarını tara ───
        for entry in os.listdir(self.models_dir):
            entry_path = os.path.join(self.models_dir, entry)

            if os.path.isdir(entry_path):
                # Klasör içindeki ilk .pth dosyasını bul
                pth_files = glob.glob(os.path.join(entry_path, "*.pth"))
                if pth_files:
                    pth_path = pth_files[0]  # İlk .pth dosyasını al
                    timm_name = _get_timm_name(entry)
                    input_size = _get_input_size(timm_name)

                    self._registry[entry] = {
                        "display_name": entry,
                        "timm_name": timm_name,
                        "pth_path": pth_path,
                        "input_size": input_size,
                        "loaded": False,
                    }

            elif entry.endswith(".pth"):
                # Kök dizindeki .pth dosyası
                base_name = entry.replace(".pth", "")
                timm_name = _get_timm_name(base_name)
                input_size = _get_input_size(timm_name)

                self._registry[base_name] = {
                    "display_name": base_name,
                    "timm_name": timm_name,
                    "pth_path": entry_path,
                    "input_size": input_size,
                    "loaded": False,
                }

        print(f"[Registry] {len(self._registry)} model bulundu:")
        for name, info in sorted(self._registry.items()):
            print(f"  • {name} → timm:{info['timm_name']} ({info['input_size']}px)")

        return len(self._registry)

    def list_models(self) -> list:
        """
        Kayıtlı model bilgilerini döndür.

        Returns:
            list: [ { name, timm_name, input_size, loaded }, ... ]
        """
        return [
            {
                "name": name,
                "timm_name": info["timm_name"],
                "input_size": info["input_size"],
                "loaded": info["loaded"],
            }
            for name, info in sorted(self._registry.items())
        ]

    def get_model(self, name: str) -> EmotionPredictor:
        """
        İsme göre model döndür. İlk çağrıda lazy loading yapılır.

        Args:
            name: Model adı (registry'deki display_name)

        Returns:
            EmotionPredictor: Yüklenmiş ve kullanıma hazır model

        Raises:
            KeyError: Model registry'de bulunamazsa
        """
        if name not in self._registry:
            raise KeyError(
                f"Model bulunamadı: '{name}'\n"
                f"Mevcut modeller: {list(self._registry.keys())}"
            )

        # ─── Cache'de varsa direkt döndür ───
        if name in self._cache:
            return self._cache[name]

        # ─── Thread-safe lazy loading ───
        with self._lock:
            # Double-check (başka thread yüklemiş olabilir)
            if name in self._cache:
                return self._cache[name]

            info = self._registry[name]
            print(f"[Registry] Model yükleniyor: {name} (timm:{info['timm_name']})")

            # ─── EmotionPredictor oluştur ───
            predictor = EmotionPredictor(
                model_path=info["pth_path"],
                timm_model_name=info["timm_name"],
                input_size=info["input_size"],
            )

            # Cache'e kaydet
            self._cache[name] = predictor
            info["loaded"] = True

            print(f"[Registry] ✅ {name} yüklendi ve cache'lendi")
            return predictor

    def get_default_model_name(self) -> str:
        """Registry'deki ilk modelin adını döndür (varsayılan model)."""
        if not self._registry:
            return None
        return sorted(self._registry.keys())[0]

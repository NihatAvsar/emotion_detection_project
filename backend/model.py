"""
model.py detaylari:
- Giris: 224x224 RGB goruntu
- Cikis: 5 duygu sinifi (angry, happy, neutral, sad, surprised)
- Dogruluk: ~%89
"""

import torch # PyTorch kütüphanesi (Derin öğrenme tensor işlemleri ve model yönetimi için)
import torch.nn.functional as F # Aktivasyon ve softmax gibi fonksiyonel sinir ağı bileşenleri
import numpy as np # Görüntü matrisleri ve sayısal işlemler için kullanılan kütüphane
from PIL import Image # Python Imaging Library — Tensor dönüşümü öncesi resim nesnesi yönetimi
from torchvision import transforms # Görüntüleri modele hazırlamak için transform pipeline modülü
import timm # PyTorch Image Models (timm) — Hazır ve modern CNN/Transformer mimarileri kütüphanesi
import os # Dosya varlığı ve sistem yolu kontrolleri için standart modül

# ─── Duygu siniflari (alfabetik sirada, egitim ile uyumlu) ───
EMOTION_CLASSES = ["angry", "happy", "neutral", "sad", "surprised"] # Modelin çıkış katmanındaki 5 farklı duygu sınıfının listesi

# ─── Turkce etiketler ───
DUYGU_ETIKETLERI_TR = { # İngilizce duygu etiketlerinin kullanıcıya gösterilecek Türkçe karşılıkları
    "angry": "Kızgın",
    "happy": "Mutlu",
    "neutral": "Nötr",
    "sad": "Üzgün",
    "surprised": "Şaşkın",
}

# ─── Emoji eslestirme ───
DUYGU_EMOJILERI = { # Görsel arayüz zenginleştirmesi için duygulara atanan emoji karakterleri
    "angry": "😠",
    "happy": "😊",
    "neutral": "😐",
    "sad": "😢",
    "surprised": "😲",
}

# ─── ImageNet normalizasyon parametreleri ───
IMAGENET_ORTALAMA = [0.485, 0.456, 0.406] # ImageNet veri setinin RGB kanalları için genel renk ortalaması listesi
IMAGENET_STD_SAPMA = [0.229, 0.224, 0.225] # ImageNet veri setinin RGB kanalları için standart sapma listesi

def _donusum_olustur(giris_boyutu: int = 224): # Resimleri yapay zeka modelinin istediği formata getiren transform fonksiyonu
    """Belirtilen giris boyutuna gore transform pipeline olustur."""
    return transforms.Compose([ # Sıralı görüntü işleme adımlarını (pipeline) birleştirir
        transforms.Resize((giris_boyutu, giris_boyutu)),  # Resmi modelin kabul ettiği kare piksel boyutlarına ölçekler
        transforms.ToTensor(),                             # Görüntüyü [0, 255] piksel aralığından [0.0, 1.0] PyTorch tensorüne çevirir
        transforms.Normalize(                              # Görüntü piksellerini ImageNet ortalama ve sapma değerlerine göre normalize eder
            mean=IMAGENET_ORTALAMA,
            std=IMAGENET_STD_SAPMA
        ),
    ])

# ─── Geriye uyumluluk: varsayilan transform ───
cikarsama_donusumu = _donusum_olustur(224) # Sınıf dışında doğrudan kullanım için 224x224 boyutlu varsayılan dönüştürücü


class EmotionPredictor: # ConvNeXt Tiny modelini yükleyen ve yüzlerden duygu tahmini yapan ana sınıf
    """
    ConvNeXt Tiny tabanli duygu tahmin sinifi.

    Kullanim:
        tahminleyici = EmotionPredictor("convnext_tiny_best.pth")
        sonuc = tahminleyici.predict(yuz_goruntusu_np)
    """

    def __init__(self, model_yolu: str, timm_model_name: str = "convnext_tiny", # Sınıfın başlatıcı ve model yükleyici metodu
                 giris_boyutu: int = 224, device: str = None):
        """
        Model yukleme ve hazirlik.

        Args:
            model_yolu: .pth model dosyasinin yolu
            timm_model_name: timm kutuphanesindeki model adi (varsayilan: convnext_tiny)
            giris_boyutu: Model giris boyutu (varsayilan: 224)
            device: "cuda" veya "cpu" (None ise otomatik secim)
        """
        self.timm_model_name = timm_model_name # Kullanılacak timm model mimarisinin adını sınıfa kaydeder
        self.giris_boyutu = giris_boyutu # Çıkarım esnasında kullanılacak giriş çözünürlüğünü saklar

        # ─── Giris boyutuna gore transform olustur ───
        self.transform = _donusum_olustur(giris_boyutu) # Bu modele özel çözünürlükle resim ön işleme adımlarını hazırlar

        # ─── Cihaz secimi (GPU varsa GPU, yoksa CPU) ───
        if device is None: # Eğer çalıştırılacak donanım dışarıdan açıkça belirtilmediyse
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") # CUDA (Nvidia GPU) desteği varsa seçir, yoksa CPU'ya döner
        else: # Eğer donanım dışarıdan string olarak paslandıysa
            self.device = torch.device(device) # Doğrudan o donanımı (Örn: "cuda:0") hedef cihaz olarak ayarlar

        print(f"[Model] Cihaz: {self.device}") # Modelin hangi donanım üzerinde (CPU/GPU) çalışacağını konsola yazar

        # ─── timm model olustur (5 sinif) ───
        self.model = timm.create_model( # Timm havuzundan boş (ağırlıksız) sinir ağı mimarisini oluşturur
            timm_model_name, # Çağrılacak mimari adı (Örn: convnext_tiny)
            pretrained=False,  # İnternetten hazır ImageNet ağırlıklarını indirme, dosyadan yükleme yapacağımızı belirtir
            num_classes=len(EMOTION_CLASSES), # Sınıflandırma kafasındaki (head) çıkış nöron sayısını 5 olarak ayarlar
        )

        # ─── Egitilmis agirliklari yukle ───
        if not os.path.exists(model_yolu): # Eğer verilen yolda .pth uzantılı ağırlık dosyası bulunamadıysa
            raise FileNotFoundError( # Hata fırlatarak programı durdurur ve eksik dosya uyarısı yapar
                f"Model dosyasi bulunamadi: {model_yolu}\n" # Bulunamayan dosya konumu
                f"Lutfen 'convnext_tiny_best.pth' dosyasini proje kok dizinine kopyalayin." # Çözüm rehber mesajı
            )

        agirlik_sozlugu = torch.load(model_yolu, map_location=self.device, weights_only=True) # Model ağırlıklarını güvenli modda diske okur
        self.model.load_state_dict(agirlik_sozlugu) # Okunan eğitilmiş ağırlık parametrelerini oluşturulan boş modele enjekte eder
        print(f"[Model] Agirliklar yuklendi: {model_yolu}") # Yükleme işleminin başarıyla tamamlandığını konsola yazar

        # ─── Eval moduna gec (dropout / batchnorm kapatir) ───
        self.model.eval() # Modeli test/çıkarım moduna alır (Eğitimde kullanılan Dropout ve BatchNorm katmanlarını dondurur)
        self.model.to(self.device) # Tüm sinir ağını ve parametre matrislerini hesaplama yapacağı donanıma (GPU/CPU) taşır
        print(f"[Model] Hazir - {len(EMOTION_CLASSES)} sinif: {EMOTION_CLASSES}") # Modelin kaç sınıfla göreve hazır olduğunu basar

    def predict(self, yuz_goruntusu: np.ndarray) -> dict: # Numpy matrisi olarak gelen yüz resmini işleyip tahmin üreten metot
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
        if len(yuz_goruntusu.shape) == 3 and yuz_goruntusu.shape[2] == 3: # Görüntü 3 kanallı renkli bir matris ise
            rgb_goruntu = yuz_goruntusu[:, :, ::-1]  # OpenCV'nin standart BGR sıralamasını tersine çevirerek RGB yapar
        else: # Görüntü zaten tek kanallı gri veya önceden dönüştürülmüşse
            rgb_goruntu = yuz_goruntusu # Olduğu gibi kabul et

        # ─── NumPy → PIL Image ───
        pil_goruntu = Image.fromarray(rgb_goruntu.astype(np.uint8)) # Sayısal NumPy dizisini PIL Image nesnesi formatına dönüştürür

        # ─── Transform uygula: resize, normalize, tensor ───
        giris_tensoru = self.transform(pil_goruntu) # Görüntüyü boyutlandırır, normalize eder ve PyTorch tensorü yapar
        giris_grubu = giris_tensoru.unsqueeze(0).to(self.device)  # Modele göndermek için sol tarafa sahte bir batch (grup) boyutu ekler [1, C, H, W]

        # ─── Inference (gradient hesaplamasi kapali — hiz + bellek) ───
        with torch.no_grad(): # Çıkarım esnasında türev/grad hesaplamasını kapatarak bellek sızıntısını önler ve hızı katlar
            ham_ciktilar = self.model(giris_grubu)                    # Görüntü grubunu sinir ağına besler ve ham logit çıktılarını alır
            olasiliklar = F.softmax(ham_ciktilar, dim=1)[0]          # Ham çıktıları Softmax fonksiyonu ile [0, 1] arası olasılık değerlerine çevirir

        # ─── En yuksek olasilikli sinifi bul ───
        guven_skoru, tahmin_indeksi = torch.max(olasiliklar, dim=0) # Olasılık listesindeki en yüksek değeri (güven) ve onun dizin numarasını (index) bulur
        tahmin_edilen_duygu = EMOTION_CLASSES[tahmin_indeksi.item()] # Dizin numarasını kullanarak İngilizce duygu sınıfı adını çeker

        # ─── Tum sinif olasiliklirini dict'e cevir ───
        olasilik_sozlugu = { # 5 duygunun her birinin tahmin edilme ihtimallerini içeren bir sözlük yapısı kurar
            cls: round(olasiliklar[i].item(), 4) # Değerleri PyTorch tensoründen standart float tipine çevirir ve 4 basamağa yuvarlar
            for i, cls in enumerate(EMOTION_CLASSES) # Tüm duygu sınıflarını sırasıyla gezer
        }

        return { # Dış dünyaya teslim edilecek olan yapılandırılmış çıkarım sonuç sözlüğü
            "emotion": tahmin_edilen_duygu, # En yüksek ihtimalli İngilizce duygu adı (Örn: "happy")
            "emotion_tr": DUYGU_ETIKETLERI_TR[tahmin_edilen_duygu], # Duygunun Türkçe metin karşılığı (Örn: "Mutlu")
            "emoji": DUYGU_EMOJILERI[tahmin_edilen_duygu], # Duyguyu temsil eden emoji (Örn: "😊")
            "confidence": round(guven_skoru.item(), 4), # Tahminin doğruluk olasılık skoru (Örn: 0.9452)
            "probabilities": olasilik_sozlugu, # Tüm sınıfların tek tek dağılım oranları sözlüğü
        }
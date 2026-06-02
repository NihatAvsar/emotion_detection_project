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

import os # Dosya ve dizin haritalama işlemleri için kullanılan standart modül
import glob # Belirli kalıplara uyan dosya yollarını (Örn: *.pth) bulmak için kullanılan modül
import threading # Çoklu iş parçacığı (Thread) kontrolü ve kilit mekanizmaları için kullanılan modül
from model import EmotionPredictor # Duygu durum tahmini yapan ana model sarmalayıcı sınıfı

# ─────────────────────────────────────────────
# Klasor adi → timm model ismi eslestirmesi
# ─────────────────────────────────────────────
FOLDER_TO_TIMM = { # Fiziksel klasör adlarını timm kütüphanesindeki karşılıklarına eşleyen sözlük sabit
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
TIMM_INPUT_SIZES = { # Standart 224 pikselden farklı giriş boyutuna sahip istisnai modellerin sözlüğü
    "xception":        299, # Xception modeli için giriş resim boyutu 299x299 pikseldir
    "efficientnet_b3": 300, # EfficientNet B3 modeli için giriş resim boyutu 300x300 pikseldir
}
VARSAYILAN_GIRIS_BOYUTU = 224 # Listede olmayan diğer tüm modeller için kullanılacak genel varsayılan çözünürlük


def _klasor_adi_normalize_et(ad: str) -> str: # Klasör adlarındaki gereksiz boşluk ve ekleri temizleyen yardımcı fonksiyon
    """
    Klasor veya dosya adini normalize et.
    Ornek: 'Resnet18' → 'resnet18', 'convnext_tiny_best' → 'convnext_tiny'
    """
    normalize_edilmis = ad.strip() # Klasör adının başındaki ve sonundaki boşluk karakterlerini temizler

    # '_best' suffix'ini kaldir
    if normalize_edilmis.endswith("_best"): # Eğer klasör adı eğitimden kalan '_best' ifadesi ile bitiyorsa
        normalize_edilmis = normalize_edilmis[:-5] # Sağdaki 5 karakteri (_best) kırparak saf model adını bırakır

    return normalize_edilmis # Temizlenmiş klasör adını döndürür


def _timm_adi_getir(klasor_adi: str) -> str: # Klasör adından timm kütüphanesinin anlayacağı model adını türeten fonksiyon
    """
    Klasor adindan timm model ismini cikar.
    Once eslestirme tablosunu kontrol eder, bulamazsa adi oldugu gibi dondurur.
    """
    # Once tablodan dene (orijinal ad)
    if klasor_adi in FOLDER_TO_TIMM: # Eğer klasör adı haritalama tablosunda birebir mevcutsa
        return FOLDER_TO_TIMM[klasor_adi] # Tablodaki timm karşılığını doğrudan döndür

    # Normalize edip tekrar dene
    normalize_edilmis = _klasor_adi_normalize_et(klasor_adi) # Klasör adını normalize etme fonksiyonuna gönderir
    if normalize_edilmis in FOLDER_TO_TIMM: # Normalize edilmiş hali tabloda varsa
        return FOLDER_TO_TIMM[normalize_edilmis] # Tablodaki timm karşılığını döndür

    # Kucuk harfe cevirip dene
    kucuk_harf = normalize_edilmis.lower() # Büyük/küçük harf duyarlılığını aşmak için tamamen küçük harfe çevirir
    for anahtar, deger in FOLDER_TO_TIMM.items(): # Eşleştirme tablosundaki tüm anahtarları tek tek gez
        if anahtar.lower() == kucuk_harf: # Eğer tablodaki anahtarın küçük harf hali eşleşiyorsa
            return deger # Eşleşen timm model ismini döndür

    # Tabloda bulunamadi — adi dondur (timm'in kendisi deneyecek)
    return normalize_edilmis.lower() # Hiçbir şey bulunamazsa ham temiz adı küçük harfe çevirip şansını denemesi için döndür


def _giris_boyutu_getir(timm_adi: str) -> int: # Modelin timm adına göre kaç piksellik resim istediğini bulan fonksiyon
    """timm model ismine gore giris boyutu dondur."""
    return TIMM_INPUT_SIZES.get(timm_adi, VARSAYILAN_GIRIS_BOYUTU) # İstisnai tablolara bakar, yoksa 224 döndürür


class ModelRegistry: # Bilgisayardaki model dosyalarını yöneten, listeleyen ve yükleyen ana kayıt sınıfı
    """
    Coklu model kayit ve lazy-loading yoneticisi.

    Kullanim:
        kayit_defteri = ModelRegistry("/path/to/models")
        kayit_defteri.tara()
        tahminleyici = kayit_defteri.model_getir("resnet18")
    """

    def __init__(self, modeller_dizini: str): # Sınıfın başlatıcı metodu
        """
        Args:
            modeller_dizini: Model klasorlerinin bulundugu dizin (or. backend/models/)
        """
        self.modeller_dizini = os.path.abspath(modeller_dizini) # Verilen dizin yolunu tam (mutlak) işletim sistemi yoluna çevirir

        # ─── Kayit defteri: { gorunen_ad: { timm_name, pth_path, input_size } } ───
        self._kayit_defteri: dict = {} # Disk üzerinde keşfedilen tüm modellerin meta verilerini tutacak sözlük

        # ─── Onbellek: { gorunen_ad: EmotionPredictor instance } ───
        self._onbellek: dict = {} # Belleğe (RAM) yüklenmiş olan canlı model nesnelerini saklayan havuz

        # ─── Thread-safe yukleme ───
        self._kilit = threading.Lock() # Aynı anda birden fazla istek geldiğinde modelin iki kez yüklenmesini önleyen kilit nesnesi

    def tara(self) -> int: # Belirtilen modeller dizinini tarayarak modelleri hafızaya kaydeden metot
        """
        modeller_dizini'ni tara, tum model dosyalarini bul ve kayit defterine ekle.

        Returns:
            int: Bulunan model sayisi
        """
        if not os.path.isdir(self.modeller_dizini): # Eğer belirtilen model dizini fiziksel olarak mevcut değilse
            print(f"[KayitDefteri] Uyari: {self.modeller_dizini} dizini bulunamadi") # Konsola uyarı mesajı bas
            return 0 # Bulunan model sayısını sıfır olarak döndür

        self._kayit_defteri.clear() # Yeni tarama öncesi kayıt defteri içeriğini tamamen temizler

        # ─── 1. Alt klasorlerdeki .pth dosyalarini tara ───
        for girdi in os.listdir(self.modeller_dizini): # Ana model dizini içindeki tüm dosya ve klasörleri listeler
            girdi_yolu = os.path.join(self.modeller_dizini, girdi) # Klasör içi elemanın tam yolunu oluşturur

            if os.path.isdir(girdi_yolu): # Eğer bu eleman bir klasör (alt dizin) ise
                # Klasor icindeki ilk .pth dosyasini bul
                pth_dosyalari = glob.glob(os.path.join(girdi_yolu, "*.pth")) # Klasör içinde uzantısı .pth olan dosyaları arar
                if pth_dosyalari: # Eğer klasörün içinde en az bir tane .pth uzantılı ağırlık dosyası bulunduysa
                    pth_yolu = pth_dosyalari[0] # Listelenen pth dosyalarından ilkini (varsayılanı) seçer
                    timm_adi = _timm_adi_getir(girdi) # Klasör adını kullanarak timm kütüphanesi model adını bulur
                    giris_boyutu = _giris_boyutu_getir(timm_adi) # Modelin ihtiyaç duyduğu girdi çözünürlüğünü alır

                    self._kayit_defteri[girdi] = { # Keşfedilen modeli klasör adıyla kayıt defterine ekler
                        "display_name": girdi, # Arayüzde veya API'de görünecek model ismi (Klasör adı)
                        "timm_name": timm_adi, # Timm kütüphanesinin mimariyi ayağa kaldırırken isteyeceği kod ad
                        "pth_path": pth_yolu, # Model ağırlık dosyasının tam fiziksel disk yolu
                        "input_size": giris_boyutu, # Modelin resim işleme boyutu
                        "loaded": False, # Model henüz belleğe yüklenmediği için yüklendi bilgisini False yapar
                    }

            elif girdi.endswith(".pth"): # Eğer eleman klasör değil de doğrudan ana dizindeki bir .pth dosyası ise
                # Kok dizindeki .pth dosyasi
                temel_ad = girdi.replace(".pth", "") # Dosya uzantısını (.pth) kaldırarak saf model ismini elde eder
                timm_adi = _timm_adi_getir(temel_ad) # Dosya adından timm kütüphanesi adını türetir
                giris_boyutu = _giris_boyutu_getir(timm_adi) # Giriş çözünürlük değerini alır

                self._kayit_defteri[temel_ad] = { # Modeli dosya adıyla kayıt defterine kaydeder
                    "display_name": temel_ad, # Görünecek model ismi
                    "timm_name": timm_adi, # Timm mimari adı
                    "pth_path": girdi_yolu, # Dosyanın tam disk yolu
                    "input_size": giris_boyutu, # Giriş çözünürlüğü
                    "loaded": False, # İlk aşamada belleğe yüklenme durumunu False yapar
                }

        print(f"[KayitDefteri] {len(self._kayit_defteri)} model bulundu:") # Konsola kaç adet model keşfedildiğini yazdırır
        for ad, bilgi in sorted(self._kayit_defteri.items()): # Bulunan modelleri isim sırasına göre dönerek listeler
            print(f"  - {ad} -> timm:{bilgi['timm_name']} ({bilgi['input_size']}px)") # Model özet bilgilerini konsola basar

        return len(self._kayit_defteri) # Toplam kaydedilen model sayısını geri döndürür

    def modelleri_listele(self) -> list: # Kayıtlı modelleri API'ye veya arayüze listelemek için optimize eden metot
        """
        Kayitli model bilgilerini dondur.

        Returns:
            list: [ { name, timm_name, input_size, loaded }, ... ]
        """
        return [ # Sözlük yapısındaki verileri liste formatına çevirerek döndürür
            {
                "name": ad, # Modelin kayıtlı adı
                "timm_name": bilgi["timm_name"], # Timm sistem ismi
                "input_size": bilgi["input_size"], # Çözünürlük boyutu
                "loaded": bilgi["loaded"], # Bellekte aktif olup olmadığı bilgisi
            }
            for ad, bilgi in sorted(self._kayit_defteri.items()) # Tüm modelleri alfabetik sırayla dönerek listeyi oluşturur
        ]

    def model_getir(self, ad: str) -> EmotionPredictor: # İstendiğinde modeli belleğe yükleyen (Lazy Loading) ana erişim metodu
        """
        Isme gore model dondur. Ilk cagirida lazy loading yapilir.

        Args:
            ad: Model adi (kayit defterindeki display_name)

        Returns:
            EmotionPredictor: Yuklenmis ve kullanima hazir model

        Raises:
            KeyError: Model kayit defterinde bulunamazsa
        """
        if ad not in self._kayit_defteri: # Eğer istenen model ismi kayıt defterinde hiç yoksa
            raise KeyError( # KeyError fırlatarak mevcut geçerli modellerin listesini ekrana basar
                f"Model bulunamadi: '{ad}'\n" # İstenen geçersiz ad
                f"Mevcut modeller: {list(self._kayit_defteri.keys())}" # Seçilebilecek doğru alternatifler
            )

        # ─── Onbellekte varsa direkt dondur ───
        if ad in self._onbellek: # Eğer model daha önce zaten çağrılmış ve belleğe yüklenmişse
            return self._onbellek[ad] # Diskten tekrar okumayıp bellekteki (cache) hazır nesneyi döndürür

        # ─── Thread-safe lazy loading ───
        with self._kilit: # Aynı anda gelen isteklerin kilit mekanizmasına takılmasını sağlar (Eş zamanlılık koruması)
            # Double-check (baska thread yuklenmis olabilir)
            if ad in self._onbellek: # Kilit sırası beklerken başka bir iş parçacığı modeli yüklemiş mi kontrolü (Çift kontrol kalıbı)
                return self._onbellek[ad] # Eğer bekleme esnasında yüklendiyse direkt hazır olanı döndür

            bilgi = self._kayit_defteri[ad] # Modelin disk yolu ve mimari ad bilgilerini kayıt defterinden alır
            print(f"[KayitDefteri] Model yukleniyor: {ad} (timm:{bilgi['timm_name']})") # Konsola yükleme işleminin başladığını yaz

            # ─── EmotionPredictor olustur ───
            tahminleyici = EmotionPredictor( # Gerçek ağırlık dosyasını diske okutarak yapay zeka modelini RAM'e yükler
                model_yolu=bilgi["pth_path"], # Fiziksel .pth dosyasının konumu
                timm_model_name=bilgi["timm_name"], # Timm mimari adı nesnesi
                giris_boyutu=bilgi["input_size"], # Modelin resim işleme matris boyutu
            )

            # Onbellege kaydet
            self._onbellek[ad] = tahminleyici # Yüklenen canlı nesneyi gelecekteki hızlı çağrılar için önbelleğe yerleştirir
            bilgi["loaded"] = True # Modelin kayıt defterindeki durumunu yüklendi (True) olarak günceller

            print(f"[KayitDefteri] ✅ {ad} yuklendi ve onbelleklendi") # Konsola başarılı yükleme onay mesajı yazar
            return tahminleyici # Kullanıma hazır, canlı tahminleyici nesnesini döndürür

    def varsayilan_model_adi_getir(self) -> str: # Sistemde model seçilmediğinde otomatik atanacak ilk modeli seçen metot
        """Kayit defterindeki ilk modelin adini dondur (varsayilan model)."""
        if not self._kayit_defteri: # Eğer kayıt defterinde taranmış hiçbir model bulunamadıysa
            return None # Geriye None değeri döndür
        return sorted(self._kayit_defteri.keys())[0] # Alfabetik sıralamadaki ilk modelin ismini varsayılan olarak seçer
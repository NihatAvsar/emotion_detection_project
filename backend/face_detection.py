"""
MediaPipe Yuz Tespiti Modulu (Optimize Edilmis)
=================================================
Performans optimizasyonlari:

1. VIDEO modu — MediaPipe'in video stream'i icin optimize modeli
2. Yuz cache — Her frame'de tespit calistirmak yerine,
   son tespiti N frame boyunca yeniden kullanir
3. Downscale — Tespit oncesi goruntugu kuculterek hiz kazanir
4. Verimli renk donusumu — gereksiz kopyalamadan kacinir

Not: MediaPipe 0.10.20+ Tasks API kullanir.
"""

import os # Dosya ve dizin yolu işlemleri için kullanılan standart modül
import time # Zaman damgası üretmek ve süre ölçümü için kullanılan modül
import cv2 # OpenCV görüntü işleme kütüphanesi
import numpy as np # Çok boyutlu diziler ve matris işlemleri için kullanılan kütüphane
import mediapipe as mp # Google MediaPipe yapay zeka ve bilgisayarlı görü kütüphanesi
from mediapipe.tasks import python # MediaPipe Tasks API Python bağlayıcıları
from mediapipe.tasks.python import vision # MediaPipe bilgisayarlı görü (vision) görevleri modülü


class FaceDetector: # Optimize edilmiş yüz tespit ve kırpma işlemlerini yöneten ana sınıf
    """
    Optimize edilmis MediaPipe Tasks API yuz tespit sinifi.

    Ozellikler:
    - VIDEO modu (stream optimize)
    - Yuz onbellegi (her N frame'de bir tespit)
    - Downscale ile hizli tespit
    """

    def __init__(
        self,
        min_tespit_guveni: float = 0.5, # Yüz olarak kabul edilecek minimum doğruluk/güven eşiği
        onbellek_kare_sayisi: int = 3, # Yüz tespitinin kaç karede bir tetikleneceğini belirleyen sınır
        tespit_kucultme_orani: float = 0.5, # Model çalışmadan önce görüntünün ölçeklendirileceği küçültme oranı
    ):
        """
        Args:
            min_tespit_guveni: Minimum yuz tespit guven esigi
            onbellek_kare_sayisi: Kac frame boyunca eski tespit sonucunu kullanacak
            tespit_kucultme_orani: Tespit oncesi goruntu kucultme orani (0.5 = yari boyut)
        """
        # ─── BlazeFace model dosyasini bul ───
        model_dosya_adi = "blaze_face_short_range.tflite" # Kullanılacak olan hafif ve hızlı BlazeFace model dosyasının adı
        model_yolu = os.path.join( # Mevcut dosyanın bulunduğu dizin ile model adını birleştirerek tam yolu oluşturur
            os.path.dirname(os.path.abspath(__file__)), model_dosya_adi # Bu scriptin mutlak dizin yolunu alır
        )

        if not os.path.exists(model_yolu): # Eğer belirtilen yolda model dosyası fiziksel olarak yoksa
            raise FileNotFoundError( # Hata fırlatarak programı durdur ve kullanıcıyı bilgilendir
                f"MediaPipe model dosyasi bulunamadi: {model_yolu}\n" # Bulunamayan modelin arandığı tam yol
                f"Lutfen '{model_dosya_adi}' dosyasini backend/ dizinine koyun." # Çözüm önerisi mesajı
            )

        # ─── VIDEO modu ile FaceDetector olustur ───
        base_options = python.BaseOptions(model_asset_path=model_yolu) # MediaPipe model dosyasının konumunu temel ayarlara yükler
        options = vision.FaceDetectorOptions( # Yüz tespit edicinin çalışma parametrelerini yapılandırır
            base_options=base_options, # Temel model ayarları referansı
            running_mode=vision.RunningMode.VIDEO, # Ardışık kareler arası takibi optimize eden VIDEO çalışma modu
            min_detection_confidence=min_tespit_guveni, # Dışarıdan verilen minimum güven eşiği ataması
        )
        self.detector = vision.FaceDetector.create_from_options(options) # Yapılandırılan ayarlarla MediaPipe yüz tespit nesnesini üretir

        # ─── Onbellek ayarlari ───
        self.onbellek_kare_sayisi = onbellek_kare_sayisi # Kaç karede bir modelin tetikleneceği bilgisini saklar
        self._kare_sayaci = 0 # Kare atlama takibi için kullanılan iç sayaç başlangıcı
        self._onbellekteki_kutular = None # Son başarılı tespitte bulunan yüz kutularını tutan hafıza alanı
        self._tespit_kucultme_orani = tespit_kucultme_orani # Görüntü küçültme katsayısını sınıfta saklar

        print( # Konsola sistemin başarıyla hangi ayarlarla başladığı bilgisini yazdırır
            f"[YuzTespit] Baslatildi - VIDEO modu, " # Çalışma modu bilgisi
            f"onbellek:{onbellek_kare_sayisi} kare, kucultme:{tespit_kucultme_orani}" # Önbellek ve downscale parametreleri
        )

    def _yuzleri_tespit_et(self, kare: np.ndarray) -> list: # Görütü üzerinde MediaPipe modelini koşturan iç metot
        """
        MediaPipe ile yuz tespiti yap (downscale + VIDEO modu).

        Returns:
            list of dict: [ {"x": int, "y": int, "w": int, "h": int}, ... ]
        """
        y_boyut, g_boyut = kare.shape[:2] # Gelen orijinal görüntünün yükseklik ve genişlik değerlerini alır

        # ─── Downscale: tespit icin kucultulmus kare ───
        oran = self._tespit_kucultme_orani # Küçültme oranını yerel değişkene aktarır
        if oran < 1.0: # Eğer oran 1.0'dan küçükse yani küçültme talep edilmişse
            kucuk_kare = cv2.resize( # OpenCV ile görüntüyü yeniden boyutlandırır (Hız kazanmak için)
                kare, # Orijinal büyük kare
                (int(g_boyut * oran), int(y_boyut * oran)), # Yeni küçültülmüş genişlik ve yükseklik piksel değerleri
                interpolation=cv2.INTER_LINEAR, # Yeniden boyutlandırmada kullanılacak doğrusal interpolasyon algoritması
            )
        else: # Eğer oran 1.0 veya daha büyükse küçültme yapma
            kucuk_kare = kare # Görüntüyü olduğu gibi kullan
            oran = 1.0 # Oranı standart değere eşitle

        # ─── BGR → RGB ───
        rgb_kare = cv2.cvtColor(kucuk_kare, cv2.COLOR_BGR2RGB) # OpenCV'nin standart BGR formatını MediaPipe'ın istediği RGB formatına çevirir

        # ─── MediaPipe Image ───
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_kare) # RGB matris verisini MediaPipe'ın özel Image nesnesine dönüştürür

        # ─── VIDEO modu: kesin artan timestamp gerekir ───
        zaman_damgasi_ms = int(time.time() * 1000) # VIDEO modunun çalışması için gerekli olan milisaniye cinsinden zaman damgası üretir
        tespit_sonucu = self.detector.detect_for_video( # MediaPipe video tespiti fonksiyonunu çalıştırır
            mp_image, zaman_damgasi_ms # Görüntü nesnesi ve benzersiz artan zaman damgası parametreleri
        )

        sinir_kutulari = [] # Normalize değerlerden kurtarılmış gerçek piksel koordinat kutularının listesi
        if tespit_sonucu.detections: # Eğer model görüntüde en az bir adet yüz tespit edebildiyse
            for tespit in tespit_sonucu.detections: # Tespit edilen tüm yüz nesneleri üzerinde döngü başlatır
                kutu = tespit.bounding_box # Yüzün etrafındaki sınırlayıcı kutu (bounding box) nesnesini alır
                sinir_kutulari.append({ # Küçültülmüş koordinatları orijinal büyük görüntü boyutuna geri ölçekleyerek listeye ekler
                    "x": int(kutu.origin_x / oran), # Küçültülmüş sol üst X koordinatını eski haline getirir
                    "y": int(kutu.origin_y / oran), # Küçültülmüş sol üst Y koordinatını eski haline getirir
                    "w": int(kutu.width / oran), # Küçültülmüş genişlik değerini orijinal boyutuna büyütür
                    "h": int(kutu.height / oran), # Küçültülmüş yükseklik değerini orijinal boyutuna büyütür
                })

        return sinir_kutulari # Hesaplanan tüm net yüz kutularını liste olarak döndürür

    def tespit_et_ve_kirp( # Dışarıdan çağrılan, önbelleği yöneten ve yüzleri kesip büyüten ana metot
        self,
        kare: np.ndarray, # İşlenecek olan anlık BGR formatındaki OpenCV karesi
        hedef_boyut: int = 640, # Kırpılan yüzlerin çıktı olarak getirileceği kare piksel boyutu (Genişlik=Yükseklik)
        bosluk_orani: float = 0.25, # Yüzün dar kalmaması için etrafına eklenecek marj/boşluk yüzdesi
    ) -> list:
        """
        Goruntudeki yuzleri tespit et, kirp ve yeniden boyutlandir.

        Args:
            kare: BGR formatinda OpenCV goruntusu
            hedef_boyut: Hedef cikti boyutu (kare)
            bosluk_orani: Yuz etrafina eklenecek bosluk orani

        Returns:
            list: (kirpilmis_yuz, kutu_dict) ikilisi — bossa []
        """
        y_boyut, g_boyut = kare.shape[:2] # Görüntünün anlık yükseklik ve genişliğini piksel cinsinden alır

        # ─── Onbellek kontrolu ───
        self._kare_sayaci += 1 # Gelen her yeni kare için iç sayacı bir artırır
        if self._onbellekteki_kutular is None or self._kare_sayaci >= self.onbellek_kare_sayisi: # Önbellek boşsa veya yenileme zamanı geldiyse
            self._onbellekteki_kutular = self._yuzleri_tespit_et(kare) # Gerçek yapay zeka modelini çalıştırıp kutuları günceller
            self._kare_sayaci = 0 # Yeni tespit yapıldığı için kare sayacını tekrar sıfırlar

        kutular = self._onbellekteki_kutular # Güncel veya önbellekten gelen yüz kutularını işleme alır
        if not kutular: # Eğer görüntüde veya önbellekte hiç yüz kutusu yoksa
            return [] # Süreci uzatmadan doğrudan boş liste döndürür

        yuzler = [] # Kırpılmış resimler ve kutu koordinatlarının beraber tutulacağı sonuç listesi

        for kutu in kutular: # Tespit edilen tüm yüz kutuları üzerinde döngüye girer
            x_min, y_min = kutu["x"], kutu["y"] # Kutunun sol üst köşe koordinatları
            kutu_g, kutu_y = kutu["w"], kutu["h"] # Kutunun genişlik ve yükseklik değerleri

            # ─── Kare padding ───
            merkez_x = x_min + kutu_g // 2 # Yüz kutusunun tam orta X noktasını bulur
            merkez_y = y_min + kutu_y // 2 # Yüz kutusunun tam orta Y noktasını bulur
            kenar = int(max(kutu_g, kutu_y) * (1 + bosluk_orani)) # En uzun kenarı baz alıp boşluk oranı ekleyerek ideal bir kare kenarı hesaplar

            # ─── Sinir kontrolu ile kirpma ───
            kirp_x1 = max(0, merkez_x - kenar // 2) # Kırpılacak bölgenin sol X sınırını bulur (0'dan küçük olmasını engeller)
            kirp_y1 = max(0, merkez_y - kenar // 2) # Kırpılacak bölgenin üst Y sınırını bulur (0'dan küçük olmasını engeller)
            kirp_x2 = min(g_boyut, merkez_x + kenar // 2) # Kırpılacak bölgenin sağ X sınırını bulur (Resim genişliğini aşamaz)
            kirp_y2 = min(y_boyut, merkez_y + kenar // 2) # Kırpılacak bölgenin alt Y sınırını bulur (Resim yüksekliğini aşamaz)

            yuz_kirpma = kare[kirp_y1:kirp_y2, kirp_x1:kirp_x2] # Numpy matris dilimlemesi (slicing) ile yüz bölgesini resimden kesip alır

            if yuz_kirpma.size == 0: # Eğer kırpılan matris boş veya geçersiz bir boyuttaysa (Çizgi veya sıfır alan durumunda)
                continue # Bu yüzü pas geç ve döngüdeki bir sonraki yüze atla

            # ─── Resize ───
            yuz_yeniden_boyutlu = cv2.resize( # Kırpılan yüz parçasını duygu analizi modelinin isteyeceği standart boyuta getirir
                yuz_kirpma, # Kesilen yüz resmi parçası
                (hedef_boyut, hedef_boyut), # Belirlenen hedef kare boyutları (Örn: 640x640)
                interpolation=cv2.INTER_LINEAR, # Büyütme/küçültme esnasında pikselleri yumuşatan doğrusal interpolasyon
            )

            yuzler.append((yuz_yeniden_boyutlu, kutu)) # Kırpılmış standart boyuttaki yüz resmini ve koordinat sözlüğünü ikili (tuple) olarak ekler

        return yuzler # Elde edilen tüm işlenmiş (kırpılmış_yuz, kutu_bilgisi) listesini döndürür

    def onbellegi_sifirla(self): # Kamera akışı koptuğunda veya yeni bir video başladığında çağrılan temizlik metodu
        """Yeni stream baslatildiginda onbellegi sifirla."""
        self._onbellekteki_kutular = None # Eski video akışından kalan önbellek kutularını temizler
        self._kare_sayaci = 0 # Kare atlama sayacını sıfırlayarak yeni akışa hazır hale getirir

    def __del__(self): # Sınıf nesnesi bellekten silinirken (Garbage Collector çalıştığında) tetiklenen yıkıcı metot
        """Temizlik."""
        if hasattr(self, "detector"): # Eğer sınıf içinde detector nesnesi başarıyla oluşturulmuşsa
            self.detector.close() # MediaPipe C++ arka plan bileşenlerini ve ayrılan kaynakları güvenli bir şekilde kapatır
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

import os
import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class FaceDetector:
    """
    Optimize edilmis MediaPipe Tasks API yuz tespit sinifi.

    Ozellikler:
    - VIDEO modu (stream optimize)
    - Yuz onbellegi (her N frame'de bir tespit)
    - Downscale ile hizli tespit
    """

    def __init__(
        self,
        min_tespit_guveni: float = 0.5,
        onbellek_kare_sayisi: int = 3,
        tespit_kucultme_orani: float = 0.5,
    ):
        """
        Args:
            min_tespit_guveni: Minimum yuz tespit guven esigi
            onbellek_kare_sayisi: Kac frame boyunca eski tespit sonucunu kullanacak
            tespit_kucultme_orani: Tespit oncesi goruntu kucultme orani (0.5 = yari boyut)
        """
        # ─── BlazeFace model dosyasini bul ───
        model_dosya_adi = "blaze_face_short_range.tflite"
        model_yolu = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), model_dosya_adi
        )

        if not os.path.exists(model_yolu):
            raise FileNotFoundError(
                f"MediaPipe model dosyasi bulunamadi: {model_yolu}\n"
                f"Lutfen '{model_dosya_adi}' dosyasini backend/ dizinine koyun."
            )

        # ─── VIDEO modu ile FaceDetector olustur ───
        base_options = python.BaseOptions(model_asset_path=model_yolu)
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_detection_confidence=min_tespit_guveni,
        )
        self.detector = vision.FaceDetector.create_from_options(options)

        # ─── Onbellek ayarlari ───
        self.onbellek_kare_sayisi = onbellek_kare_sayisi
        self._kare_sayaci = 0
        self._onbellekteki_kutular = None
        self._tespit_kucultme_orani = tespit_kucultme_orani

        print(
            f"[YuzTespit] Baslatildi - VIDEO modu, "
            f"onbellek:{onbellek_kare_sayisi} kare, kucultme:{tespit_kucultme_orani}"
        )

    def _yuzleri_tespit_et(self, kare: np.ndarray) -> list:
        """
        MediaPipe ile yuz tespiti yap (downscale + VIDEO modu).

        Returns:
            list of dict: [ {"x": int, "y": int, "w": int, "h": int}, ... ]
        """
        y_boyut, g_boyut = kare.shape[:2]

        # ─── Downscale: tespit icin kucultulmus kare ───
        oran = self._tespit_kucultme_orani
        if oran < 1.0:
            kucuk_kare = cv2.resize(
                kare,
                (int(g_boyut * oran), int(y_boyut * oran)),
                interpolation=cv2.INTER_LINEAR,
            )
        else:
            kucuk_kare = kare
            oran = 1.0

        # ─── BGR → RGB ───
        rgb_kare = cv2.cvtColor(kucuk_kare, cv2.COLOR_BGR2RGB)

        # ─── MediaPipe Image ───
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_kare)

        # ─── VIDEO modu: kesin artan timestamp gerekir ───
        zaman_damgasi_ms = int(time.time() * 1000)
        tespit_sonucu = self.detector.detect_for_video(
            mp_image, zaman_damgasi_ms
        )

        sinir_kutulari = []
        if tespit_sonucu.detections:
            for tespit in tespit_sonucu.detections:
                kutu = tespit.bounding_box
                sinir_kutulari.append({
                    "x": int(kutu.origin_x / oran),
                    "y": int(kutu.origin_y / oran),
                    "w": int(kutu.width / oran),
                    "h": int(kutu.height / oran),
                })

        return sinir_kutulari

    def tespit_et_ve_kirp(
        self,
        kare: np.ndarray,
        hedef_boyut: int = 640,
        bosluk_orani: float = 0.25,
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
        y_boyut, g_boyut = kare.shape[:2]

        # ─── Onbellek kontrolu ───
        self._kare_sayaci += 1
        if self._onbellekteki_kutular is None or self._kare_sayaci >= self.onbellek_kare_sayisi:
            self._onbellekteki_kutular = self._yuzleri_tespit_et(kare)
            self._kare_sayaci = 0

        kutular = self._onbellekteki_kutular
        if not kutular:
            return []

        yuzler = []

        for kutu in kutular:
            x_min, y_min = kutu["x"], kutu["y"]
            kutu_g, kutu_y = kutu["w"], kutu["h"]

            # ─── Kare padding ───
            merkez_x = x_min + kutu_g // 2
            merkez_y = y_min + kutu_y // 2
            kenar = int(max(kutu_g, kutu_y) * (1 + bosluk_orani))

            # ─── Sinir kontrolu ile kirpma ───
            kirp_x1 = max(0, merkez_x - kenar // 2)
            kirp_y1 = max(0, merkez_y - kenar // 2)
            kirp_x2 = min(g_boyut, merkez_x + kenar // 2)
            kirp_y2 = min(y_boyut, merkez_y + kenar // 2)

            yuz_kirpma = kare[kirp_y1:kirp_y2, kirp_x1:kirp_x2]

            if yuz_kirpma.size == 0:
                continue

            # ─── Resize ───
            yuz_yeniden_boyutlu = cv2.resize(
                yuz_kirpma,
                (hedef_boyut, hedef_boyut),
                interpolation=cv2.INTER_LINEAR,
            )

            yuzler.append((yuz_yeniden_boyutlu, kutu))

        return yuzler

    def onbellegi_sifirla(self):
        """Yeni stream baslatildiginda onbellegi sifirla."""
        self._onbellekteki_kutular = None
        self._kare_sayaci = 0

    def __del__(self):
        """Temizlik."""
        if hasattr(self, "detector"):
            self.detector.close()

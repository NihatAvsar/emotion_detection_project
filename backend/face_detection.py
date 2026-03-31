"""
MediaPipe Yüz Tespiti Modülü (Optimize Edilmiş)
=================================================
Performans optimizasyonları:

1. VIDEO modu — MediaPipe'ın video stream'i için optimize modeli
2. Yüz cache — Her frame'de tespit çalıştırmak yerine,
   son tespiti N frame boyunca yeniden kullanır
3. Downscale — Tespit öncesi görüntüyü küçülterek hız kazanır
4. Verimli renk dönüşümü — gereksiz kopyalamadan kaçınır

Not: MediaPipe 0.10.20+ Tasks API kullanır.
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
    Optimize edilmiş MediaPipe Tasks API yüz tespit sınıfı.

    Özellikler:
    - VIDEO modu (stream optimize)
    - Face cache (her N frame'de bir tespit)
    - Downscale ile hızlı tespit
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        cache_frames: int = 3,
        detection_downscale: float = 0.5,
    ):
        """
        Args:
            min_detection_confidence: Minimum yüz tespit güven eşiği
            cache_frames: Kaç frame boyunca eski tespit sonucunu kullanacak
            detection_downscale: Tespit öncesi görüntü küçültme oranı (0.5 = yarı boyut)
        """
        # ─── BlazeFace model dosyasını bul ───
        model_filename = "blaze_face_short_range.tflite"
        model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), model_filename
        )

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"MediaPipe model dosyası bulunamadı: {model_path}\n"
                f"Lütfen '{model_filename}' dosyasını backend/ dizinine koyun."
            )

        # ─── VIDEO modu ile FaceDetector oluştur ───
        # VIDEO modu, ardışık frame'ler arasında temporal tutarlılık sağlar
        # ve stream'ler için optimize edilmiştir
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_detection_confidence=min_detection_confidence,
        )
        self.detector = vision.FaceDetector.create_from_options(options)

        # ─── Cache ayarları ───
        self.cache_frames = cache_frames          # Her N frame'de bir tespit
        self._frame_counter = 0                   # Frame sayacı
        self._cached_bboxes = None                # Cache'lenmiş bbox'lar
        self._detection_downscale = detection_downscale  # Küçültme oranı
        # VIDEO modu için gerçek zamanlı timestamp kullanıyoruz
        # (monotonically increasing — oturumlar arası sorun yaşanmaz)

        print(
            f"[FaceDetector] Başlatıldı — VIDEO modu, "
            f"cache:{cache_frames} frame, downscale:{detection_downscale}"
        )

    def _detect_faces(self, frame: np.ndarray) -> list:
        """
        MediaPipe ile yüz tespiti yap (downscale + VIDEO modu).

        Returns:
            list of dict: [ {"x": int, "y": int, "w": int, "h": int}, ... ]
        """
        h, w = frame.shape[:2]

        # ─── Downscale: tespit için küçültülmüş frame ───
        scale = self._detection_downscale
        if scale < 1.0:
            small_frame = cv2.resize(
                frame,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_LINEAR,  # Küçültmede INTER_LINEAR yeterli
            )
        else:
            small_frame = frame
            scale = 1.0

        # ─── BGR → RGB ───
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # ─── MediaPipe Image ─── (numpy doğrudan — kopyalama yok)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # ─── VIDEO modu: kesin artan (monotonically increasing) timestamp gerekir ───
        # Sayaç yerine gerçek zaman kullanıyoruz — böylece reset_cache()
        # sonrasında da timestamp asla geriye gitmez.
        timestamp_ms = int(time.time() * 1000)
        detection_result = self.detector.detect_for_video(
            mp_image, timestamp_ms
        )

        bboxes = []
        if detection_result.detections:
            for detection in detection_result.detections:
                bbox = detection.bounding_box
                # Downscale oranını geri uygula → orijinal koordinatlar
                bboxes.append({
                    "x": int(bbox.origin_x / scale),
                    "y": int(bbox.origin_y / scale),
                    "w": int(bbox.width / scale),
                    "h": int(bbox.height / scale),
                })

        return bboxes

    def detect_and_crop(
        self,
        frame: np.ndarray,
        target_size: int = 640,
        padding_ratio: float = 0.25,
    ) -> list:
        """
        Görüntüdeki yüzleri tespit et, kırp ve yeniden boyutlandır.

        Optimizasyon: Her frame'de tespit çalıştırmaz,
        cache_frames kadar eski sonucu yeniden kullanır.

        Args:
            frame: BGR formatında OpenCV görüntüsü
            target_size: Hedef çıktı boyutu (kare)
            padding_ratio: Yüz etrafına eklenecek boşluk oranı

        Returns:
            list: (cropped_face, bbox_dict) ikilisi — boşsa []
        """
        h, w = frame.shape[:2]

        # ─── Cache kontrolü: Her N frame'de bir tespit çalıştır ───
        self._frame_counter += 1
        if self._cached_bboxes is None or self._frame_counter >= self.cache_frames:
            self._cached_bboxes = self._detect_faces(frame)
            self._frame_counter = 0

        bboxes = self._cached_bboxes
        if not bboxes:
            return []

        faces = []

        for bbox in bboxes:
            x_min, y_min = bbox["x"], bbox["y"]
            box_w, box_h = bbox["w"], bbox["h"]

            # ─── Kare padding ───
            center_x = x_min + box_w // 2
            center_y = y_min + box_h // 2
            side = int(max(box_w, box_h) * (1 + padding_ratio))

            # ─── Sınır kontrolü ile kırpma ───
            crop_x1 = max(0, center_x - side // 2)
            crop_y1 = max(0, center_y - side // 2)
            crop_x2 = min(w, center_x + side // 2)
            crop_y2 = min(h, center_y + side // 2)

            face_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

            if face_crop.size == 0:
                continue

            # ─── Resize (INTER_LINEAR — küçültmede INTER_AREA'dan hızlı) ───
            face_resized = cv2.resize(
                face_crop,
                (target_size, target_size),
                interpolation=cv2.INTER_LINEAR,
            )

            faces.append((face_resized, bbox))

        return faces

    def reset_cache(self):
        """Yeni stream başlatıldığında cache'i sıfırla."""
        self._cached_bboxes = None
        self._frame_counter = 0
        # NOT: timestamp artık time.time() tabanlı — sıfırlama gerekmiyor

    def __del__(self):
        """Temizlik."""
        if hasattr(self, "detector"):
            self.detector.close()

"""
Gerçek Zamanlı Yüz Duygu Analizi — FastAPI Backend
====================================================
Bu sunucu:
1. ConvNeXt Tiny modelini yükler
2. MediaPipe ile yüz tespiti yapar
3. WebSocket ve REST API üzerinden duygu tahmini sunar

Endpoint'ler:
- WebSocket: ws://localhost:8000/ws/predict
- REST POST: http://localhost:8000/api/predict
- Health:    http://localhost:8000/health

Çalıştırma:
    python main.py
"""

import base64
import json
import time
import os
import asyncio
from contextlib import asynccontextmanager
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from model import EmotionPredictor
from face_detection import FaceDetector
from model_registry import ModelRegistry

# ─────────────────────────────────────────────
# Global model ve detector referansları
# ─────────────────────────────────────────────
emotion_predictor: EmotionPredictor = None
face_detector: FaceDetector = None
model_registry: ModelRegistry = None


# ─────────────────────────────────────────────
# Lifespan: Startup & Shutdown
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Sunucu başlatılırken model registry ve face detector'ı yükle.
    Sunucu kapanırken temizlik yap.
    """
    global emotion_predictor, face_detector, model_registry

    print("=" * 60)
    print("  Duygu Analizi Servisi Başlatılıyor...")
    print("=" * 60)

    # ─── Model Registry: backend/models dizinini tara ───
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    model_registry = ModelRegistry(models_dir)
    model_registry.scan()

    # ─── Varsayılan modeli yükle (eski tek-model uyumluluğu) ───
    model_filename = "convnext_tiny_best.pth"
    search_dirs = [
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
        os.getcwd(),
    ]
    model_path = None
    for d in search_dirs:
        candidate = os.path.abspath(os.path.join(d, model_filename))
        if os.path.exists(candidate):
            model_path = candidate
            break
    if model_path:
        emotion_predictor = EmotionPredictor(model_path)

    # ─── MediaPipe Face Detector'ı başlat ───
    face_detector = FaceDetector(min_detection_confidence=0.5)

    print("=" * 60)
    print("  ✅ Servis hazır — http://localhost:8000")
    print("=" * 60)

    yield

    # ─── Shutdown: temizlik ───
    print("[Shutdown] Servis kapatılıyor...")


# ─────────────────────────────────────────────
# FastAPI Uygulaması
# ─────────────────────────────────────────────
app = FastAPI(
    title="Duygu Analizi API",
    description="Gerçek zamanlı yüz duygu tanıma servisi",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ayarları (frontend erişimi için) ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme ortamı — production'da sınırlandır
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Yardımcı: Base64 → OpenCV Frame
# ─────────────────────────────────────────────
def decode_base64_image(base64_str: str) -> np.ndarray:
    """
    Base64 kodlanmış görüntüyü OpenCV (BGR) numpy array'e çevir.

    Args:
        base64_str: data:image/... prefix'li veya düz base64 string

    Returns:
        np.ndarray: BGR formatında OpenCV görüntüsü
    """
    # ─── Data URL prefix'ini kaldır ───
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]

    # ─── Base64 → bytes → numpy array → OpenCV image ───
    img_bytes = base64.b64decode(base64_str)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    return frame


# ─────────────────────────────────────────────
# Ortak inference pipeline
# ─────────────────────────────────────────────
def process_frame(frame: np.ndarray, model_name: str = None) -> dict:
    """
    Tek bir frame üzerinde tam inference pipeline çalıştır.

    İşlem hattı:
    1. MediaPipe ile yüz tespit et
    2. Yüz bölgesini kırp + resize
    3. Seçilen model ile duygu tahmini yap

    Args:
        frame: BGR formatında OpenCV görüntüsü
        model_name: Kullanılacak model adı (None ise varsayılan)

    Returns:
        dict: API yanıtı (yüz bulunduysa tahmin, yoksa boş)
    """
    # ─── Modeli belirle ───
    if model_name and model_registry:
        try:
            predictor = model_registry.get_model(model_name)
        except KeyError as e:
            return {"success": False, "message": str(e), "faces": []}
    else:
        predictor = emotion_predictor

    if predictor is None:
        return {"success": False, "message": "Model yüklenmemiş", "faces": []}

    h, w = frame.shape[:2]

    # ─── Yüz tespiti ───
    faces = face_detector.detect_and_crop(frame)

    if not faces:
        return {
            "success": False,
            "message": "Yüz tespit edilemedi",
            "faces": [],
        }

    results = []

    for face_img, bbox in faces:
        # ─── Duygu tahmini ───
        prediction = predictor.predict(face_img)

        # ─── Bounding box'ı normalize et (0-1 arası, frontend uyumlu) ───
        results.append({
            "emotion": prediction["emotion"],
            "emotion_tr": prediction["emotion_tr"],
            "emoji": prediction["emoji"],
            "confidence": prediction["confidence"],
            "probabilities": prediction["probabilities"],
            "face_bbox": {
                "x": bbox["x"] / w,
                "y": bbox["y"] / h,
                "w": bbox["w"] / w,
                "h": bbox["h"] / h,
            },
        })

    # ─── Yüzleri soldan sağa sırala (ekrandaki konuma göre tutarlı sıra) ───
    results.sort(key=lambda f: f["face_bbox"]["x"])

    # ─── Her yüze face_id ata (1'den başlayarak, soldan sağa) ───
    for idx, face in enumerate(results):
        face["face_id"] = idx + 1

    return {
        "success": True,
        "face_count": len(results),
        "faces": results,
        "model_used": model_name or "default",
        "timestamp": time.time(),
    }


# ─────────────────────────────────────────────
# WebSocket Endpoint — Gerçek Zamanlı Stream
# ─────────────────────────────────────────────
@app.websocket("/ws/predict")
async def websocket_predict(websocket: WebSocket):
    """
    WebSocket üzerinden gerçek zamanlı duygu tahmini.

    Protokol:
    1. Client base64-encoded frame gönderir
    2. Server JSON yanıt döndürür
    3. Back-pressure: client yanıt gelene kadar yeni frame göndermez

    Mesaj formatı (gelen):  base64 encoded JPEG
    Mesaj formatı (giden):  JSON { success, faces: [...], timestamp }
    """
    await websocket.accept()
    print("[WebSocket] Yeni bağlantı kabul edildi")

    # ─── Stream başlangıcında face cache sıfırla (anında tespit) ───
    face_detector.reset_cache()

    frame_count = 0
    skip_interval = 2        # Her N frame'de bir inference yap
    last_result = None       # Son inference sonucu (skip edilenlerde döndürülür)

    try:
        while True:
            # ─── Client'tan mesaj al (JSON veya base64) ───
            data = await websocket.receive_text()

            # ─── JSON formatı: { "model": "resnet18", "frame": "base64..." } ───
            model_name = None
            frame_data = data

            try:
                msg = json.loads(data)
                if isinstance(msg, dict):
                    model_name = msg.get("model", None)
                    frame_data = msg.get("frame", data)
            except (json.JSONDecodeError, TypeError):
                pass

            frame_count += 1

            # ─── Frame skipping: Her skip_interval'da bir inference ───
            # Atlanan frame'lerde son sonucu döndür (düşük latency)
            if last_result is not None and (frame_count % skip_interval) != 0:
                await websocket.send_json(last_result)
                continue

            # ─── Base64 → OpenCV frame ───
            frame = decode_base64_image(frame_data)
            if frame is None:
                await websocket.send_json({
                    "success": False,
                    "message": "Geçersiz görüntü verisi",
                })
                continue

            # ─── Inference pipeline (thread pool — event loop bloklamaz) ───
            result = await asyncio.to_thread(
                process_frame, frame, model_name
            )
            last_result = result

            # ─── Sonucu JSON olarak gönder ───
            await websocket.send_json(result)

            if frame_count % 100 == 0:
                print(f"[WebSocket] {frame_count} frame işlendi")

    except WebSocketDisconnect:
        print(f"[WebSocket] Bağlantı kesildi ({frame_count} frame işlendi)")
    except Exception as e:
        print(f"[WebSocket] Hata: {e}")


# ─────────────────────────────────────────────
# REST API Endpoint
# ─────────────────────────────────────────────
class PredictRequest(BaseModel):
    """REST API istek modeli."""
    image: str            # Base64 encoded görüntü
    model: str = None     # Opsiyonel model adı


@app.post("/api/predict")
async def rest_predict(request: PredictRequest):
    """
    REST API üzerinden tekil duygu tahmini.

    Body:
        { "image": "base64_encoded_image_string", "model": "resnet18" }

    Returns:
        JSON: { success, faces: [...], model_used, timestamp }
    """
    frame = decode_base64_image(request.image)
    if frame is None:
        return {"success": False, "message": "Geçersiz görüntü verisi"}

    return process_frame(frame, model_name=request.model)


# ─────────────────────────────────────────────
# Model Listesi Endpoint
# ─────────────────────────────────────────────
@app.get("/models")
async def get_models():
    """
    Mevcut tüm modelleri listele.

    Returns:
        JSON: { models: [ { name, timm_name, input_size, loaded } ] }
    """
    if model_registry is None:
        return {"models": []}

    return {"models": model_registry.list_models()}


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Servis sağlık kontrolü."""
    return {
        "status": "ok",
        "model_loaded": emotion_predictor is not None,
        "detector_loaded": face_detector is not None,
    }


# ─────────────────────────────────────────────
# Sunucu Başlatma
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Production'da reload kapalı (model tekrar yüklenmez)
        log_level="info",
    )

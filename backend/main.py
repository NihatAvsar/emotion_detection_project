"""
Gercek Zamanli Yuz Duygu Analizi — FastAPI Backend
=================================================
Bu sunucu:
1. ConvNeXt Tiny modelini yukler
2. MediaPipe ile yuz tespiti yapar
3. WebSocket ve REST API uzerinden duygu tahmini sunar
4. Takip (tracking) ile ayni kisiyi kareler arasinda esler
5. MySQL veritabanina musteri session ve emotion event kaydi yapar
6. Analytics endpointleri sunar

Endpoint'ler:
- WebSocket: ws://localhost:8000/ws/predict
- REST POST: http://localhost:8000/api/predict
- Models:    http://localhost:8000/models
- Health:    http://localhost:8000/health

Analytics:
- Overview:       http://localhost:8000/analytics/overview
- Hourly Visits:  http://localhost:8000/analytics/hourly-visits
- Recent Sessions:http://localhost:8000/analytics/recent-sessions
- Live:           http://localhost:8000/analytics/live

Calistirma:
    python main.py
"""

import base64
import json
import time
import os
import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, date, time as dt_time, timedelta
from typing import Dict, List, Optional, Tuple

from timezone_utils import istanbul_now

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    BigInteger,
    String,
    Integer,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

from model import EmotionPredictor
from face_detection import FaceDetector
from model_registry import ModelRegistry


# ============================================================
# ENV ve Veritabani Ayarlari
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        f"DATABASE_URL bulunamadi. Lutfen {ENV_PATH} icindeki .env dosyasini kontrol et."
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# SQLAlchemy Modelleri
# ============================================================
class Business(Base):
    __tablename__ = "businesses"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    industry = Column(String(100), nullable=True)
    contact_email = Column(String(150), nullable=True)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=istanbul_now, nullable=False)
    updated_at = Column(DateTime, default=istanbul_now, onupdate=istanbul_now, nullable=False)

    branches = relationship("Branch", back_populates="business")


class Branch(Base):
    __tablename__ = "branches"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    business_id = Column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    address_line = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=istanbul_now, nullable=False)
    updated_at = Column(DateTime, default=istanbul_now, onupdate=istanbul_now, nullable=False)

    business = relationship("Business", back_populates="branches")
    cameras = relationship("Camera", back_populates="branch")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    branch_id = Column(BigInteger, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    camera_name = Column(String(150), nullable=False)
    camera_code = Column(String(100), nullable=False, unique=True)
    location_description = Column(String(255), nullable=True)
    stream_source = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=istanbul_now, nullable=False)
    updated_at = Column(DateTime, default=istanbul_now, onupdate=istanbul_now, nullable=False)

    branch = relationship("Branch", back_populates="cameras")
    sessions = relationship("CustomerSession", back_populates="camera")


class CustomerSession(Base):
    __tablename__ = "customer_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    camera_id = Column(BigInteger, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    tracked_face_id = Column(String(100), nullable=True)
    session_status = Column(String(20), default="active", nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    last_seen_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    dominant_emotion = Column(String(50), nullable=True)
    emotion_distribution = Column(JSON, nullable=True)
    average_confidence = Column(Float, nullable=True)
    total_detections = Column(Integer, default=0, nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=istanbul_now, nullable=False)
    updated_at = Column(DateTime, default=istanbul_now, onupdate=istanbul_now, nullable=False)

    camera = relationship("Camera", back_populates="sessions")
    emotion_events = relationship("EmotionEvent", back_populates="session")


class EmotionEvent(Base):
    __tablename__ = "emotion_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("customer_sessions.id", ondelete="CASCADE"), nullable=False)
    detected_at = Column(DateTime, nullable=False, index=True)
    emotion_label = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    bbox_x = Column(Integer, nullable=True)
    bbox_y = Column(Integer, nullable=True)
    bbox_width = Column(Integer, nullable=True)
    bbox_height = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=istanbul_now, nullable=False)

    session = relationship("CustomerSession", back_populates="emotion_events")


# ============================================================
# Global model ve detector referanslari
# ============================================================
duygu_tahminleyici: EmotionPredictor = None
yuz_tespit_edici: FaceDetector = None
model_kayit_defteri: ModelRegistry = None


# ============================================================
# Yuz Takip Sistemi
# ============================================================
@dataclass
class Track:
    track_id: str
    bbox: dict
    last_seen: datetime


class FaceTracker:
    def __init__(self, iou_threshold: float = 0.35, max_missing_seconds: float = 2.0):
        self.iou_threshold = iou_threshold
        self.max_missing_seconds = max_missing_seconds
        self.tracks_by_camera: Dict[str, Dict[str, Track]] = {}
        self.global_counter = 0

    def _iou(self, box_a: dict, box_b: dict) -> float:
        ax1, ay1 = box_a["x"], box_a["y"]
        ax2, ay2 = ax1 + box_a["width"], ay1 + box_a["height"]

        bx1, by1 = box_b["x"], box_b["y"]
        bx2, by2 = bx1 + box_b["width"], by1 + box_b["height"]

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = box_a["width"] * box_a["height"]
        area_b = box_b["width"] * box_b["height"]
        union_area = area_a + area_b - inter_area

        if union_area <= 0:
            return 0.0

        return inter_area / union_area

    def _cleanup_old_tracks(self, camera_code: str, now: datetime):
        camera_tracks = self.tracks_by_camera.setdefault(camera_code, {})
        silinecekler = []

        for track_id, track in camera_tracks.items():
            yas = (now - track.last_seen).total_seconds()
            if yas > self.max_missing_seconds:
                silinecekler.append(track_id)

        for track_id in silinecekler:
            del camera_tracks[track_id]

    def update(self, camera_code: str, detections: List[dict], now: Optional[datetime] = None) -> List[dict]:
        now = now or istanbul_now()
        self._cleanup_old_tracks(camera_code, now)

        camera_tracks = self.tracks_by_camera.setdefault(camera_code, {})
        unmatched_track_ids = set(camera_tracks.keys())

        results = []

        for det in detections:
            best_track_id = None
            best_iou = 0.0

            for track_id in list(unmatched_track_ids):
                score = self._iou(det["bbox"], camera_tracks[track_id].bbox)
                if score >= self.iou_threshold and score > best_iou:
                    best_iou = score
                    best_track_id = track_id

            if best_track_id is None:
                self.global_counter += 1
                best_track_id = f"{camera_code}_face_{self.global_counter}"
                camera_tracks[best_track_id] = Track(
                    track_id=best_track_id,
                    bbox=det["bbox"],
                    last_seen=now,
                )
            else:
                camera_tracks[best_track_id].bbox = det["bbox"]
                camera_tracks[best_track_id].last_seen = now
                unmatched_track_ids.discard(best_track_id)

            det["tracked_face_id"] = best_track_id
            results.append(det)

        results.sort(key=lambda item: item["bbox"]["x"])
        return results


face_tracker = FaceTracker()


# ============================================================
# Session Servisi
# ============================================================
@dataclass
class ActiveSessionState:
    db_session_id: int
    camera_db_id: int
    tracked_face_id: str
    start_time: datetime
    last_seen_time: datetime
    last_event_saved_at: datetime
    total_detections: int = 0
    confidence_sum: float = 0.0
    emotion_counts: dict = field(default_factory=lambda: defaultdict(int))


class SessionService:
    def __init__(self):
        self.active_sessions: Dict[Tuple[int, str], ActiveSessionState] = {}
        self.session_gap_seconds = 2.0
        self.event_save_interval_seconds = 2.0

    def _build_distribution(self, counts: dict, total: int) -> dict:
        if total == 0:
            return {"counts": {}, "ratios": {}}

        return {
            "counts": dict(counts),
            "ratios": {
                emotion: round(count / total, 4)
                for emotion, count in counts.items()
            },
        }

    def process_detection(
        self,
        db: Session,
        camera_db_id: int,
        tracked_face_id: str,
        emotion_label: str,
        confidence_score: float,
        bbox: dict,
        detected_at: Optional[datetime] = None,
    ):
        detected_at = detected_at or istanbul_now()
        key = (camera_db_id, tracked_face_id)

        if key not in self.active_sessions:
            yeni_session = CustomerSession(
                camera_id=camera_db_id,
                tracked_face_id=tracked_face_id,
                session_status="active",
                start_time=detected_at,
                last_seen_time=detected_at,
                total_detections=0,
            )
            db.add(yeni_session)
            db.commit()
            db.refresh(yeni_session)

            self.active_sessions[key] = ActiveSessionState(
                db_session_id=yeni_session.id,
                camera_db_id=camera_db_id,
                tracked_face_id=tracked_face_id,
                start_time=detected_at,
                last_seen_time=detected_at,
                last_event_saved_at=detected_at,
            )

        state = self.active_sessions[key]
        state.last_seen_time = detected_at
        state.total_detections += 1
        state.confidence_sum += confidence_score
        state.emotion_counts[emotion_label] += 1

        event_kaydet = (
            (detected_at - state.last_event_saved_at).total_seconds()
            >= self.event_save_interval_seconds
        )

        if event_kaydet:
            event = EmotionEvent(
                session_id=state.db_session_id,
                detected_at=detected_at,
                emotion_label=emotion_label,
                confidence_score=confidence_score,
                bbox_x=bbox.get("x"),
                bbox_y=bbox.get("y"),
                bbox_width=bbox.get("width"),
                bbox_height=bbox.get("height"),
            )
            db.add(event)

            session_row = db.get(CustomerSession, state.db_session_id)
            if session_row:
                session_row.last_seen_time = state.last_seen_time
                session_row.total_detections = state.total_detections
                session_row.average_confidence = round(
                    state.confidence_sum / max(state.total_detections, 1), 4
                )

            db.commit()
            state.last_event_saved_at = detected_at

    def close_stale_sessions(self, db: Session, now: Optional[datetime] = None):
        now = now or istanbul_now()
        kapanacaklar = []

        for key, state in self.active_sessions.items():
            idle_seconds = (now - state.last_seen_time).total_seconds()
            if idle_seconds > self.session_gap_seconds:
                kapanacaklar.append(key)

        for key in kapanacaklar:
            state = self.active_sessions[key]

            session_row = db.get(CustomerSession, state.db_session_id)
            if session_row:
                total = state.total_detections
                dominant_emotion = None

                if state.emotion_counts:
                    dominant_emotion = max(state.emotion_counts, key=state.emotion_counts.get)

                session_row.session_status = "closed"
                session_row.end_time = state.last_seen_time
                session_row.last_seen_time = state.last_seen_time
                session_row.duration_seconds = int(
                    (state.last_seen_time - state.start_time).total_seconds()
                )
                session_row.total_detections = total
                session_row.average_confidence = round(
                    state.confidence_sum / max(total, 1), 4
                )
                session_row.dominant_emotion = dominant_emotion
                session_row.emotion_distribution = self._build_distribution(
                    state.emotion_counts,
                    total,
                )

                db.commit()

            del self.active_sessions[key]

    def get_active_session_count(self, camera_db_id: Optional[int] = None) -> int:
        if camera_db_id is None:
            return len(self.active_sessions)

        return sum(
            1
            for (cam_id, _), _state in self.active_sessions.items()
            if cam_id == camera_db_id
        )

    def get_live_sessions(self, camera_db_id: Optional[int] = None) -> List[dict]:
        sonuc = []

        for (cam_id, tracked_face_id), state in self.active_sessions.items():
            if camera_db_id is not None and cam_id != camera_db_id:
                continue

            dominant_emotion = None
            if state.emotion_counts:
                dominant_emotion = max(state.emotion_counts, key=state.emotion_counts.get)

            sonuc.append({
                "camera_id": cam_id,
                "tracked_face_id": tracked_face_id,
                "start_time": state.start_time.isoformat(),
                "last_seen_time": state.last_seen_time.isoformat(),
                "total_detections": state.total_detections,
                "average_confidence": round(
                    state.confidence_sum / max(state.total_detections, 1), 4
                ),
                "dominant_emotion": dominant_emotion,
            })

        return sonuc


session_service = SessionService()


# ============================================================
# Veritabani Yardimcilari
# ============================================================
def varsayilan_kurulumu_hazirla():
    """
    Tablolari olusturur ve en az bir kamera kaydi yoksa varsayilan bir kayit ekler.
    """
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        kamera = db.query(Camera).filter(Camera.camera_code == "CAM001").first()
        if kamera:
            return

        business = db.query(Business).first()
        if not business:
            business = Business(
                name="Ornek Isletme",
                industry="Perakende",
                contact_email="ornek@isletme.com",
            )
            db.add(business)
            db.commit()
            db.refresh(business)

        branch = db.query(Branch).first()
        if not branch:
            branch = Branch(
                business_id=business.id,
                name="Merkez Sube",
                city="Kayseri",
                district="Merkez",
                address_line="Ornek Adres",
            )
            db.add(branch)
            db.commit()
            db.refresh(branch)

        kamera = Camera(
            branch_id=branch.id,
            camera_name="Giris Kamerasi",
            camera_code="CAM001",
            location_description="Varsayilan kamera",
            stream_source="webcam_0",
        )
        db.add(kamera)
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[Veritabani] Varsayilan kurulum hatasi: {e}")
    finally:
        db.close()


# ============================================================
# Lifespan: Startup & Shutdown
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Sunucu baslatilirken:
    - veritabanini hazirla
    - model registry'yi tara
    - varsayilan modeli yukle
    - yuz detector'u baslat

    Sunucu kapanirken temizlik yap.
    """
    global duygu_tahminleyici, yuz_tespit_edici, model_kayit_defteri

    print("=" * 60)
    print("  Duygu Analizi Servisi Baslatiliyor...")
    print("=" * 60)

    varsayilan_kurulumu_hazirla()

    modeller_dizini = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    model_kayit_defteri = ModelRegistry(modeller_dizini)
    model_kayit_defteri.tara()

    model_dosya_adi = "convnext_tiny_best.pth"
    arama_dizinleri = [
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
        os.getcwd(),
    ]

    model_yolu = None
    for dizin in arama_dizinleri:
        aday_yol = os.path.abspath(os.path.join(dizin, model_dosya_adi))
        if os.path.exists(aday_yol):
            model_yolu = aday_yol
            break

    if model_yolu:
        duygu_tahminleyici = EmotionPredictor(model_yolu)
    else:
        print("[Startup] Uyari: Varsayilan model dosyasi bulunamadi.")

    yuz_tespit_edici = FaceDetector(min_tespit_guveni=0.5)

    print("=" * 60)
    print("  [OK] Servis hazir -> http://localhost:8000")
    print("=" * 60)

    yield

    print("[Shutdown] Servis kapatiliyor...")


# ============================================================
# FastAPI Uygulamasi
# ============================================================
app = FastAPI(
    title="Duygu Analizi API",
    description="Gercek zamanli yuz duygu tanima servisi",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Yardimci: Base64 → OpenCV Frame
# ============================================================
def base64_goruntu_coz(base64_metni: str) -> np.ndarray:
    if "," in base64_metni:
        base64_metni = base64_metni.split(",")[1]

    goruntu_baytlari = base64.b64decode(base64_metni)
    goruntu_dizisi = np.frombuffer(goruntu_baytlari, dtype=np.uint8)
    kare = cv2.imdecode(goruntu_dizisi, cv2.IMREAD_COLOR)

    return kare


# ============================================================
# Ortak inference pipeline
# ============================================================
def kare_isle(kare: np.ndarray, model_adi: str = None) -> dict:
    if model_adi and model_kayit_defteri:
        try:
            tahminleyici = model_kayit_defteri.model_getir(model_adi)
        except KeyError as e:
            return {"success": False, "message": str(e), "faces": []}
    else:
        tahminleyici = duygu_tahminleyici

    if tahminleyici is None:
        return {"success": False, "message": "Model yuklenmemis", "faces": []}

    y_boyut, g_boyut = kare.shape[:2]

    yuzler = yuz_tespit_edici.tespit_et_ve_kirp(kare)

    if not yuzler:
        return {
            "success": False,
            "message": "Yuz tespit edilemedi",
            "faces": [],
        }

    sonuclar = []

    for yuz_goruntusu, kutu in yuzler:
        tahmin = tahminleyici.predict(yuz_goruntusu)

        sonuclar.append({
            "emotion": tahmin["emotion"],
            "emotion_tr": tahmin["emotion_tr"],
            "emoji": tahmin["emoji"],
            "confidence": float(tahmin["confidence"]),
            "probabilities": tahmin["probabilities"],
            "face_bbox": {
                "x": kutu["x"] / g_boyut,
                "y": kutu["y"] / y_boyut,
                "w": kutu["w"] / g_boyut,
                "h": kutu["h"] / y_boyut,
            },
            "face_bbox_px": {
                "x": int(kutu["x"]),
                "y": int(kutu["y"]),
                "w": int(kutu["w"]),
                "h": int(kutu["h"]),
            },
        })

    sonuclar.sort(key=lambda f: f["face_bbox"]["x"])

    for idx, yuz in enumerate(sonuclar):
        yuz["face_id"] = idx + 1

    return {
        "success": True,
        "face_count": len(sonuclar),
        "faces": sonuclar,
        "model_used": model_adi or "default",
        "timestamp": time.time(),
    }


def takip_ve_oturum_guncelle(
    api_sonucu: dict,
    camera_code: str,
    db: Optional[Session] = None,
) -> dict:
    if not api_sonucu.get("success") or not api_sonucu.get("faces"):
        if db is not None:
            session_service.close_stale_sessions(db=db, now=istanbul_now())
        return api_sonucu

    simdi = istanbul_now()

    takip_girdileri = []
    for yuz in api_sonucu["faces"]:
        bbox_px = yuz["face_bbox_px"]
        takip_girdileri.append({
            "bbox": {
                "x": bbox_px["x"],
                "y": bbox_px["y"],
                "width": bbox_px["w"],
                "height": bbox_px["h"],
            },
            "emotion_label": yuz["emotion"],
            "confidence_score": float(yuz["confidence"]),
        })

    takip_sonuclari = face_tracker.update(
        camera_code=camera_code,
        detections=takip_girdileri,
        now=simdi,
    )

    for yuz, takip in zip(api_sonucu["faces"], takip_sonuclari):
        yuz["tracked_face_id"] = takip["tracked_face_id"]

    if db is not None:
        kamera = db.query(Camera).filter(Camera.camera_code == camera_code).first()

        if kamera is not None:
            for yuz in api_sonucu["faces"]:
                bbox_px = yuz["face_bbox_px"]

                session_service.process_detection(
                    db=db,
                    camera_db_id=kamera.id,
                    tracked_face_id=yuz["tracked_face_id"],
                    emotion_label=yuz["emotion"],
                    confidence_score=float(yuz["confidence"]),
                    bbox={
                        "x": bbox_px["x"],
                        "y": bbox_px["y"],
                        "width": bbox_px["w"],
                        "height": bbox_px["h"],
                    },
                    detected_at=simdi,
                )

            session_service.close_stale_sessions(db=db, now=simdi)
            api_sonucu["active_customer_count"] = session_service.get_active_session_count(kamera.id)
        else:
            api_sonucu["database_warning"] = f"{camera_code} kodlu kamera veritabaninda bulunamadi."

    for yuz in api_sonucu["faces"]:
        yuz.pop("face_bbox_px", None)

    return api_sonucu


# ============================================================
# WebSocket Endpoint — Gercek Zamanli Stream
# ============================================================
@app.websocket("/ws/predict")
async def websocket_tahmin(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Yeni baglanti kabul edildi")

    yuz_tespit_edici.onbellegi_sifirla()

    kare_sayaci = 0
    atlama_araligi = 2
    son_sonuc = None

    db = SessionLocal()

    try:
        while True:
            veri = await websocket.receive_text()

            model_adi = None
            camera_code = "CAM001"
            kare_verisi = veri

            try:
                mesaj = json.loads(veri)
                if isinstance(mesaj, dict):
                    model_adi = mesaj.get("model", None)
                    camera_code = mesaj.get("camera_code", "CAM001")
                    kare_verisi = mesaj.get("frame", veri)
            except (json.JSONDecodeError, TypeError):
                pass

            kare_sayaci += 1

            if son_sonuc is not None and (kare_sayaci % atlama_araligi) != 0:
                await websocket.send_json(son_sonuc)
                continue

            kare = base64_goruntu_coz(kare_verisi)
            if kare is None:
                await websocket.send_json({
                    "success": False,
                    "message": "Gecersiz goruntu verisi",
                })
                continue

            sonuc = await asyncio.to_thread(kare_isle, kare, model_adi)
            sonuc = takip_ve_oturum_guncelle(
                api_sonucu=sonuc,
                camera_code=camera_code,
                db=db,
            )

            son_sonuc = sonuc
            await websocket.send_json(sonuc)

            if kare_sayaci % 100 == 0:
                print(f"[WebSocket] {kare_sayaci} kare islendi")

    except WebSocketDisconnect:
        print(f"[WebSocket] Baglanti kesildi ({kare_sayaci} kare islendi)")
    except Exception as e:
        print(f"[WebSocket] Hata: {e}")
    finally:
        try:
            session_service.close_stale_sessions(db=db, now=istanbul_now() + timedelta(seconds=10))
        except Exception:
            pass
        db.close()


# ============================================================
# REST API Endpoint
# ============================================================
class PredictRequest(BaseModel):
    image: str
    model: str = None
    camera_code: str = "CAM001"


@app.post("/api/predict")
async def rest_tahmin(request: PredictRequest, db: Session = Depends(get_db)):
    kare = base64_goruntu_coz(request.image)
    if kare is None:
        return {"success": False, "message": "Gecersiz goruntu verisi"}

    sonuc = kare_isle(kare, model_adi=request.model)
    sonuc = takip_ve_oturum_guncelle(
        api_sonucu=sonuc,
        camera_code=request.camera_code,
        db=db,
    )

    return sonuc


# ============================================================
# Model Listesi Endpoint
# ============================================================
@app.get("/models")
async def modelleri_getir():
    if model_kayit_defteri is None:
        return {"models": []}

    return {"models": model_kayit_defteri.modelleri_listele()}


# ============================================================
# Analytics Endpointleri
# ============================================================
@app.get("/analytics/overview")
def analytics_overview(
    target_date: Optional[date] = Query(None),
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    gun = target_date or istanbul_now().date()
    baslangic = datetime.combine(gun, dt_time.min)
    bitis = baslangic + timedelta(days=1)

    base_query = db.query(CustomerSession).filter(
        CustomerSession.start_time >= baslangic,
        CustomerSession.start_time < bitis,
    )

    if camera_id is not None:
        base_query = base_query.filter(CustomerSession.camera_id == camera_id)

    total_customers = base_query.count()

    emotion_rows = (
        base_query.with_entities(
            CustomerSession.dominant_emotion,
            func.count(CustomerSession.id)
        )
        .group_by(CustomerSession.dominant_emotion)
        .all()
    )

    emotion_distribution = {
        (emotion or "unknown"): count
        for emotion, count in emotion_rows
    }

    avg_duration = (
        base_query.with_entities(func.avg(CustomerSession.duration_seconds))
        .scalar()
    )

    recent_rows = (
        base_query.order_by(CustomerSession.start_time.desc())
        .limit(10)
        .all()
    )

    recent_sessions = []
    for row in recent_rows:
        recent_sessions.append({
            "id": row.id,
            "tracked_face_id": row.tracked_face_id,
            "camera_id": row.camera_id,
            "start_time": row.start_time.isoformat() if row.start_time else None,
            "end_time": row.end_time.isoformat() if row.end_time else None,
            "duration_seconds": row.duration_seconds,
            "dominant_emotion": row.dominant_emotion,
            "average_confidence": row.average_confidence,
            "total_detections": row.total_detections,
            "session_status": row.session_status,
        })

    return {
        "date": gun.isoformat(),
        "total_customers": total_customers,
        "active_customers": session_service.get_active_session_count(camera_id),
        "emotion_distribution": emotion_distribution,
        "average_session_duration": round(avg_duration or 0, 2),
        "recent_sessions": recent_sessions,
    }


@app.get("/analytics/hourly-visits")
def hourly_visits(
    target_date: Optional[date] = Query(None),
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    gun = target_date or istanbul_now().date()
    baslangic = datetime.combine(gun, dt_time.min)
    bitis = baslangic + timedelta(days=1)

    query = db.query(
        func.hour(CustomerSession.start_time).label("hour"),
        func.count(CustomerSession.id).label("count")
    ).filter(
        CustomerSession.start_time >= baslangic,
        CustomerSession.start_time < bitis,
    )

    if camera_id is not None:
        query = query.filter(CustomerSession.camera_id == camera_id)

    rows = query.group_by(func.hour(CustomerSession.start_time)).all()

    result = {hour: 0 for hour in range(24)}
    for hour, count in rows:
        result[int(hour)] = count

    return {
        "date": gun.isoformat(),
        "hourly_visits": result,
    }


@app.get("/analytics/recent-sessions")
def recent_sessions(
    limit: int = Query(20, ge=1, le=100),
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(CustomerSession)

    if camera_id is not None:
        query = query.filter(CustomerSession.camera_id == camera_id)

    rows = query.order_by(CustomerSession.start_time.desc()).limit(limit).all()

    return [
        {
            "id": row.id,
            "tracked_face_id": row.tracked_face_id,
            "camera_id": row.camera_id,
            "start_time": row.start_time.isoformat() if row.start_time else None,
            "end_time": row.end_time.isoformat() if row.end_time else None,
            "duration_seconds": row.duration_seconds,
            "dominant_emotion": row.dominant_emotion,
            "average_confidence": row.average_confidence,
            "total_detections": row.total_detections,
            "session_status": row.session_status,
        }
        for row in rows
    ]


@app.get("/analytics/live")
def analytics_live(
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    session_service.close_stale_sessions(db=db, now=istanbul_now())

    return {
        "active_customer_count": session_service.get_active_session_count(camera_id),
        "active_sessions": session_service.get_live_sessions(camera_id),
    }


@app.get("/analytics/compare-yesterday")
def analytics_compare_yesterday(
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Dunku ozet verilerini dondurur.
    Frontend bugun vs dun karsilastirmasi yapmak icin kullanir.
    """
    dun = (istanbul_now() - timedelta(days=1)).date()
    baslangic = datetime.combine(dun, dt_time.min)
    bitis = baslangic + timedelta(days=1)

    base_query = db.query(CustomerSession).filter(
        CustomerSession.start_time >= baslangic,
        CustomerSession.start_time < bitis,
    )

    if camera_id is not None:
        base_query = base_query.filter(CustomerSession.camera_id == camera_id)

    total_customers = base_query.count()

    emotion_rows = (
        base_query.with_entities(
            CustomerSession.dominant_emotion,
            func.count(CustomerSession.id)
        )
        .group_by(CustomerSession.dominant_emotion)
        .all()
    )

    emotion_distribution = {
        (emotion or "unknown"): count
        for emotion, count in emotion_rows
    }

    avg_duration = (
        base_query.with_entities(func.avg(CustomerSession.duration_seconds))
        .scalar()
    )

    avg_confidence = (
        base_query.with_entities(func.avg(CustomerSession.average_confidence))
        .scalar()
    )

    return {
        "date": dun.isoformat(),
        "total_customers": total_customers,
        "emotion_distribution": emotion_distribution,
        "average_session_duration": round(avg_duration or 0, 2),
        "average_confidence": round(avg_confidence or 0, 4),
    }


@app.get("/analytics/emotion-hourly-trend")
def analytics_emotion_hourly_trend(
    target_date: Optional[date] = Query(None),
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Saatlik duygu kirilimi.
    Her saat icin hangi duygunun kac kez goruldugunu dondurur.
    """
    gun = target_date or istanbul_now().date()
    baslangic = datetime.combine(gun, dt_time.min)
    bitis = baslangic + timedelta(days=1)

    query = db.query(
        func.hour(EmotionEvent.detected_at).label("hour"),
        EmotionEvent.emotion_label,
        func.count(EmotionEvent.id).label("count"),
    ).join(
        CustomerSession,
        EmotionEvent.session_id == CustomerSession.id,
    ).filter(
        EmotionEvent.detected_at >= baslangic,
        EmotionEvent.detected_at < bitis,
    )

    if camera_id is not None:
        query = query.filter(CustomerSession.camera_id == camera_id)

    rows = query.group_by(
        func.hour(EmotionEvent.detected_at),
        EmotionEvent.emotion_label,
    ).all()

    # Saatlik veriyi { saat: { emotion: count } } formatina cevir
    sonuc = {}
    for hour in range(24):
        sonuc[str(hour)] = {
            "happy": 0, "sad": 0, "angry": 0,
            "surprised": 0, "neutral": 0,
        }

    for hour, emotion, count in rows:
        saat_str = str(int(hour))
        if saat_str in sonuc and emotion in sonuc[saat_str]:
            sonuc[saat_str][emotion] = count

    return {
        "date": gun.isoformat(),
        "hourly_emotions": sonuc,
    }


@app.get("/analytics/filters")
def analytics_filters(db: Session = Depends(get_db)):
    """
    Dashboard filtreleri icin sube ve kamera listelerini dondurur.
    """
    branches = db.query(Branch).filter(Branch.is_active == 1).all()
    cameras = db.query(Camera).filter(Camera.is_active == 1).all()

    return {
        "branches": [
            {
                "id": b.id,
                "name": b.name,
                "city": b.city,
                "district": b.district,
            }
            for b in branches
        ],
        "cameras": [
            {
                "id": c.id,
                "branch_id": c.branch_id,
                "camera_name": c.camera_name,
                "camera_code": c.camera_code,
                "location_description": c.location_description,
            }
            for c in cameras
        ],
    }


# ============================================================
# Health Check
# ============================================================
@app.get("/health")
async def saglik_kontrolu():
    db_ok = True
    db_hata = None

    try:
        db = SessionLocal()
        db.execute(func.now().select() if False else None)
        db.close()
    except Exception as e:
        db_ok = False
        db_hata = str(e)

    return {
        "status": "ok",
        "model_loaded": duygu_tahminleyici is not None,
        "detector_loaded": yuz_tespit_edici is not None,
        "database_loaded": db_ok,
        "database_error": db_hata,
    }


# ============================================================
# Sunucu Baslatma
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
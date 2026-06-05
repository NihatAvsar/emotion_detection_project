from datetime import datetime

from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship

from database import Base
from timezone_utils import istanbul_now


class Business(Base):
    __tablename__ = "businesses"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    industry = Column(String(100), nullable=True)
    contact_email = Column(String(150), nullable=True)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=istanbul_now, nullable=False)
    updated_at = Column(DateTime, default=istanbul_now, onupdate=istanbul_now, nullable=False)

    branches = relationship("Branch", back_populates="business", cascade="all, delete-orphan")
    summaries = relationship("EmotionSummary", back_populates="business")


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
    cameras = relationship("Camera", back_populates="branch", cascade="all, delete-orphan")
    summaries = relationship("EmotionSummary", back_populates="branch")


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
    sessions = relationship("CustomerSession", back_populates="camera", cascade="all, delete-orphan")
    summaries = relationship("EmotionSummary", back_populates="camera")


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
    emotion_events = relationship("EmotionEvent", back_populates="session", cascade="all, delete-orphan")


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


class EmotionSummary(Base):
    __tablename__ = "emotion_summaries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    business_id = Column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(BigInteger, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    camera_id = Column(BigInteger, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    summary_date = Column(DateTime, nullable=False)
    summary_hour = Column(Integer, nullable=True)
    total_sessions = Column(Integer, default=0, nullable=False)
    total_detections = Column(Integer, default=0, nullable=False)
    avg_session_duration = Column(Float, nullable=True)
    avg_confidence = Column(Float, nullable=True)
    dominant_emotion = Column(String(50), nullable=True)
    happy_count = Column(Integer, default=0, nullable=False)
    sad_count = Column(Integer, default=0, nullable=False)
    angry_count = Column(Integer, default=0, nullable=False)
    surprised_count = Column(Integer, default=0, nullable=False)
    neutral_count = Column(Integer, default=0, nullable=False)
    positive_ratio = Column(Float, nullable=True)
    negative_ratio = Column(Float, nullable=True)
    neutral_ratio = Column(Float, nullable=True)
    created_at = Column(DateTime, default=istanbul_now, nullable=False)
    updated_at = Column(DateTime, default=istanbul_now, onupdate=istanbul_now, nullable=False)

    business = relationship("Business", back_populates="summaries")
    branch = relationship("Branch", back_populates="summaries")
    camera = relationship("Camera", back_populates="summaries")
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Tuple

from sqlalchemy.orm import Session

from models import CustomerSession, EmotionEvent


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
        detected_at: datetime | None = None,
    ):
        detected_at = detected_at or datetime.utcnow()
        key = (camera_db_id, tracked_face_id)

        if key not in self.active_sessions:
            new_session = CustomerSession(
                camera_id=camera_db_id,
                tracked_face_id=tracked_face_id,
                session_status="active",
                start_time=detected_at,
                last_seen_time=detected_at,
                total_detections=0,
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            self.active_sessions[key] = ActiveSessionState(
                db_session_id=new_session.id,
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

        should_save_event = (
            (detected_at - state.last_event_saved_at).total_seconds()
            >= self.event_save_interval_seconds
        )

        if should_save_event:
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

    def close_stale_sessions(self, db: Session, now: datetime | None = None):
        now = now or datetime.utcnow()
        keys_to_close = []

        for key, state in self.active_sessions.items():
            idle_seconds = (now - state.last_seen_time).total_seconds()
            if idle_seconds > self.session_gap_seconds:
                keys_to_close.append(key)

        for key in keys_to_close:
            state = self.active_sessions[key]

            session_row = db.get(CustomerSession, state.db_session_id)
            if session_row:
                total = state.total_detections
                dominant_emotion = None

                if state.emotion_counts:
                    dominant_emotion = max(
                        state.emotion_counts,
                        key=state.emotion_counts.get
                    )

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

    def get_active_session_count(self, camera_db_id: int | None = None) -> int:
        if camera_db_id is None:
            return len(self.active_sessions)

        return sum(
            1
            for (cam_id, _), _state in self.active_sessions.items()
            if cam_id == camera_db_id
        )


session_service = SessionService()
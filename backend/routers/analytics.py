from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import CustomerSession
from services.session_service import session_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def analytics_overview(
    target_date: date | None = Query(None),
    camera_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    day = target_date or datetime.utcnow().date()
    start_dt = datetime.combine(day, time.min)
    end_dt = start_dt + timedelta(days=1)

    base_query = db.query(CustomerSession).filter(
        CustomerSession.start_time >= start_dt,
        CustomerSession.start_time < end_dt,
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
            "start_time": row.start_time.isoformat() if row.start_time else None,
            "end_time": row.end_time.isoformat() if row.end_time else None,
            "duration_seconds": row.duration_seconds,
            "dominant_emotion": row.dominant_emotion,
            "average_confidence": row.average_confidence,
            "total_detections": row.total_detections,
            "session_status": row.session_status,
        })

    return {
        "date": day.isoformat(),
        "total_customers": total_customers,
        "active_customers": session_service.get_active_session_count(camera_id),
        "emotion_distribution": emotion_distribution,
        "average_session_duration": round(avg_duration or 0, 2),
        "recent_sessions": recent_sessions,
    }


@router.get("/hourly-visits")
def hourly_visits(
    target_date: date | None = Query(None),
    camera_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    day = target_date or datetime.utcnow().date()
    start_dt = datetime.combine(day, time.min)
    end_dt = start_dt + timedelta(days=1)

    query = db.query(
        func.hour(CustomerSession.start_time).label("hour"),
        func.count(CustomerSession.id).label("count")
    ).filter(
        CustomerSession.start_time >= start_dt,
        CustomerSession.start_time < end_dt,
    )

    if camera_id is not None:
        query = query.filter(CustomerSession.camera_id == camera_id)

    rows = query.group_by(func.hour(CustomerSession.start_time)).all()

    result = {hour: 0 for hour in range(24)}
    for hour, count in rows:
        result[int(hour)] = count

    return {
        "date": day.isoformat(),
        "hourly_visits": result,
    }


@router.get("/recent-sessions")
def recent_sessions(
    limit: int = Query(20, ge=1, le=100),
    camera_id: int | None = Query(None),
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
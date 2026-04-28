from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


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
        if union_area == 0:
            return 0.0

        return inter_area / union_area

    def _cleanup_old_tracks(self, camera_code: str, now: datetime):
        camera_tracks = self.tracks_by_camera.setdefault(camera_code, {})
        to_delete = []

        for track_id, track in camera_tracks.items():
            age_seconds = (now - track.last_seen).total_seconds()
            if age_seconds > self.max_missing_seconds:
                to_delete.append(track_id)

        for track_id in to_delete:
            del camera_tracks[track_id]

    def update(self, camera_code: str, detections: List[dict], now: datetime | None = None) -> List[dict]:
        now = now or datetime.utcnow()
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
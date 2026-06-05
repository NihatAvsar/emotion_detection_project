from dataclasses import dataclass # Veri sınıfları oluşturmak için kullanılan modül
from datetime import datetime # Zaman damgası ve süre hesaplama işlemleri için kullanılan modül
from typing import Dict, List # Tip ipuçlarında sözlük (Dict) ve liste (List) belirtmek için gerekli modüller

from timezone_utils import istanbul_now # İstanbul saat dilimi yardımcı fonksiyonu


@dataclass # Sadece veri tutma amacı taşıyan yapılar için dataclass dekoratörü
class Track: # Takip edilen her bir yüz nesnesini temsil eden sınıf
    track_id: str # Yüze atanan benzersiz takip kimliği
    bbox: dict # Yüzün konumunu belirten sınırlayıcı kutu (x, y, width, height)
    last_seen: datetime # Yüzün kamera tarafından en son görüldüğü zaman damgası


class FaceTracker: # Kameralardan gelen yüz tespitlerini eşleştirip takip eden ana sınıf
    def __init__(self, iou_threshold: float = 0.35, max_missing_seconds: float = 2.0): # Sınıf başlatıcı fonksiyonu (Kurucu metot)
        self.iou_threshold = iou_threshold # İki kutunun aynı yüz sayılması için gereken minimum kesişim oranı (Eşik değer)
        self.max_missing_seconds = max_missing_seconds # Bir yüzün hafızadan silinmeden önce kameradan uzak kalabileceği maksimum süre
        self.tracks_by_camera: Dict[str, Dict[str, Track]] = {} # Kameralara göre gruplanmış aktif yüz takip nesnelerinin sözlüğü
        self.global_counter = 0 # Yeni yüzlere benzersiz numara vermek için kullanılan genel sayaç

    def _iou(self, box_a: dict, box_b: dict) -> float: # İki sınırlayıcı kutu arasındaki kesişim/birleşim (IoU) oranını hesaplayan metot
        ax1, ay1 = box_a["x"], box_a["y"] # İlk kutunun sol üst köşe koordinatları (X ve Y)
        ax2, ay2 = ax1 + box_a["width"], ay1 + box_a["height"] # İlk kutunun sağ alt köşe koordinatları

        bx1, by1 = box_b["x"], box_b["y"] # İkinci kutunun sol üst köşe koordinatları (X ve Y)
        bx2, by2 = bx1 + box_b["width"], by1 + box_b["height"] # İkinci kutunun sağ alt köşe koordinatları

        inter_x1 = max(ax1, bx1) # Kesişim bölgesinin sol üst X koordinatı
        inter_y1 = max(ay1, by1) # Kesişim bölgesinin sol üst Y koordinatı
        inter_x2 = min(ax2, bx2) # Kesişim bölgesinin sağ alt X koordinatı
        inter_y2 = min(ay2, by2) # Kesişim bölgesinin sağ alt Y koordinatı

        inter_w = max(0, inter_x2 - inter_x1) # Kesişim bölgesinin genişliği (Negatif değerleri engellemek için max 0)
        inter_h = max(0, inter_y2 - inter_y1) # Kesişim bölgesinin yüksekliği (Negatif değerleri engellemek için max 0)
        inter_area = inter_w * inter_h # Kesişim bölgesinin toplam alanı

        area_a = box_a["width"] * box_a["height"] # İlk kutunun toplam alanı
        area_b = box_b["width"] * box_b["height"] # İkinci kutunun toplam alanı

        union_area = area_a + area_b - inter_area # İki kutunun toplam birleşim alanı (Kesişim alanı mükerrer olmasın diye çıkarılır)
        if union_area == 0: # Eğer birleşim alanı sıfırsa (Bölme işleminde sıfıra bölünme hatasını engellemek için kontrol)
            return 0.0 # IoU skorunu doğrudan sıfır olarak döndür

        return inter_area / union_area # Kesişim alanını birleşim alanına bölerek IoU skorunu döndür

    def _cleanup_old_tracks(self, camera_code: str, now: datetime): # Süresi dolmuş, uzun süredir görülmeyen yüzleri hafızadan silen metot
        camera_tracks = self.tracks_by_camera.setdefault(camera_code, {}) # İlgili kameranın takip listesini getir, yoksa boş bir sözlük aç
        to_delete = [] # Silinmesi kararlaştırılan yüz kimliklerinin tutulacağı geçici liste

        for track_id, track in camera_tracks.items(): # Kameradaki tüm aktif yüz takipleri üzerinde döngü başlat
            age_seconds = (now - track.last_seen).total_seconds() # Yüzün son görülme anından bu yana geçen toplam süreyi saniye olarak hesapla
            if age_seconds > self.max_missing_seconds: # Eğer geçen süre izin verilen maksimum kayıp süresinden büyükse
                to_delete.append(track_id) # Bu yüz kimliğini silinecekler listesine ekle

        for track_id in to_delete: # Silinmesi kesinleşen yüz kimlikleri üzerinde döngü başlat
            del camera_tracks[track_id] # Yüz nesnesini ilgili kameranın aktif takip listesinden tamamen kaldır

    def update(self, camera_code: str, detections: List[dict], now: datetime | None = None) -> List[dict]: # Yeni gelen yüz tespitleri ile takip durumunu güncelleyen ana metot
        now = now or istanbul_now() # Eğer zaman damgası dışarıdan verilmediyse İstanbul saatini al
        self._cleanup_old_tracks(camera_code, now) # Tespit işlemlerine başlamadan önce eski/kaybolan yüzleri temizle

        camera_tracks = self.tracks_by_camera.setdefault(camera_code, {}) # İlgili kameranın güncel takip listesini referans al
        unmatched_track_ids = set(camera_tracks.keys()) # Kameradaki tüm aktif takip kimliklerini başlangıçta "eşleşmemiş" olarak kümeye ekle

        results = [] # Takip kimlikleri iliştirilmiş yeni tespit sonuçlarının ekleneceği liste

        for det in detections: # Modelden gelen anlık yüz tespitleri (detections) üzerinde tek tek dön
            best_track_id = None # Mevcut tespit için en iyi eşleşen eski yüzün kimliği (Başlangıçta boş)
            best_iou = 0.0 # Mevcut tespit için yakalanan en yüksek kesişim (IoU) oranı

            for track_id in list(unmatched_track_ids): # Henüz hiçbir yeni tespitle eşleşmemiş eski yüzler üzerinde dön
                score = self._iou(det["bbox"], camera_tracks[track_id].bbox) # Anlık tespit kutusu ile eski yüzün kutusu arasındaki IoU değerini hesapla
                if score >= self.iou_threshold and score > best_iou: # Skor eşik değerden büyükse ve şu ana kadarki en iyi skordan yüksekse
                    best_iou = score # En iyi IoU skorunu güncelle
                    best_track_id = track_id # En iyi eşleşen yüzün kimliğini kaydet

            if best_track_id is None: # Eğer hiçbir eski yüzle yeterli IoU eşleşmesi sağlanamadıysa (Yeni bir yüz geldiyse)
                self.global_counter += 1 # Genel sayacı bir artırarak yeni bir yüz numarası üret
                best_track_id = f"{camera_code}_face_{self.global_counter}" # Kameraya özel, benzersiz yeni bir yüz kimliği stringi oluştur
                camera_tracks[best_track_id] = Track( # Yeni yüzü kameranın aktif takip listesine kaydet
                    track_id=best_track_id, # Üretilen benzersiz yüz kimliği
                    bbox=det["bbox"], # Yüzün güncel konum kutusu
                    last_seen=now, # Görülme zamanı olarak şu anki zamanı ata
                )
            else: # Eğer eski bir yüzle başarılı bir eşleşme sağlandıysa
                camera_tracks[best_track_id].bbox = det["bbox"] # Eski yüzün konum bilgisini yeni tespit kutusuyla güncelle
                camera_tracks[best_track_id].last_seen = now # Eski yüzün son görülme zamanını şu anki zaman olarak güncelle
                unmatched_track_ids.discard(best_track_id) # Eşleşen yüzü "eşleşmemiş eski yüzler" kümesinden çıkar

            det["tracked_face_id"] = best_track_id # Tespit sözlüğünün içine takip edilen yüz kimliğini yeni bir alan olarak ekle
            results.append(det) # Güncellenmiş tespiti sonuç listesine dahil et

        results.sort(key=lambda item: item["bbox"]["x"]) # Sonuç listesini ekranın solundan sağına göre (X koordinatına göre) sırala
        return results # Takip kimlikleri eklenmiş ve sıralanmış tespit listesini döndür


face_tracker = FaceTracker() # Proje genelinde doğrudan kullanılabilecek küresel FaceTracker örneğini (instance) oluştur
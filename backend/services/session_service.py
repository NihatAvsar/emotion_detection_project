from collections import defaultdict # Olmayan anahtarlara varsayılan değer atayan sözlük yapısı
from dataclasses import dataclass, field # Veri sınıfları ve varsayılan alan fabrikaları tanımlamak için modüller
from datetime import datetime # Zaman damgası ve süre ölçümü işlemleri için gerekli modül
from typing import Dict, Tuple # Tip ipuçlarında sözlük (Dict) ve demet (Tuple) yapılarını tanımlamak için modüller

from timezone_utils import istanbul_now # İstanbul saat dilimi yardımcı fonksiyonu

from sqlalchemy.orm import Session # SQLAlchemy veritabanı oturum tipi yönetimi

from models import CustomerSession, EmotionEvent # Müşteri seansı ve duygu olayı veritabanı modelleri


@dataclass # Sadece verileri bir arada tutmak için oluşturulmuş hafif veri sınıfı yapısı
class ActiveSessionState: # Bellekte (RAM) anlık olarak takip edilen aktif seans durum modeli
    db_session_id: int # Veritabanındaki eşleşen müşteri seansı kaydının benzersiz ID'si
    camera_db_id: int # Seansın ait olduğu veritabanındaki kamera ID'si
    tracked_face_id: str # Yüz takip mekanizmasından gelen benzersiz yüz kimlik stringi
    start_time: datetime # Seansın ilk başladığı (yüzün ilk görüldüğü) anın zaman damgası
    last_seen_time: datetime # Yüzün kamera tarafından en son tespit edildiği anın zaman damgası
    last_event_saved_at: datetime # Veritabanına en son ne zaman periyodik duygu olayı kaydedildiğini tutan zaman damgası
    total_detections: int = 0 # Bu seans boyunca yüzün toplam kaç karede tespit edildiği bilgisi
    confidence_sum: float = 0.0 # Ortalama hesaplamak için tespitlerin güvenilirlik skorlarının toplamı
    emotion_counts: dict = field(default_factory=lambda: defaultdict(int)) # Duyguların kaçar kez yakalandığını tutan varsayılan 0 değerli sözlük


class SessionService: # Müşteri seans süreçlerini ve duygu analizi kayıtlarını yöneten ana servis sınıfı
    def __init__(self): # Sınıfın kurucu (başlatıcı) metodu
        self.active_sessions: Dict[Tuple[int, str], ActiveSessionState] = {} # Bellekte aktif seansları (KameraID, YüzID) anahtarıyla tutan sözlük
        self.session_gap_seconds = 2.0 # Bir seansın kapanmış sayılması için gereken maksimum hareketsizlik (görülmeme) süresi
        self.event_save_interval_seconds = 2.0 # Veritabanına yeni bir periyodik duygu olayı (EmotionEvent) yazılması için geçmesi gereken süre

    def _build_distribution(self, counts: dict, total: int) -> dict: # Duygu dağılım adetlerini ve oranlarını hesaplayan yardımcı metot
        if total == 0: # Eğer toplam tespit sayısı sıfırsa (Hatalı durumlarda sıfıra bölünmeyi engellemek için)
            return {"counts": {}, "ratios": {}} # Boş adet ve oran sözlükleri döndür

        return { # Hesaplanan dağılım sözlüğünü döndür
            "counts": dict(counts), # Tespit adetlerini standart Python sözlüğüne çevirerek ekle
            "ratios": { # Her bir duygunun toplam tespitler içerisindeki oranını hesapla
                emotion: round(count / total, 4) # Duygu adedini toplama böl ve virgülden sonra 4 basamağa yuvarla
                for emotion, count in counts.items() # Tüm duygu adetleri üzerinde tek tek dön
            },
        }

    def process_detection( # Kameradan yeni bir yüz ve duygu tespiti geldiğinde çalışan ana işleme metodu
        self,
        db: Session, # Veritabanı işlemleri için SQLAlchemy oturumu
        camera_db_id: int, # Tespitin geldiği kamera ID'si
        tracked_face_id: str, # Takip edilen yüzün kimliği
        emotion_label: str, # Tespit edilen anlık duygu etiketi (Örn: happy, sad)
        confidence_score: float, # Duygu tespitinin güvenilirlik skoru (0.0 - 1.0 arası)
        bbox: dict, # Yüzün anlık sınırlayıcı kutu koordinatları (x, y, width, height)
        detected_at: datetime | None = None, # Tespitin yapıldığı zaman (Verilmezse o anki zaman alınır)
    ):
        detected_at = detected_at or istanbul_now() # Zaman damgası boşsa İstanbul saatini ata
        key = (camera_db_id, tracked_face_id) # Bellekte arama yapmak için Kamera ID ve Yüz ID birleşiminden benzersiz anahtar oluştur

        if key not in self.active_sessions: # Eğer bu yüz için bellekte henüz aktif bir seans tanımı yoksa (İlk defa görülüyor ise)
            new_session = CustomerSession( # Yeni bir müşteri seansı veritabanı modeli oluştur
                camera_id=camera_db_id, # İlgili kamera bağlantısı
                tracked_face_id=tracked_face_id, # Takip edilen yüz kimliği
                session_status="active", # Seans durumunu başlangıçta "active" yap
                start_time=detected_at, # Seans başlangıç zamanı
                last_seen_time=detected_at, # Seans son görülme zamanı (Başlangıçta ilk görülme anı)
                total_detections=0, # Başlangıçta toplam tespit sayısı sıfır
            )
            db.add(new_session) # Yeni seans kaydını veritabanı işlem listesine ekle
            db.commit() # Veritabanına kalıcı olarak kaydet (ID oluşması için)
            db.refresh(new_session) # Oluşan ID dahil güncel veritabanı satır bilgilerini nesneye yükle

            self.active_sessions[key] = ActiveSessionState( # Bellekteki aktif seanslar sözlüğüne yeni durumu ekle
                db_session_id=new_session.id, # Veritabanından gelen benzersiz seans ID'si
                camera_db_id=camera_db_id, # Kamera ID'si
                tracked_face_id=tracked_face_id, # Yüz ID'si
                start_time=detected_at, # Başlangıç zamanı
                last_seen_time=detected_at, # Son görülme zamanı
                last_event_saved_at=detected_at, # İlk olay kayıt zamanı başlangıcı
            )

        state = self.active_sessions[key] # Bellekten ilgili yüzün mevcut seans durumunu referans al
        state.last_seen_time = detected_at # Son görülme zamanını bu yeni tespit zamanıyla güncelle
        state.total_detections += 1 # Toplam tespit sayısını bir artır
        state.confidence_sum += confidence_score # Güvenilirlik skorunu toplam havuza ekle
        state.emotion_counts[emotion_label] += 1 # İlgili duygu etiketinin sayacını bir artır

        should_save_event = ( # Belirlenen aralık süresine göre veritabanına olay kaydedilip kaydedilmeyeceğini kontrol et
            (detected_at - state.last_event_saved_at).total_seconds() # Son olay kaydından bu yana geçen süreyi saniye cinsinden hesapla
            >= self.event_save_interval_seconds # Geçen süre belirlenen aralık sınırından büyük veya eşit mi kontrolü
        )

        if should_save_event: # Eğer olay kaydetme zamanı geldiyse
            event = EmotionEvent( # Yeni bir anlık duygu olayı (EmotionEvent) modeli oluştur
                session_id=state.db_session_id, # Olayın bağlı olduğu seans ID'si
                detected_at=detected_at, # Olayın gerçekleştiği zaman damgası
                emotion_label=emotion_label, # O andaki duygu etiketi
                confidence_score=confidence_score, # O andaki duygu güven skoru
                bbox_x=bbox.get("x"), # Sınırlayıcı kutunun X koordinatı
                bbox_y=bbox.get("y"), # Sınırlayıcı kutunun Y koordinatı
                bbox_width=bbox.get("width"), # Sınırlayıcı kutunun genişliği
                bbox_height=bbox.get("height"), # Sınırlayıcı kutunun yüksekliği
            )
            db.add(event) # Olay nesnesini veritabanı işlem sırasına ekle

            session_row = db.get(CustomerSession, state.db_session_id) # Güncelleme yapmak için veritabanındaki ana seans satırını getir
            if session_row: # Satır başarıyla bulunduysa
                session_row.last_seen_time = state.last_seen_time # Veritabanındaki son görülme zamanını bellektekiyle senkronize et
                session_row.total_detections = state.total_detections # Toplam tespit sayısını veritabanında güncelle
                session_row.average_confidence = round( # Şu ana kadarki ortalama güven skorunu hesapla ve güncelle
                    state.confidence_sum / max(state.total_detections, 1), 4 # Toplam skoru tespit sayısına böl (en az 1'e bölerek güvene al) ve yuvarla
                )

            db.commit() # Tüm olay ekleme ve seans güncelleme işlemlerini veritabanına işle
            state.last_event_saved_at = detected_at # Bellekteki son olay kaydedilme zamanını güncel zamana çek

    def close_stale_sessions(self, db: Session, now: datetime | None = None): # Belirli süre işlem görmeyen (kamera odağından çıkan) seansları kapatan metot
        now = now or istanbul_now() # Zaman damgası belirtilmemişse anlık İstanbul zamanını baz al
        keys_to_close = [] # Kapatılması gereken seans anahtarlarının toplanacağı geçici liste

        for key, state in self.active_sessions.items(): # Bellekteki tüm aktif seansları sırayla incele
            idle_seconds = (now - state.last_seen_time).total_seconds() # Seansın son görülmesinden bu yana geçen boşta kalma süresini hesapla
            if idle_seconds > self.session_gap_seconds: # Eğer boşta kalma süresi izin verilen sınırı (gap_seconds) aşmışsa
                keys_to_close.append(key) # Seansı kapatılacaklar listesine dahil et

        for key in keys_to_close: # Kapatılması kesinleşen seans anahtarları üzerinde döngü başlat
            state = self.active_sessions[key] # Kapatılacak seansın bellekteki anlık durum verisini al

            session_row = db.get(CustomerSession, state.db_session_id) # Veritabanındaki ilgili seans satırını çek
            if session_row: # Eğer veritabanı satırı mevcutsa
                total = state.total_detections # Seansın toplam tespit sayısını değişkene al
                dominant_emotion = None # Başlangıçta baskın duygu değerini boş tanımla

                if state.emotion_counts: # Eğer seans boyunca en az bir duygu tespiti yapılmışsa
                    dominant_emotion = max( # En yüksek sayıya sahip olan duygu etiketini bul
                        state.emotion_counts, # Duygu sayılarının tutulduğu sözlük
                        key=state.emotion_counts.get # Karşılaştırmayı sözlüğün değerlerine (sayılara) göre yap
                    )

                session_row.session_status = "closed" # Seans durumunu veritabanında "closed" (kapalı) olarak işaretle
                session_row.end_time = state.last_seen_time # Seans bitiş zamanını yüzün son görüldüğü an olarak ata
                session_row.last_seen_time = state.last_seen_time # Son görülme zamanını doğrula ve güncelle
                session_row.duration_seconds = int( # Seansın toplam kalma süresini saniye cinsinden hesapla ve tam sayıya çevir
                    (state.last_seen_time - state.start_time).total_seconds() # Son görülme anından başlangıç anını çıkarıp saniyeye çevir
                )
                session_row.total_detections = total # Toplam tespit sayısını son kez veritabanına yaz
                session_row.average_confidence = round( # Seansın genel ortalama güven skorunu son kez hesapla
                    state.confidence_sum / max(total, 1), 4 # Toplam güven skorunu toplam tespite böl ve yuvarla
                )
                session_row.dominant_emotion = dominant_emotion # Seansın genelinde en çok görülen baskın duyguyu veritabanına ata
                session_row.emotion_distribution = self._build_distribution( # Tüm duyguların adet ve yüzde dağılımını json yapısı olarak ata
                    state.emotion_counts, # Duygu adetleri sözlüğü
                    total, # Toplam tespit sayısı
                )

                db.commit() # Seans kapatma işlemlerini veritabanında kalıcı hale getir

            del self.active_sessions[key] # Kapatılan seansı bellekteki (RAM) aktif seanslar listesinden tamamen sil

    def get_active_session_count(self, camera_db_id: int | None = None) -> int: # Anlık aktif seans sayısını veren metot
        if camera_db_id is None: # Eğer herhangi bir kamera kısıtlaması belirtilmediyse
            return len(self.active_sessions) # Bellekteki toplam aktif seans sayısını doğrudan döndür

        return sum( # Belirli bir kameraya ait aktif seansların sayısını hesapla
            1 # Her eşleşen seans için 1 değerini üret
            for (cam_id, _), _state in self.active_sessions.items() # Bellekteki seansların anahtar bilgilerini dön
            if cam_id == camera_db_id # Eğer seansın kamera ID'si aranan kamera ID'sine eşitse listeye dahil et
        )


session_service = SessionService() # Proje genelinde tek bir merkezden kullanılacak küresel SessionService nesnesini (Singleton benzeri) oluştur
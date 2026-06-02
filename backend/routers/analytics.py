from datetime import date, datetime, time, timedelta # Tarih ve zaman işlemleri için gerekli modüller

from fastapi import APIRouter, Depends, Query # FastAPI yönlendirici, bağımlılık enjeksiyonu ve sorgu parametreleri
from sqlalchemy import func # SQLAlchemy SQL fonksiyonları (count, avg, hour vb.)
from sqlalchemy.orm import Session # SQLAlchemy veritabanı oturum tipi

from database import get_db # Veritabanı bağlantı oturumu sağlayan bağımlılık
from models import CustomerSession # Müşteri seans bilgilerini tutan veritabanı modeli
from services.session_service import session_service # Aktif seans sayılarını çeken servis katmanı

router = APIRouter(prefix="/analytics", tags=["analytics"]) # Analitik uç noktaları için ortak ön ek ve etiket tanımı


@router.get("/overview") # Genel analitik özetini dönen GET uç noktası
def analytics_overview(
    target_date: date | None = Query(None), # İsteğe bağlı hedef tarih parametresi (Varsayılan: None)
    camera_id: int | None = Query(None), # İsteğe bağlı kamera ID parametresi (Varsayılan: None)
    db: Session = Depends(get_db), # Veritabanı oturum bağımlılığı enjeksiyonu
):
    day = target_date or datetime.utcnow().date() # Tarih belirtilmemişse bugünün UTC tarihini baz al
    start_dt = datetime.combine(day, time.min) # Günün başlangıç saati (00:00:00)
    end_dt = start_dt + timedelta(days=1) # Bir sonraki günün başlangıcı (Ertesi gün 00:00:00)

    base_query = db.query(CustomerSession).filter( # İlgili gün içindeki seansları filtreleyen ana sorgu başlangıcı
        CustomerSession.start_time >= start_dt, # Başlangıç zamanı bugünün başından büyük veya eşit olanlar
        CustomerSession.start_time < end_dt, # Başlangıç zamanı ertesi günün başından küçük olanlar
    )

    if camera_id is not None: # Eğer kamera ID parametresi gönderilmişse
        base_query = base_query.filter(CustomerSession.camera_id == camera_id) # Sorguya kamera filtresini ekle

    total_customers = base_query.count() # Filtrelere uyan toplam müşteri seans sayısını hesapla

    emotion_rows = ( # Duygu dağılımı verilerini çekmek için sorgu oluştur
        base_query.with_entities( # Sadece belirli kolonları çekerek optimizasyon sağla
            CustomerSession.dominant_emotion, # Baskın duygu kolonu
            func.count(CustomerSession.id) # Her duygunun toplam kaç kez geçtiği bilgisi
        )
        .group_by(CustomerSession.dominant_emotion) # Çekilen verileri baskın duyguya göre grupla
        .all() # Sorguyu çalıştır ve tüm satırları getir
    )

    emotion_distribution = { # Gelen veriyi anahtar-değer (dict) formatına dönüştür
        (emotion or "unknown"): count # Duygu değeri boşsa "unknown" yaz, yanına sayısını koy
        for emotion, count in emotion_rows # Çekilen tüm satırları tek tek dönerek sözlüğü doldur
    }

    avg_duration = ( # Ortalama seans süresini hesaplayan sorgu
        base_query.with_entities(func.avg(CustomerSession.duration_seconds)) # Saniye cinsinden sürelerin ortalamasını al
        .scalar() # Tek bir skaler değer olarak sonucu döndür
    )

    recent_rows = ( # Son eklenen seansları getiren sorgu
        base_query.order_by(CustomerSession.start_time.desc()) # Başlangıç zamanına göre sondan başa (azalan) sırala
        .limit(10) # En güncel olan ilk 10 kaydı sınırla
        .all() # Sorguyu çalıştırıp kayıtları listele
    )

    recent_sessions = [] # API çıktısına uygun formatta tutulacak son seanslar listesi
    for row in recent_rows: # Çekilen son 10 satır üzerinde döngü başlat
        recent_sessions.append({ # Her seans bilgisini JSON formatına uygun sözlük yapısına çevirerek ekle
            "id": row.id, # Seans ID'si
            "tracked_face_id": row.tracked_face_id, # Takip edilen yüz ID'si
            "start_time": row.start_time.isoformat() if row.start_time else None, # Başlangıç zamanını ISO formatına çevir
            "end_time": row.end_time.isoformat() if row.end_time else None, # Bitiş zamanını ISO formatına çevir
            "duration_seconds": row.duration_seconds, # Saniye cinsinden toplam süre
            "dominant_emotion": row.dominant_emotion, # Tespit edilen baskın duygu
            "average_confidence": row.average_confidence, # Ortalama duygu/yüz doğruluk skoru
            "total_detections": row.total_detections, # Seans boyunca yapılan toplam tespit sayısı
            "session_status": row.session_status, # Seansın anlık durumu (aktif, bitti vb.)
        })

    return { # API'den dönecek özet analitik verisi nesnesi
        "date": day.isoformat(), # Analitiğin ait olduğu tarih stringi
        "total_customers": total_customers, # Günlük toplam tekil müşteri/ziyaretçi sayısı
        "active_customers": session_service.get_active_session_count(camera_id), # Şu an anlık olarak içeride olan aktif kişi sayısı
        "emotion_distribution": emotion_distribution, # Duyguların sayısal dağılım listesi
        "average_session_duration": round(avg_duration or 0, 2), # Ortalama kalma süresi (virgülden sonra 2 basamak)
        "recent_sessions": recent_sessions, # Son 10 seansa ait detaylı veri listesi
    }


@router.get("/hourly-visits") # Saatlik ziyaretçi yoğunluğunu dönen GET uç noktası
def hourly_visits(
    target_date: date | None = Query(None), # İsteğe bağlı hedef tarih parametresi
    camera_id: int | None = Query(None), # İsteğe bağlı kamera ID parametresi
    db: Session = Depends(get_db), # Veritabanı oturum bağımlılığı
):
    day = target_date or datetime.utcnow().date() # Tarih seçilmediyse bugünün UTC tarihini kullan
    start_dt = datetime.combine(day, time.min) # Günün başlangıcı (00:00:00)
    end_dt = start_dt + timedelta(days=1) # Günün bitişi / sonraki günün başı (00:00:00)

    query = db.query( # Saatlik gruplama için sorgu oluştur
        func.hour(CustomerSession.start_time).label("hour"), # Başlangıç zamanından sadece saat bilgisini (0-23) çıkar
        func.count(CustomerSession.id).label("count") # O saat diliminde başlayan seansların toplam sayısını al
    ).filter( # Tarih aralığı filtresini uygula
        CustomerSession.start_time >= start_dt, # Belirtilen günün içindeki kayıtlar
        CustomerSession.start_time < end_dt, # Ertesi güne sarkmayan kayıtlar
    )

    if camera_id is not None: # Kamera ID filtresi eklenmişse
        query = query.filter(CustomerSession.camera_id == camera_id) # Sorguyu sadece o kameraya ait verilerle kısıtla

    rows = query.group_by(func.hour(CustomerSession.start_time)).all() # Saat değerine göre gruplayıp veritabanından çek

    result = {hour: 0 for hour in range(24)} # 0'dan 23'e kadar tüm saatleri varsayılan olarak 0 ziyaretçi ile tanımla
    for hour, count in rows: # Veritabanından gelen yoğunluk verilerini oku
        result[int(hour)] = count # İlgili saat anahtarına gerçek ziyaretçi sayısını ata

    return { # API yanıtını dön
        "date": day.isoformat(), # Sorgulanan günün tarihi
        "hourly_visits": result, # 24 saatlik ziyaret dağılım sözlüğü
    }


@router.get("/recent-sessions") # Doğrudan son seansları listelemek için kullanılan GET uç noktası
def recent_sessions(
    limit: int = Query(20, ge=1, le=100), # Getirilecek kayıt sayısı limit parametresi (En az 1, en fazla 100, varsayılan 20)
    camera_id: int | None = Query(None), # İsteğe bağlı kamera bazlı filtreleme parametresi
    db: Session = Depends(get_db), # Veritabanı oturum bağımlılığı
):
    query = db.query(CustomerSession) # Müşteri seansları tablosu için temel sorgu oluştur

    if camera_id is not None: # Eğer spesifik bir kamera ID verilmişse
        query = query.filter(CustomerSession.camera_id == camera_id) # Sadece o kameradan gelen seansları filtrele

    rows = query.order_by(CustomerSession.start_time.desc()).limit(limit).all() # En yeni seansları limite göre sıralayıp getir

    return [ # List comprehension ile gelen tüm satır verilerini JSON nesne listesi olarak döndür
        {
            "id": row.id, # Seans benzersiz kimliği
            "tracked_face_id": row.tracked_face_id, # Takip edilen nesne/yüz numarası
            "camera_id": row.camera_id, # Seansın ait olduğu kamera ID'si
            "start_time": row.start_time.isoformat() if row.start_time else None, # ISO formatında seans başlangıcı
            "end_time": row.end_time.isoformat() if row.end_time else None, # ISO formatında seans bitişi
            "duration_seconds": row.duration_seconds, # Toplam kalma süresi (Saniye)
            "dominant_emotion": row.dominant_emotion, # Analiz edilen ana duygu durumu
            "average_confidence": row.average_confidence, # Analiz güvenilirlik skoru ortalaması
            "total_detections": row.total_detections, # Toplam kare analiz sayısı
            "session_status": row.session_status, # Seansın bitme/devam etme durumu
        }
        for row in rows # Gelen veritabanı satır listesinde dön
    ]
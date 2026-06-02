from sqlalchemy import create_engine # Veritabanı motorunu (bağlantı havuzunu) oluşturan SQLAlchemy fonksiyonu
from sqlalchemy.orm import sessionmaker, declarative_base # Oturum fabrikası ve modeller için temel sınıf üreten fonksiyonlar
from dotenv import load_dotenv # .env dosyasındaki çevre değişkenlerini sisteme yükleyen fonksiyon
import os # Sistem çevre değişkenlerine (environment variables) erişmek için kullanılan standart Python modülü

load_dotenv() # Proje kök dizininde bulunan .env dosyasındaki verileri okuyup sisteme yükler

DATABASE_URL = os.getenv("DATABASE_URL") # Sistem değişkenleri arasından "DATABASE_URL" anahtarına sahip bağlantı metnini alır

engine = create_engine( # Veritabanı ile iletişim kuracak ana motor nesnesini yapılandırır
    DATABASE_URL, # Veritabanı tipi, kullanıcı adı, şifre ve adres bilgilerini içeren bağlantı adresi
    pool_pre_ping=True # Havuzdaki bağlantıların kopup kopmadığını her sorgu öncesi test eden (canlılık kontrolü) mekanizma
)

SessionLocal = sessionmaker( # Veritabanı üzerinde sorgu ve kayıt işlemleri yapmayı sağlayan oturum (Session) sınıfı fabrikası
    autocommit=False, # İşlemlerin otomatik olarak veritabanına işlenmesini engeller (Geliştirici elle db.commit() demelidir)
    autoflush=False, # Sorgu çalıştırılmadan önce yapılan değişikliklerin otomatik olarak veritabanına gönderilmesini kapatır
    bind=engine # Bu oturum fabrikasının hangi veritabanı motorunu (engine) kullanacağını bağlar
)

Base = declarative_base() # Veritabanı tablolarına karşılık gelecek ORM modellerinin türeyeceği temel (base) sınıfı oluşturur

def get_db(): # FastAPI uç noktalarında Dependency Injection (Bağımlılık Enjeksiyonu) için kullanılacak veritabanı yield fonksiyonu
    db = SessionLocal() # Fabrikayı kullanarak yeni, izole bir veritabanı oturumu (Session) başlatır
    try: # Hata yönetim bloğu başlatır (İşlemler esnasında hata çıksa bile finally bloğunun çalışmasını garanti eder)
        yield db # Oluşturulan veritabanı oturumunu isteği işleyen uç noktaya (router) geçici olarak teslim eder
    finally: # İstek tamamlandığında veya bir hata oluşup süreç kesildiğinde mutlaka çalışacak olan güvenli bölge
        db.close() # Veritabanı bağlantı havuzunu korumak ve sızıntıları önlemek için açılan oturumu kesin olarak kapatır
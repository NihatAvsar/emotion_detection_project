"""
Türkiye (İstanbul) saat dilimi yardımcı modülü.
Proje genelinde tüm zaman damgaları için kullanılır.
UTC yerine Europe/Istanbul kullanılarak saatler doğru gösterilir.
"""

from datetime import datetime, timedelta, timezone

# Türkiye saat dilimi: UTC+3 (sabit, yaz saati uygulaması yok)
ISTANBUL_TZ = timezone(timedelta(hours=3), name="Europe/Istanbul")


def istanbul_now() -> datetime:
    """
    İstanbul saatini naive datetime olarak döndürür.
    Veritabanında timezone bilgisi olmadan (naive) saklanır.
    """
    return datetime.now(ISTANBUL_TZ).replace(tzinfo=None)

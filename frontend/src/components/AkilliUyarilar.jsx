/**
 * AkilliUyarilar Bileseni
 * ========================
 * Metriklere dayali kural tabanli uyari sistemi.
 * Negatif duygu orani, kizgin musteri orani, yogunluk ve veri kalitesi kontrol eder.
 *
 * Props:
 * ozet      — analytics overview verisi
 * oturumlar — son oturumlar listesi
 */

export default function AkilliUyarilar({ ozet, oturumlar }) { // Bileşenin ana fonksiyon tanımı ve yıkıcı (destructuring) props alımı
  if (!ozet) return null; // Eğer parent bileşenden ozet verisi henüz yüklenmediyse arayüzde hiçbir şey render etme (boş dön)

  const dagilim = ozet.emotion_distribution || {}; // Duygu dağılım nesnesini al, veri yoksa çökmemesi için boş nesneye eşitle
  const toplam = Object.values(dagilim).reduce((a, b) => a + b, 0) || 1; // Toplam duygu adetlerini topla, 0 ise sıfıra bölünmeyi önlemek için 1 yap
  const oturumListesi = oturumlar || ozet?.recent_sessions || []; // Oturum listesi prop'tan gelmediyse ozet içindeki son seansları kullan, yoksa boş dizi ata

  const negatifSayisi = (dagilim.sad || 0) + (dagilim.angry || 0); // Üzgün ve kızgın müşteri sayılarının toplamını alarak negatif hacmi bul
  const kizginSayisi = dagilim.angry || 0; // Sadece kızgın olarak sınıflandırılan müşteri sayısını al
  const negatifOran = Math.round((negatifSayisi / toplam) * 100); // Negatif duyguların genel toplama yüzde oranını hesapla ve tam sayıya yuvarla
  const kizginOran = Math.round((kizginSayisi / toplam) * 100); // Kızgın müşterilerin genel toplama yüzde oranını hesapla ve tam sayıya yuvarla

  // ─── Ortalama güven ───
  const guvenDegerleri = oturumListesi // Model çıkarım güven skorlarını hesaplamak için dizi operasyonu başlat
    .filter(o => o.average_confidence != null) // Güven skoru null veya undefined olmayan geçerli seansları filtrele
    .map(o => o.average_confidence); // Seans nesnelerinin içinden sadece güven skoru değerlerini (sayıları) alarak yeni dizi oluştur
  const ortGuven = guvenDegerleri.length > 0 // Eğer filtrelenmiş listede en az bir güven değeri varsa
    ? guvenDegerleri.reduce((a, b) => a + b, 0) / guvenDegerleri.length // Tüm skorları topla ve toplam eleman sayısına bölerek ortalamayı bul
    : 1; // Eğer hiç seans verisi yoksa varsayılan olarak en yüksek kaliteyi (1) kabul et

  const aktifMusteri = ozet.active_customers || 0; // Şu an anlık olarak kamerada aktif olan müşteri sayısını al, yoksa 0 kabul et

  // ─── Uyarıları oluştur ───
  const uyarilar = []; // Şartlara göre doldurulacak olan dinamik uyarı nesneleri dizisi

  if (negatifOran >= 30) { // Negatif duygu oranı %30 veya daha yüksekse (En kritik durum)
    uyarilar.push({ // Kritik seviyede yüksek negatif duygu uyarı nesnesini listeye ekle
      tip: 'kritik', // CSS sınıfı tetiklemek için kullanılacak tip belirteci
      ikon: '🔴', // Kritik durumu simgeleyen kırmızı yuvarlak emojisi
      baslik: 'Yüksek Negatif Duygu', // Uyarının ana başlığı
      mesaj: `Negatif duygu oranı %${negatifOran} ile kritik seviyede. Müşteri memnuniyeti tehlikede.`, // Dinamik yüzde içeren mesaj metni
    });
  } else if (negatifOran >= 20) { // Negatif duygu oranı %20 ile %29 arasındaysa (Orta risk durumu)
    uyarilar.push({ // İzleme önerisi içeren orta seviye uyarı nesnesini listeye ekle
      tip: 'uyari', // CSS sınıfı için uyarı tipi
      ikon: '🟡', // Orta seviye riski simgeleyen sarı yuvarlak emojisi
      baslik: 'Artan Negatif Duygu', // Uyarının ana başlığı
      mesaj: `Negatif duygu oranı %${negatifOran}. İzlenmesi önerilir.`, // Durum bilgilendirme mesaj metni
    });
  }

  if (kizginOran >= 20) { // Sadece kızgınlık oranı %20 veya üzerindeyse (Doğrudan mağaza içi kriz senaryosu)
    uyarilar.push({ // Mağaza içi operasyonel acil durum uyarı nesnesini listeye ekle
      tip: 'kritik', // CSS sınıfı için kritik tipi
      ikon: '😠', // Kızgın yüz ifadesi emojisi
      baslik: 'Kızgın Müşteri Uyarısı', // Uyarının ana başlığı
      mesaj: `Kızgın müşteri oranı %${kizginOran} ile yüksek. Acil müdahale gerekebilir.`, // Müdahale çağrısı içeren mesaj metni
    });
  }

  if (aktifMusteri >= 10) { // Anlık aktif müşteri sayısı 10 kişiyi geçtiyse (Kasa/reyon yoğunluk kontrolü)
    uyarilar.push({ // Mağaza yoğunluk bilgilendirme nesnesini listeye ekle
      tip: 'bilgi', // CSS sınıfı için standart bilgi (info) tipi
      ikon: '👥', // İnsan topluluğu emojisi
      baslik: 'Yoğunluk Uyarısı', // Uyarının ana başlığı
      mesaj: `Şu an ${aktifMusteri} aktif müşteri var. Yoğun dönem.`, // Anlık müşteri sayısını belirten mesaj metni
    });
  }

  if (ortGuven < 0.5 && oturumListesi.length > 0) { // Model güven ortalaması %50'nin altına düştüyse ve içeride veri varsa
    uyarilar.push({ // Donanımsal/Çevresel kalite uyarı nesnesini listeye ekle
      tip: 'uyari', // CSS sınıfı için uyarı tipi
      ikon: '🔬', // Mikroskop emojisi (Veri analizi kalitesini simgeler)
      baslik: 'Düşük Veri Kalitesi', // Uyarının ana başlığı
      mesaj: `Ortalama güven skoru %${Math.round(ortGuven * 100)}. Kamera konumu veya ışık kontrol edilmeli.`, // Donanım iyileştirme tavsiye mesajı
    });
  }

  if (uyarilar.length === 0) { // Eğer yukarıdaki hiçbir olumsuz kurala takılınmadıysa (Her şey idealse)
    uyarilar.push({ // Kullanıcıya içini rahatlatacak başarılı durum nesnesini ekle
      tip: 'basarili', // CSS sınıfı için başarılı (success) tipi
      ikon: '✅', // Yeşil onay işareti emojisi
      baslik: 'Her Şey Yolunda', // Uyarının ana başlığı
      mesaj: 'Tüm metrikler normal aralıkta. Müşteri deneyimi olumlu seyrediyor.', // Olumlu durum mesaj metni
    });
  }

  return ( // JSX (HTML benzeri arayüz yapısı) çıktısının başladığı yer
    <div className="glass-card"> {/* Buzlu cam efektli ana kart kapsayıcı div'i */}
      <div className="card-header"> {/* Kartın başlık ve sayaç alanını tutan üst bölme */}
        <span className="icon">⚠️</span> {/* Kart sol sabit uyar ikonu */}
        <h2>Akıllı Uyarılar</h2> {/* Kart başlık metni */}
        {uyarilar.some(u => u.tip === 'kritik') && ( // Eğer üretilen uyarıların içinde en az bir tane 'kritik' seviye varsa
          <span className="uyari-sayac kritik">{uyarilar.filter(u => u.tip === 'kritik').length}</span> // Kritik tipteki uyarıları filtrele ve adedini kırmızı rozet (badge) olarak render et
        )}
      </div>
      <div className="card-body uyari-icerik"> {/* Uyarı kartlarının listeleneceği gövde bölmesi */}
        {uyarilar.map((uyari, i) => ( // Üretilen tüm dinamik uyarıları döngüye sokarak ekrana basar (React map fonksiyonu)
          <div className={`uyari-kart ${uyari.tip}`} key={i}> {/* Uyarının tipine göre dinamik sınıf alan (kritik, uyari vb.) ve benzersiz key alan kart satırı */}
            <span className="uyari-ikon">{uyari.ikon}</span> {/* Uyarının durum emojisi */}
            <div className="uyari-bilgi"> {/* Başlık ve mesajı dikeyde hizalayan iç bölme */}
              <span className="uyari-baslik">{uyari.baslik}</span> {/* Uyarının kalın yazılacak başlık alanı */}
              <span className="uyari-mesaj">{uyari.mesaj}</span> {/* Uyarının detaylı açıklama metni alanı */}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
# Gerçek Zamanlı Yüz Duygu Analizi Platformu

Bu proje, kamera görüntülerinden yüzleri gerçek zamanlı olarak tespit eden, tespit edilen yüzlerdeki duygu durumunu derin öğrenme modeliyle sınıflandıran ve sonuçları web arayüzünde anlık olarak görselleştiren bir duygu analiz platformudur.

Sistem; canlı kamera akışı, yüz tespiti, duygu sınıflandırma, kişi takibi, müşteri oturumu oluşturma, veritabanı kaydı ve analiz paneli bileşenlerinden oluşur. Frontend tarafında React + Vite, backend tarafında FastAPI, görüntü işleme tarafında OpenCV ve MediaPipe, duygu tahmini tarafında ise PyTorch tabanlı ConvNeXt Tiny modeli kullanılmaktadır.

---

## Projenin Amacı

Bu projenin amacı, fiziksel ortamlarda bulunan kişilerin yüz ifadelerini analiz ederek anlık duygu durumlarını belirlemek ve bu bilgileri işletmeler için anlamlı verilere dönüştürmektir.

Sistem özellikle mağaza, hizmet noktası, danışma alanı, etkinlik alanı veya müşteri deneyimi ölçümü yapılmak istenen ortamlarda kullanılabilecek şekilde tasarlanmıştır.

Proje sayesinde:

- Kamera görüntüsünden yüzler gerçek zamanlı algılanır.
- Her yüz için baskın duygu tahmini yapılır.
- Birden fazla yüz aynı anda analiz edilebilir.
- Aynı kişi kareler arasında takip edilerek müşteri oturumu oluşturulur.
- Duygu tahminleri güven skorlarıyla birlikte gösterilir.
- Günlük müşteri sayısı, aktif müşteri sayısı, duygu dağılımı ve saatlik yoğunluk gibi metrikler analiz panelinde sunulur.

---

## Kullanılan Teknolojiler

### Frontend

- React
- Vite
- React Router
- Recharts
- HTML5 Video API
- Canvas API
- WebSocket
- CSS

### Backend

- Python
- FastAPI
- Uvicorn
- WebSocket
- PyTorch
- Torchvision
- timm
- MediaPipe
- OpenCV
- NumPy
- Pillow
- SQLAlchemy
- PyMySQL
- python-dotenv

### Veritabanı

- MySQL
- SQLAlchemy ORM

---

## Sistem Mimarisi

Proje iki ana katmandan oluşur:

- Frontend: Kullanıcı arayüzü, kamera erişimi ve görselleştirme işlemleri
- Backend: Görüntü işleme, yüz tespiti, duygu tahmini, takip sistemi ve veritabanı işlemleri

Genel veri akışı:

Kamera Görüntüsü
      ↓
React Frontend
      ↓ WebSocket ile base64 JPEG kare gönderimi
FastAPI Backend
      ↓
OpenCV ile görüntü çözümleme
      ↓
MediaPipe ile yüz tespiti
      ↓
Yüz kırpma ve ön işleme
      ↓
ConvNeXt Tiny modeli ile duygu tahmini
      ↓
Kişi takibi ve oturum güncelleme
      ↓
MySQL veritabanına kayıt
      ↓
JSON sonuçlarının frontend'e gönderilmesi
      ↓
Canlı görselleştirme ve analiz paneli

---

## Yapay Zeka Modeli

Projede duygu sınıflandırma için ConvNeXt Tiny mimarisi kullanılmaktadır. ConvNeXt, modern CNN yaklaşımlarını kullanan güçlü bir görüntü sınıflandırma mimarisidir.

Model, yüz görüntüsünü giriş olarak alır ve beş farklı duygu sınıfından birini tahmin eder.

### Model Özellikleri

- Mimari: ConvNeXt Tiny
- Kütüphane: PyTorch + timm
- Giriş: Yüz görüntüsü
- Çıkış: 5 duygu sınıfı
- Tahmin çıktısı:
  - Duygu etiketi
  - Türkçe duygu karşılığı
  - Emoji
  - Güven skoru
  - Her sınıf için olasılık değeri

---

## Duygu Sınıfları

| İngilizce Etiket | Türkçe Karşılık | Emoji |
|---|---|---|
| happy | Mutlu | 😊 |
| sad | Üzgün | 😢 |
| angry | Kızgın | 😠 |
| surprised | Şaşkın | 😲 |
| neutral | Nötr | 😐 |

---

## Yüz Tespiti

Yüz tespiti için MediaPipe kullanılmaktadır. MediaPipe, gerçek zamanlı görüntü işleme için optimize edilmiş bir framework olduğu için kamera akışlarında düşük gecikmeyle çalışmaya uygundur.

Yüz tespiti sürecinde:

- Kamera görüntüsü backend'e gönderilir.
- Görüntü OpenCV ile işlenir.
- MediaPipe ile yüz bölgeleri tespit edilir.
- Tespit edilen yüzler kırpılır.
- Kırpılan yüzler model girişine uygun hale getirilir.
- Duygu tahmini yapılır.

Performans için görüntü küçültme, yüz tespiti önbelleği ve video modunda çalışma gibi optimizasyonlar uygulanmıştır.

---

## Canlı Tespit Ekranı

Canlı tespit ekranı, sistemin gerçek zamanlı analiz bölümüdür. Kullanıcı kamerayı başlattığında tarayıcıdan alınan görüntüler belirli aralıklarla backend'e gönderilir.

Bu ekranda:

- Kamera görüntüsü canlı olarak gösterilir.
- Tespit edilen yüzlerin etrafına kutu çizilir.
- Her yüzün duygu etiketi ve güven yüzdesi gösterilir.
- Anlık FPS bilgisi görüntülenir.
- Aktif müşteri sayısı takip edilir.
- Birden fazla yüz varsa kullanıcı yüz seçimi yapabilir.
- Seçilen yüz için baskın duygu paneli gösterilir.
- Duygu olasılıkları bar grafik olarak gösterilir.
- Duygu değişimi zaman çizelgesi üzerinde izlenebilir.

---

## WebSocket ile Gerçek Zamanlı İletişim

Canlı analiz için WebSocket kullanılmaktadır. WebSocket, sürekli bağlantı sağladığı için gerçek zamanlı görüntü aktarımı ve hızlı yanıt alma açısından klasik HTTP isteklerine göre daha uygundur.

Akış şu şekildedir:

1. Frontend kamera karesini canvas üzerine çizer.
2. Kare JPEG formatında base64 verisine dönüştürülür.
3. Veri WebSocket üzerinden backend'e gönderilir.
4. Backend yüz tespiti ve duygu analizi yapar.
5. Sonuç JSON olarak frontend'e döner.
6. Frontend sonucu canlı olarak görselleştirir.

WebSocket endpoint:

```text
/ws/predict
```

Örnek yanıt:

```json
{
  "success": true,
  "face_count": 1,
  "faces": [
    {
      "emotion": "happy",
      "emotion_tr": "Mutlu",
      "emoji": "😊",
      "confidence": 0.9234,
      "probabilities": {
        "angry": 0.01,
        "happy": 0.92,
        "neutral": 0.04,
        "sad": 0.02,
        "surprised": 0.01
      },
      "face_bbox": {
        "x": 0.25,
        "y": 0.15,
        "w": 0.5,
        "h": 0.6
      }
    }
  ],
  "timestamp": 1710100000.123
}
```

---

## Kişi Takibi ve Oturum Yönetimi

Sistem yalnızca anlık duygu tahmini yapmakla kalmaz, aynı kişiyi kısa süreli kamera akışı boyunca takip ederek müşteri oturumu oluşturur.

Takip sisteminde:

- Her kamera için ayrı takip listesi tutulur.
- Yüz kutuları önceki karelerdeki yüz kutularıyla karşılaştırılır.
- Benzer konumdaki yüzler aynı kişi olarak kabul edilir.
- Yeni kişi algılandığında yeni takip kimliği oluşturulur.
- Kısa süre görünmeyen kişiler için oturum kapatılır.

Oturum bilgileri:

- Başlangıç zamanı
- Bitiş zamanı
- Oturum süresi
- Toplam tespit sayısı
- Ortalama güven skoru
- Baskın duygu
- Duygu dağılımı
- Takip edilen yüz kimliği

Bu yapı sayesinde sistem, yalnızca kare bazlı değil, müşteri bazlı analiz de yapabilir.

---

## Analiz Paneli

Analiz paneli, toplanan verileri işletme bakış açısıyla görselleştiren dashboard sayfasıdır.

Analiz panelinde:

- Toplam müşteri sayısı
- Aktif müşteri sayısı
- Ortalama oturum süresi
- Pozitif, nötr ve negatif duygu oranları
- Duygu dağılımı pasta grafiği
- Saatlik müşteri yoğunluğu grafiği
- Canlı oturumlar
- Son müşteri oturumları tablosu

gösterilir.

Panel belirli aralıklarla otomatik yenilenir ve seçilen tarihe göre analiz yapılabilir.

---

## Veritabanı Yapısı

Projede MySQL veritabanı kullanılmaktadır. SQLAlchemy ORM ile tablolar Python modelleri üzerinden yönetilir.

Ana tablolar:

| Tablo | Açıklama |
|---|---|
| businesses | İşletme bilgileri |
| branches | Şube bilgileri |
| cameras | Kamera bilgileri |
| customer_sessions | Müşteri/yüz oturumları |
| emotion_events | Oturum içindeki duygu tespit olayları |
| emotion_summaries | Özetlenmiş analiz verileri |

---

## API Endpointleri

| Endpoint | Yöntem | Açıklama |
|---|---|---|
| `/ws/predict` | WebSocket | Gerçek zamanlı kamera akışı üzerinden duygu tahmini |
| `/api/predict` | POST | Tekil görüntü için duygu tahmini |
| `/models` | GET | Sistemdeki modelleri listeler |
| `/analytics/overview` | GET | Günlük genel analiz özetini verir |
| `/analytics/hourly-visits` | GET | Saatlik müşteri yoğunluğunu verir |
| `/analytics/recent-sessions` | GET | Son müşteri oturumlarını listeler |
| `/analytics/live` | GET | Aktif oturum ve aktif müşteri bilgisini verir |
| `/health` | GET | Sistem sağlık kontrolü yapar |

---

## Kurulum

### Backend Kurulumu

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend varsayılan olarak şu adreste çalışır:

http://localhost:8000

### Frontend Kurulumu

```bash
cd frontend
npm install
npm run dev
```

Frontend varsayılan olarak şu adreste çalışır:

http://localhost:5173

---

## Kullanım

1. Backend sunucusunu başlatın.
2. Frontend geliştirme sunucusunu başlatın.
3. Tarayıcıdan `http://localhost:5173` adresine gidin.
4. Canlı Tespit sayfasında Kamerayı Başlat butonuna tıklayın.
5. Tarayıcı kamera iznini onaylayın.
6. Sistem yüzleri tespit edip duygu analizini gerçek zamanlı olarak göstermeye başlar.
7. Analiz Paneli sayfasından kaydedilen oturumları ve duygu istatistiklerini görüntüleyebilirsiniz.

---

## Proje Yapısı

emotion_detection_project/
├── backend/
│   ├── main.py
│   ├── model.py
│   ├── face_detection.py
│   ├── model_registry.py
│   ├── models.py
│   ├── database.py
│   ├── requirements.txt
│   ├── convnext_tiny_best.pth
│   └── blaze_face_short_range.tflite
│
├── frontend/
│   ├── package.json
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── api.js
│       ├── pages/
│       │   ├── CanliTespit.jsx
│       │   └── AnalizPaneli.jsx
│       └── components/
│           ├── WebcamView.jsx
│           ├── EmotionPanel.jsx
│           ├── ProbabilityBar.jsx
│           ├── EmotionTimeline.jsx
│           ├── ModelSelector.jsx
│           ├── FaceListPanel.jsx
│           ├── DashboardKartlari.jsx
│           ├── DuyguDagilimi.jsx
│           ├── SaatlikGrafik.jsx
│           └── OturumTablosu.jsx
│
└── README.md

---

## Performans Optimizasyonları

Gerçek zamanlı çalışmayı desteklemek için projede çeşitli optimizasyonlar uygulanmıştır:

- WebSocket ile düşük gecikmeli iletişim
- JPEG sıkıştırmalı base64 kare aktarımı
- MediaPipe video modu
- Yüz tespitinde görüntü küçültme
- Yüz tespit sonuçlarının kısa süreli önbelleğe alınması
- PyTorch inference sırasında gradient hesaplamanın kapatılması
- Modelin eval modunda çalıştırılması
- GPU varsa otomatik CUDA kullanımı
- Frontend tarafında aynı anda tek bekleyen kare gönderimi
- Model registry ile lazy loading ve cache kullanımı

---

## Güçlü Yönler

- Gerçek zamanlı çalışan uçtan uca sistem
- Modern derin öğrenme modeli kullanımı
- Web tabanlı kullanıcı dostu arayüz
- Birden fazla yüzü aynı anda analiz edebilme
- Yüz takibi ile oturum bazlı analiz
- MySQL ile kalıcı veri saklama
- Dashboard ile işletme odaklı görselleştirme
- Model seçimi ve çoklu model altyapısı
- Duygu olasılıklarını detaylı gösterme
- Canlı ve geçmiş verileri birlikte sunma

---

## Kullanım Alanları

Bu proje aşağıdaki alanlarda kullanılabilir:

- Mağazalarda müşteri memnuniyeti analizi
- Perakende sektöründe müşteri deneyimi ölçümü
- Hizmet noktalarında yoğunluk ve duygu takibi
- Etkinlik alanlarında katılımcı tepkisi analizi
- Eğitim ortamlarında öğrenci duygu durumunun incelenmesi
- İnsan-bilgisayar etkileşimi çalışmaları
- Akıllı mağaza ve akıllı kamera sistemleri
- Kullanıcı deneyimi araştırmaları

---

## Etik ve Gizlilik

Yüz ve duygu analizi hassas veri içerebileceği için bu tür sistemlerde etik ve gizlilik konuları önemlidir.

Dikkat edilmesi gereken noktalar:

- Kullanıcılardan açık rıza alınmalıdır.
- Sistem yalnızca gerekli verileri işlemelidir.
- Kişisel kimlik tespiti yapılmamalıdır.
- Görüntüler mümkünse saklanmamalı, yalnızca analiz sonuçları tutulmalıdır.
- Veriler anonim takip kimlikleriyle ilişkilendirilmelidir.
- Kullanım alanında bilgilendirme yapılmalıdır.
- Duygu tahminlerinin kesin psikolojik sonuç olmadığı belirtilmelidir.

---

## Sonuç

Bu proje, yapay zeka destekli gerçek zamanlı duygu analizi ile müşteri deneyimini ölçmeye yönelik kapsamlı bir web platformudur. Kamera görüntüsünden yüz tespiti yapılmakta, tespit edilen yüzler ConvNeXt Tiny modeliyle sınıflandırılmakta ve sonuçlar canlı olarak kullanıcı arayüzünde gösterilmektedir.

Kişi takibi ve oturum yönetimi sayesinde sistem yalnızca anlık duygu tahmini yapmakla kalmaz, müşteri bazlı davranış ve duygu analizi de sağlar. Analiz paneli ile toplam müşteri sayısı, aktif müşteri sayısı, ortalama oturum süresi, duygu dağılımı ve saatlik yoğunluk gibi metrikler görselleştirilerek işletmeler için karar destek aracı haline gelir.
```
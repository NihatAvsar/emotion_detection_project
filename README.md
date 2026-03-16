# 🎭 Gerçek Zamanlı Yüz Duygu Analizi

> **ConvNeXt Tiny** + **MediaPipe** ile gerçek zamanlı duygu tanıma web uygulaması.

## 🏗️ Mimari

```
┌──────────────┐    WebSocket    ┌──────────────────┐
│   Frontend   │ ◄════════════► │     Backend      │
│  React+Vite  │   base64 JPEG  │     FastAPI      │
│              │   ◄── JSON ──  │                  │
│ • Kamera     │                │ • MediaPipe      │
│ • Bbox çizim │                │ • ConvNeXt Tiny  │
│ • Grafikler  │                │ • PyTorch        │
└──────────────┘                └──────────────────┘
```

## 📋 Gereksinimler

- **Python** 3.9+
- **Node.js** 18+
- **GPU** (opsiyonel — CPU'da da çalışır)

## 🚀 Kurulum & Çalıştırma

### 1. Backend

```bash
cd backend

# Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Bağımlılıkları yükle
pip install -r requirements.txt

# Sunucuyu başlat
python main.py
```

> Sunucu `http://localhost:8000` adresinde başlar.

### 2. Frontend

```bash
cd frontend

# Bağımlılıkları yükle
npm install

# Geliştirme sunucusunu başlat
npm run dev
```

> Uygulama `http://localhost:5173` adresinde açılır.

### 3. Kullanım

1. Tarayıcıda `http://localhost:5173` adresini açın
2. **"Kamerayı Başlat"** butonuna tıklayın
3. Kamera izni verin
4. Gerçek zamanlı duygu analizi başlar!

## 🎯 Duygu Sınıfları

| Duygu | Türkçe | Emoji |
|-------|--------|-------|
| happy | Mutlu | 😊 |
| sad | Üzgün | 😢 |
| angry | Kızgın | 😠 |
| surprised | Şaşkın | 😲 |
| neutral | Nötr | 😐 |

## 📁 Proje Yapısı

```
duygu_proje/
├── convnext_tiny_best.pth       # Eğitilmiş model (%89 doğruluk)
├── backend/
│   ├── requirements.txt         # Python bağımlılıkları
│   ├── main.py                  # FastAPI — WS + REST endpoint
│   ├── model.py                 # ConvNeXt Tiny inference
│   └── face_detection.py        # MediaPipe yüz tespiti
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx              # Ana uygulama (WS + kamera)
│   │   ├── index.css            # Dark theme stiller
│   │   └── components/
│   │       ├── WebcamView.jsx   # Kamera + bounding box
│   │       ├── EmotionPanel.jsx # Baskın duygu paneli
│   │       ├── ProbabilityBar.jsx # Olasılık barları
│   │       └── EmotionTimeline.jsx # 30s zaman çizelgesi
│   └── ...
└── README.md
```

## 🔧 API Endpoints

| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/ws/predict` | WebSocket | Gerçek zamanlı stream |
| `/api/predict` | POST | Tekil tahmin |
| `/health` | GET | Sağlık kontrolü |

### WebSocket yanıt formatı

```json
{
  "success": true,
  "faces": [
    {
      "emotion": "happy",
      "emotion_tr": "Mutlu",
      "emoji": "😊",
      "confidence": 0.9234,
      "probabilities": {
        "angry": 0.01, "happy": 0.92, "neutral": 0.04,
        "sad": 0.02, "surprised": 0.01
      },
      "face_bbox": { "x": 0.25, "y": 0.15, "w": 0.5, "h": 0.6 }
    }
  ],
  "timestamp": 1710100000.123
}
```

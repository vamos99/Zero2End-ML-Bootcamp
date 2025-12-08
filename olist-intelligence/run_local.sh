#!/bin/bash

# Renkler
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Olist Intelligence Local Başlatıcı${NC}"
echo "========================================"

# Python ortamı kontrolü
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ venv aktif ediliyor...${NC}"
    source venv/bin/activate
else
    echo "⚠️ venv bulunamadı! Lütfen önce kurulum adımlarını yapın."
    exit 1
fi

# 1. MLflow Başlat (Arka Planda)
echo -e "${BLUE}📊 MLflow (Port 5000) başlatılıyor...${NC}"
mlflow ui --port 5000 > /dev/null 2>&1 &
MLFLOW_PID=$!
echo -e "${GREEN}✅ MLflow PID: $MLFLOW_PID${NC}"

# 2. API Başlat (Arka Planda)
echo -e "${BLUE}🔌 API (Port 8000) başlatılıyor...${NC}"
uvicorn src.app:app --host 127.0.0.1 --port 8000 > /dev/null 2>&1 &
API_PID=$!
echo -e "${GREEN}✅ API PID: $API_PID${NC}"

# Bekle (API'nin ayağa kalkması için)
echo "⏳ Servislerin hazır olması bekleniyor (5 sn)..."
sleep 5

# 3. Dashboard Başlat (Ön Planda)
echo -e "${BLUE}📈 Dashboard (Port 8501) başlatılıyor...${NC}"
echo "ℹ️ Çıkış yapmak için Ctrl+C'ye basın (Tüm servisler kapanacak)"

# Cleanup fonksiyonu (Kapanışta hepsini öldür)
cleanup() {
    echo -e "\n${BLUE}🛑 Servisler durduruluyor...${NC}"
    kill $MLFLOW_PID
    kill $API_PID
    echo -e "${GREEN}✅ Tüm süreçler temizlendi.${NC}"
    exit
}

trap cleanup SIGINT

streamlit run src/dashboard.py

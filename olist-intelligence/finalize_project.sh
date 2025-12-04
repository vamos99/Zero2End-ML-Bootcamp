#!/bin/bash

# Stop on error
set -e

echo "🚀 Başlatılıyor: Olist 360° Finalizasyon İşlemi (Clean & Fix)"

# 0. Sanal Ortam (venv) Kontrolü
EXISTING_VENV="../venv"
LOCAL_VENV="venv"

if [ -d "$EXISTING_VENV" ]; then
    echo "✅ Mevcut sanal ortam bulundu: $EXISTING_VENV"
    source $EXISTING_VENV/bin/activate
elif [ -d "$LOCAL_VENV" ]; then
    echo "✅ Yerel sanal ortam bulundu: $LOCAL_VENV"
    source $LOCAL_VENV/bin/activate
else
    echo "🌱 Hiçbir sanal ortam bulunamadı, yeni oluşturuluyor..."
    python3 -m venv $LOCAL_VENV
    source $LOCAL_VENV/bin/activate
fi

# 1. Kütüphaneleri Yükle
echo "📦 Kütüphaneler yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -U kaleido
pip install jupyter

# 2. Konfigürasyonu Zorla (Python scripti ile)
echo "🔧 PNG ayarı notebooklara işleniyor..."
python3 force_fix_viz.py

# 3. Temizlik ve Yeniden Çalıştırma
echo "🧹 Notebook çıktıları temizleniyor (Dosya boyutunu düşürmek için)..."
jupyter nbconvert --clear-output --inplace notebooks/*.ipynb

echo "🔄 Notebooklar çalıştırılıyor (PNG üretmek için)..."
jupyter nbconvert --to notebook --execute --inplace notebooks/1_general_eda_and_prep.ipynb
echo "✅ Notebook 1 Tamamlandı."

jupyter nbconvert --to notebook --execute --inplace notebooks/2_logistics_engine.ipynb
echo "✅ Notebook 2 Tamamlandı."

jupyter nbconvert --to notebook --execute --inplace notebooks/3_customer_sentinel.ipynb
echo "✅ Notebook 3 Tamamlandı."

jupyter nbconvert --to notebook --execute --inplace notebooks/4_growth_engine.ipynb
echo "✅ Notebook 4 Tamamlandı."

# 4. Git'e Yükle
echo "📤 GitHub'a yükleniyor..."
git add notebooks/*.ipynb
git commit -m "fix: reduce notebook size and enable static png rendering for github"
git push origin main

echo "🎉 İşlem Başarıyla Tamamlandı! GitHub'ı kontrol edebilirsiniz."

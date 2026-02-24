#!/bin/bash
# Tony ERP Print Agent - تشغيل سريع على Linux

clear

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           Tony ERP - Print Agent v1.0                     ║"
echo "║           خدمة الطباعة المباشرة                          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# التحقق من Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 غير مثبت!"
    echo "قم بتثبيته: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[✓] Python مثبت"
echo ""

# التحقق من المكتبات
if ! python3 -c "import websockets" &> /dev/null; then
    echo "[!] المكتبات غير مثبتة - جاري التثبيت..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] فشل تثبيت المكتبات"
        exit 1
    fi
    echo "[✓] تم تثبيت المكتبات"
fi

echo "[✓] المكتبات جاهزة"
echo ""

# تشغيل الخدمة
echo "═══════════════════════════════════════════════════════════"
echo "   🚀 تشغيل خدمة الطباعة..."
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "الخدمة ستعمل على: ws://localhost:9876"
echo "لإيقاف الخدمة: اضغط Ctrl+C"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""

python3 agent.py

# عند الإيقاف
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "   تم إيقاف الخدمة"
echo "═══════════════════════════════════════════════════════════"

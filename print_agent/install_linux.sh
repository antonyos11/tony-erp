#!/bin/bash
# Tony ERP Print Agent - تثبيت على Linux

echo "========================================"
echo "   Tony ERP Print Agent - تثبيت"
echo "========================================"
echo ""

# التحقق من Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 غير مثبت!"
    echo "قم بتثبيته: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[1/5] تحديث النظام..."
sudo apt update

echo ""
echo "[2/5] تثبيت CUPS (نظام الطباعة)..."
sudo apt install -y cups libcups2-dev

echo ""
echo "[3/5] تثبيت مكتبات Python..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "[ERROR] فشل تثبيت المكتبات"
    exit 1
fi

echo ""
echo "[4/5] إعداد صلاحيات الطباعة..."
sudo usermod -a -G lpadmin $USER

echo ""
echo "[5/5] إنشاء خدمة systemd..."
sudo tee /etc/systemd/system/tony-print-agent.service > /dev/null <<EOF
[Unit]
Description=Tony ERP Print Agent
After=network.target cups.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 $(pwd)/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# تفعيل الخدمة
sudo systemctl daemon-reload
sudo systemctl enable tony-print-agent.service

echo ""
echo "========================================"
echo "    ✓ اكتمل التثبيت بنجاح!"
echo "========================================"
echo ""
echo "لتشغيل الخدمة:"
echo "  sudo systemctl start tony-print-agent"
echo ""
echo "لإيقاف الخدمة:"
echo "  sudo systemctl stop tony-print-agent"
echo ""
echo "لعرض الحالة:"
echo "  sudo systemctl status tony-print-agent"
echo ""
echo "الخدمة ستعمل على: ws://localhost:9876"
echo ""

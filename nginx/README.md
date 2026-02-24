# Nginx Configurations

| ملف | الاستخدام |
|------|-----------|
| `docker.conf` | إعداد Docker Compose مع الحاويات |
| `production.conf` | إعداد الإنتاج المباشر (bare-metal مع Let's Encrypt) |

## Docker
```bash
docker-compose --profile production up -d
```

## Production (bare-metal)
```bash
sudo cp nginx/production.conf /etc/nginx/sites-available/tonyerp
sudo ln -sf /etc/nginx/sites-available/tonyerp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

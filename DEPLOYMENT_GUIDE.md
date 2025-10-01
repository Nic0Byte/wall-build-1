# 🔧 Configurazione Ambiente - Wall-Build System

Questo documento spiega come configurare correttamente il sistema per **sviluppo locale** e **produzione**.

---

## 📁 File di Configurazione Disponibili

- **`.env.local`** - Configurazione per sviluppo locale (tuo computer)
- **`.env.production`** - Configurazione per produzione (server zenet.whisprr.it)
- **`.env`** - File attivo (NON committare su Git!)

---

## 🏠 Setup Sviluppo Locale

### 1. Copia il file di configurazione locale:
```bash
# Windows PowerShell
Copy-Item .env.local .env

# Linux/Mac
cp .env.local .env
```

### 2. Avvia il server:
```bash
python main.py server
```

### 3. Apri il browser:
```
http://localhost:8000
```

### ✅ Caratteristiche sviluppo:
- CORS: Accetta tutte le origini (`*`)
- Debug: Abilitato
- Auto-reload: Attivo
- Log: Formato testo leggibile
- Password admin: `admin123`

---

## 🚀 Setup Produzione (zenet.whisprr.it)

### 1. Copia il file di configurazione produzione:
```bash
# Windows PowerShell
Copy-Item .env.production .env

# Linux/Mac
cp .env.production .env
```

### 2. **IMPORTANTE**: Modifica `.env` e cambia questi valori:

#### 🔑 SECRET_KEY (OBBLIGATORIO):
Genera una nuova chiave sicura:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Copia l'output e sostituisci `CAMBIARE_QUESTA_CHIAVE_IN_PRODUZIONE_GENERANE_UNA_NUOVA`

#### 🔒 ADMIN_PASSWORD (OBBLIGATORIO):
Cambia `CambiareQuestaPwd2024!` con una password forte

#### 🌐 CORS_ORIGINS (già configurato):
```properties
CORS_ORIGINS=https://zenet.whisprr.it,https://www.zenet.whisprr.it,http://localhost:8000
```

### 3. Verifica le impostazioni:
```properties
DEBUG=false
DEVELOPMENT_MODE=false
LOG_LEVEL=INFO
RELOAD=false
```

### 4. Avvia il server in produzione:

#### Opzione A - Uvicorn (semplice):
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Opzione B - Gunicorn (raccomandato per Linux):
```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Opzione C - Systemd (per avvio automatico):
Crea file `/etc/systemd/system/wallbuild.service`:
```ini
[Unit]
Description=Wall-Build API Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/wall-build_v3
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Poi:
```bash
sudo systemctl daemon-reload
sudo systemctl enable wallbuild
sudo systemctl start wallbuild
sudo systemctl status wallbuild
```

---

## 🔒 Configurazione Reverse Proxy (Nginx)

Se usi Nginx come reverse proxy per HTTPS, crea questo file:

`/etc/nginx/sites-available/zenet.whisprr.it`:
```nginx
server {
    listen 80;
    server_name zenet.whisprr.it www.zenet.whisprr.it;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name zenet.whisprr.it www.zenet.whisprr.it;

    # Certificati SSL (usa Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/zenet.whisprr.it/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/zenet.whisprr.it/privkey.pem;

    # Configurazione SSL moderna
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # File upload size
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support (se necessario)
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Attiva la configurazione:
```bash
sudo ln -s /etc/nginx/sites-available/zenet.whisprr.it /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔐 Certificato SSL con Let's Encrypt

```bash
# Installa Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Ottieni certificato SSL
sudo certbot --nginx -d zenet.whisprr.it -d www.zenet.whisprr.it

# Auto-rinnovo (già configurato)
sudo certbot renew --dry-run
```

---

## 📊 Monitoraggio e Log

### Visualizza log in tempo reale:
```bash
# File log
tail -f logs/wallbuild.log

# Systemd logs
sudo journalctl -u wallbuild -f
```

### Verifica stato servizio:
```bash
sudo systemctl status wallbuild
```

---

## 🧪 Test della Configurazione

### Test locale:
```bash
curl http://localhost:8000/api/v1/health
```

### Test produzione:
```bash
curl https://zenet.whisprr.it/api/v1/health
```

Risposta attesa:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## ⚠️ Checklist Pre-Deployment

Prima di andare in produzione, verifica:

- [ ] `SECRET_KEY` cambiata (generata nuova)
- [ ] `ADMIN_PASSWORD` cambiata
- [ ] `CORS_ORIGINS` configurato con domini corretti
- [ ] `DEBUG=false`
- [ ] `DEVELOPMENT_MODE=false`
- [ ] `LOG_LEVEL=INFO`
- [ ] Certificato SSL configurato
- [ ] Nginx configurato come reverse proxy
- [ ] Firewall configurato (porta 80, 443 aperte)
- [ ] Backup database configurato
- [ ] Servizio systemd configurato per avvio automatico

---

## 🆘 Troubleshooting

### Problema: CORS error in produzione
**Soluzione**: Verifica che `CORS_ORIGINS` contenga il dominio corretto:
```properties
CORS_ORIGINS=https://zenet.whisprr.it
```

### Problema: 502 Bad Gateway
**Soluzione**: Verifica che il servizio Python sia in esecuzione:
```bash
sudo systemctl status wallbuild
curl http://localhost:8000/api/v1/health
```

### Problema: Upload file fallisce
**Soluzione**: Aumenta `client_max_body_size` in Nginx e `MAX_UPLOAD_SIZE` nel `.env`

### Problema: Certificato SSL scaduto
**Soluzione**: Rinnova con Certbot:
```bash
sudo certbot renew
sudo systemctl reload nginx
```

---

## 📞 Supporto

Per problemi o domande:
- Controlla i log: `logs/wallbuild.log`
- Verifica lo stato del servizio: `sudo systemctl status wallbuild`
- Testa l'endpoint health: `/api/v1/health`

---

## 🔄 Switch tra Ambienti

### Da Locale a Produzione:
```bash
Copy-Item .env.production .env
# Modifica SECRET_KEY e ADMIN_PASSWORD
python main.py server
```

### Da Produzione a Locale:
```bash
Copy-Item .env.local .env
python main.py server
```

---

**Nota**: Non committare MAI il file `.env` su Git! È già incluso nel `.gitignore`.

# Wall-Build Dependencies Guide

## 📦 Panoramica delle Dipendenze

Wall-Build utilizza diverse categorie di dipendenze per funzionalità specifiche:

## 🎯 Requirements Files

- **`requirements.txt`**: Dipendenze core necessarie per il funzionamento base
- **`requirements-dev.txt`**: Dipendenze aggiuntive per sviluppo e testing  
- **`requirements-prod.txt`**: Dipendenze ottimizzate per produzione Linux

## 📋 Dipendenze Core (requirements.txt)

### Geometria e Plotting
- **shapely**: Operazioni geometriche avanzate, gestione poligoni e calcoli spaziali
- **numpy**: Calcoli numerici, array operations per geometrie
- **matplotlib**: Generazione grafici, visualizzazioni, preview pareti
- **svgpathtools**: Parsing e manipolazione file SVG

### Web Framework & API
- **fastapi**: Framework web moderno, API REST, WebSocket support
- **uvicorn**: Server ASGI ad alte prestazioni
- **jinja2**: Template engine per pagine HTML
- **python-multipart**: Gestione upload file multipart

### Database & ORM
- **sqlalchemy**: ORM robusto per gestione database
- **alembic**: Sistema di migrazione database (opzionale)

### Autenticazione & Sicurezza
- **python-jose**: JWT token generation e validation
- **passlib**: Password hashing sicuro con bcrypt
- **cryptography**: Operazioni crittografiche cross-platform

### Validazione Dati
- **pydantic**: Validazione e serializzazione dati
- **pydantic[email]**: Supporto validazione email

### Export & File Processing
- **reportlab**: Generazione PDF professionali
- **ezdxf**: Creazione e manipolazione file DXF/DWG
- **dxfgrabber**: Parser DWG avanzato (opzionale)
- **Pillow**: Elaborazione e manipolazione immagini

### Utility & Performance
- **orjson**: JSON parsing/serialization ultra-veloce
- **requests**: HTTP client per testing e API calls
- **python-dotenv**: Supporto file .env per configurazione

## 🛠️ Dipendenze Sviluppo (requirements-dev.txt)

### Testing Framework
- **pytest**: Framework di testing robusto e flessibile
- **pytest-asyncio**: Testing per codice asincrono
- **pytest-cov**: Coverage testing e reportistica
- **httpx**: Client HTTP asincrono per test FastAPI

### Code Quality
- **black**: Formatter automatico del codice Python
- **isort**: Ordinamento automatico import
- **flake8**: Linting e controllo stile codice
- **mypy**: Type checking statico

### Documentation
- **sphinx**: Generazione documentazione automatica
- **sphinx-rtd-theme**: Tema ReadTheDocs per documentazione

### Debugging & Profiling
- **ipdb**: Debugger interattivo migliorato
- **memory-profiler**: Profiling uso memoria
- **line-profiler**: Profiling performance riga per riga

### Development Utilities
- **watchdog**: Monitoring modifiche file per auto-reload
- **rich**: Output terminal colorato e formattato
- **bandit**: Security linter per vulnerabilità
- **safety**: Scanner vulnerabilità dipendenze

## 🚀 Dipendenze Produzione (requirements-prod.txt)

### Production Server
- **gunicorn**: WSGI server robusto per deployment Linux
- **gevent**: Worker asincroni per alta concorrenza

### Process Management
- **supervisor**: Gestione e monitoring processi

### Performance & Caching
- **redis**: Cache distribuita e session storage
- **hiredis**: Client Redis ottimizzato

### Monitoring & Logging
- **prometheus-client**: Metriche per monitoring Prometheus
- **structlog**: Logging strutturato
- **sentry-sdk**: Error tracking e performance monitoring

### Security Hardening
- **pyopenssl**: Supporto SSL/TLS avanzato
- **certifi**: Bundle certificati CA aggiornati

### Database Production
- **psycopg2-binary**: Driver PostgreSQL ottimizzato
- **mysqlclient**: Driver MySQL (opzionale)

### System Integration
- **python-systemd**: Integrazione con systemd Linux
- **setproctitle**: Modifiche nome processo
- **healthcheck**: Endpoint health check per load balancer

## 📥 Installazione

### Sviluppo Locale
```bash
# Base
pip install -r requirements.txt

# Con tools di sviluppo
pip install -r requirements-dev.txt
```

### Produzione Linux
```bash
# Produzione completa
pip install -r requirements-prod.txt

# O setup automatico
chmod +x setup_linux.sh
./setup_linux.sh
```

### Docker (esempio)
```dockerfile
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Produzione
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt
```

## 🔧 Gestione Versioni

### Principi di Versioning
- **Versioni pinned**: Per stability in produzione
- **Range compatibili**: Per flessibilità sviluppo
- **Separazione concern**: Dev vs Prod dependencies

### Update Dipendenze
```bash
# Check outdated packages
pip list --outdated

# Update sicuro (rispetta ranges)
pip install --upgrade -r requirements.txt

# Force update (attenzione!)
pip install --upgrade --force-reinstall -r requirements.txt
```

### Testing Compatibilità
```bash
# Test con nuove versioni
pip install -r requirements-dev.txt
pytest tests/

# Test produzione
pip install -r requirements-prod.txt
python main.py server --dev
```

## 🐛 Troubleshooting

### Errori Comuni

**ImportError: No module named 'xxx'**
```bash
pip install -r requirements.txt --force-reinstall
```

**Conflict dependencies**
```bash
pip-tools compile requirements.in
pip-sync requirements.txt
```

**Slow installation**
```bash
pip install --no-deps -r requirements.txt
pip check  # Verifica dipendenze
```

### Platform-Specific Issues

**Linux: build errors**
```bash
# Ubuntu/Debian
sudo apt install python3-dev build-essential

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

**macOS: compilation issues**
```bash
xcode-select --install
brew install python@3.11
```

## 📊 Dependency Analysis

### Size Impact
- **Core only**: ~50MB
- **With dev tools**: ~150MB  
- **Full production**: ~80MB

### Critical Path
1. **shapely** + **numpy**: Geometria core
2. **fastapi** + **uvicorn**: Web server
3. **sqlalchemy**: Database
4. **reportlab** + **ezdxf**: Export functionality

### Optional Components
- **dxfgrabber**: Advanced DWG parsing
- **redis**: Caching (produzione)
- **sentry-sdk**: Error tracking
- **prometheus-client**: Monitoring

Le dipendenze sono organizzate per supportare deployment scalabili da sviluppo locale a produzione enterprise.

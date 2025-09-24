# 🏗️ **WALL-BUILD v3** - Sistema Professionale per Progettazione Pareti

## 📋 **Descrizione Progetto**

**Wall-Build** è un sistema avanzato per la progettazione automatica di pareti modulari utilizzando blocchi standardizzati. Il software analizza file CAD (SVG, DWG, DXF), calcola automaticamente il packing ottimale dei blocchi e genera documentazione tecnica completa per la produzione.

### 🎯 **Caratteristiche Principali**

- **🔍 Parser Universale**: Supporto SVG, DWG, DXF con fallback intelligente
- **🧩 Algoritmo Packing**: Ottimizzazione automatica disposizione blocchi
- **📊 Analisi Qualità**: Controllo sovrapposizioni, blocchi fuori parete, efficienza
- **📄 Export Multi-formato**: JSON, PDF, DXF per CAD, visualizzazioni PNG
- **🔐 Sistema Sicuro**: Autenticazione JWT, gestione utenti, database SQLAlchemy
- **🌐 Web Interface**: API REST + Frontend responsivo
- **⚙️ Configurabile**: Environment variables, temi colori, dimensioni blocchi

---

## 🚀 **Quick Start**

### 1. **Setup Ambiente**
```bash
# Clona repository
git clone https://github.com/Nic0Byte/wall-build.git
cd wall-build_v3

# Installa dipendenze
pip install -r requirements.txt

# Configura environment
cp .env.example .env
# Modifica .env con le tue configurazioni
```

### 2. **Inizializza Database**
```bash
python -c "from database.config import init_database; init_database()"
```

### 3. **Avvia Server**
```bash
# Sviluppo
python main.py server --dev

# Produzione
python main.py server
```

### 4. **Accedi all'Interfaccia**
- **URL**: http://localhost:8000
- **Credenziali Admin**: `admin` / `WallBuild2024!`
- **API Docs**: http://localhost:8000/docs

---

## 🏗️ **Architettura Sistema**

### 📁 **Struttura Modulare**
```
wall-build_v3/
├── 🌐 api/              # REST API e autenticazione
├── 🗄️  database/         # Modelli e servizi database
├── 🔧 utils/            # Utilities e configurazioni
├── 📄 parsers/          # Parser file CAD (SVG/DWG/DXF)
├── 📤 exporters/        # Export JSON/PDF/DXF
├── 🧱 core/             # Algoritmi packing e analisi
├── 🧪 tests/           # Suite di test completa
├── 📊 static/          # Frontend web interface
└── 📋 templates/       # Template HTML
```

### 🔄 **Flusso di Lavoro**
1. **Upload File**: Carica file CAD (SVG/DWG/DXF)
2. **Parsing**: Estrazione geometrie parete e aperture
3. **Packing**: Calcolo disposizione ottimale blocchi
4. **Analisi**: Controllo qualità e metriche
5. **Export**: Generazione documentazione tecnica
6. **Download**: PDF reports, DXF per CAD, JSON dati

---

## 🧱 **Algoritmo Packing**

### 📐 **Blocchi Standard**
- **Tipo A**: 1239mm × 495mm (Grande)
- **Tipo B**: 826mm × 495mm (Medio)  
- **Tipo C**: 413mm × 495mm (Piccolo)

### 🎯 **Strategia Ottimizzazione**
- **Row-based packing**: Riempimento per righe con offset
- **Multi-strategy**: Prova diverse combinazioni A-B-C
- **Custom pieces**: Gestione automatica pezzi irregolari
- **Quality analysis**: Controllo sovrapposizioni e posizionamento

### 📊 **Metriche Qualità**
- **Efficienza**: Percentuale blocchi standard vs custom
- **Coverage**: Copertura area parete
- **Waste ratio**: Rapporto spreco materiale
- **Quality score**: Punteggio complessivo 0-100

---

## 🔧 **Configurazione Avanzata**

### 📄 **Environment Variables**
Vedi `.env.example` per tutte le opzioni disponibili:

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database
DATABASE_URL=sqlite:///data/wallbuild.db

# Security
SECRET_KEY=your-production-secret-key

# Blocchi personalizzati
BLOCK_WIDTHS=1239,826,413
BLOCK_HEIGHT=495
```

### 🎨 **Personalizzazioni**
- **Dimensioni blocchi**: Configurabili via environment o frontend
- **Temi colori**: Personalizzazione palette visualizzazioni
- **Parametri algoritmo**: Tolleranze, margini, strategie
- **Export formats**: Template PDF, layout DXF, formati JSON

---

## 🧪 **Testing & Quality**

### 🔍 **Test Suite**
```bash
# Test completo
python tests/test_master.py

# Test rapido
python tests/test_master.py quick

# Test file specifico
python tests/test_master.py file esempio.svg
```

### 📈 **Quality Assurance**
- **Parsing tests**: Validazione file CAD
- **Packing tests**: Controllo algoritmi ottimizzazione
- **Export tests**: Verifica output formats
- **Integration tests**: Test end-to-end workflow

---

## 🚀 **Deployment**

### 🐳 **Docker (Raccomandato)**
```bash
# Build image
docker build -t wall-build:latest .

# Run container
docker run -p 8000:8000 -v ./data:/app/data wall-build:latest
```

### 🖥️ **Server Linux**
```bash
# Installa dipendenze produzione
pip install -r requirements-prod.txt

# Setup systemd service
sudo cp wall-build.service /etc/systemd/system/
sudo systemctl enable wall-build
sudo systemctl start wall-build
```

### ☁️ **Cloud Deployment**
- **Heroku**: Ready con `Procfile`
- **AWS/Azure**: Container support
- **Railway/Render**: Auto-deploy da Git

---

## 📚 **Documentazione Tecnica**

### 📖 **Guide Dettagliate**
- **[DEPENDENCIES.md](DEPENDENCIES.md)**: Gestione dipendenze e versioning
- **[README_TESTS.md](README_TESTS.md)**: Suite di test e QA
- **[ENV_SETUP.md](ENV_SETUP.md)**: Configurazione environment
- **[REQUISITI_PORTE_FINESTRE.md](REQUISITI_PORTE_FINESTRE.md)**: Specifiche tecniche

### 🔗 **API Documentation**
- **OpenAPI/Swagger**: `/docs` (development)
- **ReDoc**: `/redoc` (production)
- **Postman Collection**: Disponibile su richiesta

---

## 🤝 **Contribuire al Progetto**

### 🔧 **Setup Sviluppo**
```bash
# Installa dipendenze development
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Linting
flake8 .
black .
```

### 📋 **Linee Guida**
- **Code Style**: PEP 8 con Black formatter
- **Testing**: Coverage minima 80%
- **Docs**: Docstrings per funzioni pubbliche
- **Git**: Commit messages convenzionali

---

## 🛠️ **Troubleshooting**

### ❓ **Problemi Comuni**

**🚫 Server non si avvia**
```bash
# Controlla configurazione
python -c "from utils.config import print_configuration_summary; print_configuration_summary()"

# Verifica database
python -c "from database.config import init_database; init_database()"
```

**🔍 File parsing fallisce**
```bash
# Test parsing specifico
python tests/test_parsing_fallback.py
```

**📊 Export non funziona**
```bash
# Verifica dipendenze
pip install reportlab ezdxf
```

### 🆘 **Supporto**
- **Issues**: [GitHub Issues](https://github.com/Nic0Byte/wall-build/issues)
- **Documentazione**: File README specifici per modulo
- **Logs**: Controllo `logs/wallbuild.log` per errori dettagliati

---

## 📄 **Licenza & Credits**

**Wall-Build v3** - Sistema sviluppato per ottimizzazione progettazione pareti modulari.

### 🏢 **Utilizzo Commerciale**
Contattare per licensing e supporto commerciale.

### 🙏 **Riconoscimenti**
- **Shapely**: Operazioni geometriche avanzate
- **FastAPI**: Framework web moderno
- **ReportLab**: Generazione PDF professionale
- **SQLAlchemy**: ORM robusto per database

---

*Ultima modifica: Settembre 2025 - v3.0*
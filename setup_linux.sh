#!/bin/bash

# Wall-Build Setup Script per Linux
# Questo script configura l'ambiente per il sistema Wall-Build su Linux

set -e  # Esci se qualsiasi comando fallisce

echo "🐧 Wall-Build Linux Setup"
echo "========================="

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per stampare messaggi colorati
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Controlla prerequisiti di sistema
print_info "Controllo prerequisiti di sistema..."

# Controlla Python 3.8+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION trovato"
    
    # Controlla versione minima
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
        print_success "Versione Python compatibile"
    else
        print_error "Python 3.8+ richiesto, trovato $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python3 non trovato. Installare con: sudo apt install python3 python3-pip"
    exit 1
fi

# Controlla pip
if command -v pip3 &> /dev/null; then
    print_success "pip3 trovato"
else
    print_error "pip3 non trovato. Installare con: sudo apt install python3-pip"
    exit 1
fi

# 2. Crea ambiente virtuale
print_info "Configurazione ambiente virtuale..."

if [ ! -d "venv" ]; then
    print_info "Creazione ambiente virtuale..."
    python3 -m venv venv
    print_success "Ambiente virtuale creato"
else
    print_warning "Ambiente virtuale già esistente"
fi

# Attiva ambiente virtuale
source venv/bin/activate
print_success "Ambiente virtuale attivato"

# 3. Aggiorna pip e installa dipendenze
print_info "Installazione dipendenze..."

pip install --upgrade pip

# Installa dipendenze base
print_info "Installazione dipendenze base..."
pip install -r requirements.txt

# Chiedi se installare dipendenze di sviluppo
read -p "Installare anche le dipendenze di sviluppo? [y/N]: " install_dev
if [[ $install_dev =~ ^[Yy]$ ]]; then
    print_info "Installazione dipendenze di sviluppo..."
    pip install -r requirements-dev.txt
    print_success "Dipendenze di sviluppo installate"
fi

print_success "Dipendenze installate"

# 4. Configura directory per Linux
print_info "Configurazione directory di sistema..."

# Crea directory XDG-compliant
XDG_DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
XDG_CACHE_HOME=${XDG_CACHE_HOME:-"$HOME/.cache"}

WALLBUILD_DATA_DIR="$XDG_DATA_HOME/wallbuild"
WALLBUILD_CACHE_DIR="$XDG_CACHE_HOME/wallbuild"

mkdir -p "$WALLBUILD_DATA_DIR"
mkdir -p "$WALLBUILD_CACHE_DIR"

print_success "Directory create: $WALLBUILD_DATA_DIR"
print_success "Cache directory: $WALLBUILD_CACHE_DIR"

# 5. Inizializza database
print_info "Inizializzazione database..."

export WALLBUILD_DB_PATH="$WALLBUILD_DATA_DIR/wallbuild.db"
export WALLBUILD_OUTPUT_DIR="$WALLBUILD_CACHE_DIR"

python3 -c "
from database.config import init_database
init_database()
print('Database inizializzato con successo')
"

print_success "Database configurato in $WALLBUILD_DB_PATH"

# 6. Crea script di avvio
print_info "Creazione script di avvio..."

cat > start_wallbuild.sh << 'EOF'
#!/bin/bash

# Wall-Build Startup Script

# Configura variabili d'ambiente
export WALLBUILD_DB_PATH="$HOME/.local/share/wallbuild/wallbuild.db"
export WALLBUILD_OUTPUT_DIR="$HOME/.cache/wallbuild"
export WALLBUILD_HOST="0.0.0.0"
export WALLBUILD_PORT="8000"

# Per produzione, imposta una chiave segreta sicura
# export WALLBUILD_SECRET_KEY="your_secure_secret_key_here"

# Attiva ambiente virtuale
source venv/bin/activate

# Avvia server
echo "🚀 Avvio Wall-Build Server..."
echo "🌐 Il server sarà disponibile su http://localhost:8000"
echo "🛑 Premi Ctrl+C per fermare"

python3 main.py server
EOF

chmod +x start_wallbuild.sh
print_success "Script di avvio creato: ./start_wallbuild.sh"

# 7. Crea file di configurazione ambiente
print_info "Creazione file di configurazione..."

cat > .env.example << 'EOF'
# Wall-Build Environment Configuration per Linux

# Database
WALLBUILD_DB_PATH=/home/user/.local/share/wallbuild/wallbuild.db

# Output directory  
WALLBUILD_OUTPUT_DIR=/home/user/.cache/wallbuild

# Server configuration
WALLBUILD_HOST=0.0.0.0
WALLBUILD_PORT=8000

# Security (IMPORTANTE: cambiare in produzione!)
WALLBUILD_SECRET_KEY=your_secure_secret_key_here
WALLBUILD_TOKEN_EXPIRE_MINUTES=120

# Optional: Log level
# WALLBUILD_LOG_LEVEL=INFO
EOF

print_success "File di esempio creato: .env.example"

# 8. Verifica installazione
print_info "Verifica installazione..."

python3 -c "
try:
    import fastapi, uvicorn, shapely, matplotlib, reportlab, ezdxf
    print('✅ Tutte le dipendenze importate correttamente')
except ImportError as e:
    print(f'❌ Errore importazione: {e}')
    exit(1)
"

# 9. Informazioni finali
echo ""
echo "🎉 Setup completato con successo!"
echo ""
print_info "Per avviare Wall-Build:"
echo "   ./start_wallbuild.sh"
echo ""
print_info "Alternative manuali:"
echo "   source venv/bin/activate"
echo "   python3 main.py server"
echo ""
print_info "Per personalizzare la configurazione:"
echo "   cp .env.example .env"
echo "   # Modifica .env con i tuoi valori"
echo "   source .env && python3 main.py server"
echo ""
print_warning "IMPORTANTE per produzione:"
echo "   - Cambia WALLBUILD_SECRET_KEY in .env"
echo "   - Considera l'uso di un proxy reverse (nginx)"
echo "   - Configura firewall appropriato"
echo ""
print_success "Sistema pronto per l'uso! 🚀"

"""
Database Models per Sistema Parametri Materiali
Gestisce materiali, spessori, guide e configurazioni di progetto
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()

class MaterialType(enum.Enum):
    """Tipi di materiale supportati."""
    TRUCIOLATO = "truciolato"
    MDF = "mdf" 
    COMPENSATO = "compensato"
    OSB = "osb"
    ALTRO = "altro"

class GuideType(enum.Enum):
    """Tipologie di guide supportate."""
    GUIDE_50MM = "50mm"
    GUIDE_75MM = "75mm" 
    GUIDE_100MM = "100mm"

class WallPosition(enum.Enum):
    """Posizione parete rispetto a muri esistenti."""
    LIBERA = "libera"           # Parete completamente libera
    APPOGGIATA_UN_LATO = "appoggiata_un_lato"  # Appoggiata a un muro esistente
    APPOGGIATA_DUE_LATI = "appoggiata_due_lati"  # Tra due muri esistenti
    INCASSATA = "incassata"     # Completamente incassata

class Material(Base):
    """Modello per i materiali disponibili."""
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    type = Column(Enum(MaterialType), nullable=False)
    
    # Spessori disponibili per questo materiale (JSON array)
    available_thicknesses = Column(Text, nullable=False)  # Es: "[10, 14, 18, 25]"
    
    # Proprietà tecniche
    density_kg_m3 = Column(Float, nullable=True)         # Densità kg/m³
    moisture_resistance = Column(Boolean, default=False)  # Resistenza umidità
    fire_class = Column(String(10), nullable=True)       # Classe fuoco (A1, B, C, etc.)
    
    # Metadata
    supplier = Column(String(200), nullable=True)        # Fornitore
    notes = Column(Text, nullable=True)                   # Note tecniche
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relazioni
    project_configs = relationship("ProjectMaterialConfig", back_populates="material")
    
    def __repr__(self):
        return f"<Material(name='{self.name}', type='{self.type.value}')>"

class Guide(Base):
    """Modello per le guide disponibili.""" 
    __tablename__ = 'guides'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(GuideType), nullable=False)
    
    # Dimensioni in mm
    width_mm = Column(Integer, nullable=False)            # Larghezza guida
    depth_mm = Column(Integer, nullable=False)            # Profondità guida
    
    # Proprietà tecniche
    max_load_kg = Column(Float, nullable=True)           # Carico massimo kg
    material_compatibility = Column(Text, nullable=True)  # Materiali compatibili (JSON)
    
    # Metadata
    manufacturer = Column(String(200), nullable=True)    # Produttore
    model_code = Column(String(50), nullable=True)       # Codice modello
    price_per_meter = Column(Float, nullable=True)       # Prezzo al metro
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relazioni
    project_configs = relationship("ProjectMaterialConfig", back_populates="guide")
    
    def __repr__(self):
        return f"<Guide(name='{self.name}', type='{self.type.value}', width={self.width_mm}mm)>"

class ProjectMaterialConfig(Base):
    """Configurazione materiali per un progetto specifico."""
    __tablename__ = 'project_material_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Riferimenti
    user_id = Column(Integer, nullable=False, index=True)
    project_name = Column(String(200), nullable=False)
    
    # Materiale e spessore
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    material_thickness_mm = Column(Integer, nullable=False)  # Spessore specifico scelto
    
    # Guide
    guide_id = Column(Integer, ForeignKey('guides.id'), nullable=False)
    
    # Calcoli automatici risultanti
    closure_thickness_mm = Column(Integer, nullable=False)   # Spessore chiusura calcolato
    
    # Posizione parete e vincoli
    wall_position = Column(Enum(WallPosition), nullable=False, default=WallPosition.LIBERA)
    ceiling_height_mm = Column(Integer, nullable=True)       # Altezza soffitto (None = arriva a soffitto)
    
    # Lati con muri esistenti (JSON array di stringhe)
    existing_walls_sides = Column(Text, nullable=True)       # Es: ["left", "bottom"]
    
    # Configurazioni speciali per moduli particolari
    special_modules_config = Column(Text, nullable=True)     # JSON con configurazioni speciali
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relazioni
    material = relationship("Material", back_populates="project_configs")
    guide = relationship("Guide", back_populates="project_configs")
    
    def calculate_closure_thickness(self):
        """Calcola lo spessore di chiusura automaticamente."""
        # Logica: spessore_materiale + larghezza_guida + spessore_materiale
        if self.material and self.guide:
            self.closure_thickness_mm = (self.material_thickness_mm * 2) + self.guide.width_mm
        return self.closure_thickness_mm
    
    def get_existing_walls_list(self):
        """Restituisce la lista dei lati con muri esistenti."""
        if not self.existing_walls_sides:
            return []
        import json
        try:
            return json.loads(self.existing_walls_sides)
        except:
            return []
    
    def set_existing_walls_list(self, sides_list):
        """Imposta la lista dei lati con muri esistenti."""
        import json
        self.existing_walls_sides = json.dumps(sides_list) if sides_list else None
    
    def __repr__(self):
        return f"<ProjectMaterialConfig(project='{self.project_name}', material_id={self.material_id}, guide_id={self.guide_id})>"

class MaterialRule(Base):
    """Regole per combinazioni materiale + guida."""
    __tablename__ = 'material_rules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    guide_id = Column(Integer, ForeignKey('guides.id'), nullable=False)
    
    # Regole specifiche
    is_compatible = Column(Boolean, default=True)           # Se la combinazione è compatibile
    min_thickness_mm = Column(Integer, nullable=True)       # Spessore minimo materiale
    max_thickness_mm = Column(Integer, nullable=True)       # Spessore massimo materiale
    
    # Fattori di correzione
    tolerance_mm = Column(Float, default=0.0)               # Tolleranza aggiuntiva
    strength_factor = Column(Float, default=1.0)            # Fattore di resistenza
    
    # Note tecniche
    technical_notes = Column(Text, nullable=True)           # Note per questa combinazione
    warning_message = Column(String(500), nullable=True)    # Avviso se necessario
    
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relazioni
    material = relationship("Material")
    guide = relationship("Guide")
    
    def __repr__(self):
        return f"<MaterialRule(material_id={self.material_id}, guide_id={self.guide_id}, compatible={self.is_compatible})>"

class ProjectTemplate(Base):
    """Template di configurazioni predefinite per progetti comuni."""
    __tablename__ = 'project_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Configurazione predefinita (JSON)
    default_material_type = Column(Enum(MaterialType), nullable=False)
    default_thickness_mm = Column(Integer, nullable=False)
    default_guide_type = Column(Enum(GuideType), nullable=False)
    default_wall_position = Column(Enum(WallPosition), default=WallPosition.LIBERA)
    
    # Template specifici (es: "Parete bagno", "Parete cucina", "Divisorio ufficio")
    category = Column(String(100), nullable=True)          # Categoria template
    typical_dimensions = Column(Text, nullable=True)       # Dimensioni tipiche (JSON)
    
    # Metadata
    usage_count = Column(Integer, default=0)               # Numero di utilizzi
    created_by_user_id = Column(Integer, nullable=True)    # Creato da utente (None = sistema)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)             # Visibile a tutti gli utenti
    
    def __repr__(self):
        return f"<ProjectTemplate(name='{self.name}', category='{self.category}')>"

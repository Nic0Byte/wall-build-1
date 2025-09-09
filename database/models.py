"""
Database Models per Wall-Build
Modelli SQLAlchemy per gestione utenti e sessioni
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    """Modello utente per il database."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=True)
    company = Column(String(200), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

class Session(Base):
    """Modello sessione per il database.""" 
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    def __repr__(self):
        return f"<Session(user_id={self.user_id}, expires_at='{self.expires_at}')>"

class Project(Base):
    """Modello progetto per il database."""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<Project(name='{self.name}', user_id={self.user_id})>"

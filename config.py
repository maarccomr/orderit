import os

class Config:
    """Configuración principal para la aplicación del restaurante."""
    # Clave secreta para la aplicación, se obtiene del entorno o usa un valor por defecto
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-por-defecto'
    
    # URI de la base de datos, usando SQLite por defecto
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///restaurant.db'
    
    # Deshabilitar el seguimiento de modificaciones de SQLAlchemy para ahorrar recursos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Permitir caracteres no ASCII en JSON (para tildes y eñes en español)
    JSON_AS_ASCII = False

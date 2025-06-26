"""
Configuración y carga de variables de entorno para el servicio CrewAI.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Settings:
    """Configuración centralizada del servicio CrewAI."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # LlamaCloud Configuration
    LLAMACLOUD_API_KEY: str = os.getenv("LLAMACLOUD_API_KEY", "")
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    
    # Service Authentication
    INGESTION_SERVICE_TOKEN: str = os.getenv("INGESTION_SERVICE_TOKEN", "")
    
    # Application Configuration
    PORT: int = int(os.getenv("PORT", "8001"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CrewAI Configuration
    CREW_VERBOSE: bool = os.getenv("CREW_VERBOSE", "True").lower() == "true"
    CREW_MEMORY: bool = os.getenv("CREW_MEMORY", "True").lower() == "true"
    PROCESSING_TIMEOUT: int = int(os.getenv("PROCESSING_TIMEOUT", "300"))
    
    # Document Ingestion Configuration
    DOCUMENT_INGESTION_URL: str = os.getenv("DOCUMENT_INGESTION_URL", "https://pipefy-document-ingestion-modular.onrender.com")
    
    @classmethod
    def validate_required_vars(cls) -> list[str]:
        """
        Valida que las variables de entorno requeridas estén configuradas.
        
        Returns:
            Lista de variables faltantes (vacía si todas están configuradas)
        """
        required_vars = {
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_ANON_KEY": cls.SUPABASE_ANON_KEY,
            "INGESTION_SERVICE_TOKEN": cls.INGESTION_SERVICE_TOKEN,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        return missing_vars
    
    @classmethod
    def get_auth_headers(cls) -> dict:
        """Retorna los headers para autenticación del servicio."""
        return {
            "Authorization": f"Bearer {cls.INGESTION_SERVICE_TOKEN}",
            "Content-Type": "application/json"
        }
    
    @classmethod
    def get_openai_config(cls) -> dict:
        """Retorna la configuración para OpenAI."""
        return {
            "api_key": cls.OPENAI_API_KEY,
            "model": "gpt-4o-mini",  # Modelo por defecto
            "temperature": 0.1,      # Baja temperatura para consistencia
        }

# Instancia global de configuración
settings = Settings()

# Validar variables requeridas al importar
missing_vars = settings.validate_required_vars()
if missing_vars:
    print(f"⚠️  ADVERTENCIA: Variables de entorno faltantes: {', '.join(missing_vars)}")
    print("   Asegúrate de configurar el archivo .env antes de ejecutar el servicio.")
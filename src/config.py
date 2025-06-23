from typing import Optional
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # IDs de fases en Pipefy
    PIPEFY_COMPLETE_DOCS_PHASE_ID: str = Field(..., description="ID de la fase para documentación completa")
    PIPEFY_INCOMPLETE_DOCS_PHASE_ID: str = Field(..., description="ID de la fase para documentación incompleta")
    PIPEFY_ERROR_PHASE_ID: str = Field(..., description="ID de la fase para casos con error")
    
    # ID del campo de estado en Pipefy
    PIPEFY_STATUS_FIELD_ID: str = Field(..., description="ID del campo de estado en Pipefy")
    
    # Webhook secret para validación
    PIPEFY_WEBHOOK_SECRET: Optional[str] = Field(None, description="Secret para validar webhooks de Pipefy")
    
    class Config:
        env_file = ".env"
        case_sensitive = True 
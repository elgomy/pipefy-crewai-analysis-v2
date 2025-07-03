#!/usr/bin/env python3
"""
Pipefy CrewAI Analysis Service v2.0 - ENFOQUE HÍBRIDO INTELIGENTE
Servicio especializado en análisis de documentos usando triagem_agente

ARQUITECTURA HÍBRIDA:
- Este servicio se enfoca ÚNICAMENTE en el análisis con IA
- Usa herramientas SIMPLES que llaman al backend para operaciones complejas
- NO contiene lógica de APIs externas, solo análisis y razonamiento
"""

import os
import asyncio
import logging
import json
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import re

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Header
from pydantic import BaseModel, Field
from supabase import create_client, Client
from dotenv import load_dotenv

# Importaciones de CrewAI
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
import yaml

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# URL del backend (Document Ingestion Service)
BACKEND_URL = os.getenv("DOCUMENT_INGESTION_URL", "https://pipefy-document-ingestion-modular.onrender.com")

# Cliente Supabase global
supabase_client: Optional[Client] = None

# ============================================================================
# HERRAMIENTAS SIMPLES QUE LLAMAN AL BACKEND
# ============================================================================
# NOTA: Las herramientas ahora están centralizadas en src/tools/backend_api_tools.py
# para mantener la arquitectura modular limpia y evitar duplicación de código.

# ============================================================================
# CONFIGURACIÓN DEL AGENTE ENFOCADO
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação FastAPI."""
    global supabase_client
    
    # Startup
    logger.info("🤖 Iniciando Pipefy CrewAI Analysis Service v2.0 - HÍBRIDO INTELIGENTE...")
    
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logger.error("ERRO: Variáveis SUPABASE_URL e SUPABASE_ANON_KEY são obrigatórias.")
        raise RuntimeError("Configuração Supabase incompleta.")
    
    if not OPENAI_API_KEY:
        logger.error("ERRO: Variável OPENAI_API_KEY é obrigatória.")
        raise RuntimeError("Token OpenAI não configurado.")
    
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Cliente Supabase inicializado com sucesso.")
    except Exception as e:
        logger.error(f"ERRO ao inicializar cliente Supabase: {e}")
        raise RuntimeError(f"Falha na inicialização do Supabase: {e}")
    
    logger.info(f"🔗 Backend configurado en: {BACKEND_URL}")
    logger.info("🎯 Agente de Triagem configurado com herramientas híbridas.")
    
    yield
    
    # Shutdown
    logger.info("INFO: Encerrando CrewAI Analysis Service...")

app = FastAPI(
    lifespan=lifespan,
    title="Pipefy CrewAI Analysis Service v2.0 - Híbrido Inteligente",
    description="Servicio de análisis especializado que usa herramientas simples para llamar al backend"
)

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class DocumentInfo(BaseModel):
    name: str
    file_url: str
    document_tag: str

class AnalysisRequest(BaseModel):
    case_id: str = Field(..., description="ID do case/card do Pipefy")
    documents: List[DocumentInfo] = Field(..., description="Lista de documentos para análise")
    current_date: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Data atual")
    pipe_id: Optional[str] = Field(None, description="ID do pipe do Pipefy")

class AnalysisResponse(BaseModel):
    status: str
    case_id: str
    analysis_result: Any  # Permitir cualquier tipo para evitar errores de validación
    message: str

# ============================================================================
# CONFIGURACIÓN DEL AGENTE ENFOCADO
# ============================================================================

def create_faq_knowledge_source() -> PDFKnowledgeSource:
    """Cria a fonte de conhecimento baseada no FAQ.pdf"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"🏠 Directorio base: {base_dir}")
        
        # Detectar entorno y configurar path
        render_knowledge_path = "/opt/render/project/src/knowledge/FAQ.pdf"
        render_triagem_path = "/opt/render/project/src/triagem_crew/knowledge/FAQ.pdf"
        
        original_cwd = os.getcwd()
        logger.info(f"🔄 Directorio de trabajo original: {original_cwd}")
        
        try:
            if os.path.exists(render_knowledge_path):
                os.chdir("/opt/render/project/src")
                logger.info("🌐 Entorno Render - usando knowledge/")
                faq_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                logger.info("✅ FAQ.pdf cargado exitosamente")
                return faq_source
                
            elif os.path.exists(render_triagem_path):
                os.chdir("/opt/render/project/src/triagem_crew")
                logger.info("🌐 Entorno Render - usando triagem_crew/knowledge/")
                faq_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                logger.info("✅ FAQ.pdf cargado exitosamente")
                return faq_source
            
            # Entorno local
            local_knowledge = os.path.join(base_dir, "knowledge", "FAQ.pdf")
            local_triagem = os.path.join(base_dir, "triagem_crew", "knowledge", "FAQ.pdf")
            
            if os.path.exists(local_knowledge):
                os.chdir(base_dir)
                logger.info("🏠 Entorno local - usando knowledge/")
                faq_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                logger.info("✅ FAQ.pdf cargado exitosamente")
                return faq_source
                
            elif os.path.exists(local_triagem):
                triagem_dir = os.path.join(base_dir, "triagem_crew")
                os.chdir(triagem_dir)
                logger.info("🏠 Entorno local - usando triagem_crew/knowledge/")
                faq_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                logger.info("✅ FAQ.pdf cargado exitosamente")
                return faq_source
            
            logger.error("❌ FAQ.pdf no encontrado en ninguna ubicación")
            raise FileNotFoundError("FAQ.pdf not found")
            
        finally:
            os.chdir(original_cwd)
            logger.info(f"🔄 Directorio restaurado a: {original_cwd}")
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar fonte de conhecimento FAQ.pdf: {e}")
        raise

def load_agent_config() -> Dict[str, Any]:
    """Carrega a configuração do agente do arquivo YAML"""
    try:
        with open("triagem_crew/config/agents.yaml", "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Erro ao carregar configuração do agente: {e}")
        raise

def load_task_config() -> Dict[str, Any]:
    """Carrega a configuração das tarefas do arquivo YAML"""
    try:
        with open("triagem_crew/config/tasks.yaml", "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Erro ao carregar configuração das tarefas: {e}")
        raise

def create_triagem_agent() -> Agent:
    """Cria o agente de triagem com herramientas híbridas simples"""
    try:
        agent_config = load_agent_config()
        faq_source = create_faq_knowledge_source()
        
        # Herramientas simples que llaman al backend
        from src.tools.backend_api_tools import BACKEND_API_TOOLS
        tools = BACKEND_API_TOOLS
        
        return Agent(
            role=agent_config["triagem_agent"]["role"],
            goal=agent_config["triagem_agent"]["goal"],
            backstory=agent_config["triagem_agent"]["backstory"],
            tools=tools,
            knowledge_sources=[faq_source],
            verbose=True,
            allow_delegation=False
        )
    except Exception as e:
        logger.error(f"Erro ao criar agente de triagem: {e}")
        raise

def create_triagem_task_from_inputs(inputs: Dict[str, Any], agent: Agent) -> Task:
    """Cria a tarefa de triagem baseada nos inputs"""
    try:
        task_config = load_task_config()
        
        return Task(
            description=task_config["triagem_task"]["description"].format(**inputs),
            expected_output=task_config["triagem_task"]["expected_output"],
            agent=agent
        )
    except Exception as e:
        logger.error(f"Erro ao criar tarefa de triagem: {e}")
        raise

# ============================================================================
# ENDPOINTS PRINCIPALES
# ============================================================================

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_documents(request: AnalysisRequest) -> AnalysisResponse:
    """
    Endpoint principal para análisis de documentos.
    ENFOQUE HÍBRIDO: Solo hace análisis, las operaciones complejas las hace el backend.
    """
    try:
        logger.info(f"🔍 Iniciando análisis para case_id: {request.case_id}")
        
        # Preparar inputs para el agente
        inputs = {
            "case_id": request.case_id,
            "documents": [doc.dict() for doc in request.documents],
            "current_date": request.current_date,
            "pipe_id": request.pipe_id or "default"
        }
        
        # Crear agente y tarea
        agent = create_triagem_agent()
        task = create_triagem_task_from_inputs(inputs, agent)
        
        # Ejecutar crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        # Ejecutar análisis
        result = crew.kickoff(inputs=inputs)
        
        logger.info(f"✅ Análisis completado para case_id: {request.case_id}")
        
        # Procesar resultado del crew para extraer JSON estructurado
        crew_output = str(result) if result else ""
        
        # Intentar extraer JSON del resultado
        structured_response = None
        try:
            # Buscar JSON en el resultado del crew
            import json
            import re
            
            # Buscar patrones JSON en el texto
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, crew_output)
            
            for match in json_matches:
                try:
                    parsed_json = json.loads(match)
                    # Buscar JSON válido con campos esperados del análisis
                    if isinstance(parsed_json, dict) and (
                        'classificacao' in parsed_json or 
                        'classification' in parsed_json or
                        'status_geral' in parsed_json or
                        'case_id' in parsed_json
                    ):
                        structured_response = parsed_json
                        logger.info(f"🎯 JSON estruturado extraído: {structured_response}")
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"⚠️ No se pudo extraer JSON estructurado: {e}")
        
        # Preparar respuesta compatible con servicio de ingestión
        analysis_result = {
            "informe": crew_output,
            "structured_response": structured_response,
            "risk_score": "Medium",  # Default
            "documents_analyzed": len(request.documents)
        }
        
        # Guardar en Supabase (tabla informe_cadastro)
        try:
            informe_data = {
                "case_id": request.case_id,
                "informe": crew_output,
                "risk_score": "Medium",
                "documents_analyzed": len(request.documents),
                "analysis_details": structured_response if structured_response else {}
            }
            
            supabase_client.table("informe_cadastro").insert(informe_data).execute()
            logger.info(f"💾 Informe guardado en Supabase tabla informe_cadastro para case_id: {request.case_id}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando informe en Supabase: {e}")
        
        return AnalysisResponse(
            status="completed",  # Cambio: usar "completed" en lugar de "success"
            case_id=request.case_id,
            analysis_result=analysis_result,  # Cambio: usar estructura compatible
            message="Análisis completado exitosamente"
        )
        
    except Exception as e:
        logger.error(f"❌ Error en análisis para case_id {request.case_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis para case_id {request.case_id}: {str(e)}"
        )

@app.get("/")
async def root():
    """Endpoint raíz del servicio"""
    return {
        "service": "Pipefy CrewAI Analysis Service v2.0",
        "status": "running",
        "architecture": "Enfoque Híbrido Inteligente",
        "description": "Servicio de análisis especializado con herramientas simples",
        "backend_url": BACKEND_URL
    }

@app.get("/health")
async def health_check():
    """Health check del servicio"""
    try:
        # Verificar conexión a Supabase
        if supabase_client:
            test_response = supabase_client.table("documents").select("count", count="exact").limit(1).execute()
            supabase_status = "connected"
        else:
            supabase_status = "disconnected"
        
        # Verificar conexión al backend
        try:
            with httpx.Client(timeout=5.0) as client:
                backend_response = client.get(f"{BACKEND_URL}/health")
                backend_status = "connected" if backend_response.status_code == 200 else "error"
        except:
            backend_status = "disconnected"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "supabase": supabase_status,
                "backend": backend_status,
                "backend_url": BACKEND_URL
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000))) 
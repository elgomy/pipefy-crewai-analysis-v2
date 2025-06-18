#!/usr/bin/env python3
"""
Pipefy CrewAI Analysis Service v2.0
Servicio especializado en análisis de documentos usando triagem_agente
"""

import os
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import re

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
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

# Cliente Supabase global
supabase_client: Optional[Client] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação FastAPI."""
    global supabase_client
    
    # Startup
    logger.info("🤖 Iniciando Pipefy CrewAI Analysis Service v2.0...")
    
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
    
    logger.info("🎯 Triagem Agent configurado e pronto para análise.")
    
    yield
    
    # Shutdown
    logger.info("INFO: Encerrando CrewAI Analysis Service...")

app = FastAPI(
    lifespan=lifespan,
    title="Pipefy CrewAI Analysis Service v2.0",
    description="Serviço especializado em análise de documentos usando triagem_agente"
)

# Modelos Pydantic
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

# Función para crear fonte de conhecimento FAQ.pdf
def create_faq_knowledge_source() -> PDFKnowledgeSource:
    """Cria a fonte de conhecimento baseada no FAQ.pdf"""
    import os
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"🏠 Directorio base: {base_dir}")
        
        # SOLUCIÓN DEFINITIVA: PDFKnowledgeSource SIEMPRE prefixa "knowledge/"
        # Por tanto, debemos darle SOLO el nombre del archivo, no la ruta completa
        # Y el working directory debe ser el directorio que contiene "knowledge/"
        
        # Detectar si estamos en Render
        render_knowledge_path = "/opt/render/project/src/knowledge/FAQ.pdf"
        render_triagem_path = "/opt/render/project/src/triagem_crew/knowledge/FAQ.pdf"
        
        original_cwd = os.getcwd()
        logger.info(f"🔄 Directorio de trabajo original: {original_cwd}")
        
        try:
            if os.path.exists(render_knowledge_path):
                # Entorno Render - usar knowledge/ directo
                logger.info("🌐 Detectado entorno Render - usando /opt/render/project/src/knowledge/")
                os.chdir("/opt/render/project/src")
                
                # PDFKnowledgeSource buscará: knowledge/ + FAQ.pdf = knowledge/FAQ.pdf ✅
                logger.info("🚀 Creando PDFKnowledgeSource con archivo: FAQ.pdf")
                faq_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                logger.info("✅ FAQ.pdf cargado exitosamente desde directorio knowledge/")
                return faq_source
                
            elif os.path.exists(render_triagem_path):
                # Entorno Render - usar triagem_crew/knowledge/
                logger.info("🌐 Detectado entorno Render - usando /opt/render/project/src/triagem_crew/")
                os.chdir("/opt/render/project/src/triagem_crew")
                
                # PDFKnowledgeSource buscará: knowledge/ + FAQ.pdf = knowledge/FAQ.pdf ✅
                logger.info("🚀 Creando PDFKnowledgeSource con archivo: FAQ.pdf")
                faq_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                logger.info("✅ FAQ.pdf cargado exitosamente desde directorio triagem_crew/knowledge/")
                return faq_source
            
            # Entorno local/desarrollo
            local_knowledge = os.path.join(base_dir, "knowledge", "FAQ.pdf")
            local_triagem = os.path.join(base_dir, "triagem_crew", "knowledge", "FAQ.pdf")
            
            if os.path.exists(local_knowledge):
                logger.info("🏠 Entorno local - usando knowledge/ directo")
                os.chdir(base_dir)
                logger.info("🚀 Creando PDFKnowledgeSource con archivo: FAQ.pdf")
                faq_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                logger.info("✅ FAQ.pdf cargado exitosamente desde directorio local knowledge/")
                return faq_source
                
            elif os.path.exists(local_triagem):
                logger.info("🏠 Entorno local - usando triagem_crew/knowledge/")
                triagem_dir = os.path.join(base_dir, "triagem_crew")
                os.chdir(triagem_dir)
                logger.info("🚀 Creando PDFKnowledgeSource con archivo: FAQ.pdf")
                faq_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                logger.info("✅ FAQ.pdf cargado exitosamente desde directorio local triagem_crew/knowledge/")
                return faq_source
            
            # Si llegamos aquí, no encontramos el archivo
            logger.error(f"❌ FAQ.pdf no encontrado en ninguna ubicación conocida")
            logger.error(f"   Verificado: {render_knowledge_path}")
            logger.error(f"   Verificado: {render_triagem_path}")
            logger.error(f"   Verificado: {local_knowledge}")
            logger.error(f"   Verificado: {local_triagem}")
            raise FileNotFoundError("FAQ.pdf not found in any expected location")
            
        finally:
            # Restaurar directorio original
            os.chdir(original_cwd)
            logger.info(f"🔄 Directorio restaurado a: {original_cwd}")
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar fonte de conhecimento FAQ.pdf: {e}")
        raise

class SupabaseDocumentTool(BaseTool):
    name: str = "supabase_document_tool"
    description: str = "Acessa documentos armazenados no Supabase Storage"
    
    def _run(self, case_id: str) -> dict:
        """Obtém informações dos documentos do Supabase"""
        try:
            if not supabase_client:
                return {"error": "Cliente Supabase não disponível"}
            # Consultar documentos na tabela
            response = supabase_client.table("documents").select("*").eq("case_id", case_id).execute()
            if response.data:
                logger.info(f"📄 Encontrados {len(response.data)} documentos para case_id: {case_id}")
                return {"documents": response.data}
            else:
                return {"documents": []}
        except Exception as e:
            logger.error(f"Erro ao acessar documentos: {e}")
            return {"error": str(e)}

# Função para carregar configurações YAML
def load_agent_config() -> Dict[str, Any]:
    """Carrega a configuração do agente do arquivo YAML"""
    try:
        with open("triagem_crew/config/agents.yaml", "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Erro ao carregar agents.yaml: {e}")
        raise

def load_task_config() -> Dict[str, Any]:
    """Carrega a configuração das tarefas do arquivo YAML"""
    try:
        with open("triagem_crew/config/tasks.yaml", "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Erro ao carregar tasks.yaml: {e}")
        raise

# Función para crear el agente
def create_triagem_agent() -> Agent:
    """Cria o agente de triagem baseado na configuração YAML"""
    config = load_agent_config()
    agent_config = config["triagem_agente"]
    
    # Ferramentas disponíveis (FAQ.pdf se maneja a nivel de crew)
    tools = [
        SupabaseDocumentTool()
    ]
    
    return Agent(
        role=agent_config["role"],
        goal=agent_config["goal"],
        backstory=agent_config["backstory"],
        verbose=agent_config.get("verbose", True),
        allow_delegation=agent_config.get("allow_delegation", False),
        max_iter=agent_config.get("max_iter", 3),
        max_execution_time=agent_config.get("max_execution_time", 300),
        tools=tools
    )

# Função para criar a tarefa
def create_triagem_task_from_inputs(inputs: Dict[str, Any], agent: Agent) -> Task:
    config = load_task_config()["tarefa_validacao_documental"]
    # Formatear descripción con los datos de inputs (sin checklist)
    description = config["description"].format(
        case_id=inputs.get("case_id", ""),
        documents=json.dumps(inputs.get("documents", []), ensure_ascii=False),
        current_date=inputs.get("current_date", "")
    )
    return Task(
        description=description,
        expected_output=config["expected_output"],
        agent=agent,
        context=[]
    )

# --- SANITIZACIÓN DE PAYLOADS PARA SUPABASE ---

INFORME_CADASTRO_FIELDS = {
    "case_id",
    "informe",
    "status",
    "created_at",
    "updated_at"
}

def sanitize_informe_cadastro_payload(data: dict) -> dict:
    """
    Elimina cualquier clave no permitida del payload para informe_cadastro.
    """
    return {k: v for k, v in data.items() if k in INFORME_CADASTRO_FIELDS}

def clean_json_string(raw: str) -> str:
    """
    Elimina backticks, saltos de línea y espacios innecesarios del string JSON.
    """
    if not isinstance(raw, str):
        return raw
    # Elimina triple backtick y espacios
    cleaned = re.sub(r"^`{3,}\s*|\s*`{3,}$", "", raw.strip())
    return cleaned.strip()

# Função para salvar resultado no Supabase
async def save_analysis_result(case_id: str, analysis_result: Dict[str, Any]) -> bool:
    """Salva o resultado da análise na tabela informe_cadastro"""
    try:
        if not supabase_client:
            logger.error("Cliente Supabase não disponível")
            return False
        logger.info(f"🧪 [save_analysis_result] Tipo de analysis_result: {type(analysis_result)} | Valor: {repr(analysis_result)}")
        import json
        import traceback
        # Si analysis_result es string, limpiar y parsear
        if isinstance(analysis_result, str):
            try:
                cleaned = clean_json_string(analysis_result)
                analysis_result = json.loads(cleaned)
            except Exception as e:
                logger.error(f"❌ Error al limpiar/parsear analysis_result: {e}")
                logger.error(traceback.format_exc())
                analysis_result = {"raw_result": analysis_result}
        elif not isinstance(analysis_result, dict):
            logger.error(f"❌ analysis_result NO es dict en save_analysis_result. Valor: {repr(analysis_result)}")
            logger.error(traceback.format_exc())
            analysis_result = {"raw_result": analysis_result}
        if isinstance(analysis_result, dict):
            status_value = analysis_result.get("status_geral", "Pendente")
        else:
            logger.error(f"❌ analysis_result NO es dict tras todos los intentos. Valor final: {repr(analysis_result)}")
            status_value = "Pendente"
        data_to_insert = {
            "case_id": case_id,
            "informe": json.dumps(analysis_result, ensure_ascii=False, indent=2),
            "status": status_value,
            "created_at": datetime.now().isoformat(),
        }
        data_to_insert = sanitize_informe_cadastro_payload(data_to_insert)
        response = await asyncio.to_thread(
            supabase_client.table("informe_cadastro").upsert(data_to_insert, on_conflict="case_id").execute
        )
        if hasattr(response, 'error') and response.error:
            logger.error(f"Erro ao salvar resultado: {response.error.message}")
            return False
        logger.info(f"✅ Resultado da análise salvo para case_id: {case_id}")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar resultado da análise: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

class TriagemCrew:
    """
    Orquesta la ejecución de CrewAI para triagem documental, replicando la lógica modular.
    """
    def __init__(self, inputs: Dict[str, Any]):
        self.inputs = inputs

    def run(self) -> str:
        logger.info(f"[TriagemCrew] Inputs recibidos: {self.inputs}")
        # Crear fuente de conocimiento
        faq_knowledge = create_faq_knowledge_source()
        # Crear agente
        agent = create_triagem_agent()
        # Crear tarea (usar solo la versión que acepta dict)
        task = create_triagem_task_from_inputs(self.inputs, agent)
        # Crear crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            knowledge_sources=[faq_knowledge]
        )
        logger.info("[TriagemCrew] Ejecutando CrewAI...")
        result = crew.kickoff(inputs=self.inputs)
        logger.info(f"[TriagemCrew] Resultado bruto de CrewAI: {repr(result)}")
        return str(result)

# Endpoint principal
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_documents(request: AnalysisRequest) -> AnalysisResponse:
    """Analisa documentos usando CrewAI (lógica modular)"""
    try:
        logger.info(f"🚀 Iniciando análise para case_id: {request.case_id}")
        inputs = {
            "case_id": request.case_id,
            "documents": [doc.dict() for doc in request.documents],
            "current_date": datetime.now().strftime('%Y-%m-%d')
        }
        crew_runner = TriagemCrew(inputs)
        crew_result_str = crew_runner.run()
        logger.info(f"[POST /analyze] Resultado bruto CrewAI: {crew_result_str}")
        try:
            logger.info(f"[POST /analyze] Antes de limpieza: {repr(crew_result_str)}")
            cleaned_result = clean_json_string(crew_result_str)
            logger.info(f"[POST /analyze] Después de limpieza: {repr(cleaned_result)}")
            result_json = json.loads(cleaned_result)
        except Exception as e:
            logger.error(f"❌ Error al parsear resultado CrewAI a JSON: {e}")
            import traceback
            logger.error(traceback.format_exc())
            result_json = {"raw_result": crew_result_str}
        status = result_json.get("status_geral", "Pendente")
        await save_analysis_result(request.case_id, result_json)
        logger.info("✅ Análise CrewAI concluída (modular)")
        return AnalysisResponse(
            case_id=request.case_id,
            status="completed",
            analysis_result=result_json,
            message="Análise concluída com sucesso (modular)"
        )
    except Exception as e:
        logger.error(f"❌ Erro na análise modular: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro na análise modular: {e}")

# Endpoint síncrono para compatibilidad con servicio de ingestión
@app.post("/analyze/sync", response_model=AnalysisResponse)
async def analyze_documents_sync(request: AnalysisRequest) -> AnalysisResponse:
    """
    Endpoint síncrono para análisis de documentos - Compatible con servicio de ingestión
    Idéntico al endpoint /analyze pero con ruta /analyze/sync para compatibilidad
    """
    return await analyze_documents(request)

# Endpoints auxiliares
@app.get("/")
async def root():
    """Endpoint raiz com informações do serviço"""
    return {
        "service": "Pipefy CrewAI Analysis Service v2.0",
        "status": "running",
        "agent": "triagem_agente",
        "description": "Serviço especializado em análise de documentos de triagem"
    }

@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "crewai_analysis_v2"
    }

@app.get("/config")
async def get_config():
    """Endpoint para verificar configuração do agente"""
    try:
        agent_config = load_agent_config()
        task_config = load_task_config()
        
        return {
            "agent_config": agent_config,
            "task_config": task_config,
            "status": "config_loaded"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar configuração: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
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
    checklist_url: str = Field(..., description="URL do checklist de referência")
    current_date: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Data atual")
    pipe_id: Optional[str] = Field(None, description="ID do pipe do Pipefy")

class AnalysisResponse(BaseModel):
    status: str
    case_id: str
    analysis_result: Dict[str, Any]
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
    
    def _run(self, case_id: str) -> str:
        """Obtém informações dos documentos do Supabase"""
        try:
            if not supabase_client:
                return "Cliente Supabase não disponível"
            
            # Consultar documentos na tabela
            response = supabase_client.table("documents").select("*").eq("case_id", case_id).execute()
            
            if response.data:
                logger.info(f"📄 Encontrados {len(response.data)} documentos para case_id: {case_id}")
                return json.dumps(response.data, indent=2)
            else:
                return f"Nenhum documento encontrado para case_id: {case_id}"
                
        except Exception as e:
            logger.error(f"Erro ao acessar documentos: {e}")
            return f"Erro no acesso: {str(e)}"

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
def create_triagem_task(request: AnalysisRequest, agent: Agent) -> Task:
    """Cria a tarefa de validação baseada na configuração YAML"""
    config = load_task_config()
    task_config = config["tarefa_validacao_documental"]
    # Preparar dados dos documentos
    documents_data = [
        {
            "file_url": doc.file_url,
            "name": doc.name,
            "document_tag": doc.document_tag
        }
        for doc in request.documents
    ]
    # Formatar descrição com dados específicos
    description = task_config["description"].format(
        case_id=request.case_id,
        documents=json.dumps(documents_data, indent=2),
        checklist_content=f"Checklist disponível em: {request.checklist_url}",
        current_date=request.current_date
    )
    expected_output = task_config["expected_output"].format(
        case_id=request.case_id,
        current_date=request.current_date
    )
    # Corregir context: siempre debe ser lista
    context_value = task_config.get("context", "")
    if isinstance(context_value, str):
        context = [context_value.strip()] if context_value.strip() else []
    elif isinstance(context_value, list):
        context = context_value
    else:
        context = []
    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
        context=context,
        output_format=task_config.get("output_format", "json")
    )

# Função para salvar resultado no Supabase
async def save_analysis_result(case_id: str, analysis_result: Dict[str, Any]) -> bool:
    """Salva o resultado da análise na tabela informe_cadastro"""
    try:
        if not supabase_client:
            logger.error("Cliente Supabase não disponível")
            return False
        
        # Preparar dados para inserção
        data_to_insert = {
            "case_id": case_id,
            "informe": json.dumps(analysis_result, ensure_ascii=False, indent=2),
            "status": analysis_result.get("status_geral", "Pendente"),
            "created_at": datetime.now().isoformat(),
            "service": "crewai_triagem_v2"
        }
        
        # Inserir na tabela
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
        return False

# Endpoint principal
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_documents(request: AnalysisRequest) -> AnalysisResponse:
    """Analisa documentos usando CrewAI"""
    try:
        logger.info(f"🚀 Iniciando análise para case_id: {request.case_id}")
        
        # Crear fuente de conocimiento FAQ.pdf
        faq_knowledge = create_faq_knowledge_source()
        
        # Crear agente y tarea
        agent = create_triagem_agent()
        task = create_triagem_task(request, agent)
        
        # Crear crew con fuente de conocimiento
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            knowledge_sources=[faq_knowledge]  # FAQ.pdf como fuente de conocimiento
        )
        
        # Ejecutar análisis
        logger.info("🔄 Executando análise CrewAI...")
        result = crew.kickoff()
        
        # Procesar resultado
        if hasattr(result, 'raw'):
            analysis_result = result.raw
        else:
            analysis_result = str(result)
        
        logger.info("✅ Análise CrewAI concluída")
        
        # Guardar resultado
        await save_analysis_result(request.case_id, analysis_result)
        
        return AnalysisResponse(
            case_id=request.case_id,
            status="completed",
            analysis_result=analysis_result,
            message="Análise concluída com sucesso"
        )
        
    except Exception as e:
        error_msg = f"Erro na análise: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return AnalysisResponse(
            case_id=request.case_id,
            status="error",
            analysis_result={},  # Siempre dict vacío para evitar error de Pydantic
            message=error_msg
        )

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
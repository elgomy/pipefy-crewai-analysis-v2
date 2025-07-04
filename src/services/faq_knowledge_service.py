"""
Servicio optimizado para el manejo del FAQ.pdf como fuente de conocimiento.
"""
import os
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
import unicodedata

logger = logging.getLogger(__name__)

def _normalize_name(name):
    # Elimina acentos, pasa a minúsculas y quita caracteres especiales
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = name.lower().replace('-', ' ').replace('_', ' ').replace('.', ' ').replace('/', ' ')
    name = ''.join(c for c in name if c.isalnum() or c.isspace())
    return ' '.join(name.split())

class FAQKnowledgeService:
    """
    Servicio optimizado para el manejo del FAQ.pdf.
    Implementa caché, validación de actualizaciones y extracción de reglas.
    """
    
    def __init__(self):
        self._knowledge_source: Optional[PDFKnowledgeSource] = None
        self._last_load_time: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=30)  # Recargar cada 30 minutos
        self._rules_cache: Dict[str, Any] = {}
        self._faq_path: Optional[Path] = None
        self._checklist: Optional[list] = None
        self._checklist_path = self._find_checklist_file()
        
    def _find_faq_file(self) -> Optional[Path]:
        """
        Busca el archivo FAQ.pdf en las ubicaciones conocidas.
        
        Returns:
            Path: Ruta al archivo FAQ.pdf o None si no se encuentra
        """
        # Detectar si estamos en Render
        render_paths = [
            Path("/opt/render/project/src/knowledge/FAQ.pdf"),
            Path("/opt/render/project/src/triagem_crew/knowledge/FAQ.pdf")
        ]
        
        # Buscar en entorno Render
        for path in render_paths:
            if path.exists():
                logger.info(f"🌐 FAQ.pdf encontrado en entorno Render: {path}")
                return path
        
        # Buscar en entorno local
        base_dir = Path(__file__).parent.parent.parent
        local_paths = [
            base_dir / "knowledge" / "FAQ.pdf",
            base_dir / "triagem_crew" / "knowledge" / "FAQ.pdf"
        ]
        
        for path in local_paths:
            if path.exists():
                logger.info(f"🏠 FAQ.pdf encontrado en entorno local: {path}")
                return path
        
        logger.error("❌ FAQ.pdf no encontrado en ninguna ubicación conocida")
        return None
    
    def _should_reload(self) -> bool:
        """
        Determina si el FAQ debe ser recargado basado en:
        1. Si nunca fue cargado
        2. Si el caché expiró
        3. Si el archivo fue modificado
        
        Returns:
            bool: True si debe recargarse
        """
        if not self._knowledge_source or not self._last_load_time:
            return True
            
        now = datetime.now()
        
        # Verificar expiración del caché
        if now - self._last_load_time > self._cache_duration:
            return True
            
        # Verificar si el archivo fue modificado
        if self._faq_path and self._faq_path.exists():
            mtime = datetime.fromtimestamp(self._faq_path.stat().st_mtime)
            if mtime > self._last_load_time:
                return True
                
        return False
    
    def get_knowledge_source(self) -> Optional[PDFKnowledgeSource]:
        """
        Obtiene la fuente de conocimiento FAQ.pdf, recargando si es necesario.
        
        Returns:
            PDFKnowledgeSource: Fuente de conocimiento o None si hay error
        """
        try:
            # Encontrar el archivo si aún no lo hemos hecho
            if not self._faq_path:
                self._faq_path = self._find_faq_file()
                if not self._faq_path:
                    return None
            
            # Verificar si debemos recargar
            if self._should_reload():
                logger.info("🔄 Recargando FAQ.pdf...")
                
                # Cambiar al directorio correcto para PDFKnowledgeSource
                original_cwd = os.getcwd()
                os.chdir(str(self._faq_path.parent.parent))
                
                try:
                    # PDFKnowledgeSource buscará en knowledge/FAQ.pdf
                    self._knowledge_source = PDFKnowledgeSource(file_paths=["FAQ.pdf"])
                    self._last_load_time = datetime.now()
                    self._rules_cache = {}  # Limpiar caché de reglas
                    logger.info("✅ FAQ.pdf recargado exitosamente")
                finally:
                    os.chdir(original_cwd)
            
            return self._knowledge_source
            
        except Exception as e:
            logger.error(f"❌ Error cargando FAQ.pdf: {e}")
            return None
    
    def extract_rules(self, section: str) -> Dict[str, Any]:
        """
        Extrae reglas específicas del FAQ para una sección.
        Implementa caché para evitar reprocesamiento.
        
        Args:
            section: Sección del FAQ a procesar (ej: "documentos", "pendencias")
            
        Returns:
            Dict: Reglas extraídas y procesadas
        """
        # Verificar caché
        if section in self._rules_cache:
            return self._rules_cache[section]
            
        knowledge_source = self.get_knowledge_source()
        if not knowledge_source:
            return {}
            
        try:
            # Aquí implementaríamos la lógica específica para extraer
            # y procesar reglas según la sección solicitada
            rules = {}  # TODO: Implementar extracción específica
            
            # Guardar en caché
            self._rules_cache[section] = rules
            return rules
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo reglas de {section}: {e}")
            return {}

    def _find_checklist_file(self) -> Optional[Path]:
        """
        Busca el archivo JSON del checklist estructurado.
        """
        # Render y local
        paths = [
            Path("/opt/render/project/src/triagem_crew/knowledge/faq_checklist.json"),
            Path(__file__).parent.parent / "triagem_crew" / "knowledge" / "faq_checklist.json",
            Path(__file__).parent.parent / "knowledge" / "faq_checklist.json"
        ]
        for path in paths:
            if path.exists():
                logger.info(f"📋 Checklist JSON encontrado: {path}")
                return path
        logger.warning("⚠️ Checklist JSON no encontrado en ubicaciones conocidas")
        return None

    def load_checklist(self) -> Optional[list]:
        """
        Carga el checklist estructurado desde JSON (con caché).
        """
        if self._checklist is not None:
            return self._checklist
        if not self._checklist_path or not self._checklist_path.exists():
            logger.error("❌ No se pudo cargar el checklist JSON")
            return None
        try:
            with open(self._checklist_path, encoding="utf-8") as f:
                self._checklist = json.load(f)
            logger.info(f"✅ Checklist cargado con {len(self._checklist)} reglas")
            return self._checklist
        except Exception as e:
            logger.error(f"❌ Error cargando checklist JSON: {e}")
            return None

    def validate_documents(self, documentos: list) -> dict:
        checklist = self.load_checklist()
        if not checklist:
            logger.error("❌ No hay checklist para validar documentos")
            return {"status": "error", "logs": ["Checklist no disponible"], "detalles": {}}
        logs = []
        detalles = {}
        status_geral = "Aprovado"
        acciones_automaticas = []
        from crewai.llms import OpenAI
        llm = OpenAI()
        logger.info(f"[MATCHING-IA] Iniciando validación IA de documentos. Total ítems checklist: {len(checklist)}")
        for regla in checklist:
            nombre = regla["Item do Checklist"].strip("* ")
            doc_names = [d.get("name", "") for d in documentos]
            doc_contents = {d.get("name", ""): d.get("parsed_content", "")[:500] for d in documentos}
            prompt = f"""
Eres un asistente experto en validación documental para onboarding empresarial. Tu tarea es analizar si alguno de los documentos anexados corresponde al ítem del checklist:

Ítem del checklist: '{nombre}'

Documentos anexados (nombre): {doc_names}

Fragmentos de contenido de cada documento (máx 500 caracteres):
{json.dumps(doc_contents, ensure_ascii=False, indent=2)}

Responde SOLO con el nombre exacto del documento que corresponde, o una lista de nombres si hay más de uno. Si ninguno corresponde, responde exactamente 'Ninguno'. Si tienes dudas, elige el más probable y explica brevemente por qué.
"""
            logger.info(f"[MATCHING-IA] Prompt enviado al LLM para '{nombre}': {prompt[:300]}...")
            try:
                respuesta = llm(prompt)
                logger.info(f"[MATCHING-IA] Respuesta del LLM para '{nombre}': {respuesta}")
                doc_match = None
                razonamiento = respuesta
                for i, d in enumerate(documentos):
                    doc_name = d.get("name", "")
                    if doc_name in respuesta or doc_name.lower() in respuesta.lower():
                        doc_match = i
                        break
                if doc_match is not None:
                    doc = documentos[doc_match]
                    detalles[nombre] = {"status": "Presente", "regla": regla, "validacion": "IA", "razonamiento": razonamiento, "doc_name": doc.get("name")}
                    logs.append(f"✅ Documento presente (IA): {nombre} → {doc.get('name')}")
                    logger.info(f"[MATCHING-IA] Documento validado por IA: '{nombre}' → '{doc.get('name')}'")
                else:
                    detalles[nombre] = {"status": "Faltante", "regla": regla, "validacion": "IA", "razonamiento": razonamiento}
                    logs.append(f"❌ Falta documento: {nombre}")
                    logger.info(f"[MATCHING-IA] Documento faltante según IA: '{nombre}'")
                    if "Bloqueante" in regla["Classificação da Pendência (se houver)"]:
                        status_geral = "Pendencia_Bloqueante"
                    elif status_geral != "Pendencia_Bloqueante":
                        status_geral = "Pendencia_NaoBloqueante"
                    if "Cartão CNPJ" in nombre or "cartão cnpj" in nombre.lower():
                        acciones_automaticas.append({
                            "type": "GENERATE_DOCUMENT",
                            "document_type": nombre,
                            "reason": "Falta Cartão CNPJ - se generará automáticamente",
                            "accion": regla["Ação Automática do Sistema"]
                        })
            except Exception as e:
                logger.warning(f"[MATCHING-IA] Error consultando LLM para matching de '{nombre}': {e}")
                detalles[nombre] = {"status": "Faltante", "regla": regla, "error": str(e)}
                logs.append(f"❌ Falta documento: {nombre} (error IA)")
        logger.info(f"[MATCHING-IA] Validación IA completada. Status general: {status_geral}")
        return {"status": status_geral, "logs": logs, "detalles": detalles, "acciones_automaticas": acciones_automaticas}

# Instancia global del servicio
faq_knowledge_service = FAQKnowledgeService() 
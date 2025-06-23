"""
Servicio optimizado para el manejo del FAQ.pdf como fuente de conocimiento.
"""
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource

logger = logging.getLogger(__name__)

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

# Instancia global del servicio
faq_knowledge_service = FAQKnowledgeService() 
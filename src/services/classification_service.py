"""
Servicio de clasificación de documentos basado en FAQ.pdf v2.0.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from src.services.faq_knowledge_service import faq_knowledge_service

logger = logging.getLogger(__name__)

class ClassificationType(Enum):
    """Tipos de clasificación según FAQ v2.0."""
    APROVADO = "Aprovado"
    PENDENCIA_BLOQUEANTE = "Pendencia_Bloqueante"
    PENDENCIA_NAO_BLOQUEANTE = "Pendencia_NaoBloqueante"

@dataclass
class DocumentAnalysis:
    """Resultado del análisis de un documento."""
    document_type: str
    is_valid: bool
    is_present: bool
    issues: List[str]
    confidence_score: float
    metadata: Dict[str, Any]

@dataclass
class ClassificationResult:
    """Resultado de la clasificación de un caso."""
    classification_type: ClassificationType
    document_analyses: List[DocumentAnalysis]
    blocking_issues: List[str]
    non_blocking_issues: List[str]
    confidence_score: float
    auto_actions: List[Dict[str, Any]]
    summary: str

class ClassificationService:
    """
    Servicio de clasificación de documentos basado en FAQ v2.0.
    Utiliza el FAQ.pdf como única fuente de conocimiento.
    """
    
    def __init__(self):
        self._rules = {}
        self._load_rules()
    
    def _load_rules(self):
        """Carga las reglas del FAQ."""
        try:
            # Cargar reglas de documentos
            self._rules["documents"] = faq_knowledge_service.extract_rules("documentos")
            
            # Cargar reglas de pendencias
            self._rules["issues"] = faq_knowledge_service.extract_rules("pendencias")
            
            # Cargar reglas de acciones automáticas
            self._rules["actions"] = faq_knowledge_service.extract_rules("acciones")
            
            logger.info("✅ Reglas cargadas exitosamente del FAQ")
            
        except Exception as e:
            logger.error(f"❌ Error cargando reglas del FAQ: {e}")
            self._rules = {}
    
    def classify_documents(self, documents_data: Dict[str, Any], card_data: Dict[str, Any], case_id: str) -> ClassificationResult:
        """
        Clasifica un conjunto de documentos según las reglas del FAQ v2.0, validando exhaustivamente y enriqueciendo si falta Cartão CNPJ.
        Args:
            documents_data: Dict con los documentos presentes (tag -> datos)
            card_data: Dict con los campos del card de Pipefy (incluye 'cnpj')
            case_id: ID del caso/card
        Returns:
            ClassificationResult: Resultado de la clasificación
        """
        try:
            logger.info(f"🔍 Consultando reglas de documentos en FAQ.pdf...")
            required_docs = self._rules["documents"].keys()
            logger.info(f"📋 Documentos requeridos según FAQ: {list(required_docs)}")
            # Validar presencia de todos los documentos requeridos
            document_analyses = []
            docs_present = set(documents_data.keys())
            auto_actions_log = []
            for doc_type in required_docs:
                doc_data = documents_data.get(doc_type, {})
                analysis = self._analyze_document(doc_type, doc_data)
                document_analyses.append(analysis)
                logger.info(f"🔎 Documento '{doc_type}': presente={analysis.is_present}, válido={analysis.is_valid}, issues={analysis.issues}")
            # Enriquecimiento automático si falta Cartão CNPJ
            cartao_cnpj_tag = "cartao_cnpj"
            cartao_cnpj_analysis = next((a for a in document_analyses if a.document_type == cartao_cnpj_tag), None)
            if cartao_cnpj_analysis and not cartao_cnpj_analysis.is_present:
                logger.info(f"⚠️ Falta Cartão CNPJ. Intentando enriquecer usando EnriquecerClienteAPITool...")
                cnpj_raw = card_data.get("cnpj", "")
                cnpj_clean = ''.join(filter(str.isdigit, str(cnpj_raw)))
                logger.info(f"🔢 CNPJ extraído del card: '{cnpj_raw}' → normalizado: '{cnpj_clean}'")
                enrich_result = None
                if cnpj_clean and len(cnpj_clean) == 14:
                    # Llamada real al backend de ingestion
                    import httpx
                    from config import settings
                    ingestion_url = settings.DOCUMENT_INGESTION_URL.rstrip('/')
                    endpoint = f"{ingestion_url}/api/v1/gerar_e_armazenar_cartao_cnpj"
                    payload = {"cnpj": cnpj_clean, "case_id": case_id}
                    try:
                        logger.info(f"[CARTAO_CNPJ] Llamando a {endpoint} con payload: {payload}")
                        response = httpx.post(endpoint, json=payload, timeout=60)
                        response.raise_for_status()
                        enrich_result = response.json()
                        logger.info(f"[CARTAO_CNPJ] Respuesta backend: {enrich_result}")
                    except Exception as e:
                        logger.error(f"[CARTAO_CNPJ] Error llamando al backend de ingestion: {e}")
                        enrich_result = {"success": False, "error": str(e)}
                    auto_actions_log.append({
                        "type": "GENERATE_DOCUMENT",
                        "document_type": cartao_cnpj_tag,
                        "reason": "Falta Cartão CNPJ - generado automáticamente",
                        "enrich_result": enrich_result
                    })
                else:
                    logger.warning(f"❌ CNPJ no válido o ausente en el card: '{cnpj_raw}'")
                    auto_actions_log.append({
                        "type": "GENERATE_DOCUMENT",
                        "document_type": cartao_cnpj_tag,
                        "reason": "Falta Cartão CNPJ - CNPJ no válido o ausente, no se pudo generar automáticamente"
                    })
            # Determinar clasificación general
            classification_type = self._determine_classification(document_analyses)
            # Identificar issues
            blocking_issues, non_blocking_issues = self._identify_issues(document_analyses)
            # Determinar acciones automáticas
            auto_actions = self._determine_auto_actions(
                classification_type,
                document_analyses,
                blocking_issues,
                non_blocking_issues
            )
            # Agregar acciones automáticas de enriquecimiento
            if auto_actions_log:
                auto_actions.extend(auto_actions_log)
            # Calcular score de confianza
            confidence_score = self._calculate_confidence_score(document_analyses)
            # Generar resumen
            summary = self._generate_summary(
                classification_type,
                document_analyses,
                blocking_issues,
                non_blocking_issues,
                auto_actions
            )
            logger.info(f"📄 Resumen de análisis:\n{summary}")
            return ClassificationResult(
                classification_type=classification_type,
                document_analyses=document_analyses,
                blocking_issues=blocking_issues,
                non_blocking_issues=non_blocking_issues,
                confidence_score=confidence_score,
                auto_actions=auto_actions,
                summary=summary
            )
        except Exception as e:
            logger.error(f"❌ Error en clasificación de documentos: {e}")
            raise
    
    def _analyze_document(self, doc_type: str, doc_data: Dict[str, Any]) -> DocumentAnalysis:
        """Analiza un documento específico según las reglas del FAQ, usando parsed_content."""
        try:
            doc_rules = self._rules["documents"].get(doc_type, {})
            is_valid = True
            issues = []
            # Verificar presencia usando parsed_content
            parsed_content = doc_data.get("parsed_content", "")
            is_present = bool(parsed_content and parsed_content.strip())
            if not is_present and doc_rules.get("required", True):
                is_valid = False
                issues.append(f"Documento {doc_type} es requerido pero no tiene contenido parseado ('parsed_content')")
            # Si está presente, validar según reglas (puedes agregar aquí lógica de validación sobre el texto)
            if is_present:
                # Validar fecha si aplica
                if "expiry_date" in doc_data and doc_rules.get("validate_expiry", False):
                    try:
                        expiry_date = datetime.fromisoformat(doc_data["expiry_date"])
                        if expiry_date < datetime.now():
                            is_valid = False
                            issues.append(f"Documento {doc_type} está expirado")
                    except ValueError:
                        is_valid = False
                        issues.append(f"Documento {doc_type} tiene formato de fecha inválido: {doc_data['expiry_date']}")
                # Validar campos requeridos (puedes hacer validaciones sobre el texto de parsed_content aquí)
                for field in doc_rules.get("required_fields", []):
                    if field not in doc_data or not doc_data[field]:
                        is_valid = False
                        issues.append(f"Campo requerido '{field}' faltante en {doc_type}")
            confidence_score = 1.0 if is_valid and is_present else 0.5
            return DocumentAnalysis(
                document_type=doc_type,
                is_valid=is_valid,
                is_present=is_present,
                issues=issues,
                confidence_score=confidence_score,
                metadata=doc_data
            )
        except Exception as e:
            logger.error(f"❌ Error analizando documento {doc_type}: {e}")
            raise
    
    def _determine_classification(self, analyses: List[DocumentAnalysis]) -> ClassificationType:
        """Determina la clasificación general según el FAQ v2.0."""
        try:
            # Verificar si hay documentos inválidos bloqueantes
            has_blocking_issues = any(
                not analysis.is_valid and
                self._rules["documents"].get(analysis.document_type, {}).get("blocking_if_invalid", True)
                for analysis in analyses
            )
            
            if has_blocking_issues:
                return ClassificationType.PENDENCIA_BLOQUEANTE
            
            # Verificar si hay documentos inválidos no bloqueantes
            has_non_blocking_issues = any(
                not analysis.is_valid and
                not self._rules["documents"].get(analysis.document_type, {}).get("blocking_if_invalid", True)
                for analysis in analyses
            )
            
            if has_non_blocking_issues:
                return ClassificationType.PENDENCIA_NAO_BLOQUEANTE
            
            return ClassificationType.APROVADO
            
        except Exception as e:
            logger.error(f"❌ Error determinando clasificación: {e}")
            raise
    
    def _identify_issues(self, analyses: List[DocumentAnalysis]) -> Tuple[List[str], List[str]]:
        """Identifica y categoriza issues según el FAQ."""
        try:
            blocking_issues = []
            non_blocking_issues = []
            
            for analysis in analyses:
                doc_rules = self._rules["documents"].get(analysis.document_type, {})
                
                for issue in analysis.issues:
                    if doc_rules.get("blocking_if_invalid", True):
                        blocking_issues.append(issue)
                    else:
                        non_blocking_issues.append(issue)
            
            return blocking_issues, non_blocking_issues
            
        except Exception as e:
            logger.error(f"❌ Error identificando issues: {e}")
            raise
    
    def _determine_auto_actions(
        self,
        classification: ClassificationType,
        analyses: List[DocumentAnalysis],
        blocking_issues: List[str],
        non_blocking_issues: List[str]
    ) -> List[Dict[str, Any]]:
        """Determina acciones automáticas según el FAQ."""
        try:
            actions = []
            action_rules = self._rules["actions"]
            
            # Acción de movimiento de card
            phase_id = action_rules.get("phase_mapping", {}).get(classification.value)
            if phase_id:
                actions.append({
                    "type": "MOVE_CARD",
                    "phase_id": phase_id,
                    "reason": f"Clasificación: {classification.value}"
                })
            
            # Acciones por documento
            for analysis in analyses:
                doc_rules = self._rules["documents"].get(analysis.document_type, {})
                
                # Si es auto-generable y está ausente o inválido
                if doc_rules.get("auto_generable", False) and (not analysis.is_present or not analysis.is_valid):
                    actions.append({
                        "type": "GENERATE_DOCUMENT",
                        "document_type": analysis.document_type,
                        "reason": "Documento auto-generable requerido"
                    })
            
            # Notificaciones WhatsApp
            if blocking_issues:
                actions.append({
                    "type": "NOTIFY_WHATSAPP",
                    "recipient": "gestor_comercial",
                    "message": "Pendencias bloqueantes identificadas"
                })
            
            return actions
            
        except Exception as e:
            logger.error(f"❌ Error determinando acciones automáticas: {e}")
            raise
    
    def _calculate_confidence_score(self, analyses: List[DocumentAnalysis]) -> float:
        """Calcula el score de confianza general."""
        try:
            if not analyses:
                return 0.0
            
            total_score = sum(analysis.confidence_score for analysis in analyses)
            return total_score / len(analyses)
            
        except Exception as e:
            logger.error(f"❌ Error calculando score de confianza: {e}")
            return 0.0
    
    def _generate_summary(
        self,
        classification: ClassificationType,
        analyses: List[DocumentAnalysis],
        blocking_issues: List[str],
        non_blocking_issues: List[str],
        auto_actions: List[Dict[str, Any]]
    ) -> str:
        """Genera un resumen en formato markdown."""
        try:
            summary = [
                f"# Resumen de Clasificación\n",
                f"## Status: {classification.value}\n",
                "\n## Documentos Analizados:\n"
            ]
            
            for analysis in analyses:
                status = "✅" if analysis.is_valid else "❌"
                summary.append(f"- {status} {analysis.document_type}")
                if analysis.issues:
                    for issue in analysis.issues:
                        summary.append(f"  - {issue}")
            
            if blocking_issues:
                summary.append("\n## Pendencias Bloqueantes:")
                for issue in blocking_issues:
                    summary.append(f"- 🚫 {issue}")
            
            if non_blocking_issues:
                summary.append("\n## Pendencias No Bloqueantes:")
                for issue in non_blocking_issues:
                    summary.append(f"- ⚠️ {issue}")
            
            if auto_actions:
                summary.append("\n## Acciones Automáticas:")
                for action in auto_actions:
                    summary.append(f"- 🔄 {action['type']}: {action.get('reason', '')}")
            
            return "\n".join(summary)
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen: {e}")
            return "Error generando resumen"

# Instancia global del servicio
classification_service = ClassificationService() 
import logging
from typing import Dict, Any
from src.config import settings

logger = logging.getLogger(__name__)

# Definir PipefyAPIError localmente si no está definida en otro lugar
class PipefyAPIError(Exception):
    """Excepción personalizada para errores de la API de Pipefy."""
    pass

from src.services.result_formatter import ResultFormatter

class PipefyService:
    def __init__(self, client=None):
        """
        Inicializa el servicio de Pipefy.
        
        Args:
            client: Cliente de Pipefy (opcional, se crea uno nuevo si no se proporciona)
        """
        from src.integrations.pipefy_client import PipefyClient
        self.client = client or PipefyClient()
    
    async def process_triagem_result(
        self, 
        card_id: str, 
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesa el resultado del análisis de triagem y actualiza el card en Pipefy.
        
        Args:
            card_id (str): ID del card de Pipefy
            analysis_result (Dict): Resultado del análisis de documentos
            
        Returns:
            Dict con el resultado de todas las operaciones
        """
        results = {
            "success": True,
            "card_id": card_id,
            "operations": [],
            "errors": []
        }
        
        try:
            # 1. Formatear resultados para Pipefy
            formatted_results = ResultFormatter.format_analysis_result(analysis_result, card_id)
            
            # 2. Mover card a la fase correspondiente según el resultado
            logger.info(f"Procesando triagem para card {card_id}")
            classification = "APROVADO" if analysis_result.get("is_complete") else "PENDENCIA_BLOQUEANTE"
            
            move_result = await self.client.move_card_by_classification(card_id, classification)
            results["operations"].append({
                "type": "move_card",
                "success": move_result["success"],
                "new_phase_id": move_result["new_phase_id"],
                "new_phase_name": move_result["new_phase_name"]
            })
            
            # 3. Actualizar campo con el informe detallado
            update_result = await self.client.update_card_field(
                card_id, 
                settings.FIELD_ID_INFORME, 
                formatted_results["detailed_report"]
            )
            results["operations"].append({
                "type": "update_detailed_report",
                "success": update_result["success"],
                "field_id": settings.FIELD_ID_INFORME
            })
            
            # 4. Actualizar campo con el informe resumido (si existe)
            if hasattr(settings, 'FIELD_ID_SUMMARY_INFORME'):
                summary_update_result = await self.client.update_card_field(
                    card_id, 
                    settings.FIELD_ID_SUMMARY_INFORME, 
                    formatted_results["summary_report"]
                )
                results["operations"].append({
                    "type": "update_summary_report",
                    "success": summary_update_result["success"],
                    "field_id": settings.FIELD_ID_SUMMARY_INFORME
                })
            
            logger.info(f"Triagem procesada exitosamente para card {card_id}")
            
        except PipefyAPIError as e:
            error_msg = f"Error de API Pipefy para card {card_id}: {str(e)}"
            logger.error(error_msg)
            results["success"] = False
            results["errors"].append(error_msg)
            
        except Exception as e:
            error_msg = f"Error inesperado procesando card {card_id}: {str(e)}"
            logger.error(error_msg)
            results["success"] = False
            results["errors"].append(error_msg)
        
        return results
    
    async def update_card_informe(self, card_id: str, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza el campo de informe de triagem en un card.
        
        Args:
            card_id (str): ID del card
            analysis_result (Dict): Resultado del análisis
            
        Returns:
            Dict con el resultado de la operación
        """
        try:
            # Formatear resultados
            formatted_results = ResultFormatter.format_analysis_result(analysis_result, card_id)
            
            # Actualizar campo de informe detallado
            result = await self.client.update_card_field(
                card_id, 
                settings.FIELD_ID_INFORME, 
                formatted_results["detailed_report"]
            )
            
            # Actualizar campo de informe resumido si existe
            if hasattr(settings, 'FIELD_ID_SUMMARY_INFORME'):
                await self.client.update_card_field(
                    card_id,
                    settings.FIELD_ID_SUMMARY_INFORME,
                    formatted_results["summary_report"]
                )
            
            logger.info(f"Informe actualizado para card {card_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error actualizando informe para card {card_id}: {str(e)}")
            raise 
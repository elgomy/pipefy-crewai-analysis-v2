from typing import List, Dict, Any
import httpx
import logging

# Configurar logger
logger = logging.getLogger(__name__)

class PipefyAPIError(Exception):
    """Excepción personalizada para errores de la API de Pipefy"""
    pass

class PipefyClient:
    def __init__(self, api_url: str, headers: dict, timeout: int):
        self.api_url = api_url
        self.headers = headers
        self.timeout = timeout

    async def execute_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ejecuta una query o mutation GraphQL en Pipefy.
        
        Args:
            query (str): Query o mutation GraphQL
            variables (Dict): Variables para la query
            
        Returns:
            Dict: Resultado de la query
            
        Raises:
            PipefyAPIError: Si hay error en la API de Pipefy
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json={"query": query, "variables": variables or {}},
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("errors"):
                    error_msg = f"Error GraphQL: {result['errors']}"
                    logger.error(error_msg)
                    raise PipefyAPIError(error_msg)
                
                return result.get("data", {})
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP en GraphQL: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
        except httpx.TimeoutException:
            error_msg = "Timeout en GraphQL query"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado en GraphQL: {str(e)}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)

    async def get_card_attachments(self, card_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene los documentos adjuntos de un card.
        
        Args:
            card_id (str): ID del card
            
        Returns:
            List[Dict]: Lista de documentos adjuntos con sus metadatos
            
        Raises:
            PipefyAPIError: Si hay error en la API de Pipefy
        """
        query = """
        query GetCardAttachments(\$cardId: ID!) {
          card(id: \$cardId) {
            attachments {
              url
              field {
                id
                label
              }
              filename
            }
          }
        }
        """
        
        variables = {"cardId": str(card_id)}
        
        try:
            result = await self.execute_query(query, variables)
            
            card_data = result.get("card")
            if not card_data:
                error_msg = f"Card {card_id} no encontrado"
                logger.error(error_msg)
                raise PipefyAPIError(error_msg)
            
            attachments = card_data.get("attachments", [])
            
            # Formatear documentos para CrewAI
            documents = []
            for attachment in attachments:
                if not attachment.get("url"):
                    continue
                    
                doc = {
                    "name": attachment.get("filename", "unknown"),
                    "file_url": attachment["url"],
                    "document_tag": attachment.get("field", {}).get("label", "").lower().replace(" ", "_")
                }
                documents.append(doc)
            
            logger.info(f"✅ Obtenidos {len(documents)} documentos del card {card_id}")
            return documents
                
        except Exception as e:
            error_msg = f"Error inesperado al obtener adjuntos del card {card_id}: {str(e)}"
            logger.error(error_msg)
            raise PipefyAPIError(error_msg)

    async def move_card_to_phase(self, card_id: str, phase_id: str) -> bool:
        """
        Mueve un card a una fase específica.
        
        Args:
            card_id (str): ID del card
            phase_id (str): ID de la fase destino
            
        Returns:
            bool: True si el movimiento fue exitoso
            
        Raises:
            PipefyAPIError: Si hay error en la API de Pipefy
        """
        mutation = """
        mutation MoveCardToPhase(\$card_id: ID!, \$phase_id: ID!) {
          moveCardToPhase(input: {
            card_id: \$card_id,
            destination_phase_id: \$phase_id
          }) {
            card {
              id
              current_phase {
                id
                name
              }
            }
          }
        }
        """
        
        variables = {
            "card_id": card_id,
            "phase_id": phase_id
        }
        
        try:
            result = await self.execute_query(mutation, variables)
            
            if result and result.get("moveCardToPhase", {}).get("card"):
                logger.info(f"✅ Card {card_id} movido exitosamente a la fase {phase_id}")
                return True
            
            logger.error(f"❌ Error moviendo card {card_id} a la fase {phase_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error inesperado moviendo card {card_id} a la fase {phase_id}: {str(e)}")
            return False

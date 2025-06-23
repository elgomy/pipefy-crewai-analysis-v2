import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pipefy_client import PipefyClient
from pipefy_client.exceptions import PipefyAPIError

class TestPipefyClient:
    @pytest.fixture
    def mock_attachments_response(self):
        """Mock de respuesta para documentos adjuntos."""
        return {
            "data": {
                "card": {
                    "attachments": [
                        {
                            "url": "https://example.com/doc1.pdf",
                            "field": {
                                "id": "field_1",
                                "label": "Contrato Social"
                            },
                            "filename": "contrato_social.pdf"
                        },
                        {
                            "url": "https://example.com/doc2.pdf",
                            "field": {
                                "id": "field_2",
                                "label": "Documento RG"
                            },
                            "filename": "rg.pdf"
                        }
                    ]
                }
            }
        }

    @pytest.mark.asyncio
    async def test_get_card_attachments_success(self, pipefy_client, mock_attachments_response):
        """Test obtención exitosa de documentos adjuntos."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_attachments_response
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            documents = await pipefy_client.get_card_attachments("123456")
            
            assert len(documents) == 2
            assert documents[0]["name"] == "contrato_social.pdf"
            assert documents[0]["file_url"] == "https://example.com/doc1.pdf"
            assert documents[0]["document_tag"] == "contrato_social"
            
            assert documents[1]["name"] == "rg.pdf"
            assert documents[1]["file_url"] == "https://example.com/doc2.pdf"
            assert documents[1]["document_tag"] == "documento_rg"
    
    @pytest.mark.asyncio
    async def test_get_card_attachments_no_attachments(self, pipefy_client):
        """Test cuando el card no tiene documentos adjuntos."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"card": {"attachments": []}}}
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            documents = await pipefy_client.get_card_attachments("123456")
            assert len(documents) == 0
    
    @pytest.mark.asyncio
    async def test_get_card_attachments_error(self, pipefy_client):
        """Test manejo de errores al obtener documentos adjuntos."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"errors": ["Error de prueba"]}
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(PipefyAPIError, match="Error GraphQL al obtener adjuntos"):
                await pipefy_client.get_card_attachments("123456")

    @pytest.mark.asyncio
    async def test_move_card_to_phase_success(self, mock_pipefy_client, mock_execute_query):
        """Test movimiento exitoso de card a una fase."""
        # Mock respuesta exitosa
        mock_execute_query.return_value = {
            "moveCardToPhase": {
                "card": {
                    "id": "123",
                    "current_phase": {
                        "id": "456",
                        "name": "Nueva Fase"
                    }
                }
            }
        }
        
        result = await mock_pipefy_client.move_card_to_phase("123", "456")
        assert result is True
        
        # Verificar que se llamó a execute_query con los parámetros correctos
        mock_execute_query.assert_called_once()
        call_args = mock_execute_query.call_args
        assert "moveCardToPhase" in call_args[0][0]
        assert call_args[0][1] == {"card_id": "123", "phase_id": "456"}
        
    @pytest.mark.asyncio
    async def test_move_card_to_phase_failure(self, mock_pipefy_client, mock_execute_query):
        """Test fallo al mover card a una fase."""
        # Mock respuesta fallida
        mock_execute_query.return_value = {
            "moveCardToPhase": None
        }
        
        result = await mock_pipefy_client.move_card_to_phase("123", "456")
        assert result is False
        
        # Verificar que se llamó a execute_query con los parámetros correctos
        mock_execute_query.assert_called_once()
        call_args = mock_execute_query.call_args
        assert "moveCardToPhase" in call_args[0][0]
        assert call_args[0][1] == {"card_id": "123", "phase_id": "456"}
        
    @pytest.mark.asyncio
    async def test_move_card_to_phase_api_error(self, mock_pipefy_client, mock_execute_query):
        """Test error de API al mover card."""
        # Mock error de API
        mock_execute_query.side_effect = PipefyAPIError("Error de API")
        
        with pytest.raises(PipefyAPIError):
            await mock_pipefy_client.move_card_to_phase("123", "456") 
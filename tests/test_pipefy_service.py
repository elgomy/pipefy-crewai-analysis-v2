"""
Tests para el módulo pipefy_service.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from src.services.pipefy_service import PipefyService
from src.integrations.pipefy_client import PipefyAPIError

@pytest.fixture
def mock_pipefy_client():
    """Fixture que proporciona un mock del cliente de Pipefy."""
    client = Mock()
    client.move_card_by_classification = AsyncMock()
    client.update_card_field = AsyncMock()
    return client

@pytest.fixture
def pipefy_service(mock_pipefy_client):
    """Fixture que proporciona una instancia del servicio de Pipefy con un cliente mock."""
    return PipefyService(client=mock_pipefy_client)

@pytest.fixture
def sample_analysis_result():
    """Fixture que proporciona un resultado de análisis de ejemplo."""
    return {
        "is_complete": True,
        "documents": [
            {
                "name": "Contrato Social",
                "is_valid": True
            }
        ],
        "details": {
            "validacion_identidad": {
                "nombre": "Juan Pérez",
                "documento": "12345678"
            }
        }
    }

@pytest.mark.asyncio
async def test_process_triagem_result_success(pipefy_service, mock_pipefy_client, sample_analysis_result):
    """Test procesamiento exitoso de resultado de triagem."""
    # Configurar mocks
    mock_pipefy_client.move_card_by_classification.return_value = {
        "success": True,
        "new_phase_id": "123",
        "new_phase_name": "Aprobado"
    }
    mock_pipefy_client.update_card_field.return_value = {
        "success": True
    }
    
    # Ejecutar test
    result = await pipefy_service.process_triagem_result("card_123", sample_analysis_result)
    
    # Verificar resultado
    assert result["success"] is True
    assert result["card_id"] == "card_123"
    assert len(result["operations"]) > 0
    assert not result["errors"]
    
    # Verificar que se llamaron los métodos correctos
    mock_pipefy_client.move_card_by_classification.assert_called_once()
    mock_pipefy_client.update_card_field.assert_called()

@pytest.mark.asyncio
async def test_process_triagem_result_api_error(pipefy_service, mock_pipefy_client, sample_analysis_result):
    """Test manejo de error de API durante procesamiento de triagem."""
    # Configurar mock para lanzar error
    mock_pipefy_client.move_card_by_classification.side_effect = PipefyAPIError("API Error")
    
    # Ejecutar test
    result = await pipefy_service.process_triagem_result("card_123", sample_analysis_result)
    
    # Verificar resultado
    assert result["success"] is False
    assert len(result["errors"]) == 1
    assert "Error de API Pipefy" in result["errors"][0]

@pytest.mark.asyncio
async def test_update_card_informe_success(pipefy_service, mock_pipefy_client, sample_analysis_result):
    """Test actualización exitosa de informe en card."""
    # Configurar mock
    mock_pipefy_client.update_card_field.return_value = {
        "success": True
    }
    
    # Ejecutar test
    result = await pipefy_service.update_card_informe("card_123", sample_analysis_result)
    
    # Verificar resultado
    assert result["success"] is True
    
    # Verificar que se llamó al método correcto
    mock_pipefy_client.update_card_field.assert_called()

@pytest.mark.asyncio
async def test_update_card_informe_error(pipefy_service, mock_pipefy_client, sample_analysis_result):
    """Test manejo de error al actualizar informe en card."""
    # Configurar mock para lanzar error
    mock_pipefy_client.update_card_field.side_effect = Exception("Error inesperado")
    
    # Verificar que se lanza la excepción
    with pytest.raises(Exception) as exc_info:
        await pipefy_service.update_card_informe("card_123", sample_analysis_result)
    
    assert "Error inesperado" in str(exc_info.value) 
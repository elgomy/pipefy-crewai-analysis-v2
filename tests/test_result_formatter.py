"""
Tests para el módulo result_formatter.
"""
import pytest
from datetime import datetime
from src.services.result_formatter import ResultFormatter

@pytest.fixture
def sample_analysis_result():
    """Fixture con un resultado de análisis de ejemplo."""
    return {
        "is_complete": True,
        "documents": [
            {
                "name": "Contrato Social",
                "is_valid": True
            },
            {
                "name": "RG",
                "is_valid": False,
                "error_reason": "Documento expirado"
            }
        ],
        "details": {
            "validacion_identidad": {
                "nombre": "Juan Pérez",
                "documento": "12345678"
            },
            "validacion_empresa": "Empresa válida"
        },
        "observations": "Documentos principales verificados.",
        "critical_observations": [
            "RG necesita ser actualizado",
            "Pendiente firma digital"
        ]
    }

class TestResultFormatter:
    """Tests para la clase ResultFormatter."""
    
    def test_format_analysis_result(self, sample_analysis_result):
        """Test del método principal format_analysis_result."""
        card_id = "123456"
        result = ResultFormatter.format_analysis_result(sample_analysis_result, card_id)
        
        # Verificar que retorna ambos reportes
        assert "detailed_report" in result
        assert "summary_report" in result
        
        # Verificar contenido del reporte detallado
        detailed = result["detailed_report"]
        assert card_id in detailed
        assert "✅ Completo" in detailed
        assert "Contrato Social" in detailed
        assert "RG" in detailed
        assert "Documento expirado" in detailed
        assert "Juan Pérez" in detailed
        assert "Documentos principales verificados" in detailed
        
        # Verificar contenido del reporte resumido
        summary = result["summary_report"]
        assert card_id in summary
        assert "✅ Documentación completa y válida" in summary
        assert "📄 1/2 documentos válidos" in summary
        assert "RG necesita ser actualizado" in summary
        assert "Pendiente firma digital" in summary
    
    def test_format_empty_analysis_result(self):
        """Test con un resultado de análisis vacío."""
        empty_result = {
            "is_complete": False,
            "documents": [],
            "details": {},
            "observations": ""
        }
        
        result = ResultFormatter.format_analysis_result(empty_result, "123456")
        
        # Verificar reporte detallado
        detailed = result["detailed_report"]
        assert "⚠️ Incompleto" in detailed
        assert "No se encontraron documentos para analizar" in detailed
        assert "No hay detalles adicionales del análisis" in detailed
        
        # Verificar reporte resumido
        summary = result["summary_report"]
        assert "⚠️ Documentación incompleta o inválida" in summary
        assert "📄 0/0 documentos válidos" in summary
    
    def test_format_documents_section(self, sample_analysis_result):
        """Test del método _format_documents_section."""
        docs_section = ResultFormatter._format_documents_section(sample_analysis_result["documents"])
        
        assert "✅ **Contrato Social**" in docs_section
        assert "❌ **RG**" in docs_section
        assert "Razón: Documento expirado" in docs_section
    
    def test_format_analysis_details(self, sample_analysis_result):
        """Test del método _format_analysis_details."""
        details_section = ResultFormatter._format_analysis_details(sample_analysis_result)
        
        assert "### Validacion Identidad" in details_section
        assert "**Nombre**: Juan Pérez" in details_section
        assert "**Documento**: 12345678" in details_section
        assert "**Validacion Empresa**: Empresa válida" in details_section
    
    def test_format_summary(self, sample_analysis_result):
        """Test del método _format_summary."""
        summary = ResultFormatter._format_summary(sample_analysis_result)
        
        assert "✅ Documentación completa y válida" in summary
        assert "📄 1/2 documentos válidos" in summary
        assert "⚠️ Observaciones importantes:" in summary
        assert "- RG necesita ser actualizado" in summary
        assert "- Pendiente firma digital" in summary 
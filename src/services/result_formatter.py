"""
Módulo para formatear resultados del análisis para Pipefy.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json

class ResultFormatter:
    """
    Clase para formatear resultados del análisis en el formato requerido por Pipefy.
    """
    
    @staticmethod
    def format_analysis_result(analysis_result: Dict[str, Any], card_id: str) -> Dict[str, str]:
        """
        Formatea el resultado del análisis para los campos de Pipefy.
        
        Args:
            analysis_result (Dict): Resultado del análisis de documentos
            card_id (str): ID del card de Pipefy
            
        Returns:
            Dict[str, str]: Diccionario con los campos formateados para Pipefy
        """
        # Obtener timestamp actual
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Formatear informe detallado
        detailed_report = f"""# 📄 Informe de Análisis - CrewAI v2.0

## 📊 Resumen
- **Card ID**: {card_id}
- **Fecha**: {timestamp}
- **Estado**: {"✅ Completo" if analysis_result.get("is_complete") else "⚠️ Incompleto"}

## 📋 Documentos Analizados
{ResultFormatter._format_documents_section(analysis_result.get("documents", []))}

## 🔍 Detalles del Análisis
{ResultFormatter._format_analysis_details(analysis_result)}

## 📝 Observaciones
{analysis_result.get("observations", "Sin observaciones adicionales.")}

---
*Generado automáticamente por CrewAI v2.0*"""

        # Formatear informe resumido
        summary_report = f"""📄 Análisis de Documentos - Card {card_id}
Estado: {"✅ Completo" if analysis_result.get("is_complete") else "⚠️ Incompleto"}
Fecha: {timestamp}

{ResultFormatter._format_summary(analysis_result)}"""

        return {
            "detailed_report": detailed_report,
            "summary_report": summary_report
        }
    
    @staticmethod
    def _format_documents_section(documents: list) -> str:
        """Formatea la sección de documentos analizados."""
        if not documents:
            return "No se encontraron documentos para analizar."
            
        result = ""
        for doc in documents:
            status = "✅" if doc.get("is_valid") else "❌"
            result += f"\n{status} **{doc.get('name', 'Documento sin nombre')}**"
            if not doc.get("is_valid"):
                result += f"\n   - Razón: {doc.get('error_reason', 'No especificada')}"
        return result
    
    @staticmethod
    def _format_analysis_details(analysis_result: Dict[str, Any]) -> str:
        """Formatea los detalles del análisis."""
        details = analysis_result.get("details", {})
        if not details:
            return "No hay detalles adicionales del análisis."
            
        result = ""
        for key, value in details.items():
            if isinstance(value, dict):
                result += f"\n### {key.replace('_', ' ').title()}\n"
                for sub_key, sub_value in value.items():
                    result += f"- **{sub_key.replace('_', ' ').title()}**: {sub_value}\n"
            else:
                result += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        return result
    
    @staticmethod
    def _format_summary(analysis_result: Dict[str, Any]) -> str:
        """Formatea el resumen del análisis."""
        summary = []
        
        # Agregar estado general
        if analysis_result.get("is_complete"):
            summary.append("✅ Documentación completa y válida")
        else:
            summary.append("⚠️ Documentación incompleta o inválida")
        
        # Agregar conteo de documentos
        docs = analysis_result.get("documents", [])
        valid_docs = len([d for d in docs if d.get("is_valid")])
        total_docs = len(docs)
        summary.append(f"📄 {valid_docs}/{total_docs} documentos válidos")
        
        # Agregar observaciones críticas
        if analysis_result.get("critical_observations"):
            summary.append("\n⚠️ Observaciones importantes:")
            for obs in analysis_result["critical_observations"]:
                summary.append(f"- {obs}")
        
        return "\n".join(summary) 
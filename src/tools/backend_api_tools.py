#!/usr/bin/env python3
"""
Backend API Tools - Herramientas Simples para CrewAI
ENFOQUE HÍBRIDO INTELIGENTE: Estas herramientas NO contienen lógica compleja.
Solo hacen llamadas HTTP al backend que contiene toda la lógica de negocio.

Cada herramienta es súper simple: recibe parámetros, llama al backend, devuelve respuesta.
"""

import os
import httpx
import logging
from typing import Dict, Any, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Configuración de logging
logger = logging.getLogger(__name__)

# URL del backend (Document Ingestion Service)
BACKEND_URL = os.getenv("DOCUMENT_INGESTION_URL", "https://pipefy-document-ingestion-modular.onrender.com")

class ObtenerDocumentosConContenidoAPITool(BaseTool):
    """
    HERRAMIENTA ULTRA-SIMPLE: Obtiene documentos con contenido parseado automáticamente
    
    BRILLANTE SIMPLIFICACIÓN: Los documentos YA están parseados cuando se suben.
    Solo necesitamos consultar la tabla documents existente que ya tiene todo.
    
    ¡No necesitamos endpoints de parseo porque ya está integrado en el flujo de subida!
    """
    name: str = "obtener_documentos_con_contenido_api"
    description: str = """
    Obtiene documentos de un caso CON su contenido parseado automáticamente.
    Los documentos se parsean automáticamente al subirlos, así que aquí solo consultamos.
    
    Parámetros:
    - case_id: ID del caso/card cuyos documentos obtener
    - include_content: Si incluir el contenido parseado completo (default: true)
    
    Retorna: Lista de documentos con URLs, metadatos Y contenido parseado listo para análisis.
    """
    
    def _run(self, case_id: str, include_content: bool = True) -> str:
        """
        Consulta la tabla documents que YA TIENE el contenido parseado.
        Ultra-simple: solo una consulta a Supabase.
        """
        try:
            logger.info(f"📄 Obteniendo documentos con contenido para case_id: {case_id}")
            
            # Llamada HTTP simple al backend que consulta tabla documents
            with httpx.Client(timeout=30.0) as client:
                params = {"include_content": include_content}
                response = client.get(
                    f"{BACKEND_URL}/api/v1/documentos/{case_id}",
                    params=params
                )
                response.raise_for_status()
                result = response.json()
            
            if result.get("success"):
                documents = result.get("documents", [])
                logger.info(f"✅ Encontrados {len(documents)} documentos con contenido para case_id: {case_id}")
                
                if documents:
                    doc_summaries = []
                    for doc in documents:
                        name = doc.get('name', 'Sin nombre')
                        doc_type = doc.get('document_tag', 'Sin tipo')
                        parsing_status = doc.get('parsing_status', 'unknown')
                        
                        if parsing_status == 'completed':
                            content_length = len(doc.get('parsed_content', ''))
                            confidence = doc.get('confidence_score', 0.0)
                            doc_summaries.append(
                                f"- {name} ({doc_type}): ✅ {content_length} caracteres parseados (Confianza: {confidence:.2f})"
                            )
                            
                            # Si incluir contenido, añadirlo para análisis
                            if include_content and doc.get('parsed_content'):
                                doc_summaries.append(f"  CONTENIDO: {doc['parsed_content'][:500]}..." if len(doc['parsed_content']) > 500 else f"  CONTENIDO: {doc['parsed_content']}")
                        else:
                            doc_summaries.append(f"- {name} ({doc_type}): ❌ Parseo falló o pendiente")
                    
                    return f"Documentos con contenido para {case_id}:\n" + "\n".join(doc_summaries)
                else:
                    return f"No se encontraron documentos para el case_id: {case_id}"
            else:
                error_msg = f"Error al obtener documentos: {result.get('message', 'Error desconocido')}"
                logger.error(error_msg)
                return error_msg
                
        except httpx.TimeoutException:
            error_msg = f"Timeout al obtener documentos para {case_id}"
            logger.error(error_msg)
            return error_msg
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP {e.response.status_code} al obtener documentos para {case_id}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error inesperado al obtener documentos para {case_id}: {str(e)}"
            logger.error(error_msg)
            return error_msg



class EnriquecerClienteAPITool(BaseTool):
    """
    HERRAMIENTA SIMPLE: Enriquece datos de cliente con CNPJ
    
    El agente solo necesita saber:
    "Para obtener todos los datos de un cliente, uso esta herramienta con el CNPJ"
    
    TODA la lógica compleja (CNPJá API, BrasilAPI, fallbacks, etc.) 
    está en el backend, no aquí.
    """
    name: str = "enriquecer_cliente_api"
    description: str = """
    Enriquece los datos de un cliente usando su CNPJ.
    Obtiene información completa de la empresa desde múltiples fuentes.
    
    Parámetros:
    - cnpj: CNPJ de la empresa (solo números)
    - case_id: ID del caso/card para asociar los datos
    
    Retorna: Información completa de la empresa o error si no se encuentra.
    """
    
    def _run(self, cnpj: str, case_id: str) -> str:
        """
        Llama al backend para enriquecer datos de cliente.
        Súper simple: solo hace la llamada HTTP.
        """
        try:
            logger.info(f"🔍 Llamando al backend para enriquecer CNPJ: {cnpj}")
            
            # Preparar datos para el backend
            payload = {
                "cnpj": cnpj,
                "case_id": case_id
            }
            
            # Llamada HTTP simple al backend
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{BACKEND_URL}/api/v1/cliente/enriquecer",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            if result.get("success"):
                logger.info(f"✅ Cliente enriquecido exitosamente: {cnpj}")
                return f"Cliente enriquecido exitosamente. {result.get('message', '')}"
            else:
                logger.error(f"❌ Error al enriquecer cliente: {result.get('message')}")
                return f"Error al enriquecer cliente: {result.get('message', 'Error desconocido')}"
                
        except httpx.TimeoutException:
            error_msg = f"Timeout al enriquecer cliente {cnpj}. El backend tardó más de 60 segundos."
            logger.error(error_msg)
            return error_msg
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP {e.response.status_code} al enriquecer cliente {cnpj}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error inesperado al enriquecer cliente {cnpj}: {str(e)}"
            logger.error(error_msg)
            return error_msg



class NotificarWhatsAppAPITool(BaseTool):
    """
    HERRAMIENTA SIMPLE: Envía notificación WhatsApp
    
    El agente solo necesita saber:
    "Para enviar una notificación WhatsApp, uso esta herramienta"
    
    TODA la lógica de Twilio está en el backend.
    """
    name: str = "notificar_whatsapp_api"
    description: str = """
    Envía una notificación WhatsApp al responsable de un card.
    
    Parámetros:
    - card_id: ID del card de Pipefy
    - mensaje: Mensaje a enviar
    
    Retorna: Confirmación del envío o error.
    """
    
    def _run(self, card_id: str, mensaje: str) -> str:
        """
        Llama al backend para enviar WhatsApp.
        Súper simple: solo hace la llamada HTTP.
        """
        try:
            logger.info(f"📱 Enviando WhatsApp para card_id: {card_id}")
            
            # Preparar datos para el backend
            payload = {
                "card_id": card_id,
                "mensaje": mensaje
            }
            
            # Llamada HTTP simple al backend
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{BACKEND_URL}/api/v1/whatsapp/enviar",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            if result.get("success"):
                logger.info(f"✅ WhatsApp enviado exitosamente para card: {card_id}")
                return f"WhatsApp enviado exitosamente. {result.get('message', '')}"
            else:
                logger.error(f"❌ Error al enviar WhatsApp: {result.get('message')}")
                return f"Error al enviar WhatsApp: {result.get('message', 'Error desconocido')}"
                
        except httpx.TimeoutException:
            error_msg = f"Timeout al enviar WhatsApp para card {card_id}"
            logger.error(error_msg)
            return error_msg
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP {e.response.status_code} al enviar WhatsApp para card {card_id}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error inesperado al enviar WhatsApp para card {card_id}: {str(e)}"
            logger.error(error_msg)
            return error_msg

class ActualizarPipefyAPITool(BaseTool):
    """
    HERRAMIENTA SIMPLE: Actualiza campos en Pipefy
    
    El agente solo necesita saber:
    "Para actualizar un campo en Pipefy, uso esta herramienta"
    
    TODA la lógica de Pipefy GraphQL está en el backend.
    """
    name: str = "actualizar_pipefy_api"
    description: str = """
    Actualiza un campo específico en un card de Pipefy.
    
    Parámetros:
    - card_id: ID del card de Pipefy
    - campo: Nombre del campo a actualizar
    - valor: Nuevo valor para el campo
    
    Retorna: Confirmación de la actualización o error.
    """
    
    def _run(self, card_id: str, campo: str, valor: str) -> str:
        """
        Llama al backend para actualizar Pipefy.
        Súper simple: solo hace la llamada HTTP.
        """
        try:
            logger.info(f"📝 Actualizando campo '{campo}' en card: {card_id}")
            
            # Preparar datos para el backend
            payload = {
                "card_id": card_id,
                "campo": campo,
                "valor": valor
            }
            
            # Llamada HTTP simple al backend
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{BACKEND_URL}/api/v1/pipefy/actualizar",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            if result.get("success"):
                logger.info(f"✅ Campo actualizado exitosamente en Pipefy: {card_id}")
                return f"Campo '{campo}' actualizado exitosamente en Pipefy. {result.get('message', '')}"
            else:
                logger.error(f"❌ Error al actualizar Pipefy: {result.get('message')}")
                return f"Error al actualizar campo en Pipefy: {result.get('message', 'Error desconocido')}"
                
        except httpx.TimeoutException:
            error_msg = f"Timeout al actualizar Pipefy para card {card_id}"
            logger.error(error_msg)
            return error_msg
        except httpx.HTTPStatusError as e:
            error_msg = f"Error HTTP {e.response.status_code} al actualizar Pipefy para card {card_id}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error inesperado al actualizar Pipefy para card {card_id}: {str(e)}"
            logger.error(error_msg)
            return error_msg

# Lista de todas las herramientas disponibles para el agente
# VERSIÓN SIMPLIFICADA: Integración elegante con tabla documents existente
BACKEND_API_TOOLS = [
    ObtenerDocumentosConContenidoAPITool(),  # NUEVA: Con contenido parseado integrado
    EnriquecerClienteAPITool(),
    NotificarWhatsAppAPITool(),
    ActualizarPipefyAPITool()
] 
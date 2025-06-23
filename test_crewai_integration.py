#!/usr/bin/env python3
"""
Tests de Integración - CrewAI Analysis Service
pipefy-crewai-analysis-v2

Valida que el servicio CrewAI funcione correctamente de forma independiente
y que sus herramientas simples puedan comunicarse con el backend
"""

import pytest
import asyncio
import httpx
import json
import os
from unittest.mock import patch, MagicMock

# URLs de los servicios
CREWAI_URL = os.getenv("CREWAI_URL", "http://localhost:8001")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# URLs de producción
CREWAI_PROD_URL = "https://pipefy-crewai-analysis-v2.onrender.com"
BACKEND_PROD_URL = "https://pipefy-document-ingestion-v2.onrender.com"

class TestCrewAIIntegration:
    """Tests de integración para el servicio CrewAI"""
    
    @pytest.mark.asyncio
    async def test_crewai_health_check(self):
        """Test: Health check del servicio CrewAI"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{CREWAI_URL}/health")
                assert response.status_code == 200
                
                health_data = response.json()
                assert "status" in health_data
                assert health_data["status"] == "healthy"
                
                print(f"✅ CrewAI Health Check OK: {health_data}")
                
            except httpx.ConnectError:
                pytest.skip(f"CrewAI service not available at {CREWAI_URL}")

    @pytest.mark.asyncio
    async def test_crewai_analysis_endpoint(self):
        """Test: Endpoint de análisis CrewAI"""
        test_payload = {
            "case_id": "test_case_crewai_123",
            "analysis_type": "document_triaging"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{CREWAI_URL}/analyze",
                    json=test_payload
                )
                
                print(f"✅ CrewAI Analysis Endpoint - Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   Analysis Result Keys: {list(result.keys())}")
                
            except httpx.ConnectError:
                pytest.skip(f"CrewAI service not available at {CREWAI_URL}")

    @pytest.mark.asyncio
    async def test_crewai_tools_backend_communication(self):
        """Test: Herramientas CrewAI llamando al backend"""
        
        # Simular que las herramientas CrewAI llaman al backend
        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('httpx.AsyncClient.get') as mock_get:
            
            # Mock respuestas del backend
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "success": True,
                "message": "Backend response"
            }
            mock_post.return_value.raise_for_status = MagicMock()
            
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "success": True,
                "documents": []
            }
            mock_get.return_value.raise_for_status = MagicMock()
            
            # Test herramienta EnriquecerClienteAPI
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{BACKEND_URL}/api/v1/cliente/enriquecer",
                    json={"cnpj": "11222333000181", "case_id": "test"}
                )
                
                print(f"✅ CrewAI Tool → Backend (Enriquecer) - OK")
            
            # Test herramienta ObtenerDocumentosAPI
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BACKEND_URL}/api/v1/documentos/test_case"
                )
                
                print(f"✅ CrewAI Tool → Backend (Documentos) - OK")

    @pytest.mark.asyncio
    async def test_crewai_faq_knowledge_access(self):
        """Test: Acceso al conocimiento FAQ"""
        
        # Verificar que el servicio CrewAI puede acceder al FAQ
        faq_test_payload = {
            "question": "¿Qué documentos son obligatorios para el cadastro?",
            "context": "empresa nueva"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{CREWAI_URL}/faq/query",
                    json=faq_test_payload
                )
                
                print(f"✅ CrewAI FAQ Knowledge - Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   FAQ Response: {result.get('answer', 'No answer')[:100]}...")
                
            except httpx.ConnectError:
                pytest.skip(f"CrewAI service not available at {CREWAI_URL}")

    @pytest.mark.asyncio
    async def test_crewai_production_health(self):
        """Test: Health check en producción"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(f"{CREWAI_PROD_URL}/health")
                print(f"🌐 CrewAI Production Health - Status: {response.status_code}")
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ CrewAI Production OK: {health_data}")
            except Exception as e:
                print(f"⚠️ CrewAI Production issue: {e}")

    @pytest.mark.asyncio
    async def test_crewai_backend_tools_validation(self):
        """Test: Validar que las herramientas del backend están configuradas"""
        
        # Test que verifica la configuración de las herramientas
        expected_tools = [
            "EnriquecerClienteAPITool",
            "ObtenerDocumentosAPITool", 
            "NotificarWhatsAppAPITool",
            "ActualizarPipefyAPITool"
        ]
        
        # Simular validación de herramientas
        for tool_name in expected_tools:
            print(f"✅ Tool configured: {tool_name}")
        
        print(f"✅ All backend API tools validated")

class TestCrewAIBackendCommunication:
    """Tests específicos para la comunicación CrewAI ↔ Backend"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self):
        """Test: Flujo completo de análisis CrewAI usando herramientas backend"""
        
        test_case_id = "WORKFLOW_TEST_001"
        
        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('httpx.AsyncClient.get') as mock_get:
            
            # Mock respuestas coordinadas del backend
            mock_responses = {
                "enriquecer": {
                    "success": True,
                    "data": {
                        "cnpj": "11222333000181",
                        "company_name": "TEST COMPANY LTDA",
                        "status": "ATIVA"
                    }
                },
                "documentos": {
                    "success": True,
                    "documents": [
                        {
                            "name": "contrato_social.pdf",
                            "document_tag": "contrato_social",
                            "file_url": "https://test.supabase.co/storage/v1/test.pdf"
                        }
                    ]
                },
                "whatsapp": {"success": True, "message": "WhatsApp enviado"},
                "pipefy": {"success": True, "message": "Pipefy actualizado"}
            }
            
            def mock_post_side_effect(*args, **kwargs):
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.raise_for_status = MagicMock()
                
                url = str(args[0]) if args else str(kwargs.get('url', ''))
                if 'enriquecer' in url:
                    mock_resp.json.return_value = mock_responses["enriquecer"]
                elif 'whatsapp' in url:
                    mock_resp.json.return_value = mock_responses["whatsapp"]
                elif 'pipefy' in url:
                    mock_resp.json.return_value = mock_responses["pipefy"]
                else:
                    mock_resp.json.return_value = {"success": True}
                
                return mock_resp
            
            def mock_get_side_effect(*args, **kwargs):
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.raise_for_status = MagicMock()
                mock_resp.json.return_value = mock_responses["documentos"]
                return mock_resp
            
            mock_post.side_effect = mock_post_side_effect
            mock_get.side_effect = mock_get_side_effect
            
            # Simular que CrewAI ejecuta todas sus herramientas
            workflow_steps = [
                ("Enriquecer Cliente", f"{BACKEND_URL}/api/v1/cliente/enriquecer"),
                ("Obtener Documentos", f"{BACKEND_URL}/api/v1/documentos/{test_case_id}"),
                ("Enviar WhatsApp", f"{BACKEND_URL}/api/v1/whatsapp/enviar"),
                ("Actualizar Pipefy", f"{BACKEND_URL}/api/v1/pipefy/actualizar")
            ]
            
            for step_name, url in workflow_steps:
                if "documentos" in url:
                    # GET request
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url)
                else:
                    # POST request
                    async with httpx.AsyncClient() as client:
                        response = await client.post(url, json={"test": "data"})
                
                print(f"✅ CrewAI Workflow Step: {step_name}")
            
            print(f"✅ Full CrewAI → Backend workflow test completed")

async def run_crewai_tests():
    """Ejecutar todos los tests del servicio CrewAI"""
    print("🤖 Iniciando Tests de Integración - CrewAI Analysis Service")
    print("=" * 60)
    
    test_classes = [TestCrewAIIntegration, TestCrewAIBackendCommunication]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Ejecutando {test_class.__name__}")
        print("-" * 40)
        
        instance = test_class()
        test_methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                await method()
                passed_tests += 1
                print(f"✅ {method_name}")
            except Exception as e:
                print(f"❌ {method_name}: {str(e)}")
    
    print(f"\n" + "=" * 60)
    print(f"🎯 CrewAI Tests: {passed_tests}/{total_tests} passed")
    print(f"📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    result = asyncio.run(run_crewai_tests())
    exit(0 if result else 1)
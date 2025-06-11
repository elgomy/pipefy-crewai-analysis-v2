#!/usr/bin/env python3
"""
Script de validación de variables de entorno para el servicio CrewAI.
Ejecuta este script para verificar que todas las variables requeridas estén configuradas.
"""
import sys
from config import settings

def main():
    """Valida la configuración de variables de entorno."""
    print("🔍 Validando configuración de variables de entorno...")
    print("=" * 60)
    
    # Validar variables requeridas
    missing_vars = settings.validate_required_vars()
    
    if missing_vars:
        print("❌ VARIABLES FALTANTES:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Asegúrate de:")
        print("   1. Copiar .env.example como .env")
        print("   2. Completar todas las variables requeridas")
        print("   3. Verificar que el archivo .env esté en la raíz del proyecto")
        sys.exit(1)
    
    print("✅ Todas las variables requeridas están configuradas")
    print("\n📋 CONFIGURACIÓN ACTUAL:")
    print(f"   - Puerto: {settings.PORT}")
    print(f"   - Host: {settings.HOST}")
    print(f"   - Log Level: {settings.LOG_LEVEL}")
    print(f"   - Processing Timeout: {settings.PROCESSING_TIMEOUT}s")
    print(f"   - OpenAI API: {'✅ Configurado' if settings.OPENAI_API_KEY else '❌ Faltante'}")
    print(f"   - LlamaCloud API: {'✅ Configurado' if settings.LLAMACLOUD_API_KEY else '❌ Faltante'}")
    print(f"   - Supabase URL: {'✅ Configurado' if settings.SUPABASE_URL else '❌ Faltante'}")
    print(f"   - Service Token: {'✅ Configurado' if settings.INGESTION_SERVICE_TOKEN else '❌ Faltante'}")
    
    print("\n🤖 CONFIGURACIÓN CREWAI:")
    print(f"   - Verbose Mode: {settings.CREW_VERBOSE}")
    print(f"   - Memory Enabled: {settings.CREW_MEMORY}")
    
    openai_config = settings.get_openai_config()
    print(f"\n🧠 CONFIGURACIÓN OPENAI:")
    print(f"   - Modelo: {openai_config['model']}")
    print(f"   - Temperature: {openai_config['temperature']}")
    
    print("\n🚀 Configuración válida! El servicio está listo para ejecutarse.")

if __name__ == "__main__":
    main()
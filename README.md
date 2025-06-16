# 🤖 CrewAI Analysis v2.0 - Triagem Agent

**Servicio Especializado en Triagem Documental con IA**

## 🧠 Arquitectura - Modelo Híbrido

Este servicio implementa la **"IA Estratega"** en nuestro modelo híbrido:
- **Responsabilidad**: Analizar documentos y generar estrategias de acción
- **Enfoque v2.0**: 100% dedicado al `triagem_agente` (otros agentes en stand-by)
- **Comunicación**: HTTP directo, recibe llamadas del servicio de ingestión v2.0

## 🎯 Agente Especializado: Triagem Documental

### 🔍 **Especialista en Conformidade Documental v2.0**
- **Misión**: Validar documentos contra checklist dinámico de Supabase
- **Fuentes de Conocimiento**:
  - `checklist_config` table (Supabase) - Reglas actualizables
  - `FAQ.pdf` (Knowledge Base) - Casos especiales y excepciones
- **Output**: Plan de acción estructurado en JSON

### 📊 **Clasificaciones de Salida**
```json
{
  "status_geral": "Aprovado | Pendencia_Bloqueante | Pendencia_NaoBloqueante",
  "acoes_requeridas": [
    {
      "tipo": "MOVER_CARD",
      "fase_destino": "338000018",
      "motivo": "Documentação completa e conforme"
    },
    {
      "tipo": "NOTIFICAR_WHATSAPP",
      "destinatario": "gestor_comercial",
      "mensagem": "Pendência crítica identificada"
    },
    {
      "tipo": "GERAR_DOCUMENTO_CNPJ",
      "cnpj": "12345678000199",
      "motivo": "Cartão CNPJ desatualizado"
    }
  ],
  "informe_markdown": "## Relatório de Triagem...",
  "detalhes_checklist": {...}
}
```

## 🧩 Lógica de Negocio Centralizada

### 📚 **Base de Conhecimento Dinâmica**
- **FAQ.pdf**: Casos especiais, exceções, regras de negócio
- **Checklist Config**: Regras atualizables desde Supabase
- **Prompts Especializados**: Tasks.yaml para triagem específica

### 🔄 **Flexibilidad Total**
- **Cambios de Reglas**: Actualizar FAQ.pdf o checklist_config
- **Nuevas Acciones**: Añadir tipos en `acoes_requeridas`
- **Sin Código**: Modificaciones vía conocimiento, no código Python

## 🛠️ Stack Tecnológico

- **Framework**: CrewAI + FastAPI
- **LLM**: OpenAI GPT-4o-mini
- **Knowledge**: LlamaIndex + RAG
- **Parsing**: LlamaParse para documentos
- **Deployment**: Render
- **Puerto**: 8002

## 📁 Estructura del Proyecto

```
pipefy-crewai-analysis-v2/
├── triagem_crew/
│   ├── config/
│   │   ├── agents.yaml        # Configuración del agente triagem
│   │   ├── tasks.yaml         # Tasks específicas de triagem
│   │   └── crew.yaml          # Configuración de la crew
│   ├── knowledge/
│   │   ├── FAQ.pdf           # Base de conocimiento principal
│   │   └── checklist_cache/  # Cache de checklists parseados
│   ├── tools/
│   │   ├── supabase_tool.py  # Herramientas Supabase
│   │   ├── document_tool.py  # Herramientas documentos
│   │   └── checklist_tool.py # Herramientas checklist
│   └── crew.py              # Definición de la crew
├── analysis_results/         # Resultados de análisis
├── app.py                   # Aplicación FastAPI
├── requirements.txt         # Dependencias
├── Dockerfile              # Configuración Docker
└── render.yaml             # Configuración Render
```

## 🚀 Configuración y Despliegue

### 1. Configuración de Variables de Entorno

**Paso 1**: Copia el archivo de ejemplo
```bash
cp .env.example .env
```

**Paso 2**: Completa las variables requeridas en `.env`
```bash
# OpenAI para LLM
OPENAI_API_KEY=tu_openai_api_key

# Supabase (proyecto: crewai-cadastro)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu_anon_key

# LlamaParse para parsing de documentos
LLAMACLOUD_API_KEY=tu_llama_api_key

# Autenticación entre servicios
INGESTION_SERVICE_TOKEN=tu_token_seguro_compartido
```

**Paso 3**: Valida la configuración
```bash
python validate_env.py
```

### 2. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecución Local
```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Despliegue en Render

1. **Conecta el repositorio** a Render
2. **Configura las variables de entorno** en el dashboard de Render (mismos valores del .env)
3. **Render detectará automáticamente** el `render.yaml` y desplegará el servicio

**URL del servicio**: `https://pipefy-crewai-analysis-modular.onrender.com`

## 📊 Endpoints

- `POST /triagem/analyze` - Análisis de triagem asíncrono
- `POST /triagem/analyze/sync` - Análisis de triagem síncrono
- `GET /health` - Health check
- `GET /status` - Estado del servicio
- `GET /` - Información del servicio

## 🔗 Comunicación

### **Recibe de**: pipefy-document-ingestion-v2
```json
{
  "case_id": "card_12345",
  "documents": [...],
  "checklist_config": {...}
}
```

### **Responde con**: Plan de acción estructurado
```json
{
  "status_geral": "Pendencia_Bloqueante",
  "acoes_requeridas": [...],
  "informe_markdown": "...",
  "processing_time": 45.2
}
```

## 🎯 Enfoque v2.0

- ✅ **100% Triagem Agent**: Máxima eficiencia en clasificación documental
- ⏸️ **Otros Agentes**: `extrator_agente` y `risco_agente` en stand-by
- 🚀 **Escalabilidad**: Preparado para reintegrar otros agentes posteriormente

---

**Versión**: 2.0 - Especializado en Triagem  
**Agente Principal**: Especialista en Conformidade Documental  
**Arquitectura**: IA Estratega en Modelo Híbrido

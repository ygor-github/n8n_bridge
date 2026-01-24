# Elantar n8n Bridge - Guía del Proyecto

Este proyecto es un módulo para **Odoo 18 Community** que actúa como un puente (bridge) con **n8n** para automatizar la atención al cliente en el Live Chat mediante especialistas de Inteligencia Artificial.

## 🚀 Propósito Principal
Capturar mensajes de los canales de LiveChat de Odoo y enviarlos a flujos de trabajo en n8n. n8n procesa estos mensajes usando modelos de lenguaje (LLMs) y devuelve respuestas calculadas al chat de Odoo, o realiza acciones como crear Leads en el CRM.

---

## 🏗️ Arquitectura del Sistema

### 1. Componentes en Odoo (`addons/n8n_bridge`)
*   **Modelos (`models/`):**
    *   `MailMessage` (`mail_message.py`): Extiende el sistema de mensajería para detectar nuevos mensajes en canales de chat y disparar el envío a n8n.
    *   `N8nBridgeState` (`bridge_state.py`): Gestiona el estado de la conversación (quién responde: bot o humano) y almacena datos de contexto (nombre detectado, preocupaciones del cliente, etc.).
    *   `LivechatChannel` (`livechat_channel.py`): Permite configurar URLs de webhooks y tokens por canal, además de forzar la disponibilidad online de los bots.
*   **Controladores (`controllers/main.py`):**
    *   API REST que n8n utiliza para interactuar con Odoo:
        *   `/n8n_bridge/update_state`: Actualiza el contexto y el especialista activo.
        *   `/n8n_bridge/chat_response`: Envía la respuesta del AI Agent al canal de Odoo.
        *   `/n8n_bridge/search_resource`: Búsqueda genérica de registros (mensajes, estados).
        *   `/n8n_bridge/create_resource`: Creación de registros (Leads, etc.).
*   **Datos y Seguridad (`data/`, `security/`):**
    *   `automation_rules.xml`: Define la regla que dispara el puente al crear un `mail.message`.
    *   `n8n_bot_user.xml`: Define el usuario "Virtual Assistant" que firma las respuestas IA.
    *   `config_parameters.xml`: Parámetros globales de configuración (URL de n8n, tokens).

### 2. Componentes en n8n (`flows/`)
*   **Estrategia de Orquestación:**
    *   El flujo principal (`Assistant_AKP_Website.json`) recibe el webhook de Odoo.
    *   Utiliza un **Debounce** (10s) para agrupar mensajes seguidos de un mismo usuario.
    *   Consulta el historial en Odoo para entender el hilo de la conversación.
    *   Clasifica al usuario según su intención (Refiner, Purity, Service, General).
    *   Utiliza herramientas (Tools) para guardar información persistente en Odoo.
    *   Responde a través del modelo **Llama 3.1** (vía Groq).

---

## � Botones Interactivos (Quick Replies)
El bridge soporta botones de respuesta rápida manejados desde n8n.

### Formato de Envío (HTML)
n8n puede responder con el siguiente bloque HTML:
```html
<div class="n8n-button-container">
  <button class="n8n-quick-reply" data-reply="Quiero información">ℹ️ Info</button>
  <button class="n8n-quick-reply" data-reply="Agendar cita">📅 Cita</button>
</div>
```

### Funcionamiento Técnico
*   **JS (`static/src/js/n8n_buttons.js`)**: Escucha clics en `.n8n-quick-reply`, inyecta el valor de `data-reply` en el compositor de Odoo y dispara el envío automático.
*   **CSS (`static/src/css/n8n_buttons.css`)**: Estiliza los botones con un diseño moderno y soporte para modo oscuro.

---

## �🔒 Seguridad e Integración
La comunicación se valida mediante un token enviado en el encabezado `X-N8N-Token`.
Existe una jerarquía de configuración para los parámetros (Webhook URL y Tokens):
1.  **Canal LiveChat**: Configuración específica por canal.
2.  **Variables de Entorno**: `N8N_BRIDGE_WEBHOOK_URL`, `N8N_BRIDGE_OUTGOING_TOKEN`, etc.
3.  **Sistema (ICP)**: Parámetros en Ajustes -> Técnico -> Parámetros del sistema.

---

## 🛠️ Guía de Uso Rápido
1.  **Instalación**: Instalar el módulo en Odoo 18.
2.  **Configuración**: Ir al Canal de LiveChat deseado y configurar la URL del Webhook de n8n y los tokens respectivos.
3.  **Bot**: Asegurarse de que el usuario "Virtual Assistant" sea operador del canal.
4.  **Flujos**: Importar los JSON de la carpeta `flows/` en n8n y configurar las credenciales de Groq y Odoo.

---
*Generado por Antigravity - 2026*

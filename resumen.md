# Elantar n8n Bridge - Guía Técnica del Proyecto (Odoo 18)

Este proyecto es un módulo avanzado para **Odoo 18 Community** que integra el ecosistema de **Live Chat** con la orquestación de **n8n**. Permite automatizar la atención al cliente mediante una arquitectura de multi-agentes de Inteligencia Artificial especializados.

## 🚀 Propósito Principal
El bridge actúa como una capa de comunicación bidireccional:
1.  **Captura**: Intercepta mensajes en canales de `discuss.channel` y los envía a un webhook de n8n.
2.  **Procesamiento**: n8n utiliza LLMs (como Llama 3.1) y herramientas (tools) para decidir la mejor respuesta o acción (ej: crear Leads).
3.  **Respuesta**: n8n devuelve la respuesta a Odoo, pudiendo incluir componentes interactivos y simulando comportamiento humano (escritura).

---

## 🏗️ Arquitectura Detallada

### 1. Núcleo en Odoo (`addons/n8n_bridge`)

*   **Modelos de Datos (`models/`):**
    *   `MailMessage` ([mail_message.py](file:///home/ygor/repo_faov/dev-odoo18-docker/addons/n8n_bridge/models/mail_message.py)): Extensión lógica que detecta nuevos mensajes. Implementa una **jerarquía de configuración inteligente** (Canal > Env > Parámetros de Sistema) para determinar el destino del mensaje.
    *   `BridgeState` ([bridge_state.py](file:///home/ygor/repo_faov/dev-odoo18-docker/addons/n8n_bridge/models/bridge_state.py)): Almacena el estado persistente de cada conversación, permitiendo rastrear qué "especialista" está activo y guardando contexto JSON extraído por la IA.
    *   `LivechatChannel` ([livechat_channel.py](file:///home/ygor/repo_faov/dev-odoo18-docker/addons/n8n_bridge/models/livechat_channel.py)): Extiende la configuración de canales para permitir tokens específicos y **forzar la disponibilidad 24/7** del bot, asegurando que el widget de chat sea siempre accesible.

*   **API y Controladores (`controllers/main.py`):**
    *   `/n8n_bridge/chat_response`: Endpoint de alta disponibilidad que procesa respuestas externas, maneja el bypass de sanitización de HTML para botones y soporta **simulación de escritura (typing)** para realismo.
    *   `/n8n_bridge/update_state` y `/n8n_bridge/get_state`: Gestión dinámica del agente activo y recuperación del contexto de la charla.
    *   `/n8n_bridge/set_typing`: Permite al bot marcar presencia visual en el chat sin enviar un mensaje.
    *   `Recursos Genéricos`: Endpoints `/create_resource` y `/search_resource` que dan a n8n acceso total (pero controlado por token) a cualquier modelo de Odoo (CRM, Sales, etc.).

*   **Frontend y UX (`static/`):**
    *   **Shadow DOM Compat**: Diseñado específicamente para Odoo 18, permitiendo que los botones interactivos funcionen dentro del encapsulamiento del widget de chat.
    *   **Bloqueo de Input**: ([n8n_buttons.js](file:///home/ygor/repo_faov/dev-odoo18-docker/addons/n8n_bridge/static/src/js/n8n_buttons.js)) Cuando el bot presenta opciones (Quick Replies), el campo de texto se bloquea temporalmente para guiar al usuario a una selección válida.

### 2. Orquestación en n8n (`flows/`)
*   **Agente Enrutador**: Recibe el mensaje inicial y decide a qué sub-agente (Ventas, Soporte, Marketing) transferir la conversación.
*   **Sub-agentes Especializados**: Flujos independientes ([subagente_ventas.json](file:///home/ygor/repo_faov/dev-odoo18-docker/addons/n8n_bridge/flows/subagente_ventas.json), [subagente_marketing.json](file:///home/ygor/repo_faov/dev-odoo18-docker/addons/n8n_bridge/flows/subagente_marketing.json)) con directrices y herramientas propias.

---

## 🛠️ Características Clave

| Característica | Descripción |
| :--- | :--- |
| **Smart Handover** | Detecta automáticamente la intervención de un humano en el chat y silencia al bot para evitar colisiones. |
| **Simulated Typing** | El bot puede marcar "está escribiendo..." con intervalos realistas antes de enviar una respuesta. |
| **Quick Replies** | Soporte para botones HTML con acciones como: respuesta automática, apertura de links y cierre de ventana. |
| **Multi-DB Ready** | El controlador gestiona dinámicamente la conexión a la base de datos correcta en entornos compartidos. |
| **Security First** | Validación mediante tokens granulares (`X-N8N-Token`) tanto para tráfico saliente como entrante. |

---

## ⚙️ Configuración y Seguridad
La seguridad se maneja en tres niveles:
1.  **Variables de Entorno**: `N8N_BRIDGE_INCOMING_TOKEN`, `N8N_BRIDGE_OUTGOING_TOKEN`, `N8N_BRIDGE_WEBHOOK_URL`.
2.  **Configuración de Canal**: Permite personalizar tokens y la URL del webhook de forma granular por canal de chat.
3.  **ICP (System Parameters)**: 
    *   `n8n_bridge.webhook_url`: URL global de n8n.
    *   `n8n_bridge.outgoing_token`: Token para validar tráfico Odoo -> n8n.
    *   `n8n_bridge.incoming_token`: Token para validar tráfico n8n -> Odoo.
    *   `n8n_bridge.bot_partner_id`: ID del partner que representará al bot globalmente.

> [!IMPORTANT]
> Para Odoo 18, asegúrese de que el usuario "Virtual Assistant" (creado por el módulo) tenga el Partner ID configurado en los parámetros del sistema o sea operador del canal para evitar bucles de mensajes.

---
*Revisado y actualizado por Antigravity - Enero 2026*

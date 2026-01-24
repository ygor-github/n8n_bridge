# Guía de Uso: context_data en n8n_bridge

## Propósito
El campo `context_data` permite almacenar el estado de la conversación y datos extraídos del usuario (onboarding) para evitar preguntas repetitivas.

## Estructura Recomendada para Onboarding
Para un flujo de captación de datos, se sugiere una estructura JSON que agrupe la información del cliente.

```json
{
  "status": "onboarding", 
  "step": "waiting_for_email",
  "customer_data": {
    "name": "María González",
    "language": "es_ES",
    "address": "Calle Falsa 123",
    "phone": "+5699999999"
  },
  "flags": {
    "is_returning_customer": true
  }
}
```

## Flujo Lógico sugerido para el Agente (n8n)

1. **Verificar Dato:** Al recibir un mensaje, el agente revisa si `body.context_data.customer_data.phone` existe.
2. **Preguntar vs. Continuar:** 
   - Si es `null` -> El agente pregunta: "¿Cuál es tu número?".
   - Si existe -> El agente omite la pregunta.
3. **Actualizar Estado:**
   - Cuando el usuario responde, el agente extrae el dato.
   - Envía un `POST` a `/n8n_bridge/update_state` con el JSON actualizado (haciendo merge con lo anterior).

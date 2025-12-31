from odoo import models, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _notify_n8n(self):
        """Envía el mensaje a n8n si cumple las condiciones."""
        webhook_url = "https://n8n.erpelantar.com/webhook/odoo-livechat-webhook"
        # Usar sudo() para buscar el bot y evitar problemas de permisos con Guests
        bot_partner = self.env.ref('n8n_bridge.partner_n8n_bot', raise_if_not_found=False)
        bot_partner_id = bot_partner.id if bot_partner else False
        
        for record in self:
            _logger.info("Procesando mensaje %s (Res ID: %s, Model: %s)", record.id, record.res_id, record.model)
            
            # Evitar bucles: no procesar mensajes del propio bot
            if bot_partner_id and record.author_id.id == bot_partner_id:
                _logger.info("Mensaje ignorado: Autor es el Bot n8n.")
                continue

            # Solo procesar mensajes de canales de chat (LiveChat o Discuss)
            if record.model == 'discuss.channel':
                # Soporte para Invitados (Odoo 18 usa author_guest_id para LiveChat anonimo)
                author_name = record.author_id.name or (record.author_guest_id.name if record.author_guest_id else "Invitado")
                author_id = record.author_id.id or (f"guest_{record.author_guest_id.id}" if record.author_guest_id else "unknown")

                # Verificar si el mensaje ya contiene la marca de bot para evitar bucles visuales
                if '<span class="n8n-bot">' in (record.body or ''):
                    _logger.info("Mensaje ignorado: Contiene marca de bot.")
                    continue
                
                # Buscar el estado del bridge con SUDO
                bridge_state = self.env['n8n.bridge.state'].sudo().search([
                    ('channel_id', '=', record.res_id)
                ], limit=1)

                payload = {
                    "body": record.body,
                    "author_id": author_id,
                    "author_name": author_name,
                    "res_id": record.res_id,
                    "res_model": record.model,
                    "message_id": record.id,
                    "active_specialist": bridge_state.active_specialist_id if bridge_state else False,
                    "context_data": json.loads(bridge_state.context_data) if bridge_state and bridge_state.context_data else {},
                }

                _logger.info("Enviando webhook a n8n: %s", payload)

                try:
                    # Usar timeout y no bloquear el hilo de Odoo mas de lo necesario
                    resp = requests.post(webhook_url, json=payload, timeout=5)
                    _logger.info("Respuesta de n8n (Status %s): %s", resp.status_code, resp.text)
                except Exception as e:
                    _logger.warning("Error al contactar webhook de n8n: %s", e)
            else:
                _logger.info("Mensaje ignorado: El modelo no es discuss.channel (es %s)", record.model)

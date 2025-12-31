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
        bot_partner = self.env.ref('n8n_bridge.partner_n8n_bot', raise_if_not_found=False)
        bot_partner_id = bot_partner.id if bot_partner else False
        
        for record in self:
            # Evitar bucles: no procesar mensajes del propio bot
            if record.author_id.id == bot_partner_id:
                continue

            # Solo procesar mensajes de canales de chat que no sean del bot
            if record.model == 'discuss.channel' and record.author_id and '<span class="n8n-bot">' not in (record.body or ''):
                
                # Buscar el estado del bridge para este canal
                bridge_state = self.env['n8n.bridge.state'].search([
                    ('channel_id', '=', record.res_id)
                ], limit=1)

                payload = {
                    "body": record.body,
                    "author_id": record.author_id.id,
                    "author_name": record.author_id.name,
                    "res_id": record.res_id,
                    "res_model": record.model,
                    "message_id": record.id,
                    "active_specialist": bridge_state.active_specialist_id if bridge_state else False,
                    "context_data": json.loads(bridge_state.context_data) if bridge_state and bridge_state.context_data else {},
                }

                try:
                    # Ejecutar en segundo plano no es trivial aquí, pero usamos timeout
                    requests.post(webhook_url, json=payload, timeout=5)
                except Exception as e:
                    _logger.warning("Error al contactar webhook de n8n: %s", e)

from odoo import models, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _notify_n8n(self):
        """Envía el mensaje a n8n de forma asíncrona usando configuración por canal."""
        try:
            import threading
            
            # Bot Partner para evitar bucles
            bot_partner = self.env.ref('n8n_bridge.partner_n8n_bot', raise_if_not_found=False)
            bot_partner_id = bot_partner.id if bot_partner else False
            
            icp = self.env['ir.config_parameter'].sudo()
            global_webhook_url = icp.get_param('n8n_bridge.webhook_url', 'https://n8n.erpelantar.com/webhook/odoo-diagnostic-webhook')
            global_token = "elantar_n8n_bridge_2025" # Backup token

            for record in self:
                # Filtros rápidos
                if not record.model or not record.res_id or record.model != 'discuss.channel':
                    continue

                # Evitar bucles
                if bot_partner_id and record.author_id and record.author_id.id == bot_partner_id:
                    continue

                if record.body and '<span class="n8n-bot">' in record.body:
                    continue

                # Obtener canal y su configuración específica
                channel = self.env['discuss.channel'].sudo().browse(record.res_id)
                livechat_channel = channel.livechat_channel_id
                
                webhook_url = global_webhook_url
                outgoing_token = global_token

                if livechat_channel:
                    if livechat_channel.n8n_webhook_url:
                        webhook_url = livechat_channel.n8n_webhook_url
                    if livechat_channel.n8n_outgoing_token:
                        outgoing_token = livechat_channel.n8n_outgoing_token

                # Recolección de datos
                author_name = "Invitado"
                author_id = "unknown"
                is_internal_user = False

                if record.author_id:
                    author_name = record.author_id.name or "Invitado"
                    author_id = record.author_id.id
                    user = self.env['res.users'].sudo().search([('partner_id', '=', record.author_id.id)], limit=1)
                    if user and not user.share:
                        is_internal_user = True
                elif record.author_guest_id:
                    author_name = record.author_guest_id.name or "Invitado"
                    author_id = f"guest_{record.author_guest_id.id}"

                # Estado del bridge
                bridge_state = self.env['n8n.bridge.state'].sudo().search([
                    ('channel_id', '=', record.res_id)
                ], limit=1)

                if is_internal_user:
                    _logger.debug("Intervención de staff detectada en canal %s. Silenciando bot.", record.res_id)
                    if bridge_state:
                        bridge_state.write({'active_specialist_id': 'human'})
                    else:
                        self.env['n8n.bridge.state'].sudo().create({
                            'channel_id': record.res_id,
                            'active_specialist_id': 'human'
                        })
                    continue

                context_data = {}
                active_specialist = False
                if bridge_state:
                    active_specialist = bridge_state.active_specialist_id
                    if active_specialist == 'human':
                        _logger.debug("Bot silenciado para canal %s.", record.res_id)
                        continue
                        
                    if bridge_state.context_data:
                        try:
                            context_data = json.loads(bridge_state.context_data)
                        except:
                            pass

                payload = {
                    "body": record.body,
                    "author_id": author_id,
                    "author_name": author_name,
                    "res_id": record.res_id,
                    "res_model": record.model,
                    "message_id": record.id,
                    "active_specialist": active_specialist,
                    "context_data": context_data,
                }

                # Lanzar hilo para enviar el webhook
                def send_to_n8n(url, token, data):
                    try:
                        headers = {'X-N8N-Token': token}
                        _logger.info("BRIDGE: Enviando webhook a %s con token", url)
                        requests.post(url, json=data, headers=headers, timeout=5)
                    except Exception as e:
                        _logger.warning("BRIDGE: Error en envío a n8n: %s", e)

                threading.Thread(target=send_to_n8n, args=(webhook_url, outgoing_token, payload)).start()

        except Exception as e:
            _logger.error("CRITICAL BRIDGE ERROR: Fallo en _notify_n8n: %s", e)

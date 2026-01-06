from odoo import models, api
import json
import logging
import os
import requests
import threading

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _notify_n8n(self):
        """Envía el mensaje a n8n usando configuración dinámica (Canal > Env > ICP)."""
        _logger.info("BRIDGE: _notify_n8n disparado")
        try:
            
            # Bot Partner para evitar bucles
            bot_partner = self.env.ref('n8n_bridge.partner_n8n_bot', raise_if_not_found=False)
            bot_partner_id = bot_partner.id if bot_partner else False
            
            for record in self:
                _logger.info("BRIDGE: Procesando mensaje ID %s, modelo: %s, res_id: %s", record.id, record.model, record.res_id)
                # Filtros rápidos
                if not record.model or not record.res_id or record.model != 'discuss.channel':
                    _logger.info("BRIDGE: Saltando mensaje %s (modelo %s no es discuss.channel)", record.id, record.model)
                    continue

                # Evitar bucles
                if bot_partner_id and record.author_id and record.author_id.id == bot_partner_id:
                    _logger.info("BRIDGE: Ignorando mensaje %s (es del bot)", record.id)
                    continue

                if record.body and '<span class="n8n-bot">' in record.body:
                    _logger.info("BRIDGE: Ignorando mensaje %s (contiene firma de bot)", record.id)
                    continue

                # 1. Obtener Canal y fallback de Webhook/Token
                channel = self.env['discuss.channel'].sudo().browse(record.res_id)
                livechat_channel = channel.livechat_channel_id
                
                # Jerarquía de configuración: 
                # A. Canal específico
                # B. Variable de entorno
                # C. Parámetro de sistema (ICP)
                
                webhook_url = False
                outgoing_token = False
                source = "unknown"

                # A. Probar Canal
                if livechat_channel:
                    webhook_url = livechat_channel.n8n_webhook_url
                    outgoing_token = livechat_channel.n8n_outgoing_token
                    source = "Canal LiveChat"

                # B. Probar Variables de Entorno
                if not webhook_url:
                    webhook_url = os.environ.get('N8N_BRIDGE_WEBHOOK_URL')
                    outgoing_token = os.environ.get('N8N_BRIDGE_OUTGOING_TOKEN')
                    source = "Variables de Entorno (.env)"
                
                # C. Probar ICP (Parámetros del sistema)
                if not webhook_url:
                    icp = self.env['ir.config_parameter'].sudo()
                    webhook_url = icp.get_param('n8n_bridge.webhook_url')
                    outgoing_token = icp.get_param('n8n_bridge.outgoing_token')
                    source = "Parámetros del Sistema (ICP)"

                if not webhook_url:
                    _logger.warning("BRIDGE: Mensaje %s ignorado. No hay URL de webhook configurada (Canal/Env/ICP).", record.id)
                    continue

                _logger.info("BRIDGE: Usando configuración desde %s para canal %s", source, record.res_id)

                # Recolección de datos
                author_name = "Invitado"
                author_id = "unknown"
                is_internal_user = False

                # Campos adicionales para el payload
                active_specialist = 'bot'
                context_data = {}

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
                    _logger.info("BRIDGE: Intervención de staff detectada en canal %s. Silenciando bot.", record.res_id)
                    if bridge_state:
                        bridge_state.write({'active_specialist_id': 'human'})
                    else:
                        self.env['n8n.bridge.state'].sudo().create({
                            'channel_id': record.res_id,
                            'active_specialist_id': 'human'
                        })
                    continue

                if bridge_state:
                    active_specialist = bridge_state.active_specialist_id
                    if active_specialist == 'human':
                        _logger.info("BRIDGE: Bot silenciado para canal %s (modo humano activo).", record.res_id)
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
                        response = requests.post(url, json=data, headers=headers, timeout=5)
                        _logger.info("BRIDGE: Respuesta de n8n [%s]: %s", response.status_code, response.text[:200])
                    except Exception as e:
                        _logger.warning("BRIDGE: Error en envío a n8n: %s", e)

                threading.Thread(target=send_to_n8n, args=(webhook_url, outgoing_token, payload)).start()

        except Exception as e:
            _logger.error("CRITICAL BRIDGE ERROR: Fallo en _notify_n8n: %s", e)

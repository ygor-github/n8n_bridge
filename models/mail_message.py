from odoo import models, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _notify_n8n(self):
        """Envía el mensaje a n8n de forma asíncrona y ultra-segura."""
        try:
            import threading
            # Obtener URL del webhook desde parámetros del sistema
            icp = self.env['ir.config_parameter'].sudo()
            webhook_url = icp.get_param('n8n_bridge.webhook_url', 'https://n8n.erpelantar.com/webhook/odoo-diagnostic-webhook')
            
            # Bot Partner
            bot_partner = self.env.ref('n8n_bridge.partner_n8n_bot', raise_if_not_found=False)
            bot_partner_id = bot_partner.id if bot_partner else False
            
            for record in self:
                # Filtros rápidos súper seguros
                if not record.model or not record.res_id or record.model != 'discuss.channel':
                    continue

                # Evitar bucles: no procesar mensajes del propio bot
                if bot_partner_id and record.author_id and record.author_id.id == bot_partner_id:
                    continue

                # Evitar bucles visuales: marca n8n-bot
                if record.body and '<span class="n8n-bot">' in record.body:
                    continue

                # Recolección de datos mínima requerida fuera del hilo
                author_name = "Invitado"
                author_id = "unknown"
                is_internal_user = False

                if record.author_id:
                    author_name = record.author_id.name or "Invitado"
                    author_id = record.author_id.id
                    # Verificar si el autor es un usuario interno (no portal/guest)
                    user = self.env['res.users'].sudo().search([('partner_id', '=', record.author_id.id)], limit=1)
                    if user and not user.share:
                        is_internal_user = True
                elif record.author_guest_id:
                    author_name = record.author_guest_id.name or "Invitado"
                    author_id = f"guest_{record.author_guest_id.id}"


                # Estado del bridge (Búsqueda sudo para evitar problemas de permisos)
                bridge_state = self.env['n8n.bridge.state'].sudo().search([
                    ('channel_id', '=', record.res_id)
                ], limit=1)

                # Si es un usuario interno (soporte/staff), marcar como 'human' y salir
                if is_internal_user:
                    _logger.error("!!! BRIDGE ULTRA-FINAL-DEBUG !!! Intervención de staff detectada (%s) para canal %s. Marcando especialista como 'human'.", author_name, record.res_id)
                    if bridge_state:
                        bridge_state.write({'active_specialist_id': 'human'})
                    else:
                        bridge_state = self.env['n8n.bridge.state'].sudo().create({
                            'channel_id': record.res_id,
                            'active_specialist_id': 'human'
                        })
                    continue

                context_data = {}
                active_specialist = False
                if bridge_state:
                    active_specialist = bridge_state.active_specialist_id
                    _logger.error("!!! BRIDGE ULTRA-FINAL-DEBUG !!! Canal %s actual especialista: %s", record.res_id, active_specialist)
                    
                    # Si el especialista activo es 'human', NO notificar a n8n
                    if active_specialist == 'human':
                        _logger.info("BRIDGE: El bot está SILENCIADO. Un humano tiene el control en canal %s.", record.res_id)
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

                # Lanzar hilo para enviar el webhook sin bloquear Odoo
                def send_to_n8n(url, data):
                    try:
                        _logger.info("BRIDGE: Enviando webhook asíncrono a %s", url)
                        requests.post(url, json=data, timeout=5)
                    except Exception as e:
                        _logger.warning("BRIDGE: Error en hilo de envío a n8n: %s", e)

                threading.Thread(target=send_to_n8n, args=(webhook_url, payload)).start()

        except Exception as e:
            _logger.error("CRITICAL BRIDGE ERROR: Fallo total en _notify_n8n: %s", e)

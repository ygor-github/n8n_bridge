import json
import logging
import os
import time
from odoo import http
from odoo.http import request
from markupsafe import Markup
from odoo.addons.mail.tools.discuss import Store

_logger = logging.getLogger(__name__)

class N8nBridgeController(http.Controller):

    def _check_token(self, **kwargs):
        token = request.httprequest.headers.get('X-N8N-Token')
        if not token:
            token = kwargs.get('token')

        channel_id = kwargs.get('channel_id')
        
        # 1. Probar Token del Canal
        if channel_id:
            try:
                channel = request.env['discuss.channel'].sudo().browse(int(channel_id))
                if channel.exists() and channel.livechat_channel_id:
                    expected_token = channel.livechat_channel_id.n8n_incoming_token
                    if expected_token and token == expected_token:
                        return True
            except Exception as e:
                _logger.error("BRIDGE: Error validando token de canal: %s", e)

        # 2. Probar Token de Variables de Entorno
        env_token = os.environ.get('N8N_BRIDGE_INCOMING_TOKEN')
        if env_token and token == env_token:
            return True

        # 3. Probar Token de Parámetros del Sistema (ICP)
        icp_token = request.env['ir.config_parameter'].sudo().get_param('n8n_bridge.incoming_token')
        if icp_token and token == icp_token:
            return True

        # 4. Backup token (Hardcoded - Solo para compatibilidad transicional, se eliminará)
        if token == "elantar_n8n_bridge_2025":
            return True

        _logger.warning("BRIDGE: Intento de acceso no autorizado. Channel: %s, Token: %s", channel_id, token[:5] if token else "None")
        return False

    @http.route('/n8n_bridge/update_state', type='json', auth='none', methods=['POST'], csrf=False)
    def update_bridge_state(self, **kwargs):
        if not self._check_token(**kwargs):
            return {"status": "error", "message": "Unauthorized"}
            
        channel_id = kwargs.get('channel_id')
        specialist_id = kwargs.get('specialist_id')
        context_data = kwargs.get('context_data')
        
        state_model = request.env['n8n.bridge.state'].sudo()
        
        # Validar si el contexto es un diccionario y convertirlo a string
        if isinstance(context_data, dict):
            context_data = json.dumps(context_data)
            
        state = state_model.set_active_specialist(
            channel_id=int(channel_id),
            specialist_id=specialist_id,
            context=context_data
        )
        
        return {
            "status": "success",
            "channel_id": state.channel_id.id,
            "active_specialist": state.active_specialist_id
        }

    @http.route('/n8n_bridge/get_state/<int:channel_id>', type='json', auth='none', methods=['GET'])
    def get_bridge_state(self, channel_id):
        if not self._check_token(channel_id=channel_id):
            return {"status": "error", "message": "Unauthorized"}
            
        state = request.env['n8n.bridge.state'].sudo().search([('channel_id', '=', channel_id)], limit=1)
        if not state:
            return {"status": "error", "message": "Canal no encontrado"}
            
        return {
            "status": "success",
            "active_specialist": state.active_specialist_id,
            "context_data": json.loads(state.context_data) if state.context_data else {}
        }

    @http.route('/n8n_bridge/chat_response', type='http', auth='none', methods=['POST'], csrf=False)
    def chat_response(self, **kwargs):
        """
        Versión HTTP del endpoint para mayor control y evitar errores de despacho JSON-RPC.
        """
        try:
            _logger.info("BRIDGE: Chat response request received. Content-Type: %s, Raw Data: %s", 
                         request.httprequest.content_type, request.httprequest.data)
            
            # Extraer datos JSON si vienen en el body
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data.decode('utf-8'))
                # Si es JSON-RPC 2.0, los datos reales están en 'params'
                params = data.get('params', data)
            else:
                params = kwargs

            _logger.info("BRIDGE: Chat response received (HTTP). Params: %s", params)

            if not self._check_token(**params):
                _logger.warning("BRIDGE: Unauthorized attempt with token: %s", params.get('token'))
                return request.make_json_response({"status": "error", "message": "Unauthorized"}, status=401)

            channel_id = params.get('channel_id')
            body = params.get('body')
            simulate_typing = str(params.get('simulate_typing', '')).lower() in ('true', '1', 'yes')

            if not channel_id or not body:
                _logger.warning("BRIDGE: Missing parameters. channel_id: %s, body: %s", channel_id, body)
                return request.make_json_response({"status": "error", "message": "Missing channel_id or body"}, status=400)

            # Asegurar base de datos en entornos multi-db con auth='none'
            if not request.db:
                db_name = params.get('db') or os.environ.get('DATABASE') or 'restore251229'
                _logger.info("BRIDGE: Manual DB binding triggered for: %s", db_name)
                # Odoo core import here if needed, but 'odoo' should be available
                import odoo
                request.update_env(user=odoo.SUPERUSER_ID, context={'db': db_name})
            
            # Usar admin para contexto de sistema (Odoo 18 style)
            admin_user = request.env.ref('base.user_admin').sudo()
            env_admin = request.env(user=admin_user)
            
            channel = env_admin['discuss.channel'].browse(int(channel_id)).exists()
            if not channel:
                return request.make_json_response({"status": "error", "message": "Canal no encontrado"}, status=404)

            # Buscar el ID del partner del bot
            bot_partner = False
            if channel.livechat_channel_id and channel.livechat_channel_id.n8n_bot_user_id:
                bot_partner = channel.livechat_channel_id.n8n_bot_user_id.partner_id
            
            if not bot_partner:
                bot_partner_id = env_admin['ir.config_parameter'].get_param('n8n_bridge.bot_partner_id')
                if bot_partner_id:
                    bot_partner = env_admin['res.partner'].browse(int(bot_partner_id)).exists()
            
            if not bot_partner:
                bot_partner = env_admin.ref('n8n_bridge.partner_n8n_bot', raise_if_not_found=False)

            if not bot_partner:
                bot_partner = admin_user.partner_id

            # Simulación de escritura (Opcional)
            if simulate_typing:
                member = env_admin['discuss.channel.member'].search([
                    ('channel_id', '=', channel.id),
                    ('partner_id', '=', bot_partner.id)
                ], limit=1)
                
                if not member:
                    channel.add_members(partner_ids=[bot_partner.id])
                    member = env_admin['discuss.channel.member'].search([
                        ('channel_id', '=', channel.id),
                        ('partner_id', '=', bot_partner.id)
                    ], limit=1)

                if member:
                    _logger.info("BRIDGE: Simulating human typing for bot '%s' in channel %s", bot_partner.name, channel.id)
                    
                    # 1. Empieza a escribir
                    member._notify_typing(True)
                    env_admin.cr.commit() # Forzar envío al Bus/Websocket
                    time.sleep(1.5)
                    
                    # 2. Pausa breve (opcional, para realismo)
                    member._notify_typing(False)
                    env_admin.cr.commit()
                    time.sleep(0.5)
                    
                    # 3. Vuelve a escribir
                    member._notify_typing(True)
                    env_admin.cr.commit()
                    time.sleep(1.2)
                    # No hace falta notify(False) explícito, el mensaje lo quitará

            # Asegurar que el body no traiga saltos de línea literales escapados (\n)
            if isinstance(body, str):
                body = body.replace('\\n', '\n')

            # Registrar el mensaje directamente para bypass del sanitizer
            msg_vals = {
                'body': Markup(body),
                'model': 'discuss.channel',
                'res_id': channel.id,
                'message_type': 'comment',
                'subtype_id': env_admin.ref('mail.mt_comment').id,
                'author_id': bot_partner.id,
            }
            msg = env_admin['mail.message'].create(msg_vals)
            env_admin.cr.commit() # Asegurar que el mensaje se guarda

            # Notificación Real-time para Odoo 18
            channel._bus_send('discuss.channel/new_message', {
                'id': channel.id,
                'data': Store(msg).get_result(),
            })

            # Limpiar presencia explícitamente después del mensaje
            if simulate_typing and member:
                member._notify_typing(False)
                env_admin.cr.commit()

            return request.make_json_response({"status": "success"})

        except Exception as e:
            _logger.exception("BRIDGE: Error processing chat_response")
            return request.make_json_response({"status": "error", "message": str(e)}, status=500)

    @http.route('/n8n_bridge/set_typing', type='http', auth='none', methods=['POST'], csrf=False)
    def set_typing(self, channel_id=None, status=None, **kwargs):
        """
        Permite a n8n marcar presencia (typing) en un canal.
        """
        if not self._check_token():
            return request.make_json_response({"status": "error", "message": "Unauthorized"}, status=401)

        try:
            # Obtener parámetros
            c_id = channel_id or request.params.get('channel_id')
            s_val = status or request.params.get('status')

            if not c_id:
                return request.make_json_response({"status": "error", "message": "Missing channel_id"}, status=400)

            channel_id = int(c_id)
            is_typing = str(s_val).lower() in ('true', '1', 'yes')

            _logger.info("BRIDGE: set_typing - channel: %s, status: %s", channel_id, is_typing)

            # Usamos el admin para todo el contexto
            admin_user = request.env.ref('base.user_admin').sudo()
            env_admin = request.env(user=admin_user)

            channel = env_admin['discuss.channel'].browse(channel_id).exists()
            if not channel:
                return request.make_json_response({"status": "error", "message": "Channel not found"}, status=404)

            # Buscar el partner del bot
            bot_partner_id = env_admin['ir.config_parameter'].get_param('n8n_bridge.bot_partner_id')
            if bot_partner_id:
                bot_partner = env_admin['res.partner'].browse(int(bot_partner_id)).exists()
            else:
                bot_partner = admin_user.partner_id

            if not bot_partner:
                return request.make_json_response({"status": "error", "message": "Bot partner not found"}, status=500)

            # Buscar miembro del canal
            member = env_admin['discuss.channel.member'].search([
                ('channel_id', '=', channel.id),
                ('partner_id', '=', bot_partner.id)
            ], limit=1)

            if not member:
                _logger.info("BRIDGE: Bot no es miembro del canal %s, intentando unirlo.", channel.id)
                channel.add_members(partner_ids=[bot_partner.id])
                member = env_admin['discuss.channel.member'].search([
                    ('channel_id', '=', channel.id),
                    ('partner_id', '=', bot_partner.id)
                ], limit=1)

            if member:
                member._notify_typing(is_typing)
                return request.make_json_response({"status": "success", "is_typing": is_typing})
            else:
                return request.make_json_response({"status": "error", "message": "Bot is not a member of this channel"}, status=404)

        except Exception as e:
            _logger.exception("BRIDGE: Error in set_typing")
            return request.make_json_response({"status": "error", "message": str(e)}, status=500)

    @http.route('/n8n_bridge/create_resource', type='json', auth='none', methods=['POST'], csrf=False)
    def create_resource(self, model, vals):
        """
        Endpoint genérico para crear recursos en Odoo (CRM Leads, Proyectos, Facturas).
        """
        if not self._check_token():
            return {"status": "error", "message": "Unauthorized"}

        try:
            # Crear el registro con sudo()
            record = request.env[model].sudo().create(vals)
            
            return {
                "status": "success",
                "id": record.id,
                "display_name": record.display_name
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @http.route('/n8n_bridge/search_resource', type='json', auth='none', methods=['POST'], csrf=False)
    def search_resource(self, model, domain, fields=None, limit=80, order='id desc'):
        """
        Endpoint genérico para buscar recursos en Odoo.
        """
        # Intentar deducir channel_id para autenticación granulada (Token de Canal)
        channel_id = None
        if model == 'mail.message' and isinstance(domain, list):
            is_channel_model = False
            res_id_val = None
            for criterion in domain:
                if isinstance(criterion, (list, tuple)) and len(criterion) == 3:
                    field, operator, val = criterion
                    if field == 'model' and operator == '=' and val == 'discuss.channel':
                        is_channel_model = True
                    if field == 'res_id' and operator == '=':
                        res_id_val = val
            
            if is_channel_model and res_id_val:
                channel_id = res_id_val

        # Support for n8n.bridge.state queries
        if model == 'n8n.bridge.state' and isinstance(domain, list):
            for criterion in domain:
                if isinstance(criterion, (list, tuple)) and len(criterion) == 3:
                    field, operator, val = criterion
                    if field == 'channel_id' and operator == '=':
                        channel_id = val
                        break

        # Pasar channel_id deducido a _check_token
        if not self._check_token(channel_id=channel_id):
            return {"status": "error", "message": "Unauthorized"}

        try:
            records = request.env[model].sudo().search_read(
                domain=domain,
                fields=fields or ['id', 'display_name'],
                limit=limit,
                order=order
            )
            return {
                "status": "success",
                "result": records
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

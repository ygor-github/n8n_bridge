import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class N8nBridgeController(http.Controller):

    def _check_token(self, **kwargs):
        token = request.httprequest.headers.get('X-N8N-Token')
        if not token:
            token = kwargs.get('token')

        channel_id = kwargs.get('channel_id')
        if channel_id:
            try:
                channel = request.env['discuss.channel'].sudo().browse(int(channel_id))
                if channel.exists() and channel.livechat_channel_id:
                    expected_token = channel.livechat_channel_id.n8n_incoming_token
                    if expected_token:
                        return token == expected_token
            except:
                pass

        # Fallback al token global
        return token == "elantar_n8n_bridge_2025"

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
        if not self._check_token():
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

            if not channel_id or not body:
                _logger.warning("BRIDGE: Missing parameters. channel_id: %s, body: %s", channel_id, body)
                return request.make_json_response({"status": "error", "message": "Missing channel_id or body"}, status=400)

            channel = request.env['discuss.channel'].sudo().browse(int(channel_id))
            if not channel.exists():
                return request.make_json_response({"status": "error", "message": "Canal no encontrado"}, status=404)

            # Buscar el ID del partner del bot
            bot_partner = request.env.ref('n8n_bridge.partner_n8n_bot', raise_if_not_found=False)
            if not bot_partner:
                _logger.error("BRIDGE: Partner n8n_bot not found")
                return request.make_json_response({"status": "error", "message": "Bot partner not found"}, status=500)

            # Publicar el mensaje con un usuario válido en el ambiente (evita ValueError en discuss)
            user_admin = request.env.ref('base.user_admin').sudo()
            channel.with_user(user_admin).with_context(mail_create_nosummary=True).message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                author_id=bot_partner.id
            )

            return request.make_json_response({"status": "success"})

        except Exception as e:
            _logger.exception("BRIDGE: Error processing chat_response")
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
        if not self._check_token():
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

import json
from odoo import http
from odoo.http import request

class N8nBridgeController(http.Controller):

    def _check_token(self):
        token = request.httprequest.headers.get('X-N8N-Token')
        # También permitir token en los parámetros JSON para mayor flexibilidad
        if not token and request.params.get('token'):
            token = request.params.get('token')

        if token != "elantar_n8n_bridge_2025":
            return False
        return True

    @http.route('/n8n_bridge/update_state', type='json', auth='none', methods=['POST'], csrf=False)
    def update_bridge_state(self, channel_id, specialist_id=None, context_data=None):
        if not self._check_token():
            return {"status": "error", "message": "Unauthorized"}
            
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

    @http.route('/n8n_bridge/chat_response', type='json', auth='none', methods=['POST'], csrf=False)
    def chat_response(self, channel_id, body):
        if not self._check_token():
            return {"status": "error", "message": "Unauthorized"}

        channel = request.env['discuss.channel'].sudo().browse(int(channel_id))
        if not channel:
            return {"status": "error", "message": "Canal no encontrado"}

        # Buscar el ID del partner del bot
        bot_partner = request.env.ref('n8n_bridge.partner_n8n_bot')

        # Publicar el mensaje como el Bot
        channel.with_context(mail_create_nosummary=True).message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=bot_partner.id
        )

        return {"status": "success"}

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

from odoo import models, fields, api

class LivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    n8n_webhook_url = fields.Char(
        string='URL del Webhook de n8n',
        help="URL específica de n8n para este canal. Si está vacía, se usará la configuración global."
    )
    n8n_outgoing_token = fields.Char(
        string='Token Odoo -> n8n',
        help="Token enviado en el encabezado X-N8N-Token para validar peticiones enviadas a n8n."
    )
    n8n_incoming_token = fields.Char(
        string='Token n8n -> Odoo',
        help="Token requerido para las peticiones que n8n envía a Odoo para este canal."
    )

    def _compute_available_operator_ids(self):
        """
        Sobrescribe la disponibilidad de operadores para incluir al Bot de n8n
        siempre que sea miembro del canal.
        """
        super()._compute_available_operator_ids()
        bot_user = self.env.ref('n8n_bridge.user_n8n_bot', raise_if_not_found=False)
        if bot_user:
            for record in self:
                if bot_user in record.user_ids:
                    # Añadir el bot a los operadores disponibles (forzar online)
                    record.available_operator_ids = [(4, bot_user.id)]

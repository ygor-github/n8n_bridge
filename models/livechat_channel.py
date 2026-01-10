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

    n8n_bot_user_id = fields.Many2one(
        'res.users', 
        string='Usuario Bot n8n',
        help="Selecciona el usuario interno que actuará como Bot para este canal. Debe ser miembro de los operadores."
    )
    n8n_persistent_online = fields.Boolean(
        string='Forzar disponibilidad (Siempre online)',
        default=True,
        help="Si se activa, este usuario Bot aparecerá siempre conectado en el widget, permitiendo abrir el chat incluso si no hay humanos disponibles."
    )

    def _compute_available_operator_ids(self):
        """
        Sobrescribe la disponibilidad de operadores para incluir al Bot de n8n
        si está configurado y se fuerza su disponibilidad.
        """
        super()._compute_available_operator_ids()
        for record in self:
            if record.n8n_bot_user_id and record.n8n_persistent_online:
                # Verificar si el bot es un operador del canal
                if record.n8n_bot_user_id in record.user_ids:
                    # Añadir el bot a los operadores disponibles force
                    record.available_operator_ids = [(4, record.n8n_bot_user_id.id)]

    def _get_available_users(self):
        """
        Método usado por el controlador para determinar si el widget se muestra.
        Asegura que el bot configurado esté en la lista de usuarios disponibles 
        si tiene la persistencia activada.
        """
        users = super()._get_available_users()
        for channel in self:
            if channel.n8n_bot_user_id and channel.n8n_persistent_online:
                if channel.n8n_bot_user_id in channel.user_ids:
                    if channel.n8n_bot_user_id not in users:
                        users |= channel.n8n_bot_user_id
        return users

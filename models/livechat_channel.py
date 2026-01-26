from odoo import models, fields, api
from markupsafe import Markup

class LivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    # Redefinimos el campo de bienvenida como Html para evitar el escapado automático de Odoo 18

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

    n8n_enable_html_welcome = fields.Boolean(
        string='Mensaje Bienvenida HTML/n8n',
        default=True,
        help="Si se activa, el mensaje de bienvenida se renderizará como HTML real (para botones n8n). Si se desactiva, se mostrará como texto plano original de Odoo."
    )

    available_operator_ids = fields.Many2many('res.users', compute='_compute_available_operator_ids')
    
    # Redefinimos el campo de bienvenida como Html para evitar el escapado automático de Odoo 18
    default_message = fields.Html(
        'Welcome Message', 
        help="The welcome message that the visitor will receive when starting the live chat. Support HTML for n8n buttons.",
        translate=True
    )

    def _get_channel_infos(self):
        """
        Inyecta configuraciones de n8n en las opciones que recibe el frontend.
        """
        res = super()._get_channel_infos()
        res.update({
            'n8n_enable_html_welcome': self.n8n_enable_html_welcome,
        })
        return res

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
    def _open_livechat_discuss_channel(self, visitor_name, **kwargs):
        """
        Sobrescribe la apertura del canal para asegurar que el mensaje de bienvenida
        se trate como HTML seguro (Markup) y no se escape.
        """
        self.ensure_one()
        # Llamar al original para crear el canal y obtener la info
        info = super()._open_livechat_discuss_channel(visitor_name, **kwargs)
        
        channel_id = info.get('channel', {}).get('id')
        if channel_id and self.default_message:
            channel = self.env['discuss.channel'].browse(channel_id)
            
            # Buscamos el último mensaje del canal
            last_message = self.env['mail.message'].search([
                ('res_id', '=', channel.id),
                ('model', '=', 'discuss.channel'),
            ], limit=5, order='id desc')
            
            import logging
            _logger = logging.getLogger(__name__)
            
            for msg in last_message:
                # Si el mensaje contiene rastro de nuestro HTML escapado, lo corregimos
                if '&lt;p&gt;' in msg.body or '&lt;div' in msg.body or 'n8n-button-container' in msg.body:
                    _logger.info("BRIDGE: Corrigiendo mensaje de bienvenida escapado (ID %s)", msg.id)
                    
                    # 1. Limpieza de links anidados (Odoo Sanitizer mess)
                    import re
                    # Convierte <a href="<a href='url'>url</a>"> a <a href="url">
                    # Primero manejamos los casos donde Odoo inyectó un <a> dentro del atributo href del link original
                    cleaned_body = re.sub(r'href="&lt;a\s+href=\\&quot;([^&]*)\\&quot;[^&]*&gt;.*?&lt;/a&gt;"', r'href="\1"', msg.body)
                    cleaned_body = re.sub(r'href=\\&quot;&lt;a\s+href=\\&quot;([^&]*)\\&quot;[^&]*&gt;.*?&lt;/a&gt;\\&quot;', r'href="\1"', cleaned_body)
                    
                    # 2. Unescape manual
                    unescaped_body = cleaned_body.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'").replace('\\"', '"')
                    
                    # 3. Forzar Markup
                    msg.write({'body': Markup(unescaped_body)})
                    break
            
        return info

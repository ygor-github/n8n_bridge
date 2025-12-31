from odoo import models, api

class LivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _is_available(self):
        """
        Sobrescribe la lógica de disponibilidad para que si el n8n Assistant 
        está en el canal, siempre se considere disponible.
        """
        self.ensure_one()
        # Verificar si el Bot de n8n es uno de los operadores del canal
        bot_partner = self.env.ref('n8n_bridge.partner_n8n_bot', raise_if_not_found=False)
        if bot_partner and bot_partner in self.user_ids.partner_id:
            return True
            
        # Si el bot no está, se usa la lógica estándar (humanos online)
        return super(LivechatChannel, self)._is_available()

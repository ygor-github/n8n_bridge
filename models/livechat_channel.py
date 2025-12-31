from odoo import models, api

class LivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

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

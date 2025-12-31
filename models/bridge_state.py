from odoo import models, fields

class N8nBridgeState(models.Model):
    _name = 'n8n.bridge.state'
    _description = 'Mapeo de Estado de Especialista n8n'

    channel_id = fields.Many2one('discuss.channel', string='Canal de Chat', required=True, ondelete='cascade')
    active_specialist_id = fields.Char(string='ID del Especialista Activo', help="ID del workflow de n8n o identificador del especialista.")
    last_interaction = fields.Datetime(string='Última Interacción', default=fields.Datetime.now)
    context_data = fields.Text(string='Contexto Adicional (JSON)', help="Para guardar variables temporales de la sesión.")
    lead_id = fields.Many2one('crm.lead', string='Oportunidad Generada')

    def get_active_specialist(self, channel_id):
        """Devuelve el especialista activo para un canal."""
        state = self.search([('channel_id', '=', channel_id)], limit=1)
        return state.active_specialist_id if state else False

    def set_active_specialist(self, channel_id, specialist_id, context=None):
        """Establece o actualiza el especialista para un canal."""
        state = self.search([('channel_id', '=', channel_id)], limit=1)
        vals = {
            'channel_id': channel_id,
            'active_specialist_id': specialist_id,
            'last_interaction': fields.Datetime.now(),
        }
        if context:
            vals['context_data'] = context

        if state:
            state.write(vals)
        else:
            state = self.create(vals)
        return state

    _sql_constraints = [
        ('channel_unique', 'unique(channel_id)', 'Ya existe un estado para este canal.'),
    ]

from odoo import models, fields

class N8nBridgeState(models.Model):
    _name = 'n8n.bridge.state'
    _description = 'Mapeo de Estado de Especialista n8n'

    channel_id = fields.Many2one('discuss.channel', string='Canal de Chat', required=True, ondelete='cascade')
    active_specialist_id = fields.Char(string='ID del Especialista Activo', help="ID del workflow de n8n o identificador del especialista.")
    last_interaction = fields.Datetime(string='Última Interacción', default=fields.Datetime.now)
    context_data = fields.Text(string='Contexto Adicional (JSON)', help="Para guardar variables temporales de la sesión.")

    _sql_constraints = [
        ('channel_unique', 'unique(channel_id)', 'Ya existe un estado para este canal.'),
    ]

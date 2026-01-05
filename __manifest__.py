{
    'name': 'Elantar n8n Bridge',
    'version': '18.0.1.1.3',
    'category': 'Sales/Automation',
    'summary': 'Bridge between Odoo Live Chat and n8n AI specialists',
    'description': """
        Orchestration between Odoo Community 18 and n8n.
        Captures Live Chat messages and routes them to AI agents via webhooks.
    """,
    'author': 'Elantar Ltd.',
    'depends': ['base', 'mail', 'im_livechat', 'base_automation', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'data/n8n_bot_user.xml',
        'data/automation_rules.xml',
        'data/config_parameters.xml',
        'views/livechat_channel_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

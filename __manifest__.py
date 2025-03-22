{
    'name': "brain_api_rest",
    'version': '1.0',
    'depends': ['base', 'contacts', 'sale'],
    'author': "Reynaldo Villarreal",
    'category': 'Tools',
    'description': """
    Módulo que habilita la consulta vía API REST
    """,
    # data files always loaded at installation
    'data': [
        'data/model_definition.xml',
        'views/crm_lead_views.xml',
        'views/adoption_type_views.xml',
        'security/ir.model.access.csv',
        'views/brain_tipo_cliente_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
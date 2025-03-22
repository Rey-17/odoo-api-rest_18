from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Datos del Cliente
    address = fields.Char(string="Dirección")
    industry = fields.Many2one('res.partner.industry', string="Industria")

    # Asignación y Tipo de Adopción
    adoption_type_id = fields.Many2one('brain.adoption.type', string="Tipo de Registro", required=True)

    # Tipo de adopción: Portabilidades prepagos
    numero_a_portar = fields.Char(string="Número a portar")
    sim_card = fields.Char(strin="Sim Card")

    # Tipo de adopción: Línea nueva prepago recarga 5.00
    numero_de_la_linea_nueva = fields.Char(string="Número de la línea nueva")

    #Tipo de adopción: Autogestión de Móvil y Fijo
    brain_cuenta = fields.Char(string="Cuenta")
    brain_orden = fields.Char(string="Orden")
    brain_mrc = fields.Char(string="MRC")
    tipo_cliente_id = fields.Many2one(
        'brain.tipo.cliente',
        string='Tipo de Cliente'
    )
    # brain_tipo_cliente = fields.Selection([
    #     ('masivo_fijo', 'Masivo Fijo'),
    #     ('masivo_movil', 'Masivo Movil'),
    #     ('soho_fijo', 'Soho Fijo'),
    # ])

    tipo_activacion_id = fields.Many2one(
        'brain.tipo.activacion',
        string='Tipo de Activación'
    )
    # brain_activacion = fields.Selection([
    #     ('internet', 'Internet')
    # ])

    # Documentos de Adopción
    adoption_form = fields.Binary(string="Formulario de Adopción")
    adoption_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], string="Estado de Adopción", default='pending')

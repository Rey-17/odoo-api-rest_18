from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Datos del Cliente
    address = fields.Char(string="Dirección")
    industry = fields.Many2one('res.partner.industry', string="Industria")
    brain_coordinador = fields.Many2one(
        'res.users',
        string="Coordinador",
        domain=lambda self: [('groups_id', 'in', self.env.ref('sales_team.group_sale_manager').ids)]
    )

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

    tipo_activacion_id = fields.Many2one(
        'brain.tipo.activacion',
        string='Tipo de Activación'
    )

    brain_province = fields.Char(string="Provincia")
    brain_backoffice = fields.Many2one( 'res.users',
        string="Backoffice",
        domain=lambda self: [('groups_id', 'in', self.env.ref('sales_team.group_sale_manager').ids)])

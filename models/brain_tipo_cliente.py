from odoo import models, fields

class BrainTipoCliente(models.Model):
    _name = 'brain.tipo.cliente'
    _description = 'Tipo de Cliente'

    name = fields.Char(string='Nombre del Tipo de Cliente', required=True)
    active = fields.Boolean(default=True)

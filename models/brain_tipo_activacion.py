from odoo import models, fields

class BrainTipoActivacion(models.Model):
    _name = 'brain.tipo.activacion'
    _description = 'Tipo de Activación'

    name = fields.Char(string='Nombre del Tipo de Activación', required=True)
    active = fields.Boolean(string='Activo', default=True)

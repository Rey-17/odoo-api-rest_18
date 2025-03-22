from odoo import models, fields

class BrainAdoptionType(models.Model):
    _name = 'brain.adoption.type'
    _description = 'Tipo de Registro'

    name = fields.Char(string="Nombre", required=True)
    active = fields.Boolean(default=True)

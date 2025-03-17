from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Datos del Cliente
    client_id = fields.Many2one('res.partner', string="Cliente", required=True)
    contact_phone = fields.Char(string="Teléfono")
    contact_mobile = fields.Char(string="Celular")
    contact_email = fields.Char(string="Correo Electrónico")
    address = fields.Char(string="Dirección")
    industry = fields.Many2one('res.partner.industry', string="Industria")
    observations = fields.Text(string="Observaciones")

    # Asignación y Tipo de Adopción
    coordinator_id = fields.Many2one('res.users', string="Gerente o Coordinador")
    adoption_type = fields.Selection([
        ('activo_fijo', 'Activo Fijo'),
        ('rapido', 'Rápido'),
        ('semi_fijo', 'Semi Fijo'),
    ], string="Tipo de Adopción", required=True)

    # Estado y Portabilidad
    proposal_portability = fields.Char(string="Propuesta o Portabilidad")

    # Documentos de Adopción
    adoption_form = fields.Binary(string="Formulario de Adopción")
    adoption_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], string="Estado de Adopción", default='pending')

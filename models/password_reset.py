from datetime import datetime, timedelta
from odoo import models, fields, api
import secrets

class PasswordReset(models.Model):
    _name = 'password.reset'
    _description = 'Token de restablecimiento de contraseña'

    user_id = fields.Many2one('res.users', string='Usuario')
    reset_token = fields.Char(string='Token de Restablecimiento')
    expiration = fields.Datetime(string='Fecha de Expiración', default=lambda self: datetime.now() + timedelta(hours=1))
    used = fields.Boolean(string='Usado', default=False)

    @api.model
    def create_reset_token(self, user_id):
        """Crea un token de restablecimiento para el usuario."""
        # Generar un token seguro
        token = secrets.token_urlsafe(32)
        # Crear el registro del token de restablecimiento
        reset_record = self.create({
            'user_id': user_id.id,
            'reset_token': token,
        })
        return reset_record

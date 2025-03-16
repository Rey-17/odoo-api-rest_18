from odoo import models, fields, api
from datetime import datetime, timedelta
import secrets

class AuthToken(models.Model):
    _name= 'auth.token'
    _description='Token de autenticaciòn'

    user_id = fields.Many2one('res.users', required=True)
    access_token = fields.Char(string='Access Token', required=True)
    refresh_token = fields.Char(string='Refresh Token', required=True)
    access_token_expiration = fields.Datetime(string='Expiración del Access Token', required=True)
    refresh_token_expiration = fields.Datetime(string='Expiración del Refresh Token', required=True)

    @api.model
    def create_token(self, user_id):
        """Crea y retorna un nuevo access y refresh token para el usuario."""
        # Generar access token y su fecha de expiración
        access_token = secrets.token_urlsafe(64)
        access_expiration = datetime.now() + timedelta(minutes=30)

        # Generar refresh token y su fecha de expiración
        refresh_token = secrets.token_urlsafe(64)
        refresh_expiration = datetime.now() + timedelta(days=7)

        # Crear registro en el modelo
        token = self.create({
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'access_token_expiration': access_expiration,
            'refresh_token_expiration': refresh_expiration,
        })

        return {
            'access_token': token.access_token,
            'access_expiration': token.access_token_expiration,
            'refresh_token': token.refresh_token,
            'refresh_expiration': token.refresh_token_expiration,
        }

    @api.model
    def refresh_access_token(self, refresh_token):
        """Genera un nuevo access token utilizando el refresh token."""
        # Buscar el registro del refresh token con permisos elevados
        token = self.sudo().search([('refresh_token', '=', refresh_token)], limit=1)

        if not token:
            return {'error': 'Refresh token inválido.'}

        # Validar si el refresh token ha expirado
        if token.refresh_token_expiration < datetime.now():
            return {'error': 'Refresh token expirado.'}

        # Generar un nuevo access token
        token.sudo().write({
            'access_token': secrets.token_urlsafe(64),
            'access_token_expiration': datetime.now() + timedelta(minutes=30)
        })

        return {
            'access_token': token.access_token,
            'access_expiration': token.access_token_expiration,
            'refresh_expiration': token.refresh_token_expiration
        }

from odoo import models, fields, api
from odoo.exceptions import AccessDenied
from pprint import pformat
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit='res.users'

    @api.model
    def api_authenticate(self, db, login, password, user_agent_env=None):
        """Autenticar usuario y generar access y refresh tokens."""
        user_id = super(ResUsers, self).authenticate(db, login, password, user_agent_env)
        #user_id = super().authenticate(db, login, password, user_agent_env)
        str_data = pformat(user_id)
        _logger.info("Desde res_users user_id:" + str_data)
        if not user_id:
            raise AccessDenied("Credenciales inválidas.")
        user = self.env['res.users'].sudo().browse(user_id)
        # Crear tokens para el usuario autenticado
        auth_token_model = self.env['auth.token']
        tokens = auth_token_model.sudo().create_token(user_id)

        return {
            'user_id': user_id,
            'access_token': tokens['access_token'],
            'access_expiration': tokens['access_expiration'],
            'refresh_token': tokens['refresh_token'],
            'refresh_expiration': tokens['refresh_expiration'],
            'data': {
                'name': user.name,
                'email': user.email or None# Asegurar que existe el correo o proporcionar un valor por defecto
            }
        }
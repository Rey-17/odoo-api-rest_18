from odoo import http, exceptions, fields
from odoo.http import request, Response
from odoo.exceptions import AccessDenied
from pprint import pformat
import time

import logging
import json

_logger = logging.getLogger(__name__)

class AuthController(http.Controller):

    def _verify_token(self):
        """Función para verificar la autenticidad del token."""
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False, self._brain_response({'error': 'Token de autenticación no proporcionado o mal formado.'}, 401)

        token = auth_header.split(" ")[1]
        # Verificar si el token existe y es válido
        auth_token_model = request.env['auth.token'].sudo()
        token_record = auth_token_model.search([('access_token', '=', token)], limit=1)

        if not token_record or token_record.access_token_expiration < fields.Datetime.now():
            return False, self._brain_response({'error': 'Token inválido o expirado.'}, 401)
        _logger.info('USER ID: ' + str(token_record.user_id))
        return True, token_record.user_id

    @http.route('/api/login', type='http', auth='none', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        """Endpoint de login para la API usando json.loads."""
        # Leer el cuerpo crudo de la solicitud y cargarlo como JSON
        try:
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return self._brain_response({'error': 'El cuerpo de la solicitud debe estar en formato JSON válido.'}, 400)
        # Extraer los valores de 'login' y 'password' del JSON enviado
        login = data.get('login')
        password = data.get('password')

        # Validar que ambos campos están presentes
        if not login or not password:
            return self._brain_response({'error': 'Debe proporcionar un usuario y contraseña.'}, 400)
        # Obtener la base de datos actual
        db = request.env.cr.dbname
        # Intentar autenticar al usuario en la base de datos actual
        try:
            result = request.env['res.users'].api_authenticate(db, login, password, {})
            data_str = pformat(result)
            _logger.info("Contenido del diccionario: %s", data_str)

            access_expiration_timestamp = int(result['access_expiration'].timestamp())
            refresh_expiration_timestamp = int(result['refresh_expiration'].timestamp())

            return self._brain_response({
                'user_id': result['user_id'],
                'access_token': result['access_token'],
                'access_expiration': access_expiration_timestamp,
                'refresh_token': result['refresh_token'],
                'refresh_expiration': refresh_expiration_timestamp,
                'data': result['data']
            }, 200)
        except AccessDenied:
            return self._brain_response({'error': 'Credenciales inválidas.'}, 401)

    @http.route('/api/refresh_token', type='http', auth='none', method=['POST'], csrf=False)
    def refresh_token(self, **kwargs):
        """Endpoint para refrescar el access token utilizando el refresh token."""
        try:
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return request.make_response(
                json.dumps({'error': 'El cuerpo de la solicitud debe estar en formato JSON válido.'}),
                headers={'Content-Type': 'application/json'})

        refresh_token = data.get('refresh_token')
        if not refresh_token:
            return request.make_response(json.dumps({'error': 'Debe proporcionar un refresh token.'}),
                                         headers={'Content-Type': 'application/json'}, status=400)

        auth_token_model = http.request.env['auth.token'].sudo()
        new_token_data = auth_token_model.refresh_access_token(refresh_token)

        if 'error' in new_token_data:
            return request.make_response(json.dumps({'error': new_token_data['error']}),
                                         headers={'Content-Type': 'application/json'}, status=400)

        access_expiration_timestamp = int(new_token_data['access_expiration'].timestamp())
        refresh_expiration_timestamp = int(new_token_data['refresh_expiration'].timestamp())

        # Convertir las fechas a cadenas para el formato JSON
        return request.make_response(json.dumps({
            'access_token': new_token_data['access_token'],
            'access_expiration': access_expiration_timestamp,
            'refresh_token': refresh_token,
            'refresh_expiration': refresh_expiration_timestamp
        }), headers={'Content-Type': 'application/json'})

    @http.route('/api/forgot_password', type='http', auth='none', methods=['POST'], csrf=False)
    def forgot_password(self, **kwargs):
        """API para restablecer la contraseña utilizando la funcionalidad nativa de Odoo"""
        try:
            # Leer el cuerpo crudo de la solicitud y cargarlo como JSON
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return request.make_response(
                json.dumps({'error': 'El cuerpo de la solicitud debe estar en formato JSON válido.'}),
                headers={'Content-Type': 'application/json'}, status=400
            )

        # Obtener el email del cuerpo de la solicitud
        email = data.get('email')
        if not email:
            return self._brain_response({'error': 'Debe proporcionar un correo electrónico válido.'}, 400)

        # Buscar el usuario por correo electrónico
        user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
        if not user:
            return self._brain_response({'error': 'El correo electrónico no está registrado.'}, 400)

        # Llamar al metodo nativo de Odoo para restablecer la contraseña
        try:
            user.sudo().action_reset_password()
        except Exception as e:
            return self._brain_response({'error': f'Error al generar el restablecimiento de contraseña: {str(e)}'}, 500)

        return self._brain_response({'success': 'Correo de restablecimiento enviado con éxito.'}, 200)

    # Devolver respuestas HTTP
    def _brain_response(self, data, status=200):
        """Generar una respuesta HTTP con JSON."""
        return request.make_response(json.dumps(data), headers={'Content-Type': 'application/json'}, status=status)

    def _check_access(self, model, operation='read'):
        """Configurar el entorno con el usuario del token y verificar permisos."""
        is_valid, user = self._verify_token()
        if not is_valid:
            return False, user  # Devuelve directamente la respuesta HTTP de error

        if not user:
            return False, self._brain_response({'error': 'Usuario no encontrado o token inválido.'}, 403)

        # Configurar el entorno con el usuario obtenido del token
        env = request.env(context=dict(request.env.context, uid=user.id), user=user)

        _logger.info('Checking access rights for user ID: {}'.format(user.id))
        _logger.info('Environment setup with user ID: {}'.format(env.uid))

        try:
            env[model].check_access_rights(operation)
            env[model].check_access_rule(operation)
        except AccessDenied as e:
            _logger.error('Access Denied: %s', str(e))
            return False, self._brain_response({'error': 'Acceso denegado.'}, 403)
        except Exception as e:
            _logger.error('Error checking access rights: %s', str(e))
            return False, self._brain_response({'error': 'Error al verificar los derechos de acceso: ' + str(e)}, 403)

        return True, env  # Devolver True y el entorno configurado si todo es correcto
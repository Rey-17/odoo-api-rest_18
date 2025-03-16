from odoo import http, fields
from odoo.http import request
from .auth_contoller import AuthController
from werkzeug.wrappers import Response
import json
import math
import base64
from io import BytesIO

class PartnerController(AuthController):

    @http.route('/api/partners', type='http', auth="none", methods=['GET'], csrf=False)
    def get_partners(self, **kwargs):
        """API para obtener la lista de socios (res.partner) con paginación y validación de token."""
        check, result = self._check_access('res.partner')
        if not check:
            return result  # Si es una respuesta, contiene el error

        env = result
        # Parámetros de paginación
        page = int(kwargs.get('page', 1))  # Página actual, por defecto 1
        per_page = int(kwargs.get('per_page', 10))  # Elementos por página, por defecto 10

        # Obtener el modelo de socios
        Partner = env['res.partner']
        total_items = Partner.search_count([])  # Total de socios
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1  # Paginación

        if page < 1 or page > total_pages:
            return self._brain_response({'error': 'Página fuera de rango.'}, 400)

        # Obtener los socios en la página solicitada
        partners = Partner.search([], offset=(page - 1) * per_page, limit=per_page)

        # Construir la lista de socios con la información extendida
        partner_list = []
        for partner in partners:
            category_info = [{
                'category_id': category.id,
                'category_name': category.name
            } for category in partner.category_id]

            #image_url = f"/web/image/res.partner/{partner.id}/image_1920" if partner.image_1920 else None
            image_url = f"/partner/image/{partner.id}" if partner.image_1920 else None
            partner_data = {
                'id': partner.id,
                'name': partner.name or None,
                'email': partner.email or None,
                'phone': partner.phone or None,
                'mobile': partner.mobile or None,
                'website': partner.website or None,
                'city': partner.city or None,
                'zip': partner.zip or None,
                'country_id': partner.country_id.id if partner.country_id else None,
                'country_name': partner.country_id.name if partner.country_id else None,
                'street': partner.street or None,
                'street2': partner.street2 or None,
                'state_id': partner.state_id.id if partner.state_id else None,
                'state_name': partner.state_id.name if partner.state_id else None,
                'customer_rank': partner.customer_rank or None,
                'supplier_rank': partner.supplier_rank or None,
                'type': partner.type or None,  # Puede ser 'contact', 'invoice', 'delivery', etc.
                'created_by': partner.create_uid.id if partner.create_uid else None,  # Usuario que creó el partner
                'created_by_name': partner.create_uid.name if partner.create_uid else None,
                'salesperson_id': partner.user_id.id if partner.user_id else None,  # Comercial asignado
                'salesperson_name': partner.user_id.name if partner.user_id else None,  # Nombre del comercial asignado
                'image_url': image_url,  # URL de la imagen del partner
                'categories': category_info
            }
            partner_list.append(partner_data)

        # Construir la respuesta final con metadatos de paginación
        response_data = {
            'status': 'success',
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'items': partner_list
        }

        return self._brain_response(response_data, 200)

    @http.route('/partner/image/<int:partner_id>', auth="public", type='http', methods=['GET'])
    def get_partner_image(self, partner_id, **kwargs):
        # Verificar el token primero
        # check, result = self._check_access('product.template')
        # if not check:
        #     return result
        # env = result

        # Buscar el producto por ID
        partner = request.env['res.partner'].sudo().browse(partner_id)
        if not partner.exists():
            return self._brain_response({"error": "Partner not found"}, 404)

        if not partner.image_1920:
            return self._brain_response({"error": "No image found"}, 404)

        image_data = base64.b64decode(partner.image_1920)
        #return http.send_file(BytesIO(image_data), mimetype='image/png')
        return Response(BytesIO(image_data), mimetype='image/png', direct_passthrough=True)

    @http.route('/api/partners', type='http', auth="none", methods=['POST'], csrf=False)
    def create_partner(self, **kwargs):
        """API para crear un socio (res.partner) asegurando que el usuario tiene permisos adecuados."""
        check, result = self._check_access('res.partner', 'create')
        if not check:
            return result  # Si es una respuesta, contiene el error

        env = result  # El entorno con los permisos del usuario validado

        try:
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return self._brain_response({'error': 'El cuerpo de la solicitud debe estar en formato JSON válido.'}, 400)

        # Verificar que el campo necesario 'name' está presente
        if 'name' not in data:
            return self._brain_response({'error': 'El campo "name" es obligatorio.'}, 400)

        # Crear el socio
        try:
            partner = env['res.partner'].create({
                'name': data['name'],
                'email': data.get('email'),  # Opcional
                'phone': data.get('phone'),  # Opcional
                'city': data.get('city')  # Opcional
            })
        except Exception as e:
            env.cr.rollback()  # Asegurarse de no afectar otras transacciones
            return self._brain_response({'error': str(e)}, 500)

        # Devolver información del socio creado
        return self._brain_response({
            'id': partner.id
        }, 201)

    @http.route('/api/partners/<int:partner_id>', type='http', auth="none", methods=['POST'], csrf=False)
    def update_partner(self, partner_id, **kwargs):

        check, result = self._check_access('res.partner', 'write')
        if not check:
            return result  # Si es una respuesta, contiene el error

        env = result  # El entorno con los permisos del usuario validado

        try:
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return self._brain_response({'error': 'El cuerpo de la solicitud debe estar en formato JSON válido.'}, 400)

        # Obtener el socio existente
        partner = env['res.partner'].browse(partner_id)
        if not partner.exists():
            return self._brain_response({'error': 'Datos no encontrados.'}, 404)

        # Datos para actualizar, se asume que cada campo es opcional
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'email' in data:
            update_data['email'] = data['email']
        if 'phone' in data:
            update_data['phone'] = data['phone']
        if 'city' in data:
            update_data['city'] = data['city']
        if 'street' in data:
            update_data['street'] = data['street']
        if 'zip' in data:
            update_data['zip'] = data['zip']

        # Actualizar el socio
        try:
            partner.write(update_data)
        except Exception as e:
            env.cr.rollback()  # Asegurarse de no afectar otras transacciones
            return self._brain_response({'error': str(e)}, 500)

        # Devolver información del socio actualizado
        return self._brain_response({'id': partner.id}, 200)

    @http.route('/api/partners/<int:partner_id>', type='http', auth="none", methods=['DELETE'], csrf=False)
    def delete_partner(self, partner_id, **kwargs):
        check, result = self._check_access('res.partner', 'unlink')
        if not check:
            return result  # Si es una respuesta, contiene el error

        env = result  # El entorno con los permisos del usuario validado

        # Obtener el partner
        partner = env['res.partner'].browse(partner_id)
        if not partner.exists():
            return self._brain_response({'error': 'Datos no encontrados.'}, 404)

        # Intentar eliminar el partner
        try:
            partner.unlink()
        except Exception as e:
            env.cr.rollback()  # Asegurarse de no afectar otras transacciones
            return self._brain_response({'error': str(e)}, 500)

        # Devolver confirmación de la eliminación
        return self._brain_response({'message': 'Dato eliminado correctamente.'}, 200)

    @http.route('/api/partners/<int:partner_id>', type='http', auth="none", methods=['GET'], csrf=False)
    def get_partner(self, partner_id, **kwargs):
        check, result = self._check_access('res.partner', 'read')
        if not check:
            return result  # Si es una respuesta, contiene el error
        env = result
        # Obtener el partner
        partner = env['res.partner'].browse(partner_id)
        if not partner.exists():
            return self._brain_response({'error': 'Datos no encontrados.'}, 404)

        # Preparar los datos para la respuesta
        partner_data = {
            'id': partner.id,
            'name': partner.name or None,
            'email': partner.email or None,
            'phone': partner.phone or None,
            'city': partner.city or None,
            'zip': partner.zip or None,
            'country': {
                'id': partner.country_id.id if partner.country_id else None,
                'name': partner.country_id.name if partner.country_id else None,
            },
            'state': {
                'id': partner.state_id.id if partner.state_id else None,
                'name': partner.state_id.name if partner.state_id else None,
            },
            'street': partner.street or None,
            'street2': partner.street2 or None,
            'website': partner.website or None,
            'is_company': partner.is_company or None,
            'industry_id': {
                'id': partner.industry_id.id if partner.industry_id else None,
                'name': partner.industry_id.name if partner.industry_id else None,
            },
            'image_url': f"/web/image/res.partner/{partner.id}/image_1920" if partner.image_1920 else None
        }

        # Devolver la información del partner
        return self._brain_response(partner_data, 200)

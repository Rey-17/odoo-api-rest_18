from .auth_contoller import AuthController
from odoo import http, fields
from odoo.http import request
import json

class ProductTemplateController(AuthController):

    @http.route('/api/product_templates', type='http', auth="none", methods=['GET'], csrf=False)
    def get_product_templates(self, **kwargs):
        """API para obtener una lista de plantillas de productos (product.template) con verificación de token."""

        # Verificar el token antes de proceder
        is_valid, result = self._verify_token()
        if not is_valid:
            return result  # Retorna la respuesta de error si el token es inválido

        user = result

        # Parámetros de paginación
        page = int(kwargs.get('page', 1))
        per_page = int(kwargs.get('per_page', 10))

        # Obtener el modelo de producto
        ProductTemplate = request.env['product.template'].sudo()
        total_items = ProductTemplate.search_count([])
        total_pages = (total_items + per_page - 1) // per_page  # Redondeo hacia arriba

        # Validar que la página solicitada esté dentro del rango
        if page > total_pages:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Página fuera de rango.'}),
                headers=[('Content-Type', 'application/json')], status=400
            )

        # Obtener las plantillas de productos para la página actual
        products = ProductTemplate.search([], offset=(page - 1) * per_page, limit=per_page)

        # Construir la lista de productos
        product_list = []
        for product in products:
            variants = [{'id': variant.id, 'name': variant.name} for variant in product.product_variant_ids]
            stock_quantity = sum(product.product_variant_ids.mapped('qty_available'))
            product_data = {
                'id': product.id,
                'name': product.name or None,
                'list_price': product.list_price,
                'cost_price': product.standard_price,
                'qty_available': stock_quantity,
                'description': product.description_sale or None,
                'type': product.type or None,
                'categ_id': {
                    'id': product.categ_id.id if product.categ_id else None,
                    'name': product.categ_id.name if product.categ_id else None
                },
                'uom_id': {
                    'id': product.uom_id.id if product.uom_id else None,
                    'name': product.uom_id.name if product.uom_id else None
                },
                'barcode': product.barcode or None,
                'default_code': product.default_code or None,  # SKU
                'active': product.active,
                'image_url': "/web/image/product.template/{}/image_1920".format(
                    product.id) if product.image_1920 else None,
                'priority': product.priority,
                'variants': variants
            }
            product_list.append(product_data)

        # Retornar los datos paginados como HTTP response con JSON
        return request.make_response(
            json.dumps({
                'total_items': total_items,
                'total_pages': total_pages,
                'current_page': page,
                'products': product_list
            }),
            headers=[('Content-Type', 'application/json')]
        )

import base64
from io import BytesIO

from odoo import http, fields
from odoo.http import request
from .auth_contoller import AuthController
import json
import math
import logging

_logger = logging.getLogger(__name__)

class ProductController(AuthController):

    # Obtener productos del modelo product.template con las variantes
    @http.route('/api/products_with_variants', type='http', auth="none", methods=['GET'], csrf=False)
    def get_products_with_variants(self, **kwargs):
        check, result = self._check_access('product.template')
        if not check:
            return result  # Retorna el error si el token es inválido
        env = result
        # Parámetros de paginación
        page = int(kwargs.get('page', 1))
        per_page = int(kwargs.get('per_page', 10))

        # Inicializar el dominio para los filtros
        domain = [('active', '=', True)]
        if 'name' in kwargs:
            domain.append(('name', 'ilike', kwargs['name']))
        if 'category' in kwargs:
            domain.append(('categ_id.name', '=', kwargs['category']))
        if 'price_min' in kwargs:
            domain.append(('list_price', '>=', float(kwargs['price_min'])))
        if 'price_max' in kwargs:
            domain.append(('list_price', '<=', float(kwargs['price_max'])))

        # Obtener productos desde el modelo product.template con los filtros
        product_template = env['product.template']
        total_items = product_template.search_count(domain)
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

        if page < 1 or page > total_pages:
            return self._brain_response({'error': 'Página fuera de rango.'}, 400)

        # Obtener los productos filtrados en la página solicitada
        products = product_template.search(domain, offset=(page - 1) * per_page, limit=per_page)

        # Construir la lista de productos
        product_list = []
        for product in products:
            # Diccionario para agrupar variantes por id
            variants_dict = {}
            for variant in product.product_variant_ids:
                for value in variant.product_template_variant_value_ids:
                    # Si el id del atributo ya existe en el diccionario, agrega a los atributos existentes
                    if value.attribute_id.id not in variants_dict:
                        variants_dict[value.attribute_id.id] = {
                            'id': value.attribute_id.id,
                            'name': value.attribute_id.name,
                            'type': value.attribute_id.display_type,
                            'attributes': []
                        }
                    # Crear un diccionario temporal para almacenar los valores únicos de los atributos
                    existing_values = {attr['value'] for attr in variants_dict[value.attribute_id.id]['attributes']}
                    exclude_values = []
                    for exclude in value.exclude_for:
                        # Solo se agrega si el producto excluido es el mismo que se esta recorriendo.
                        if exclude.product_tmpl_id.id == product.id:
                            if hasattr(value, 'exclude_for') and value.exclude_for:
                                for exForProduct in exclude.value_ids:
                                    exclude_values.append({
                                        'id': exForProduct.id,
                                        'attribute': exForProduct.name,
                                        'value': exForProduct.attribute_id.name,
                                        'hex': exForProduct.html_color or None,
                                        'type': exForProduct.attribute_id.display_type
                                    })

                    if value.name not in existing_values:
                        attribute_detail = {
                                'id': value.id,
                                'value': value.name,
                                'price': value.price_extra,
                                'hex': value.html_color or None,
                                'image': value.image or None,
                                'exclude': exclude_values
                            }
                        variants_dict[value.attribute_id.id]['attributes'].append(attribute_detail)
            variants = list(variants_dict.values())
            product_data = {
                'id': product.id,
                'name': product.name or None,
                'default_code': product.default_code or None,
                'price': product.list_price,
                'quantity_on_hand': product.qty_available,
                'product_type': product.type or None,
                'category': {
                    'id': product.categ_id.id if product.categ_id else None,
                    'name': product.categ_id.name if product.categ_id else None
                },
                'uom': {
                    'id': product.uom_id.id if product.uom_id else None,
                    'name': product.uom_id.name if product.uom_id else None
                },
                'variants': variants,
                'description': product.description_sale or None,
                'image_url': f"/product/image/{product.id}" if product.image_1920 else None
            }
            product_list.append(product_data)

        response_data = {
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'items': product_list
        }
        return self._brain_response(response_data, 200)

    # product.template by ID
    @http.route('/api/products_template/<int:product_id>', type='http', auth="none", methods=['GET'], csrf=False)
    def get_product_template_by_id(self, product_id, **kwargs):
        check, result = self._check_access('product.template')
        if not check:
            return result  # Retorna el error si el token es inválido

        env = result
        product = env['product.template'].browse(product_id)

        if not product.exists():
            return self._brain_response({'error': 'Producto no encontrado'}, 404)

        variants = []
        for variant in product.product_variant_ids:
            attributes = [{
                'attribute_id': value.attribute_id.id,
                'attribute_name': value.attribute_id.name,
                'value_id': value.id or None,
                'value_name': value.name or None,
                'value_color_code': value.html_color or None,
                'exclude_for': [{
                    'product_template_id': exclude.product_tmpl_id.id,
                    'product_template_name': exclude.product_tmpl_id.name
                } for exclude in value.exclude_for] if value.exclude_for else []
            } for value in variant.product_template_variant_value_ids]

            variants.append({
                'id': variant.id,
                'internal_reference': variant.default_code or None,
                'name': variant.name,
                'sales_price': variant.list_price,
                'cost': variant.standard_price,
                'on_hand': variant.qty_available,
                'forecasted': variant.virtual_available,
                'attributes': attributes
            })

        product_data = {
            'id': product.id,
            'name': product.name or None,
            'default_code': product.default_code or None,
            'price': product.list_price,
            'quantity_on_hand': product.qty_available,
            'product_type': product.type or None,
            'category': {
                'id': product.categ_id.id if product.categ_id else None,
                'name': product.categ_id.name if product.categ_id else None
            },
            'uom': {
                'id': product.uom_id.id if product.uom_id else None,
                'name': product.uom_id.name if product.uom_id else None
            },
            'variants': variants,
            'description': product.description_sale or None,
            'image_url': f"/web/image/product.template/{product.id}/image_1920" if product.image_1920 else None
        }

        return self._brain_response({'product': product_data}, 200)

    @http.route('/product/image/<int:product_id>', auth="public", type='http', methods=['GET'])
    def get_product_image(self, product_id, **kwargs):
        # Verificar el token primero
        # check, result = self._check_access('product.template')
        # if not check:
        #     return result
        # env = result

        # Buscar el producto por ID
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return self._brain_response({"error":"Product not found"}, 404)

        if not product.image_1920:
            return self._brain_response({"error": "No image found"}, 404)

        image_data = base64.b64decode(product.image_1920)
        return http.send_file(BytesIO(image_data), mimetype='image/png')

    @http.route('/api/product_categories', type='http', auth="none", methods=['GET'], csrf=False)
    def get_product_categories(self, **kwargs):
        """Retorna la lista de categorías de productos con paginación."""

        # Verificar token
        is_valid, result = self._verify_token()
        if not is_valid:
            return result  # Retorna el error si el token es inválido

        # Parámetros de paginación
        page = int(kwargs.get('page', 1))  # Página actual, por defecto 1
        per_page = int(kwargs.get('per_page', 10))  # Elementos por página, por defecto 10

        # Obtener todas las categorías de productos
        ProductCategory = request.env['product.category'].sudo()
        total_items = ProductCategory.search_count([])  # Total de categorías
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1  # Total de páginas

        if page < 1 or page > total_pages:
            return request.make_response(
                json.dumps({'error': 'Página fuera de rango.'}),
                headers={'Content-Type': 'application/json'}, status=400
            )

        # Obtener las categorías en la página solicitada
        categories = ProductCategory.search([], offset=(page - 1) * per_page, limit=per_page)

        # Construir la lista de categorías
        category_list = []
        for category in categories:
            category_data = {
                'id': category.id,
                'name': category.name or None,
                'parent_id': category.parent_id.id if category.parent_id else None,
                'parent_name': category.parent_id.name if category.parent_id else None
            }
            category_list.append(category_data)

        # Estructura de la respuesta similar a la de los productos
        response_data = {
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'items': category_list
        }

        return request.make_response(
            json.dumps(response_data),
            headers={'Content-Type': 'application/json'}, status=200
        )

    @http.route('/api/warehouses', type='http', auth="none", methods=['GET'], csrf=False)
    def get_warehouses(self, **kwargs):
        """Retorna la lista de almacenes (stock.warehouse) con paginación."""

        # Verificar token
        is_valid, result = self._verify_token()
        if not is_valid:
            return result  # Retorna el error si el token es inválido

        # Parámetros de paginación
        page = int(kwargs.get('page', 1))
        per_page = int(kwargs.get('per_page', 10))

        # Obtener todos los almacenes
        Warehouse = request.env['stock.warehouse'].sudo()
        total_items = Warehouse.search_count([])
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

        if page < 1 or page > total_pages:
            return request.make_response(
                json.dumps({'error': 'Página fuera de rango.'}),
                headers={'Content-Type': 'application/json'}, status=400
            )

        # Obtener los almacenes en la página solicitada
        warehouses = Warehouse.search([], offset=(page - 1) * per_page, limit=per_page)

        # Construir la lista de almacenes
        warehouse_list = []
        for warehouse in warehouses:
            if warehouse.id:
                warehouse_data = {
                    'id': warehouse.id,
                    'name': warehouse.name or None,
                    'code': warehouse.code or None,
                    'location_id': warehouse.lot_stock_id.id if warehouse.lot_stock_id else None,
                    'location_name': warehouse.lot_stock_id.name if warehouse.lot_stock_id else None
                }
                warehouse_list.append(warehouse_data)

        response_data = {
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'items': warehouse_list
        }
        return self._brain_response(response_data, 200)

    @http.route('/api/product_attributes', type='http', auth="none", methods=['GET'], csrf=False)
    def get_attributes(self, **kwargs):
        """Retorna la lista de atributos (product.attribute) con paginación."""

        # Verificar token
        is_valid, result = self._verify_token()
        if not is_valid:
            return result  # Retorna el error si el token es inválido

        # Parámetros de paginación
        page = int(kwargs.get('page', 1))
        per_page = int(kwargs.get('per_page', 10))

        # Obtener todos los atributos
        ProductAttribute = request.env['product.attribute'].sudo()
        total_items = ProductAttribute.search_count([])
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

        if page < 1 or page > total_pages:
            return request.make_response(
                json.dumps({'error': 'Página fuera de rango.'}),
                headers={'Content-Type': 'application/json'}, status=400
            )

        # Obtener los atributos en la página solicitada
        attributes = ProductAttribute.search([], offset=(page - 1) * per_page, limit=per_page)

        # Construir la lista de atributos
        attribute_list = []
        for attribute in attributes:
            # Detección de atributo de tipo Color
            if attribute.display_type == 'color':  # Suponiendo que 'display_type' puede indicar si es de tipo color
                color_value = [{'id': value.id, 'name': value.name, 'color_code': value.html_color} for value in
                               attribute.value_ids]
            else:
                color_value = [{'id': value.id, 'name': value.name} for value in attribute.value_ids]

            attribute_data = {
                'id': attribute.id,
                'name': attribute.name if attribute.name else None,  # Retorna None si name es Falsy
                'value_ids': color_value
            }
            attribute_list.append(attribute_data)

        response_data = {
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'items': attribute_list
        }
        return self._brain_response(response_data, 200)

    @http.route('/api/products/filters', type='http', auth="none", methods=['GET'], csrf=False)
    def get_available_filters(self, **kwargs):
        check, result = self._check_access('product.template')
        if not check:
            return result
        # Simplemente devolvemos una estructura estática o podemos hacerla más dinámica según la configuración del sistema
        filters = {
            'name': 'Filtra por nombre del producto utilizando operaciones como "ilike" para coincidencia parcial.',
            'category': 'Filtra por el nombre exacto de la categoría del producto.'
        }
        return self._brain_response({"items": filters}, 200)

    # Endpoint que devuelve las variantes de productos.
    @http.route('/api/products', type='http', auth="none", methods=['GET'], csrf=False)
    def get_products(self, **kwargs):
        check, result = self._check_access('product.product')
        if not check:
            return result  # Retorna el error si el token es inválido

        env = result
        try:
            # Parámetros de paginación y filtros
            page = int(kwargs.get('page', 1))
            per_page = int(kwargs.get('per_page', 10))
            domain = [('active', '=', True)]

            # Filtros de búsqueda
            if 'name' in kwargs:
                domain.append(('name', 'ilike', kwargs['name']))
            if 'category' in kwargs:
                domain.append(('categ_id.name', '=', kwargs['category']))

            # Búsqueda de productos con los filtros aplicados
            products = env['product.product'].search(domain, limit=per_page, offset=(page - 1) * per_page)
            total_items = env['product.product'].search_count(domain)
            total_pages = math.ceil(total_items / per_page)

            # Recopilación de detalles de productos
            items = []
            for product in products:
                categories = []
                current_category = product.categ_id
                while current_category:
                    category_details = {
                        'id': current_category.id,
                        'name': current_category.name
                    }
                    categories.append(category_details)
                    current_category = current_category.parent_id

                attributes = []
                for variant in product.product_template_variant_value_ids:
                    attribute_detail = {
                        'name': variant.attribute_id.name,
                        'value': variant.name,
                        'price_extra': variant.price_extra,
                        'html_color': variant.html_color or None,
                    }
                    attributes.append(attribute_detail)

                product_data = {
                    'id': product.id,
                    'internal_reference': product.default_code or None,
                    'name': product.name,
                    'sale_price': product.lst_price,
                    'taxes': [
                        {'id': tax.id, 'name': tax.name, 'amount': tax.amount, 'display_name': tax.display_name}
                    for tax in product.taxes_id ],
                    'standard_price': product.standard_price,
                    'on_hand': product.qty_available,
                    'virtual_available': product.virtual_available,
                    'type': product.type,
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'priority': product.priority,
                    'categories': categories[::-1],
                    'attributes': attributes,
                    'image_url': f"/product/image/{product.product_tmpl_id.id}" if product.image_1920 else None
                }
                items.append(product_data)

            # Devolver la respuesta en formato JSON
            response_data = {
                'total_items': total_items,
                'total_pages': total_pages,
                'current_page': page,
                'items': items
            }
            return self._brain_response(response_data)

        except Exception as e:
            return self._brain_response({'error': 'Error interno del servidor: ' + str(e)}, 500)

    @http.route('/api/products/<int:product_id>', type='http', auth="none", methods=['GET'], csrf=False)
    def get_product_by_id(self, product_id):
        check, result = self._check_access('product.product')
        if not check:
            return result  # Retorna el error si el token es inválido

        env = result
        try:
            product = env['product.product'].browse(product_id)
            if not product.exists():
                return self._brain_response({'error': 'Producto no encontrado'}, 404)

            categories = []
            current_category = product.categ_id
            while current_category:
                category_details = {
                    'id': current_category.id,
                    'name': current_category.name
                }
                categories.append(category_details)
                current_category = current_category.parent_id

            attributes = []
            for variant in product.product_template_variant_value_ids:
                attribute_detail = {
                    'name': variant.attribute_id.name,
                    'value': variant.name,
                    'price_extra': variant.price_extra,
                    'html_color': variant.html_color or None,
                }
                attributes.append(attribute_detail)

            product_data = {
                'id': product.id,
                'default_code': product.default_code or None,
                'name': product.name,
                'price': product.lst_price,
                'standard_price': product.standard_price,
                'quantity_on_hand': product.qty_available,
                'virtual_available': product.virtual_available,
                'type': product.type,
                'product_tmpl_id': product.product_tmpl_id.id,
                'priority': product.priority,
                'categories': categories[::-1],
                'attributes': attributes,
                'image_url': f"/product/image/{product.product_tmpl_id.id}" if product.image_1920 else None
            }

            return self._brain_response(product_data)

        except Exception as e:
            return self._brain_response({'error': 'Error interno del servidor: ' + str(e)}, 500)
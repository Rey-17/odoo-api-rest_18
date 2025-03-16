from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError
from .auth_contoller import AuthController
from datetime import datetime, timedelta
import json
import math
import logging

_logger = logging.getLogger(__name__)

class SaleOrderController(AuthController):

    @http.route('/api/sale_orders', type='http', auth='none', methods=['GET'], csrf=False)
    def get_sale_orders(self, **kwargs):
        """API para obtener las órdenes de venta junto con sus productos, con paginación, filtros y validación de token."""
        has_access, env = self._check_access('sale.order')
        if not has_access:
            return env  # Env ya es una respuesta HTTP de error
        page = int(kwargs.get('page', 1))
        per_page = int(kwargs.get('per_page', 10))
        domain = []
        if 'customer_name' in kwargs:
            domain.append(('partner_id.name', 'ilike', kwargs['customer_name']))
        if 'state' in kwargs:
            domain.append(('state', '=', kwargs['state']))
        if 'date_order' in kwargs:
            domain.append(('date_order', '>=', kwargs['date_order']))
        if 'name' in kwargs:
            domain.append(('name', 'ilike', kwargs['name']))

        # Restringir a órdenes del usuario actual si no es administrador
        if not env.user.has_group('base.group_system'):
            domain.append(('user_id', '=', env.user.id))

        sale_order_model = env['sale.order']
        total_items = sale_order_model.search_count(domain)
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
        if page < 1 or page > total_pages:
            return request.make_response(json.dumps({'error': 'Página fuera de rango.'}),
                                         headers={'Content-Type': 'application/json'}, status=400)
        sale_orders = sale_order_model.search(domain, limit=per_page, offset=(page - 1) * per_page)
        sale_orders_data = []
        for order in sale_orders:
            products_data = []
            for line in order.order_line:
                product_data = {
                    'order_line_id': line.id,
                    'product_id': line.product_id.id if line.product_id else None,
                    'product_name': line.product_id.name if line.product_id else None,
                    'image_url': f"/product/image/{line.product_id.product_tmpl_id.id}" if line.product_id.product_tmpl_id.image_1920 else None,
                    'description': line.name or None,
                    'quantity': line.product_uom_qty or None,
                    'price_unit': line.price_unit or None,
                    'subtotal': line.price_subtotal or None,
                    'tax_ids': [{"id":tax.id,"tax": tax.name} for tax in line.tax_id]  # Ajustado para manejar como array
                }
                products_data.append(product_data)
            order_data = {
                'id': order.id,
                'name': order.name,
                'customer_id': order.partner_id.id if order.partner_id else None,
                'customer_name': order.partner_id.name if order.partner_id else None,
                'customer_address_inline': order.partner_id.contact_address_inline if order.partner_id else None,
                'invoice_address': {
                    'id': order.partner_invoice_id.id,  # Id del res.partner
                    'name': order.partner_invoice_id.name  # Nombre del res.partner
                } if order.partner_invoice_id else None,
                'delivery_address': {
                    'id': order.partner_shipping_id.id,  # Id del res.partner
                    'name': order.partner_shipping_id.name
                } if order.partner_shipping_id else None,
                'payment_term': {
                    'id': order.payment_term_id.id,
                    'name': order.payment_term_id.name
                } if order.payment_term_id else None,
                'date_order': fields.Datetime.to_string(order.date_order) if order.date_order else None,
                'amount_total': order.amount_total or None,
                'state': order.state or None,
                'salesperson': {
                    'id': order.user_id.id or None,
                    'name': order.user_id.name or None
                } if order.user_id else None,
                'expiration': fields.Date.to_string(order.validity_date) if order.validity_date else None,
                'products': products_data
            }
            sale_orders_data.append(order_data)
        response_data = {
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'items': sale_orders_data
        }
        return  self._brain_response(response_data, 200)

    @http.route('/api/sale_orders/<int:sale_order_id>', type='http', auth='none', methods=['GET'], csrf=False)
    def get_sale_order_details(self, sale_order_id):
        """Devuelve los detalles completos de una orden de venta por su ID."""
        # Verificación del acceso y obtención del entorno adecuado
        check, env = self._check_access('sale.order')
        if not check:
            return env  # Env ya es una respuesta HTTP de error

        try:
            sale_order = env['sale.order'].browse(sale_order_id)
            if not sale_order.exists():
                return self._brain_response({'error': 'Sale order not found'}, 404)

            products_data = []
            for line in sale_order.order_line:
                product_data = {
                    'order_line_id': line.id,
                    'product_id': line.product_id.id if line.product_id else None,
                    'product_name': line.product_id.name if line.product_id else None,
                    'image_url': f"/product/image/{line.product_id.product_tmpl_id.id}" if line.product_id.product_tmpl_id.image_1920 else None,
                    'description': line.name or None,
                    'quantity': line.product_uom_qty or None,
                    'price_unit': line.price_unit or None,
                    'subtotal': line.price_subtotal or None,
                    'tax_ids': [{"id": tax.id, "tax": tax.name} for tax in line.tax_id]
                }
                products_data.append(product_data)

            order_details = {
                'id': sale_order.id,
                'name': sale_order.name,
                'customer_id': sale_order.partner_id.id if sale_order.partner_id else None,
                'customer_name': sale_order.partner_id.name if sale_order.partner_id else None,
                'customer_address_inline': sale_order.partner_id.contact_address_inline if sale_order.partner_id else None,
                'invoice_address': {
                    'id': sale_order.partner_invoice_id.id,
                    'name': sale_order.partner_invoice_id.name
                } if sale_order.partner_invoice_id else None,
                'delivery_address': {
                    'id': sale_order.partner_shipping_id.id,
                    'name': sale_order.partner_shipping_id.name
                } if sale_order.partner_shipping_id else None,
                'payment_term': {
                    'id': sale_order.payment_term_id.id,
                    'name': sale_order.payment_term_id.name
                } if sale_order.payment_term_id else None,
                'date_order': fields.Datetime.to_string(sale_order.date_order) if sale_order.date_order else None,
                'amount_total': sale_order.amount_total or None,
                'state': sale_order.state or None,
                'salesperson': {
                    'id': sale_order.user_id.id or None,
                    'name': sale_order.user_id.name or None
                } if sale_order.user_id else None,
                'expiration': fields.Date.to_string(sale_order.validity_date) if sale_order.validity_date else None,
                'products': products_data
            }
            return self._brain_response(order_details)

        except ValidationError as e:
            return self._brain_response({'error': str(e)}, 400)
        except Exception as e:
            _logger.error('Error retrieving sale order details: %s', str(e))
            return self._brain_response({'error': str(e)}, 500)

    def get_sale_order_details_dictionary(self, sale_order_id):
        """Devuelve los detalles completos de una orden de venta por su ID."""
        # Verificación del acceso y obtención del entorno adecuado
        check, env = self._check_access('sale.order')
        if not check:
            return env  # Env ya es una respuesta HTTP de error

        try:
            sale_order = env['sale.order'].browse(sale_order_id)
            if not sale_order.exists():
                return self._brain_response({'error': 'Sale order not found'}, 404)

            products_data = []
            for line in sale_order.order_line:
                product_data = {
                    'order_line_id': line.id,
                    'product_id': line.product_id.id if line.product_id else None,
                    'product_name': line.product_id.name if line.product_id else None,
                    'image_url': f"/product/image/{line.product_id.product_tmpl_id.id}" if line.product_id.product_tmpl_id.image_1920 else None,
                    'description': line.name or None,
                    'quantity': line.product_uom_qty or None,
                    'price_unit': line.price_unit or None,
                    'subtotal': line.price_subtotal or None,
                    'tax_ids': [{"id": tax.id, "tax": tax.name} for tax in line.tax_id]
                }
                products_data.append(product_data)

            order_details = {
                'id': sale_order.id,
                'name': sale_order.name,
                'customer_id': sale_order.partner_id.id if sale_order.partner_id else None,
                'customer_name': sale_order.partner_id.name if sale_order.partner_id else None,
                'customer_address_inline': sale_order.partner_id.contact_address_inline if sale_order.partner_id else None,
                'invoice_address': {
                    'id': sale_order.partner_invoice_id.id,
                    'name': sale_order.partner_invoice_id.name
                } if sale_order.partner_invoice_id else None,
                'delivery_address': {
                    'id': sale_order.partner_shipping_id.id,
                    'name': sale_order.partner_shipping_id.name
                } if sale_order.partner_shipping_id else None,
                'payment_term': {
                    'id': sale_order.payment_term_id.id,
                    'name': sale_order.payment_term_id.name
                } if sale_order.payment_term_id else None,
                'date_order': fields.Datetime.to_string(sale_order.date_order) if sale_order.date_order else None,
                'amount_total': sale_order.amount_total or None,
                'state': sale_order.state or None,
                'salesperson': {
                    'id': sale_order.user_id.id or None,
                    'name': sale_order.user_id.name or None
                } if sale_order.user_id else None,
                'expiration': fields.Date.to_string(sale_order.validity_date) if sale_order.validity_date else None,
                'products': products_data
            }
            return order_details

        except ValidationError as e:
            _logger.error(f'Validation Error retrieving sale order details: {str(e)}')
            raise  # Propaga la excepción para manejarla en el método llamador

        except Exception as e:
            _logger.error(f'Error retrieving sale order details: {str(e)}')
            raise  # Propaga la excepción para manejarla en el método llamador

    @http.route('/api/sale_order/<int:sale_order_id>', type='http', auth='none', methods=['POST'], csrf=False)
    def update_sale_order(self, sale_order_id):
        """Actualizar una orden de venta existente"""
        has_access, env = self._check_access('sale.order', 'write')
        if not has_access:
            return env

        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            sale_order = env['sale.order'].browse(sale_order_id)
            if not sale_order.exists():
                return self._brain_response({'error': 'Sale order not found'}, 404)

            # Preparar los campos editables solo con datos proporcionados
            editable_fields = {}
            fields_map = {
                'customer_id': 'partner_id',
                'date_order': 'date_order',
                'validity_date': 'validity_date',
                'payment_term_id': 'payment_term_id',
                'partner_invoice_id': 'partner_invoice_id',
                'partner_shipping_id': 'partner_shipping_id',
                'note': 'note'
            }

            # Recorrer el mapeo y actualizar solo si el campo correspondiente está presente en el dato
            for key, field in fields_map.items():
                if key in data:
                    if '_id' in key:
                        editable_fields[field] = int(data[key])
                    else:
                        editable_fields[field] = data[key]
            if editable_fields:
                sale_order.write(editable_fields)

            ######################## NUEVA SECCION PARA ELIMINAR UN PRODUCTO #############################
            # Identificar y actualizar o crear líneas de producto
            existing_lines_ids = {line.id for line in sale_order.order_line}
            received_lines_ids = {int(line['order_line_id']) for line in data.get('order_lines', []) if
                                  'order_line_id' in line}

            # Eliminar líneas que no están en el nuevo conjunto de datos
            lines_to_remove = existing_lines_ids - received_lines_ids
            if lines_to_remove:
                env['sale.order.line'].browse(list(lines_to_remove)).unlink()

            ######################### FIN DE LA SECCIÓN PARA ELIMINAR UN PRODUCTO ##########################################

            # Actualizar líneas de la orden solo si se proporciona 'order_lines'
            if 'order_lines' in data:
                for line in data['order_lines']:
                    line_id = line.get('order_line_id')
                    if line_id:
                        existing_line = env['sale.order.line'].browse(int(line_id))
                        if existing_line.exists():
                            line_update = {k: v for k, v in line.items() if k not in ['order_line_id', 'tax_ids', 'quantity']}
                            if 'tax_ids' in line:
                                line_update['tax_id'] = [(6, 0, line['tax_ids'])]
                            if 'quantity' in line:
                                line_update['product_uom_qty'] = float(line['quantity'])
                            existing_line.write(line_update)
                    else:
                        new_line = {
                            'order_id': sale_order.id,
                            'product_id': line['product_id'],
                            'product_uom_qty': line['quantity'],
                            'price_unit': line['price_unit'],
                            'tax_id': [(6, 0, line.get('tax_ids', []))]
                        }
                        env['sale.order.line'].create(new_line)
            try:
                data_response = self.get_sale_order_details_dictionary(sale_order_id)
            except Exception as e:
                return self._brain_response({'error': str(e)}, 500)

            return self._brain_response({
                'id': sale_order.id,
                'name': sale_order.name,
                'message': 'Sale order updated successfully',
                'data': data_response
            })

        except ValidationError as e:
            return self._brain_response({'error': str(e)}, 400)
        except Exception as e:
            _logger.error('Error updating sale order: %s', str(e))
            return self._brain_response({'error': str(e)}, 500)

    # Método para crear cotizaciones usando el id de prodctos variantes.
    @http.route('/api/create_quotation_by_variants', type='http', auth="none", methods=['POST'], csrf=False)
    def create_quotation_by_variants(self, **kwargs):
        try:
            # Verificación del token
            is_valid, result = self._check_access('sale.order')
            if not is_valid:
                return result

            # Validación y parsing del payload
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except json.JSONDecodeError:
                return self._brain_response({'error': 'JSON inválido'}, status=400)

                # Validar y obtener el usuario
            user_id = data.get('user_id')
            if user_id:
                user = request.env['res.users'].sudo().browse(int(user_id))
                if not user.exists():
                    return self._brain_response({'error': f'Usuario con ID {user_id} no encontrado'}, status=400)
            else:
                user = request.env.user

            # Obtener y validar el partner
            partner = request.env['res.partner'].sudo().browse(data['partner_id'])
            if not partner.exists():
                return self._brain_response({'error': 'Partner no encontrado'}, status=400)

            # Obtener la compañía correcta
            company = request.env.user.company_id or request.env['res.company'].sudo().search([], limit=1)

            # Verificar si el partner es válido para la compañía
            if not self._validate_partner_company(partner, company):
                # Intentar buscar o crear una versión del partner para esta compañía
                partner = self._get_or_create_company_partner(partner, company)
                if not partner:
                    return self._brain_response({
                        'error': f'El partner no es compatible con la compañía {company.name}'
                    }, status=400)

            # Preparar datos de la orden con el partner correcto
            sale_order_data = self._prepare_order_data(data, partner, company, user)

            # Procesar líneas de orden
            order_lines = []
            for line in data.get('order_line', []):
                line_data = self._process_order_line(line, company)
                if isinstance(line_data, dict) and 'error' in line_data:
                    return self._brain_response(line_data, status=400)
                order_lines.append(line_data)

            sale_order_data['order_line'] = order_lines

            # Crear la orden de venta
            sale_order = request.env['sale.order'].sudo().with_company(company.id).create(sale_order_data)

            return self._brain_response({
                'id': sale_order.id,
                'name': sale_order.name
            }, status=201)

        except Exception as e:
            _logger.error('Error al crear la cotización: %s', str(e), exc_info=True)
            return self._brain_response({'error': str(e)}, status=500)

    # Metodo usado para validar la compañia del partner
    def _validate_partner_company(self, partner, company):
        """Valida si el partner es válido para la compañía."""
        return (
                partner.company_id.id == company.id or  # Mismo company_id
                not partner.company_id.id or  # Sin company_id (multi-compañía)
                partner.company_id.id in request.env.user.company_ids.ids  # Compañía permitida para el usuario
        )

    # Metodo usado para obtener o crear una compañia de un cliente
    def _get_or_create_company_partner(self, partner, company):
        """Busca o crea una versión del partner para la compañía específica."""
        Partner = request.env['res.partner'].sudo()

        # Buscar si ya existe un partner con el mismo nombre y compañía
        existing_partner = Partner.search([
            ('name', '=', partner.name),
            ('company_id', '=', company.id)
        ], limit=1)

        if existing_partner:
            return existing_partner

        # Si está permitido, crear una nueva versión del partner
        try:
            new_partner = Partner.with_company(company.id).create({
                'name': partner.name,
                'email': partner.email,
                'phone': partner.phone,
                'company_id': company.id,
                'type': 'contact',
            })
            return new_partner
        except Exception as e:
            _logger.error('Error al crear partner: %s', str(e))
            return None

    def _prepare_order_data(self, data, partner, company, user):
        """Prepara los datos base de la orden de venta."""
        return {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'currency_id': int(data.get('currency_id', 0)) or company.currency_id.id,
            'validity_date': data.get('validity_date'),
            'note': data.get('note'),
            'company_id': company.id,
            'user_id': user.id,  # Asignar el usuario a la cotización
            'team_id': user.sale_team_id.id if user.sale_team_id else False
        }

    def _process_order_line(self, line, company):
        """Procesa una línea de orden y busca el producto correcto basado en las variantes."""
        product_template_id = line.get('product_id')
        variants = line.get('variants', [])

        if not product_template_id:
            return {'error': 'ID de producto requerido'}

        # Construir dominio para búsqueda de producto con compañía correcta
        product_domain = [
            ('product_tmpl_id', '=', product_template_id),
            '|',
            ('company_id', '=', company.id),
            ('company_id', '=', False)
        ]
        if variants:
            product_domain.append(('product_template_variant_value_ids', 'in', variants))

        # Buscar producto
        Product = request.env['product.product'].sudo()
        products = Product.with_company(company.id).search(product_domain)

        if variants:
            product = next((
                p for p in products
                if set(p.product_template_variant_value_ids.ids) == set(variants)
            ), None)
        else:
            product = products[:1]

        if not product:
            return {'error': f'No se encontró producto con template_id {product_template_id} y variantes {variants}'}

        return (0, 0, {
            'product_id': product.id,
            'product_uom_qty': line.get('product_uom_qty', 1.0),
            'price_unit': line.get('price_unit') or product.lst_price,
        })

    @http.route('/api/quotations', type='http', auth='none', methods=['POST'], csrf=False)
    def create_quotation(self):
        """Crear una nueva cotización"""
        # Verificar acceso
        has_access, env = self._check_access('sale.order', 'create')
        if not has_access:
            return env

        try:
            # Obtener datos del form-data o json
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data.decode('utf-8'))
            else:
                data = request.params
            # Validar campos requeridos
            required_fields = ['partner_id']
            for field in required_fields:
                if field not in data:
                    return self._brain_response({
                        'error': f'Campo requerido faltante: {field}'
                    }, 400)

            # Calcular fecha de expiración (30 días por defecto)
            quotation_date = datetime.now()
            expiration_date = (quotation_date + timedelta(days=30)).strftime('%Y-%m-%d')

            # Preparar datos de la cotización
            quotation_vals = {
                'partner_id': int(data.get('partner_id')),
                'company_id': env.user.company_id.id,
                'user_id': env.user.id,
                'date_order': data.get('quotation_date', quotation_date.strftime('%Y-%m-%d %H:%M:%S')),
                'validity_date': data.get('expiration', expiration_date),
                'payment_term_id': int(data.get('payment_term_id', 1)),  # ID del término de pago por defecto
                'order_line': [],

                # Direcciones
                'partner_invoice_id': int(data.get('partner_invoice_id', data.get('partner_id'))),
                'partner_shipping_id': int(data.get('partner_shipping_id', data.get('partner_id'))),

                # Campos adicionales
                'note': data.get('note', '')  # Notas de la cotización
            }

            # Procesar líneas de la orden si existen
            order_lines = data.get('order_line', [])
            if isinstance(order_lines, list):
                for line in order_lines:
                    if not all(k in line for k in ['product_id', 'product_uom_qty']):
                        return self._brain_response({
                            'error': 'Cada línea debe contener product_id y product_uom_qty'
                        }, 400)

                    line_vals = [0, 0, {
                        'product_id': int(line['product_id']),
                        'product_uom_qty': float(line['product_uom_qty']),
                        'discount': float(line.get('discount', 0.0)),
                        # 'tax_id': int(line['tax_id']),
                        # TODO: Revisar que se envien en la lista de impuestos los impuestos relacionados a la empresa a la que pertence el cliente.
                        'tax_id': [(6, 0, line['tax_id'])] if line['tax_id'] else [(6, 0, [])],
                        'name': line['description'],
                        'price_unit': float(line.get('price_unit', 0.0))
                    }]
                    quotation_vals['order_line'].append(line_vals)

            # Crear la cotización
            quotation = env['sale.order'].create(quotation_vals)
            try:
                data_response = self.get_sale_order_details_dictionary(quotation.id)
            except Exception as e:
                return self._brain_response({'error': str(e)}, 500)

            return self._brain_response({
                'id': quotation.id,
                'name': quotation.name,
                'data': data_response
            })

        except ValidationError as e:
            return self._brain_response({'error': str(e)}, 400)
        except Exception as e:
            _logger.error('Error creating quotation: %s', str(e))
            return self._brain_response({'error': str(e)}, 500)

    @http.route('/api/sale_order/configs', type='http', auth="none", methods=['GET'], csrf=False)
    def get_sale_order_configs(self, **kwargs):
        has_access, env = self._check_access('sale.order')
        if not has_access:
            return env
        # Asegurarse de que el usuario tiene acceso al modelo 'sale.order'
        try:
            payment_terms = env['account.payment.term'].search_read([], ['id', 'name'])
            # Extraer estados del pedido de venta directamente de la definición del campo en el modelo
            order_states = env['sale.order']._fields['state'].selection
            states = [{'code': state[0], 'name': state[1]} for state in order_states]

            # Obtener impuestos relacionados con la compañía del usuario
            company_taxes = env['account.tax'].search_read(
                [('company_id', '=', env.user.company_id.id)],
                ['id', 'name', 'amount_type', 'amount', 'description']
            )

            return self._brain_response({
                    'payment_terms': payment_terms,
                    'order_states': states,
                    'taxes': company_taxes
                })
        except Exception as e:
            return self._brain_response({'error': str(e)}, 400)

    #Metodo que envia el email
    @http.route('/api/sale_orders/<int:sale_order_id>/send_email', type='http', auth="none", methods=['POST'], csrf=False)
    def send_sale_order_email(self, sale_order_id, **kwargs):
        # Verificar el acceso usando el token y obteniendo el entorno adecuado
        check, result = self._check_access('sale.order')
        if not check:
            return result  # Retorna el error si el token es inválido

        env = result  # Usar el entorno configurado con el usuario del token
        sale_order = env['sale.order'].browse(sale_order_id)
        if not sale_order.exists():
            return request.make_response(json.dumps({'error': 'Orden de venta no encontrada.'}),
                                         headers={'Content-Type': 'application/json'}, status=404)

        try:
            # Ejecutar la acción de enviar el correo electrónico asociado a la cotización
            if 'action_quotation_send' in dir(sale_order):
                sale_order.action_quotation_send()
                sale_order.state = 'sent'
                env.cr.commit()
                return self._brain_response({'message': 'Email enviado correctamente.'})
            else:
                return self._brain_response({'error': 'Funcionalidad de envío de email no disponible.'}, 500)
        except Exception as e:
            return self._brain_response({'error': 'Error interno del servidor: ' + str(e)}, 500)

    @http.route('/api/sale_orders/<int:sale_order_id>/confirm', type='http', auth="none", methods=['GET'], csrf=False)
    def confirm_sale_order(self, **kwargs):
        sale_order_id = kwargs.get('sale_order_id')
        check, env = self._check_access('sale.order', 'write')
        if not check:
            return env

        try:
            sale_order = env['sale.order'].browse(int(sale_order_id))
            if not sale_order.exists():
                return self._brain_response({'error': 'Sale order no encontrado'}, 404)
            sale_order.action_confirm()
            return self._brain_response({'message': 'Sale order confirmado'})
        except Exception as e:
            return self._brain_response({'error': str(e)}, 500)

    @http.route('/api/sale_orders/<int:sale_order_id>/cancel', type='http', auth="none", methods=['GET'], csrf=False)
    def cancel_sale_order(self, sale_order_id):
        """Cancela una orden de venta si no está en estado 'confirmado'."""
        check, env = self._check_access('sale.order', 'write')
        if not check:
            return env  # Env ya es una respuesta HTTP de error

        try:
            sale_order = env['sale.order'].browse(sale_order_id)
            if not sale_order.exists():
                return self._brain_response({'error': 'Sale order no encontrado'}, 404)

            # Verificar que la orden no esté en estado 'sale' o 'done'
            if sale_order.state in ['sale', 'done']:
                return self._brain_response(
                    {'error': 'No se puede cancelar una orden en estado confirmado o completado'}, 403)

            sale_order.action_cancel()
            return self._brain_response({'message': 'Sale order cancelada correctamente'})
        except Exception as e:
            return self._brain_response({'error': str(e)}, 500)
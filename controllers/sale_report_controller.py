from odoo import http
from odoo.http import request
from datetime import datetime
from .auth_contoller import AuthController
import logging

_logger = logging.getLogger(__name__)

class SalesReportController(AuthController):

    @http.route('/api/reports/all', type='http', auth='none', methods=['GET'], csrf=False)
    def get_all_reports(self, **kwargs):
        """Devuelve todos los reportes de ventas en una sola respuesta según los parámetros y roles de usuario."""
        check, env = self._check_access('sale.order')
        if not check:
            return env  # Env ya es una respuesta HTTP de error

        start_date = kwargs.get('start_date', datetime.today().strftime('%Y-%m-%d'))
        end_date = kwargs.get('end_date', datetime.today().strftime('%Y-%m-%d'))

        try:
            data = {
                'top_products': self.get_top_products(env, start_date, end_date),
                'total_sales': self.get_total_sales(env, start_date, end_date),
                'sales_by_seller': self.get_sales_by_seller(env, start_date, end_date),
                'sales_by_product': self.get_sales_by_product(env, start_date, end_date)
            }
            return self._brain_response(data)
        except Exception as e:
            _logger.error(f"Error obtaining reports: {str(e)}")
            return self._brain_response({'error': 'Internal server error'}, status=500)

    def get_top_products(self, env, start_date, end_date):
        query = """
            SELECT
                pt.name AS product_name,
                SUM(sol.product_uom_qty) AS quantity_sold,
                ROUND((SUM(sol.product_uom_qty) / total.total_quantity) * 100, 2) AS percentage_of_total_sales
            FROM
                sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id
                JOIN product_product pp ON pp.id = sol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id,
                (SELECT SUM(product_uom_qty) AS total_quantity FROM sale_order_line sol
                 JOIN sale_order so ON so.id = sol.order_id
                 WHERE so.date_order >= %s AND so.date_order <= %s AND so.state = 'sale') AS total
            WHERE
                so.date_order >= %s AND
                so.date_order <= %s AND
                so.state = 'sale'
            GROUP BY
                pt.name, total.total_quantity
            ORDER BY
                quantity_sold DESC
            LIMIT 10;
        """
        env.cr.execute(query, (start_date, end_date, start_date, end_date))
        results = env.cr.dictfetchall()
        return results

    def get_total_sales(self, env, start_date, end_date):
        sale_orders = env['sale.order'].search(
            [('date_order', '>=', start_date), ('date_order', '<=', end_date), ('state', 'in', ['sale', 'done'])])
        return sum(order.amount_total for order in sale_orders)

    def get_sales_by_seller(self, env, start_date, end_date):
        domain = [('date_order', '>=', start_date), ('date_order', '<=', end_date), ('state', '=', 'sale')]
        if not env.user.has_group('base.group_system'):
            domain.append(('user_id', '=', env.user.id))
        results = env['sale.order'].read_group(domain, ['user_id', 'amount_total'], ['user_id'])
        # Ajustar formato de user_id
        formatted_results = [{
            'userId': result['user_id'][0],
            'userName': result['user_id'][1],
            'amountTotal': result['amount_total'],
            'count': result['user_id_count']
        } for result in results]
        return formatted_results

    def get_sales_by_product(self, env, start_date, end_date):
        domain = [('order_id.date_order', '>=', start_date), ('order_id.date_order', '<=', end_date), ('order_id.state', '=', 'sale')]
        results = env['sale.order.line'].read_group(domain, ['product_id', 'product_uom_qty', 'price_subtotal'], ['product_id'])
        # Ajustar formato para excluir dominios
        formatted_results = [{
            'productId': result['product_id'][0],
            'productName': result['product_id'][1],
            'quantitySold': result['product_uom_qty'],
            'totalSales': result['price_subtotal']
        } for result in results]
        return formatted_results

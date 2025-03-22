from odoo import http, fields
from odoo.http import request
from .auth_contoller import AuthController
from werkzeug.wrappers import Response
import json
import math
import base64
from io import BytesIO

class CrmLeadController(AuthController):

    @http.route('/api/leads', type='http', auth="none", methods=['GET'], csrf=False)
    def get_leads(self, **kwargs):
        """API para obtener la lista de oportunidades (crm.lead) con paginación y validación de token."""
        check, result = self._check_access('crm.lead')
        if not check:
            return result  # Si es una respuesta, contiene el error

        env = result
        # Parámetros de paginación
        page = int(kwargs.get('page', 1))
        per_page = int(kwargs.get('per_page', 10))

        Lead = env['crm.lead']
        total_items = Lead.search_count([])
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

        if page < 1 or page > total_pages:
            return self._brain_response({'error': 'Página fuera de rango.'}, 400)

        leads = Lead.search([], offset=(page - 1) * per_page, limit=per_page)

        lead_list = []
        for lead in leads:
            lead_data = {
                'id': lead.id,
                'name': lead.name or None,
                'email_from': lead.email_from or None,
                'phone': lead.phone or None,
                'mobile': lead.mobile or None,
                'stage_id': lead.stage_id.id if lead.stage_id else None,
                'stage_name': lead.stage_id.name if lead.stage_id else None,
                'partner_id': lead.partner_id.id if lead.partner_id else None,
                'partner_name': lead.partner_id.name if lead.partner_id else None,
                'expected_revenue': lead.expected_revenue or 0.0,
                'probability': lead.probability or 0.0,
                'user_id': lead.user_id.id if lead.user_id else None,
                'user_name': lead.user_id.name if lead.user_id else None,
                'company_id': lead.company_id.id if lead.company_id else None,
                'company_name': lead.company_id.name if lead.company_id else None,
                'create_date': lead.create_date.isoformat() if lead.create_date else None,
                'create_uid': lead.create_uid.id if lead.create_uid else None,
                'create_uid_name': lead.create_uid.name if lead.create_uid else None,
            }
            lead_list.append(lead_data)

        response_data = {
            'status': 'success',
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'items': lead_list
        }

        return self._brain_response(response_data, 200)
from odoo import http, fields
from odoo.http import request
from .auth_contoller import AuthController
from werkzeug.wrappers import Response
import json
import math
import base64
from io import BytesIO
from werkzeug.utils import secure_filename

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

                # 🔽 Campos personalizados
                'address': lead.address or None,
                'industry_id': lead.industry.id if lead.industry else None,
                'industry_name': lead.industry.name if lead.industry else None,

                'adoption_type_id': lead.adoption_type_id.id if lead.adoption_type_id else None,
                'adoption_type_name': lead.adoption_type_id.name if lead.adoption_type_id else None,

                'numero_a_portar': lead.numero_a_portar or None,
                'sim_card': lead.sim_card or None,
                'numero_de_la_linea_nueva': lead.numero_de_la_linea_nueva or None,

                'brain_cuenta': lead.brain_cuenta or None,
                'brain_orden': lead.brain_orden or None,
                'brain_mrc': lead.brain_mrc or None,

                'tipo_cliente_id': lead.tipo_cliente_id.id if lead.tipo_cliente_id else None,
                'tipo_cliente_name': lead.tipo_cliente_id.name if lead.tipo_cliente_id else None,

                'tipo_activacion_id': lead.tipo_activacion_id.id if lead.tipo_activacion_id else None,
                'tipo_activacion_name': lead.tipo_activacion_id.name if lead.tipo_activacion_id else None,

                'adoption_status': lead.adoption_status or None,
                'adoption_form': base64.b64encode(lead.adoption_form).decode('utf-8') if lead.adoption_form else None
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

    @http.route('/api/leads/<int:lead_id>/attachments', type='http', auth='none', methods=['POST'], csrf=False)
    def upload_attachment(self, lead_id, **kwargs):
        # Verificar token
        check, result = self._check_access('crm.lead', operation='write')
        if not check:
            return result  # Error 401 o 403

        env = result
        lead = env['crm.lead'].sudo().browse(lead_id)

        if not lead.exists():
            return self._brain_response({'error': 'Lead no encontrado.'}, 404)

        # Procesar archivos enviados (form-data)
        files = request.httprequest.files.getlist('files')

        if not files:
            return self._brain_response({'error': 'Debe enviar al menos un archivo en form-data.'}, 400)

        attachment_ids = []

        for file in files:
            filename = secure_filename(file.filename)
            content = file.read()

            attachment = env['ir.attachment'].sudo().create({
                'name': filename,
                'datas': base64.b64encode(content),
                'res_model': 'crm.lead',
                'res_id': lead.id,
                'mimetype': file.mimetype,
                'type': 'binary',
            })

            attachment_ids.append(attachment.id)

        # Post en el chatter con todos los archivos
        lead.message_post(
            body=f'Se adjuntaron {len(attachment_ids)} archivo(s).',
            attachment_ids=attachment_ids
        )
        return self._brain_response({'success': 'Archivos adjuntados correctamente.'}, 200)

import traceback

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

        # 🔒 Filtro: Portal solo ve sus propios leads
        domain = []
        if env.user.has_group('base.group_portal'):
            domain.append(('user_id', '=', env.uid))

        total_items = Lead.search_count([])
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

        if page < 1 or page > total_pages:
            return self._brain_response({'error': 'Página fuera de rango.'}, 400)

        leads = Lead.search(domain, offset=(page - 1) * per_page, limit=per_page)

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
                'description': lead.description,  # SE AGREGÓ EL CAMPO DESCRIPCION

                # Campos personalizados
                'address': lead.address or None,
                'industry_id': lead.industry.id if lead.industry else None,
                'industry_name': lead.industry.name if lead.industry else None,
                'coordinador_id': lead.brain_coordinador.id if lead.brain_coordinador else None,
                'coordinador_name': lead.brain_coordinador.name if lead.brain_coordinador else None,

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
                'brain_province': lead.brain_province if lead.brain_province else None
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

    @http.route('/api/sales_manager', type='http', auth="none", methods=['GET'], csrf=False)
    def get_coordinadores(self, **kwargs):
        """API para obtener lista de usuarios con rol de Coordinador (Sales Manager)"""
        check, result = self._check_access('crm.lead', operation='read')
        if not check:
            return result

        env = result
        group = env.ref('sales_team.group_sale_manager')
        coordinadores = env['res.users'].sudo().search([
            ('groups_id', 'in', [group.id])
        ])

        users_list = []
        for user in coordinadores:
            users_list.append({
                'id': user.id,
                'name': user.name,
                'email': user.email or '',
                'login': user.login
            })
        return self._brain_response({'status': 'success', 'items': users_list}, 200)

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

    @http.route('/api/leads', type='http', auth='none', methods=['POST'], csrf=False)
    def create_lead(self, **kwargs):
        """Crear una nueva oportunidad (Lead) desde la API y devolver su información completa."""
        check, result = self._check_access('crm.lead', 'create')
        if not check:
            return result

        env = result

        try:
            values = request.get_json_data()

            # Validar si el coordinador pertenece al grupo Sales Manager
            coordinador_id = values.get('coordinador_id')
            if coordinador_id:
                user = env['res.users'].sudo().browse(coordinador_id)
                grupo_coordinador = env.ref('sales_team.group_sale_manager')
                if grupo_coordinador not in user.groups_id:
                    return self._brain_response({'error': 'El usuario seleccionado no es un Coordinador válido.'}, 400)

            lead_vals = {
                'name': values.get('name'),
                'email_from': values.get('email_from'),
                'phone': values.get('phone'),
                'mobile': values.get('mobile'),
                'expected_revenue': values.get('expected_revenue'),
                'probability': values.get('probability'),
                'user_id': values.get('user_id'),
                'partner_id': values.get('partner_id'),
                'company_id': values.get('company_id'),
                'address': values.get('address'),
                'industry': values.get('industry_id'),
                'brain_coordinador': coordinador_id,
                'adoption_type_id': values.get('adoption_type_id'),
                'numero_a_portar': values.get('numero_a_portar'),
                'sim_card': values.get('sim_card'),
                'numero_de_la_linea_nueva': values.get('numero_de_la_linea_nueva'),
                'brain_cuenta': values.get('brain_cuenta'),
                'brain_orden': values.get('brain_orden'),
                'brain_mrc': values.get('brain_mrc'),
                'tipo_cliente_id': values.get('tipo_cliente_id'),
                'tipo_activacion_id': values.get('tipo_activacion_id'),
                'description': values.get('description'),
                'brain_province': values.get('brain_province'),
            }

            # Archivo adjunto opcional (base64)
            if values.get('adoption_form'):
                try:
                    lead_vals['adoption_form'] = base64.b64decode(values['adoption_form'])
                except Exception:
                    return self._brain_response({'error': 'El campo "adoption_form" debe estar en base64 válido.'}, 400)

            # Crear el lead
            lead = env['crm.lead'].sudo().create(lead_vals)

            # Armar respuesta completa
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

                # Campos personalizados
                'address': lead.address or None,
                'industry_id': lead.industry.id if lead.industry else None,
                'industry_name': lead.industry.name if lead.industry else None,
                'coordinador_id': lead.brain_coordinador.id if lead.brain_coordinador else None,
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
                'brain_province': lead.brain_province if lead.brain_province else None
            }

            return self._brain_response({'status': 'success', 'lead': lead_data}, 201)

        except Exception as e:
            error_msg = traceback.format_exc()
            return self._brain_response({'error': f'Error al crear el lead: {str(e)}', 'debug': error_msg}, 500)

    @http.route('/api/industries', type='http', auth="none", methods=['GET'], csrf=False)
    def get_industries(self, **kwargs):
        """API para obtener lista de industrias (res.partner.industry)"""
        check, result = self._check_access('crm.lead', operation='read')
        if not check:
            return result

        env = result
        industry = env['res.partner.industry']
        industries = industry.sudo().search([])

        industry_list = []
        for industry in industries:
            industry_list.append({
                'id': industry.id,
                'name': industry.name
            })

        return self._brain_response({'status': 'success', 'items': industry_list}, 200)

    @http.route('/api/adoption_types', type='http', auth="none", methods=['GET'], csrf=False)
    def get_adoption_types(self, **kwargs):
        """API para obtener lista de tipos de adopción (brain.adoption.type)"""
        check, result = self._check_access('crm.lead', operation='read')
        if not check:
            return result

        env = result
        AdoptionType = env['brain.adoption.type']
        types = AdoptionType.sudo().search([])

        type_list = []
        for adoption_type in types:
            type_list.append({
                'id': adoption_type.id,
                'name': adoption_type.name
            })

        return self._brain_response({'status': 'success', 'items': type_list}, 200)

    @http.route('/api/tipos_activacion', type='http', auth="none", methods=['GET'], csrf=False)
    def get_tipos_activacion(self, **kwargs):
        """API para obtener lista de tipos de activación (brain.tipo.activacion)"""
        check, result = self._check_access('crm.lead', operation='read')
        if not check:
            return result

        env = result
        TipoActivacion = env['brain.tipo.activacion']
        tipos = TipoActivacion.sudo().search([])

        tipo_list = []
        for tipo in tipos:
            tipo_list.append({
                'id': tipo.id,
                'name': tipo.name
            })

        return self._brain_response({'status': 'success', 'items': tipo_list}, 200)

    @http.route('/api/tipos_cliente', type='http', auth="none", methods=['GET'], csrf=False)
    def get_tipos_cliente(self, **kwargs):
        """API para obtener lista de tipos de cliente (brain.tipo.cliente)"""
        check, result = self._check_access('crm.lead', operation='read')
        if not check:
            return result

        env = result
        TipoCliente = env['brain.tipo.cliente']
        tipos = TipoCliente.sudo().search([])

        tipo_list = []
        for tipo in tipos:
            tipo_list.append({
                'id': tipo.id,
                'name': tipo.name
            })

        return self._brain_response({'status': 'success', 'items': tipo_list}, 200)

    @http.route('/api/leads/<int:lead_id>', type='http', auth='none', methods=['POST'], csrf=False)
    def update_lead(self, lead_id, **kwargs):
        """Actualizar una oportunidad (Lead) existente"""
        check, result = self._check_access('crm.lead', operation='write')
        if not check:
            return result

        env = result
        lead = env['crm.lead'].sudo().browse(lead_id)

        if not lead.exists():
            return self._brain_response({'error': 'Lead no encontrado.'}, 404)

        try:
            values = request.get_json_data()

            # Validar si el coordinador pertenece al grupo Sales Manager
            coordinador_id = values.get('coordinador_id')
            if coordinador_id:
                user = env['res.users'].sudo().browse(coordinador_id)
                grupo_coordinador = env.ref('sales_team.group_sale_manager')
                if grupo_coordinador not in user.groups_id:
                    return self._brain_response({'error': 'El usuario seleccionado no es un Coordinador válido.'}, 400)

            lead_vals = {
                'name': values.get('name'),
                'email_from': values.get('email_from'),
                'phone': values.get('phone'),
                'mobile': values.get('mobile'),
                'expected_revenue': values.get('expected_revenue'),
                'probability': values.get('probability') or 0.0,
                'user_id': values.get('user_id'),
                'partner_id': values.get('partner_id'),
                'company_id': values.get('company_id'),
                'address': values.get('address'),
                'industry': values.get('industry_id'),
                'brain_coordinador': coordinador_id,
                'adoption_type_id': values.get('adoption_type_id'),
                'numero_a_portar': values.get('numero_a_portar'),
                'sim_card': values.get('sim_card'),
                'numero_de_la_linea_nueva': values.get('numero_de_la_linea_nueva'),
                'brain_cuenta': values.get('brain_cuenta'),
                'brain_orden': values.get('brain_orden'),
                'brain_mrc': values.get('brain_mrc'),
                'tipo_cliente_id': values.get('tipo_cliente_id'),
                'tipo_activacion_id': values.get('tipo_activacion_id'),
                'description': values.get('description'),
                'brain_province': values.get('brain_province'),
            }

            # Archivo adjunto opcional (base64)
            if values.get('adoption_form'):
                try:
                    lead_vals['adoption_form'] = base64.b64decode(values['adoption_form'])
                except Exception:
                    return self._brain_response({'error': 'El campo "adoption_form" debe estar en base64 válido.'}, 400)

            # Actualizar el lead
            lead.write(lead_vals)

            # Preparar respuesta
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
                'address': lead.address or None,
                'industry_id': lead.industry.id if lead.industry else None,
                'industry_name': lead.industry.name if lead.industry else None,
                'coordinador_id': lead.brain_coordinador.id if lead.brain_coordinador else None,
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
                'brain_province': lead.brain_province if lead.brain_province else None
            }

            return self._brain_response({'status': 'success', 'lead': lead_data}, 200)

        except Exception as e:
            error_msg = traceback.format_exc()
            return self._brain_response({'error': f'Error al actualizar el lead: {str(e)}', 'debug': error_msg}, 500)


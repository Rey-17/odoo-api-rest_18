from odoo.http import request, route, Response
from .auth_contoller import AuthController
import base64
from io import BytesIO

class AttachmentAPI(AuthController):

    @route('/api/attachments/<int:attachment_id>/file', type='http', auth='none', methods=['GET'], csrf=False)
    def serve_attachment_file(self, attachment_id, **kwargs):
        # Validación de token (puedes dejarlo "public" si no necesitas restricción)
        check, result = self._check_access('ir.attachment')
        if not check:
            return result

        env = result
        attachment = env['ir.attachment'].sudo().browse(attachment_id)

        if not attachment.exists():
            return self._brain_response({"error": "Archivo no encontrado"}, 404)

        if not attachment.datas:
            return self._brain_response({"error": "El archivo no tiene contenido"}, 404)

        # Decodificar el contenido y devolverlo como stream
        file_data = base64.b64decode(attachment.datas)
        mimetype = attachment.mimetype or 'application/octet-stream'

        return Response(
            BytesIO(file_data),
            mimetype=mimetype,
            headers={
                'Content-Disposition': f'inline; filename="{attachment.name}"'
            },
            direct_passthrough=True
        )

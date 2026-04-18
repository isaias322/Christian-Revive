from odoo import fields, models, api
from odoo.exceptions import UserError
import base64
import io

class Book(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'sequence, date desc'

    sequence    = fields.Integer(string='Sequence')
    name        = fields.Char(string='Title', required=True)
    author      = fields.Char(string='Author')
    date        = fields.Date(string='Published Date')
    description = fields.Text(string='Description')
    content     = fields.Html(string='Content')
    image       = fields.Binary(string='Cover Image')
    pdf_file    = fields.Binary(string='PDF File')
    pdf_filename = fields.Char(string='PDF Filename')
    is_published = fields.Boolean(string='Published', default=True)
    language    = fields.Selection([
        ('english', 'English'),
        ('urdu', 'Urdu'),
    ], string='Language', default='english', required=True)
    category    = fields.Selection([
        ('bible_study', 'Bible Study'),
        ('devotional', 'Devotional'),
        ('theology', 'Theology'),
        ('history', 'History'),
        ('youth', 'Youth'),
        ('other', 'Other'),
    ], string='Category', default='other')

    # ── NEW FIELD ──────────────────────────────────────────────
    pdf_text = fields.Text(string='PDF Extracted Text', readonly=True)

    # ── NEW METHOD ─────────────────────────────────────────────
    def action_extract_pdf_text(self):
        try:
            import PyPDF2
        except ImportError:
            raise UserError("PyPDF2 not installed. Run: pip install PyPDF2")

        for record in self:
            if not record.pdf_file:
                raise UserError("Please upload a PDF file first.")
            try:
                pdf_bytes  = base64.b64decode(record.pdf_file)
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
                text_parts = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text.strip())
                record.pdf_text = '\n\n'.join(text_parts)
            except Exception as e:
                raise UserError(f"Failed to extract PDF text: {e}") 
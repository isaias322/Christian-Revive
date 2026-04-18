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
    pdf_text = fields.Html(string='PDF Text (Editable)', sanitize=False)

    # ── NEW METHOD ─────────────────────────────────────────────
    def action_extract_pdf_text(self):
        try:
            import pdfplumber
        except ImportError:
            raise UserError("pdfplumber not installed. Run: pip install pdfplumber")

        for record in self:
            if not record.pdf_file:
                raise UserError("Please upload a PDF file first.")
            try:
                import io as _io
                pdf_bytes = base64.b64decode(record.pdf_file)
                html_parts = []

                with pdfplumber.open(_io.BytesIO(pdf_bytes)) as pdf:
                    for page_num, page in enumerate(pdf.pages, start=1):
                        
                        # ── Extract words with positions ──────────────
                        words = page.extract_words(
                            x_tolerance=3,
                            y_tolerance=3,
                            keep_blank_chars=False,
                            use_text_flow=True,
                        )

                        if not words:
                            continue

                        # ── Group words into lines by y-position ──────
                        lines = []
                        current_line = []
                        current_y = None
                        y_tolerance = 5  # pixels tolerance for same line

                        for word in words:
                            word_y = round(word['top'])
                            if current_y is None:
                                current_y = word_y

                            if abs(word_y - current_y) <= y_tolerance:
                                current_line.append(word)
                            else:
                                if current_line:
                                    lines.append(current_line)
                                current_line = [word]
                                current_y = word_y

                        if current_line:
                            lines.append(current_line)

                        # ── Detect headings vs paragraphs ─────────────
                        # Get average font size for the page
                        all_sizes = []
                        try:
                            for char in page.chars:
                                if char.get('size'):
                                    all_sizes.append(char['size'])
                        except Exception:
                            pass

                        avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 12

                        # ── Build HTML from lines ─────────────────────
                        prev_was_blank = False
                        paragraph_words = []

                        for line in lines:
                            line_text = ' '.join(w['text'] for w in line).strip()
                            if not line_text:
                                if paragraph_words:
                                    html_parts.append(
                                        f'<p>{"  ".join(paragraph_words)}</p>')
                                    paragraph_words = []
                                prev_was_blank = True
                                continue

                            # Detect heading: short line + larger font
                            is_heading = False
                            try:
                                line_chars = [
                                    c for c in page.chars
                                    if line[0]['x0'] <= c['x0'] <= line[-1]['x1']
                                    and abs(c['top'] - line[0]['top']) <= y_tolerance
                                ]
                                if line_chars:
                                    line_size = sum(
                                        c['size'] for c in line_chars
                                        if c.get('size')
                                    ) / len(line_chars)
                                    # Heading if significantly larger than average
                                    is_heading = (
                                        line_size > avg_size * 1.2
                                        and len(line_text.split()) <= 12
                                    )
                            except Exception:
                                pass

                            if is_heading:
                                # Flush current paragraph first
                                if paragraph_words:
                                    html_parts.append(
                                        f'<p>{" ".join(paragraph_words)}</p>')
                                    paragraph_words = []
                                html_parts.append(f'<h3>{line_text}</h3>')
                            else:
                                # Check if this line ends a paragraph
                                # (short line = likely end of paragraph)
                                page_width = page.width
                                line_width = line[-1]['x1'] - line[0]['x0']
                                is_end_of_para = line_width < page_width * 0.6

                                paragraph_words.append(line_text)

                                if is_end_of_para or prev_was_blank:
                                    html_parts.append(
                                        f'<p>{" ".join(paragraph_words)}</p>')
                                    paragraph_words = []

                            prev_was_blank = False

                        # Flush remaining paragraph words
                        if paragraph_words:
                            html_parts.append(
                                f'<p>{" ".join(paragraph_words)}</p>')

                        # Page separator (except last page)
                        if page_num < len(pdf.pages):
                            html_parts.append(
                                f'<hr/><p style="color:gray;font-size:12px;">'
                                f'— Page {page_num} —</p>')

                record.pdf_text = '\n'.join(html_parts)

            except Exception as e:
                raise UserError(f"Failed to extract PDF text: {e}")
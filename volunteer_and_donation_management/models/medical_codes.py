from odoo import models, fields, api


class ICD10Code(models.Model):
    _name = 'medical.icd10'
    _description = 'ICD-10 Diagnosis Codes'
    _order = 'code'
    _rec_name = 'display_name'

    code = fields.Char(string='ICD-10 Code', required=True, index=True)
    name = fields.Char(string='Description', required=True)
    category = fields.Char(string='Category', index=True)
    chapter = fields.Char(string='Chapter')
    is_active = fields.Boolean(string='Active', default=True)
    display_name = fields.Char(
        string='Display', compute='_compute_display', store=True)

    @api.depends('code', 'name')
    def _compute_display(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name

    def app_search(self, query='', limit=20):
        """Search ICD-10 codes from Flutter app"""
        domain = [('is_active', '=', True)]
        if query:
            domain = [
                ('is_active', '=', True),
                '|', '|',
                ('code', 'ilike', query),
                ('name', 'ilike', query),
                ('category', 'ilike', query),
            ]
        records = self.sudo().search_read(
            domain,
            fields=['id', 'code', 'name', 'category', 'chapter'],
            limit=limit,
            order='code',
        )
        return records


class CPTCode(models.Model):
    _name = 'medical.cpt'
    _description = 'CPT Procedure Codes'
    _order = 'code'
    _rec_name = 'display_name'

    code = fields.Char(string='CPT Code', required=True, index=True)
    name = fields.Char(string='Description', required=True)
    category = fields.Char(string='Category', index=True)
    section = fields.Char(string='Section')
    is_active = fields.Boolean(string='Active', default=True)
    display_name = fields.Char(
        string='Display', compute='_compute_display', store=True)

    @api.depends('code', 'name')
    def _compute_display(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name

    def app_search(self, query='', limit=20):
        """Search CPT codes from Flutter app"""
        domain = [('is_active', '=', True)]
        if query:
            domain = [
                ('is_active', '=', True),
                '|', '|',
                ('code', 'ilike', query),
                ('name', 'ilike', query),
                ('category', 'ilike', query),
            ]
        return self.sudo().search_read(
            domain,
            fields=['id', 'code', 'name', 'category', 'section'],
            limit=limit,
            order='code',
        )


class SnomedConcept(models.Model):
    _name = 'medical.snomed'
    _description = 'SNOMED-CT Clinical Terms'
    _order = 'code'
    _rec_name = 'display_name'

    code = fields.Char(string='SNOMED-CT Code', required=True, index=True)
    name = fields.Char(string='Term', required=True)
    semantic_type = fields.Char(string='Semantic Type', index=True)
    is_active = fields.Boolean(string='Active', default=True)
    display_name = fields.Char(
        string='Display', compute='_compute_display', store=True)

    @api.depends('code', 'name')
    def _compute_display(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name

    def app_search(self, query='', limit=20):
        """Search SNOMED-CT from Flutter app"""
        domain = [('is_active', '=', True)]
        if query:
            domain = [
                ('is_active', '=', True),
                '|', '|',
                ('code', 'ilike', query),
                ('name', 'ilike', query),
                ('semantic_type', 'ilike', query),
            ]
        return self.sudo().search_read(
            domain,
            fields=['id', 'code', 'name', 'semantic_type'],
            limit=limit,
            order='code',
        )


class RxNormDrug(models.Model):
    _name = 'medical.rxnorm'
    _description = 'RxNorm Drug Codes'
    _order = 'name'
    _rec_name = 'display_name'

    rxcui = fields.Char(string='RxCUI', required=True, index=True)
    name = fields.Char(string='Drug Name', required=True)
    generic_name = fields.Char(string='Generic Name', index=True)
    dose_form = fields.Char(string='Dose Form')
    strength = fields.Char(string='Strength')
    route = fields.Char(string='Route')
    drug_class = fields.Char(string='Drug Class', index=True)
    is_active = fields.Boolean(string='Active', default=True)
    display_name = fields.Char(
        string='Display', compute='_compute_display', store=True)

    @api.depends('rxcui', 'name', 'strength')
    def _compute_display(self):
        for rec in self:
            parts = [f"[{rec.rxcui}]", rec.name or '']
            if rec.strength:
                parts.append(rec.strength)
            rec.display_name = ' '.join(parts)

    def app_search(self, query='', limit=20):
        """Search RxNorm drugs from Flutter app"""
        domain = [('is_active', '=', True)]
        if query:
            domain = [
                ('is_active', '=', True),
                '|', '|', '|',
                ('rxcui', 'ilike', query),
                ('name', 'ilike', query),
                ('generic_name', 'ilike', query),
                ('drug_class', 'ilike', query),
            ]
        return self.sudo().search_read(
            domain,
            fields=['id', 'rxcui', 'name', 'generic_name',
                    'dose_form', 'strength', 'route', 'drug_class'],
            limit=limit,
            order='name',
        )


# ─────────────────────────────────────────────────────────────
# PRESCRIPTION LINE — links patient to RxNorm drugs
# ─────────────────────────────────────────────────────────────
class PrescriptionLine(models.Model):
    _name = 'medical.prescription.line'
    _description = 'Prescription Line'
    _order = 'sequence, id'

    patient_id = fields.Many2one('patients', string='Patient',
                                  required=True, ondelete='cascade')
    drug_id = fields.Many2one('medical.rxnorm', string='Drug (RxNorm)')
    drug_name = fields.Char(string='Drug Name')
    snomed_id = fields.Many2one('medical.snomed',
                                 string='Indication (SNOMED-CT)')
    dosage = fields.Char(string='Dosage')
    frequency = fields.Char(string='Frequency')
    duration = fields.Char(string='Duration')
    route = fields.Char(string='Route')
    instructions = fields.Text(string='Instructions')
    quantity = fields.Integer(string='Qty', default=1)
    sequence = fields.Integer(string='Sequence', default=10)


# ─────────────────────────────────────────────────────────────
# DIAGNOSIS LINE — links patient to ICD-10 codes
# ─────────────────────────────────────────────────────────────
class DiagnosisLine(models.Model):
    _name = 'medical.diagnosis.line'
    _description = 'Diagnosis Line'
    _order = 'sequence, id'

    patient_id = fields.Many2one('patients', string='Patient',
                                  required=True, ondelete='cascade')
    icd10_id = fields.Many2one('medical.icd10', string='ICD-10 Code')
    icd10_code = fields.Char(related='icd10_id.code', store=True)
    description = fields.Char(string='Description')
    diagnosis_type = fields.Selection([
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('admitting', 'Admitting'),
    ], string='Type', default='primary')
    notes = fields.Text(string='Notes')
    sequence = fields.Integer(string='Sequence', default=10)


# ─────────────────────────────────────────────────────────────
# PROCEDURE LINE — links patient to CPT codes
# ─────────────────────────────────────────────────────────────
class ProcedureLine(models.Model):
    _name = 'medical.procedure.line'
    _description = 'Procedure Line'
    _order = 'sequence, id'

    patient_id = fields.Many2one('patients', string='Patient',
                                  required=True, ondelete='cascade')
    cpt_id = fields.Many2one('medical.cpt', string='CPT Code')
    cpt_code = fields.Char(related='cpt_id.code', store=True)
    description = fields.Char(string='Description')
    notes = fields.Text(string='Notes')
    sequence = fields.Integer(string='Sequence', default=10)
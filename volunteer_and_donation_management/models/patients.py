from odoo import models, fields, api

class Patients(models.Model):
    _name = "patients"
    _description = "Patients"

    name = fields.Char(string="Name", required=True)
    age = fields.Integer(string="Age")
    cnic = fields.Char(string="CNIC")
    dependent = fields.Integer(string="Dependent")
    image = fields.Binary(string="Photo")

    # ── Health Seeker ID & Contact ────────────────────
    health_seeker_id = fields.Char(
        string='Health Seeker ID', readonly=True, copy=False, index=True,
        default=lambda self: 'New')
    phone = fields.Char(string='Phone / Mobile', index=True)
    nic = fields.Char(string='NIC / CNIC', index=True)
    email = fields.Char(string='Email')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
        ('o+', 'O+'), ('o-', 'O-'),
    ], string='Blood Group')
    address = fields.Text(string='Address')
    emergency_contact = fields.Char(string='Emergency Contact')
    emergency_contact_name = fields.Char(string='Emergency Contact Name')

    # ── Status ───────────────────────────────────────
    status = fields.Selection([
        ('waiting','Waiting'),
        ('in_review','In Review'),
        ('treated','Treated'),
        ('follow_up','Follow-up Needed'),
    ], string='Status', default='waiting')

    # ── Medical Fields ────────────────────────────────
    sickness = fields.Text(string='Sickness / Symptoms')
    diagnosis = fields.Text(string='Doctor Diagnosis')
    prescription = fields.Text(string='Prescription / Medicines')
    notes = fields.Text(string='Additional Notes')

    # ── Staff Assignment ──────────────────────────────
    assigned_doctor = fields.Many2one(
        'hr.employee',
        domain=[('staff_role', '=', 'doctor')],
        string='Assigned Doctor'
    )
    assigned_nurse = fields.Many2one(
        'hr.employee',
        domain=[('staff_role', '=', 'nurse')],
        string='Assigned Nurse'
    )

    # ── Dates ─────────────────────────────────────────
    treatment_date = fields.Date(
        string='Treatment Date', default=fields.Date.today)
    follow_up_date = fields.Date(string='Follow-up Date')

    # ── Project ───────────────────────────────────────
    project_id = fields.Many2one('app.project', string='Project')

    # ════════════════════════════════════════════════
    # GENERAL INFO (Tab 1)
    # ════════════════════════════════════════════════
    consultation_room = fields.Char(string='Consultation Room (Cabin)')
    diseases = fields.Char(string='Diseases')
    responsible_jr_doctor = fields.Char(string='Responsible Jr. Doctor')
    urgency_level = fields.Selection([
        ('normal',    'Normal'),
        ('urgent',    'Urgent'),
        ('emergency', 'Emergency'),
    ], string='Urgency Level', default='normal')
    purpose = fields.Selection([
        ('consultation', 'Consultation'),
        ('follow_up',    'Follow-up'),
        ('emergency',    'Emergency'),
        ('checkup',      'Check-up'),
    ], string='Purpose', default='consultation')
    is_video_call = fields.Boolean(string='Is Video Call')
    outside_appointment = fields.Boolean(string='Outside Appointment')
    chief_complaints = fields.Text(string='Chief Complaints')
    history_of_present_illness = fields.Text(
        string='History of Present Illness')
    past_history = fields.Text(string='Past History')
    general_notes = fields.Text(string='General Notes')

    # ════════════════════════════════════════════════
    # VITAL SIGNS & SYMPTOMS (Tab 2)
    # ════════════════════════════════════════════════
    hr_temperature = fields.Float(string='HR Temperature (°C)')
    bmi = fields.Float(string='BMI', compute='_compute_bmi', store=True)
    weight = fields.Float(string='Weight (kg)')
    height = fields.Float(string='Height (cm)')
    bmi_state = fields.Selection([
        ('underweight', 'Underweight'),
        ('normal',      'Normal'),
        ('overweight',  'Overweight'),
        ('obese',       'Obese'),
    ], string='BMI State', compute='_compute_bmi', store=True)
    rr = fields.Integer(string='RR (bpm)')
    systolic_bp = fields.Integer(string='Systolic BP (mmHg)')
    diastolic_bp = fields.Integer(string='Diastolic BP (mmHg)')
    spo2 = fields.Integer(string='SpO2 (%)')
    rbs = fields.Float(string='RBS (mg/dL)')
    pain_level = fields.Text(string='Pain Level')
    laboratory = fields.Text(string='Laboratory Report')
    lab_image = fields.Binary(string='Lab Report Image')
    lab_pdf = fields.Binary(string='Lab Report PDF')
    lab_pdf_filename = fields.Char(string='Lab PDF Filename')
    radiological = fields.Text(string='Radiological Report')
    vital_notes = fields.Text(string='Vital Notes')

    # ════════════════════════════════════════════════
    # CLINICAL ASSESSMENT (Tab 3)
    # ════════════════════════════════════════════════
    head_neck = fields.Text(string='Head & Neck')
    ent = fields.Text(string='ENT')
    eye = fields.Text(string='Eye')
    chest_heart = fields.Text(string='Chest & Heart')
    git = fields.Text(string='GIT')
    surgery = fields.Text(string='Surgery')
    urinary_gynecology = fields.Text(string='Urinary & Gynecology')
    orthopedic_neuro = fields.Text(string='Orthopedic & Neuro')
    mouth = fields.Text(string='Mouth')
    skin = fields.Text(string='Skin')
    miscellaneous = fields.Text(string='Miscellaneous')
    mental_status = fields.Text(string='Mental Status')

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for rec in self:
            if rec.height and rec.height > 0:
                h_m = rec.height / 100
                rec.bmi = round(rec.weight / (h_m * h_m), 1)
                if rec.bmi < 18.5:
                    rec.bmi_state = 'underweight'
                elif rec.bmi < 25:
                    rec.bmi_state = 'normal'
                elif rec.bmi < 30:
                    rec.bmi_state = 'overweight'
                else:
                    rec.bmi_state = 'obese'
            else:
                rec.bmi = 0
                rec.bmi_state = 'normal'

    # ════════════════════════════════════════════════════
    # STRUCTURED DIAGNOSIS & PROCEDURES (new fields)
    # ════════════════════════════════════════════════════

    # One2many lines
    diagnosis_line_ids = fields.One2many(
        'medical.diagnosis.line', 'patient_id',
        string='Diagnoses (ICD-10)')
    procedure_line_ids = fields.One2many(
        'medical.procedure.line', 'patient_id',
        string='Procedures (CPT)')
    prescription_line_ids = fields.One2many(
        'medical.prescription.line', 'patient_id',
        string='Prescriptions (RxNorm)')

    # Primary diagnosis shortcut
    primary_icd10_id = fields.Many2one(
        'medical.icd10', string='Primary Diagnosis (ICD-10)')
    primary_icd10_code = fields.Char(
        related='primary_icd10_id.code', string='ICD-10 Code', store=True)
    


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('health_seeker_id', 'New') == 'New':
                vals['health_seeker_id'] = self.env['ir.sequence'].next_by_code(
                    'patients.health.seeker') or 'New'
        return super().create(vals_list)
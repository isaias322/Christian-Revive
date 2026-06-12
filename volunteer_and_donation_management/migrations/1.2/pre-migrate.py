def migrate(cr, version):
    """music.track.genre is changing from Selection to Char.

    Remove the old selection-option records (and their xmlids) before the
    registry reloads, otherwise Odoo's end-of-upgrade cleanup tries to read
    an `ondelete` policy from a field that is no longer a Selection and
    crashes with AttributeError: 'Char' object has no attribute 'ondelete'.
    """
    cr.execute("""
        SELECT id FROM ir_model_fields
        WHERE model = 'music.track' AND name = 'genre'
    """)
    row = cr.fetchone()
    if not row:
        return
    field_id = row[0]

    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'ir.model.fields.selection'
          AND res_id IN (
              SELECT id FROM ir_model_fields_selection WHERE field_id = %s
          )
    """, (field_id,))

    cr.execute("""
        DELETE FROM ir_model_fields_selection WHERE field_id = %s
    """, (field_id,))

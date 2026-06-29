# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Remove duplicate reviews before Odoo validates SQL constraints."""
    cr.execute("""
        DELETE FROM lifestyle_product_review review
        USING (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY product_tmpl_id, partner_id
                       ORDER BY write_date DESC NULLS LAST,
                                create_date DESC NULLS LAST,
                                id DESC
                   ) AS duplicate_rank
              FROM lifestyle_product_review
        ) ranked
        WHERE review.id = ranked.id
          AND ranked.duplicate_rank > 1
    """)

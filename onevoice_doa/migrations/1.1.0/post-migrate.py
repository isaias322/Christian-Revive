def migrate(cr, version):
    # Drop the old global unique constraint on chapter_number so chapters from
    # different books can share the same chapter number (1, 2, 3, ...).
    # The new constraint is unique(book_id, chapter_number).
    cr.execute("""
        ALTER TABLE onevoice_doa_chapter
        DROP CONSTRAINT IF EXISTS onevoice_doa_chapter_chapter_number_uniq
    """)

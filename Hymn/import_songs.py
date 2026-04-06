#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════
IMPORT EXISTING JSON SONGS INTO ODOO
═══════════════════════════════════════════════════════════

Run this ONCE after installing the hymn_management module.
It creates the two collections and imports all your existing
songs from geet_zaboor.json.

HOW TO RUN:
───────────
Option A — From Odoo shell (recommended):
    docker exec -it odoo19_christian_revive bash
    odoo shell -d christian_revive
    >>> exec(open('/mnt/custom_addons/hymn_management/import_songs.py').read())

Option B — From a scheduled action in Odoo:
    Create a server action → Execute Python Code → paste this script.

Option C — From the Python console:
    Copy the JSON content into the script below.
"""

import json

# ═══════════════════════════════════════════════════════════
# STEP 1: Create Collections (if they don't exist)
# ═══════════════════════════════════════════════════════════

Collection = env['hymn.collection']
Song = env['hymn.song']
Category = env['hymn.category']

# — Hymns Book (English) —
hymns_col = Collection.search([('code', '=', 'hymns')], limit=1)
if not hymns_col:
    hymns_col = Collection.create({
        'name': 'Hymns Book',
        'code': 'hymns',
        'description': 'Traditional and contemporary Christian hymns for worship and devotion.',
        'language': 'english',
        'color': '#4A3728',
        'is_published': True,
        'sequence': 1,
    })
    print(f'✅ Created collection: Hymns Book (id={hymns_col.id})')
else:
    print(f'ℹ️  Hymns Book already exists (id={hymns_col.id})')

# — Geet & Zaboor (Urdu) —
geet_col = Collection.search([('code', '=', 'geet_zaboor')], limit=1)
if not geet_col:
    geet_col = Collection.create({
        'name': 'گیت و زبور',
        'code': 'geet_zaboor',
        'description': 'اردو عبادت کے گیت اور زبور — اردو اور رومن اردو کے ساتھ۔',
        'language': 'urdu',
        'color': '#1565C0',
        'is_published': True,
        'sequence': 2,
    })
    print(f'✅ Created collection: گیت و زبور (id={geet_col.id})')
else:
    print(f'ℹ️  گیت و زبور already exists (id={geet_col.id})')

# ═══════════════════════════════════════════════════════════
# STEP 2: Import Geet & Zaboor songs from JSON
# ═══════════════════════════════════════════════════════════

# Paste your geet_zaboor.json content here, or load from file:
# With file:
#   with open('/mnt/custom_addons/hymn_management/data/geet_zaboor.json', 'r') as f:
#       songs_data = json.load(f)

# Or paste inline (the 30 songs from your JSON):
songs_data = []  # ← Replace with your JSON array or load from file

try:
    with open('/mnt/custom_addons/hymn_management/data/geet_zaboor.json', 'r', encoding='utf-8') as f:
        songs_data = json.load(f)
    print(f'📂 Loaded {len(songs_data)} songs from geet_zaboor.json')
except FileNotFoundError:
    print('⚠️  geet_zaboor.json not found — place it in data/ folder')
    print('   Or paste the JSON array into this script directly.')

if songs_data:
    result = Song.import_from_json('geet_zaboor', songs_data)
    print(f'✅ Imported {result["created"]} of {result["total"]} songs into گیت و زبور')

# ═══════════════════════════════════════════════════════════
# STEP 3: Import Hymns Book songs (if you have hymns.json)
# ═══════════════════════════════════════════════════════════

try:
    with open('/mnt/custom_addons/hymn_management/data/hymns.json', 'r', encoding='utf-8') as f:
        hymns_data = json.load(f)
    print(f'📂 Loaded {len(hymns_data)} songs from hymns.json')
    result = Song.import_from_json('hymns', hymns_data)
    print(f'✅ Imported {result["created"]} of {result["total"]} songs into Hymns Book')
except FileNotFoundError:
    print('ℹ️  hymns.json not found — skipping Hymns Book import')

# ═══════════════════════════════════════════════════════════
# STEP 4: Commit
# ═══════════════════════════════════════════════════════════

env.cr.commit()
print('\n🎵 Import complete! Check Hymns & Songs menu in Odoo.')
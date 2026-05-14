from odoo import models, fields, api
from datetime import date as date_type

_PLAN = [
    (1,  '2027-07-23', 'Faithfulness',      'Faithful in a Foreign Land',
     'Daniel 1',
     'Pray for believers who must stand firm in environments hostile to faith.',
     "Daniel 1 — Daniel's Resolve"),
    (2,  '2027-07-24', 'Revelation',        'God Who Reveals Mysteries',
     'Daniel 2',
     'Ask God for wisdom to understand the times we live in.',
     'Daniel 2 — The Dream of Four Kingdoms'),
    (3,  '2027-07-25', 'Courage',           'Standing Firm in the Fire',
     'Daniel 3',
     'Pray for courage for persecuted believers in hostile nations.',
     "Daniel 3 — The Fiery Furnace"),
    (4,  '2027-07-26', 'Humility',          'Humility Before the Most High',
     'Daniel 4',
     'Pray for national leaders to acknowledge the sovereignty of God.',
     "Daniel 4 — Nebuchadnezzar's Humbling"),
    (5,  '2027-07-27', 'Accountability',    'The Writing on the Wall',
     'Daniel 5',
     'Pray for holy reverence for God to sweep through our generation.',
     "Daniel 5 — Belshazzar's Feast"),
    (6,  '2027-07-28', 'Trust',             'Unshaken Trust',
     'Daniel 6',
     'Pray for steadfastness in prayer despite opposition and distraction.',
     "Daniel 6 — Daniel in the Lions' Den"),
    (7,  '2027-07-29', 'Kingdom',           'The Ancient of Days Reigns',
     'Daniel 7',
     "Declare: God's Kingdom is advancing. Pray for it to come in your city.",
     'Daniel 7 — Vision of the Four Beasts'),
    (8,  '2027-07-30', 'Discernment',       'Visions of Things to Come',
     'Daniel 8',
     'Pray for prophetic discernment and clarity in the Church.',
     'Daniel 8 — The Ram and the Goat'),
    (9,  '2027-07-31', 'Intercession',      'The Prayer of Intercession',
     'Daniel 9',
     'Pray a prayer of corporate repentance on behalf of your nation.',
     "Daniel 9 — Daniel's Great Prayer"),
    (10, '2027-08-01', 'Warfare',           'Warfare in the Heavenlies',
     'Daniel 10',
     'Pray for breakthrough in the spiritual realm over unreached nations.',
     'Daniel 10 — The Heavenly Messenger'),
    (11, '2027-08-02', 'Endurance',         'Perseverance in Great Conflict',
     'Daniel 11',
     'Pray for endurance for those facing long-term persecution.',
     'Daniel 11 — The Coming Conflicts'),
    (12, '2027-08-03', 'Hope',              'The Promise of Resurrection',
     'Daniel 12',
     'Pray for the lost — that they would receive eternal life.',
     'Daniel 12 — The Time of the End'),
    (13, '2027-08-04', 'Worship',           'Behold the Risen Christ',
     'Revelation 1',
     'Spend time in pure worship — Jesus is the First and the Last.',
     "Revelation 1 — John's Vision of Christ"),
    (14, '2027-08-05', 'First Love',        'Return to Your First Love',
     'Revelation 2:1-17',
     'Pray for the Church to rediscover its passion for Jesus.',
     'Revelation 2:1-17 — Letters to Ephesus, Smyrna & Pergamum'),
    (15, '2027-08-06', 'Holiness',          'Hold Fast What You Have',
     'Revelation 2:18-29',
     'Pray for holiness and faithfulness in the global Church.',
     'Revelation 2:18-29 — Letter to Thyatira'),
    (16, '2027-08-07', 'Awakening',         'To the Overcomers',
     'Revelation 3',
     'Pray for spiritually lukewarm churches to awaken with fresh fire.',
     'Revelation 3 — Letters to Sardis, Philadelphia & Laodicea'),
    (17, '2027-08-08', 'Adoration',         'Holy, Holy, Holy',
     'Revelation 4',
     'Worship God for who He is — not just what He does.',
     'Revelation 4 — The Throne Room of Heaven'),
    (18, '2027-08-09', 'Salvation',         'The Worthy Lamb Has Triumphed',
     'Revelation 5',
     'Pray for Muslims, Hindus and Buddhists to encounter the Lamb of God.',
     'Revelation 5 — The Scroll and the Worthy Lamb'),
    (19, '2027-08-10', 'Peace',             'Seals of the End Times',
     'Revelation 6',
     'Pray for peace and the gospel to advance in war-torn nations.',
     'Revelation 6 — The Six Seals'),
    (20, '2027-08-11', 'Harvest',           'A Multitude from Every Nation',
     'Revelation 7',
     'Pray the fulfilment of Rev 7:9 — every tribe, tongue and nation.',
     'Revelation 7 — The 144,000 and the Great Multitude'),
    (21, '2027-08-12', 'Awakening',         'The Trumpets Sound',
     'Revelation 8-9',
     'Pray for spiritual awakening like a trumpet blast over your city.',
     'Revelation 8-9 — The First Six Trumpets'),
    (22, '2027-08-13', 'Witness',           'Arise, Bold Witnesses',
     'Revelation 10-11',
     'Pray for bold witnesses like Elijah to arise in every nation.',
     'Revelation 10-11 — The Two Witnesses'),
    (23, '2027-08-14', 'Victory',           'The Dragon Is Defeated',
     'Revelation 12',
     'Plead the blood of Jesus over your family and community.',
     'Revelation 12 — The Woman and the Dragon'),
    (24, '2027-08-15', 'Steadfastness',     'Steadfast Under Pressure',
     'Revelation 13',
     'Pray for Christians in countries where faith is criminalised.',
     'Revelation 13 — The Two Beasts'),
    (25, '2027-08-16', 'Mission',           'The Eternal Gospel Goes Forth',
     'Revelation 14',
     'Pray for missionaries and evangelists in the 10/40 Window.',
     'Revelation 14 — The Lamb and the 144,000'),
    (26, '2027-08-17', 'Justice',           "Justice and God's Wrath",
     'Revelation 15-16',
     'Pray for nations to turn to God in repentance before judgment.',
     'Revelation 15-16 — The Seven Bowls of Wrath'),
    (27, '2027-08-18', 'Freedom',           'Come Out of Babylon',
     'Revelation 17',
     'Pray for believers entangled in worldly systems to be set free.',
     'Revelation 17 — Babylon the Great'),
    (28, '2027-08-19', 'Purity',            'The Fall of Babylon',
     'Revelation 18',
     'Pray for the Church to be free from materialism and compromise.',
     'Revelation 18 — Come Out of Her, My People'),
    (29, '2027-08-20', 'Triumph',           'Hallelujah! The Lord Reigns',
     'Revelation 19',
     'Declare boldly: the Kingdom of God is advancing over the nations!',
     'Revelation 19 — The Rider on the White Horse'),
    (30, '2027-08-21', 'Eternity',          'The Judgment Is His Alone',
     'Revelation 20',
     'Pray urgently for souls to be saved before the final hour.',
     'Revelation 20 — The Thousand Years & Final Judgment'),
    (31, '2027-08-22', 'Renewal',           'Behold, All Things New',
     'Revelation 21:1-14',
     'Pray for revival that transforms communities like a new creation.',
     'Revelation 21:1-14 — The New Heaven and New Earth'),
    (32, '2027-08-23', 'Glory',             'The Glory of New Jerusalem',
     'Revelation 21:15-27',
     "Pray that God's glory would fill your city as it fills New Jerusalem.",
     'Revelation 21:15-27 — The Dimensions of the Holy City'),
    (33, '2027-08-24', 'Return',            'Come, Lord Jesus',
     'Revelation 22:1-17',
     'Pray the ancient cry: Maranatha — Come, Lord Jesus!',
     "Revelation 22:1-17 — The River of Life & The Spirit Says Come"),
    (34, '2027-08-25', 'Reflection',        'Faithfulness Through the Ages',
     'Daniel 1-3',
     "Reflect on faithfulness, courage and God's sovereignty in Daniel 1-3.",
     'Daniel 1-3 — A Review of Faithful Courage'),
    (35, '2027-08-26', 'Persecuted Church', 'Pray for the Persecuted',
     'Revelation 6:9-11',
     'Pray by name for believers in North Korea, Iran, Nigeria and Pakistan.',
     "Revelation 6:9-11 — The Souls Under the Altar"),
    (36, '2027-08-27', 'Revival',           'Pray for Global Revival',
     'Daniel 9:17-19',
     'Pray for the Holy Spirit to fall on 10 unreached nations today.',
     "Daniel 9:17-19 — Daniel's Cry for Revival"),
    (37, '2027-08-28', 'Muslim Nations',    'Pray for the Muslim World',
     'Revelation 7:9-14',
     'Pray for Muslims in Pakistan, the Middle East and North Africa.',
     'Revelation 7:9-14 — A Multitude from Every Nation'),
    (38, '2027-08-29', 'Youth & Families',  'Raise Up a Generation',
     'Daniel 1:8-21',
     'Pray for young people and families to encounter God personally.',
     "Daniel 1:8-21 — Daniel's Resolve as a Young Man"),
    (39, '2027-08-30', 'Israel & Nations',  'Until All Have Heard',
     'Revelation 22:1-5',
     "Pray for Israel's salvation and completion of the Great Commission.",
     "Revelation 22:1-5 — The River of Life for All Nations"),
    (40, '2027-08-31', 'Celebration',       'One Voice, One Hope',
     'Revelation 22:20',
     'Gather with others to pray, worship and celebrate 40 days of faithfulness.',
     'Revelation 22:20 — Surely I am coming soon. Amen. Come, Lord Jesus!'),
]


class OnevoiceDevotional(models.Model):
    _name = 'onevoice.devotional'
    _description = '40-Day Devotional Schedule'
    _order = 'day_number asc'

    day_number      = fields.Integer(string='Day', required=True)
    date            = fields.Date(string='Date', required=True)
    theme           = fields.Char(string='Theme')
    title           = fields.Char(string='Title')
    reference       = fields.Char(string='Scripture Reference')
    morning_prayer  = fields.Text(string='Morning Prayer Prompt')
    evening_reading = fields.Text(string='Evening Reading')
    days_from_now   = fields.Integer(
        string='Days Away', compute='_compute_days_from_now', store=False)

    @api.depends('date')
    def _compute_days_from_now(self):
        today = date_type.today()
        for rec in self:
            rec.days_from_now = (rec.date - today).days if rec.date else 0

    @api.model
    def app_get_devotional_plan(self):
        """Return all 40 days for the Flutter app. Falls back to _PLAN if no records exist."""
        records = self.sudo().search([], order='day_number asc')
        if records:
            return [
                {
                    'day':       r.day_number,
                    'date':      str(r.date),
                    'theme':     r.theme or '',
                    'title':     r.title or '',
                    'reference': r.reference or '',
                    'morning':   r.morning_prayer or '',
                    'evening':   r.evening_reading or '',
                }
                for r in records
            ]
        return [
            {
                'day': d, 'date': dt, 'theme': theme, 'title': title,
                'reference': ref, 'morning': morning, 'evening': evening,
            }
            for d, dt, theme, title, ref, morning, evening in _PLAN
        ]

    @api.model
    def action_generate_plan(self):
        """Seed all 40 days. Skips days that already exist."""
        existing = set(self.search([]).mapped('day_number'))
        to_create = [
            {
                'day_number': d, 'date': dt, 'theme': theme,
                'title': title, 'reference': ref,
                'morning_prayer': morning, 'evening_reading': evening,
            }
            for d, dt, theme, title, ref, morning, evening in _PLAN
            if d not in existing
        ]
        if to_create:
            self.create(to_create)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '40-Day Plan Ready',
                'message': f'{len(to_create)} day(s) created.' if to_create else 'All 40 days already exist.',
                'type': 'success',
                'sticky': False,
            },
        }

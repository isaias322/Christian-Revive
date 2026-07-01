# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Keep the reusable slider out of the Sales menu after migration."""
    old_menu = env.ref('lifestyle_connector.menu_lifestyle_homepage_slide', raise_if_not_found=False)
    if old_menu and 'active' in old_menu._fields:
        old_menu.write({'active': False})

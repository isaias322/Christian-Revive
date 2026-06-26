from . import models
from . import controllers


def post_init_hook(env):
    """Flag pre-existing products in the three Lifestyle categories as
    visible to the Revive Lifestyle app, since revive_db is shared with the
    Revive App backend and new products default to hidden from both apps."""
    category_xml_ids = [
        'lifestyle_connector.category_fruits_veg',
        'lifestyle_connector.category_healthy_pantry',
        'lifestyle_connector.category_furniture_home',
    ]
    categories = env['product.category']
    for xml_id in category_xml_ids:
        category = env.ref(xml_id, raise_if_not_found=False)
        if category:
            categories += category
    if not categories:
        return
    products = env['product.template'].search([('categ_id', 'child_of', categories.ids)])
    products.write({'lifestyle_app_visible': True})

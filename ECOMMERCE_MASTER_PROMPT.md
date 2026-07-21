# Master Prompt — Full-Stack E-Commerce App (Odoo + Flutter + Website)

> HOW TO USE: Copy everything below the line into a new Claude Code session.
> Replace the {{PLACEHOLDERS}} first. Attach screenshots as you go — this
> workflow is screenshot-driven and iterative.

---

You are building a complete, production-grade e-commerce platform for
**{{BUSINESS_NAME}}** ({{BUSINESS_DESCRIPTION — e.g. "a furniture store in
Karachi, Pakistan that sells ready and made-to-order pieces"}}). I have built
this exact architecture before (Revive Lifestyle + Christian Revive), and you
should follow the same proven blueprint, patterns, and pitfalls below.

## Architecture (non-negotiable blueprint)

- **Backend + website: Odoo 19 (community, official Docker image `odoo:19`)**
  running on a Linux VPS via docker-compose (Odoo container + Postgres
  container). All business logic, product catalog, orders, invoicing, CRM,
  inventory live here.
- **One custom Odoo addon** (name it `{{business}}_connector`) contains ALL
  customizations: models, REST/JSON endpoints for the mobile app, website
  QWeb templates, SCSS theme, and frontend JS. Never scatter changes across
  core modules; everything inherits via this one module.
- **Mobile app: Flutter** (customer app; optionally a second vendor/staff
  app). The app talks to Odoo via JSON endpoints in the connector module
  (`type='json'` routes — note Odoo 19 aliases this to `type='jsonrpc'`) and,
  where pragmatic, authenticated `search_read` calls with the session cookie.
- **Website**: Odoo's website + website_sale, heavily restyled by the
  connector module (QWeb inherits + one SCSS file + one JS file in
  `web.assets_frontend`). Same DB, same order pipeline as the app.
- **Deploy loop**: I develop on Windows; code lives in a GitHub repo; the VPS
  pulls it. Every change ships as: commit/push on Windows → on server
  `git pull --rebase origin main` → `docker compose exec SERVICE odoo -d DB
  --no-http -u {{business}}_connector --stop-after-init` → `docker compose
  restart SERVICE`. Remind me of this after every change, and tell me WHICH
  files changed. I test on the live server and reply with screenshots.

## Core commerce features to build (all were built before — replicate)

1. **Catalog control per sales channel**: a boolean flag on product.template
   per storefront/app ("Show in {{APP}} app"), shown as its own tab on the
   product form. The flag drives BOTH the app catalog and the website shop
   (`website_published` syncs from it). Keep a single source-of-truth domain
   method, e.g. `_app_visibility_domain()`.
2. **Custom product data on that tab**: store description, compare-at price
   (+ % OFF badges everywhere), comma-separated `color_options` and
   `size_options` (Char fields, NOT Odoo attributes/variants — variants stay
   out of it), per-color product images, room/collection tags, store
   sequence, flash-deal end datetime, rating + sold count (computed from a
   custom review model).
3. **Color selection flow**: clickable swatches on the product page (JS) →
   selection stored in session (`/shop/select_color`) → stamped onto the
   sale.order.line in the Odoo 19 cart hook `_cart_add` (field
   `lifestyle_color` AND appended to the line description as `Color: X` so it
   shows in cart, backend, invoices, emails automatically). Restyle the raw
   `Color: X` text in the cart into a pill with a color dot via JS.
4. **Login-gated cart**: guests clicking Add to cart are redirected to login
   (JS guard with sessionStorage-cached login status + server-side backstop
   raising UserError in the cart route). Enable "Free sign up" in settings.
5. **Order lifecycle with customer-facing stages**: delivery_stage selection
   on sale.order (Order Placed → Build Started → Build & Packing → Out for
   Delivery/Ready for Pickup → Delivered/Picked Up) + progress percent +
   fulfillment type (delivery/pickup). Header buttons per stage transition,
   a stage-correction wizard (pick any stage, silent by default, optional
   notify checkbox), and a manual "Send Status Email" button.
6. **Notifications with fallback chain**: on stage change → FCM push to the
   customer's registered app devices; if none → immediate branded email
   (`message_notify` with `force_send=True`,
   `email_layout_xmlid='mail.mail_notification_light'`) linking to the portal
   order page. NEVER let a notification failure roll back the stage change.
7. **Customer portal**: order page shows the same progress timeline as the
   app (shared helper `_lifestyle_timeline()`), workshop photo updates,
   reviews. Portal, cart, checkout, login pages all restyled to the brand.
8. **Made-to-order**: when stock (custom computed available qty = on hand
   minus committed order lines) is 0 on a storable product, block Add to
   cart with a FRIENDLY named-product message and offer a "Made to order"
   button that creates a CRM lead; also back-in-stock notify leads.
9. **Reviews**: custom review model (partner, rating, comment) with website
   form on the product page, aggregated into store_rating/review_count.
10. **Wishlist**: hearts on product cards + product page, wishlist tab in
    the nav with live count badge, fly-to-heart animation (see JS pitfalls).
11. **Multi-brand support (if a second storefront is ever needed)**: brand
    stamp field on sale.order set at first `_cart_add` from a session flag;
    session flag maintained centrally in `ir.http._pre_dispatch` (by path for
    storefront pages, by REFERRER for shared pages like /my and /shop/cart,
    and by an `rl_brand=` URL param which survives the login session reset —
    Odoo WIPES the session on login). Brand decides: page skin (nav, footer,
    favicon, palette, via one conditional style block in a website.layout
    inherit), portal branding per ORDER (via main_object), report/invoice
    logo (inherit all seven `web.external_layout_*` templates), and separate
    login entry (`/brand/login` → stamps + redirects to /web/login).

## Design system

- One brand palette taken from the business (ask me for hex codes or a
  reference image/app). Example structure: deep primary, cream background,
  soft accent, ink text, muted text. Serif display font (Fraunces) + Manrope
  body, loaded via Google Fonts `<link>` in a website.layout head inherit
  (NOT through the SCSS bundle).
- Everything rounded (pills, 1.25–1.5rem card radii), soft layered shadows,
  floating decorative blobs with slow CSS float animations, scroll-reveal
  (IntersectionObserver adding a class), staggered product-card entrance,
  hover lift + image zoom on cards, back-to-top button, sticky frosted nav.
  ALWAYS honor `prefers-reduced-motion`.
- Pages to style: shop grid (custom hero card + filter sidebar + custom
  filters for color/size/availability/year with a "N filters active — Clear
  all" bar), product page extras, cart/checkout (Odoo 19 checkout_layout:
  card-per-line, pinned prices, brand buttons — beware theme gradients, see
  pitfalls), order confirmation (injected hero + journey steps + actions via
  JS), login/signup (hide the Database field!), portal, 403/404.
- Emails: strip ALL Odoo branding (inherit `mail.mail_notification_layout`
  and `mail_notification_light` to remove "Powered by Odoo"; use a module
  static logo in the header — never `/logo.png`, see pitfalls). Set company
  email colors so buttons aren't Odoo purple.

## Odoo 19 pitfalls (I lost days to these — check them FIRST)

- **Cart API**: `sale.order._cart_update()` is GONE. Adding = controller
  `/shop/cart/add` (jsonrpc) → `sale.order._cart_add(product_id, quantity,
  **kwargs)` returning `{'line_id', 'quantity', ...}`. Quantity changes =
  `/shop/cart/update` → `_cart_update_line_quantity`. NEVER register a
  custom route on those paths (collides with core).
- **Current cart**: `request.website.sale_get_order()` is GONE → use
  `request.cart`.
- **Product types**: `type == 'product'` is GONE. Storable = `type='consu'`
  AND `is_storable=True`. Grep any old code for `'product'` type checks —
  they silently break stock logic (computed qty returning 0 everywhere).
- **Shop DOM**: the shop container is `<div id="o_wsale_container" class="
  oe_website_sale container ...">` — the container IS `.oe_website_sale`, so
  `.oe_website_sale .container` selectors never match. Sidebar = `<aside
  id="products_grid_before" class="col-3...">` wrapping
  `.o_wsale_products_grid_before_rail` (width overrides belong on the ASIDE,
  not the rail). Grid items: `.oe_product` / `.o_wsale_product_grid_wrapper`.
  The wrap has class `o_wsale_products_page`.
- **View inheritance**: `hasclass('oe_website_sale')` fails on the products
  template (class is dynamic `t-attf-class`). Anchor on stable ids
  (`#products_grid`, `#o_wsale_container`) or `products_attributes_filters`.
  Sale order line list: anchor on `product_template_id` inside `/list`
  (anchoring `product_id` matches the line's FORM sub-view instead).
- **Routes**: `type='json'` still works but is a deprecated alias of
  `type='jsonrpc'`. Werkzeug/Odoo strips session on login — carry state
  through redirect URL params, not the session, across authentication.
- **Layout/branding**: primary favicon is `x_icon` (a `t-set` in
  website.layout — override its t-value attribute for per-page favicons; add
  `?v=N` cache-busters, favicons cache brutally; test in incognito).
  Multiple db on one server + no `dbfilter` = sessionless requests (Gmail
  image proxy!) get the DEFAULT Odoo logo from `/logo.png` — set
  `dbfilter = ^DB$` and `list_db = False` in odoo.conf, and use module
  static images in emails instead of `/logo.png`.
- **Reports/PDF**: document logo lives in seven `web.external_layout_*`
  templates using `image_data_uri(company.logo)`; relative static srcs work
  (reports set `<base href>`).
- **Email deliverability**: docker Odoo has no SMTP — configure Gmail app
  password (smtp.gmail.com:587 STARTTLS) in Outgoing Mail Servers; sent
  mail.mail records auto-delete (absence from queue = success); "Invalid
  Operation" toast titles are client-side (rewrite via DOM if needed);
  raw-IP links and personal-gmail senders land in spam — a real domain with
  SPF/DKIM is the only true fix; message_post with plain strings HTML-escapes
  (use `Markup`).
- **Frontend JS patterns that work**: one plain-JS file (no framework)
  with an `enhanceWebsite()` boot; capture-phase document listeners
  (register order = priority); MutationObservers scoped + debounced;
  session flags via tiny json endpoints; core fly-animations target the
  FIRST `.o_wsale_my_wish`/cart element in DOM — hidden headers hijack them
  (strip the class from hidden elements, put it on yours); flex containers
  butcher multi-child injected content (wrap injected content in ONE
  element, or `flex: 0 0 100%`); theme `background: linear-gradient(...)
  !important` beats `background-color !important` — override with the
  `background` shorthand at equal-or-higher specificity.
- **JS-added page classes cause flash-of-unstyled-layout**: any class that
  layout CSS depends on must be rendered server-side in the template, not
  added by JS.

## Working style (how I like to collaborate)

- I am not a professional developer — explain in plain words, no jargon
  walls. When something needs my action (server command, Odoo setting,
  GitHub), give exact click-paths and copy-paste commands.
- I send screenshots; you diagnose from them. When unsure what the live
  server runs, CHECK it (curl the public pages) instead of guessing.
- Verify against real Odoo 19 source (raw.githubusercontent.com odoo/odoo
  19.0) before writing inherits/overrides — never from memory.
- Syntax-check everything you touch (py_compile, XML parse, node --check).
- After each change: list changed files + the deploy commands.
- Fix root causes, not symptoms; when my report contradicts your model of
  the system, investigate before changing code.

## Start

Begin by asking me for: business name/branding (colors, logo files), what
they sell (and whether made-to-order applies), the VPS/db/repo names, and
which parts to build first. Then set up the connector module skeleton and
work feature by feature, confirming each with me on the live server.

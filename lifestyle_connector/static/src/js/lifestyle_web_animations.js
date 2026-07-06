/** @odoo-module **/

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function collectRevealTargets() {
    return document.querySelectorAll([
        '#wrap > section',
        'main section',
        '.oe_website_sale .oe_product_cart',
        '.oe_website_sale .oe_product',
        '.oe_website_sale #cart_total',
        '.oe_website_sale .oe_cart .col-lg-8',
        '.lifestyle-card',
        '.rl-contact-panel',
        '.rl-contact-info-card',
        '.rl-contact-mini',
        '.rl-contact-process',
        '.s_website_form',
        '.o_portal_wrap .card',
    ].join(','));
}

function prepareRevealTargets() {
    const targets = collectRevealTargets();
    targets.forEach((target, index) => {
        if (target.classList.contains('rl-reveal-ready')) return;
        target.classList.add('rl-reveal-ready');
        target.style.setProperty('--rl-reveal-delay', `${Math.min(index % 6, 5) * 55}ms`);
    });
    return targets;
}

function revealImmediately(targets) {
    targets.forEach((target) => target.classList.add('rl-reveal-visible'));
}

function setupRevealObserver(targets) {
    if (!('IntersectionObserver' in window) || reduceMotion) {
        revealImmediately(targets);
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('rl-reveal-visible');
            observer.unobserve(entry.target);
        });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });

    targets.forEach((target) => observer.observe(target));
}

function hideShopCategoryTabs() {
    if (!window.location.pathname.startsWith('/shop')) return;

    const categoryLabels = ['Furniture & Home', 'Fruits & Vegetables', 'Healthy Pantry'];
    const scope = document.querySelector('#wrap') || document.body;
    const matchingLinks = Array.from(scope.querySelectorAll('a')).filter((link) => {
        if (link.closest('.rl-shop-filter-block')) return false;
        const label = link.textContent.replace(/\s+/g, ' ').trim();
        const href = link.getAttribute('href') || '';
        return categoryLabels.includes(label) || href.indexOf('/shop/category/') !== -1;
    });

    if (!matchingLinks.length) return;

    const containers = new Set();
    matchingLinks.forEach((link) => {
        const container = link.closest('.nav, .nav-pills, .nav-tabs, .o_wsale_filmstip_container, .o_wsale_categories_top, .o_wsale_category_nav, ul, .btn-group, .list-group, .d-flex');
        if (container) containers.add(container);
    });

    containers.forEach((container) => {
        const text = container.textContent || '';
        const matchCount = categoryLabels.filter((label) => text.includes(label)).length;
        if (matchCount >= 1) {
            container.classList.add('d-none');
        }
    });

    matchingLinks.forEach((link) => {
        const isHidden = link.closest('.d-none');
        if (!isHidden) link.classList.add('d-none');
    });
}

function keepShopClean() {
    hideShopCategoryTabs();
    window.setTimeout(hideShopCategoryTabs, 200);

    if (!window.location.pathname.startsWith('/shop') || !('MutationObserver' in window)) return;
    // Scope to the category nav area only - watching the whole page subtree
    // fires on every DOM mutation and causes noticeable sluggishness.
    const navScope = document.querySelector(
        '.o_wsale_filmstip_container, .o_wsale_categories_top, .o_wsale_category_nav, nav'
    ) || document.querySelector('#wrap');
    let pending = false;
    const observer = new MutationObserver(() => {
        if (pending) return;
        pending = true;
        window.requestAnimationFrame(() => { hideShopCategoryTabs(); pending = false; });
    });
    observer.observe(navScope, { childList: true, subtree: true });
}


function markShopPage() {
    const path = window.location.pathname;
    const isShopListing = path === '/shop' || path.startsWith('/shop/category') || path.startsWith('/shop/page');
    if (isShopListing) {
        document.documentElement.classList.add('rl-shop-page');
    }
}

function parseMoneyValue(text) {
    const cleaned = (text || '').replace(/[^0-9.,-]/g, '').replace(/,/g, '');
    const value = parseFloat(cleaned);
    return isFinite(value) ? value : 0;
}

function formatMoneyValue(value) {
    return value.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function findProductPriceValueElement() {
    return document.querySelector('#product_detail .oe_price .oe_currency_value')
        || document.querySelector('#product_detail .product_price .oe_currency_value')
        || document.querySelector('#product_details .oe_price .oe_currency_value')
        || document.querySelector('#product_details .product_price .oe_currency_value')
        || document.querySelector('.oe_website_sale #product_detail [itemprop="price"]')
        || document.querySelector('.oe_website_sale #product_details [itemprop="price"]');
}

function getProductQuantityInput() {
    return document.querySelector('#product_detail input[name="add_qty"]')
        || document.querySelector('#product_details input[name="add_qty"]')
        || document.querySelector('#product_detail .css_quantity input')
        || document.querySelector('#product_details .css_quantity input')
        || document.querySelector('.oe_website_sale input[name="add_qty"]');
}

function updateProductTotalPrice() {
    const quantityInput = getProductQuantityInput();
    const priceElement = findProductPriceValueElement();
    if (!quantityInput || !priceElement) return;

    const quantity = Math.max(1, parseFloat(quantityInput.value || '1') || 1);
    if (!quantityInput.dataset.rlUnitPrice) {
        const currentPrice = parseMoneyValue(priceElement.textContent);
        quantityInput.dataset.rlUnitPrice = String(currentPrice / quantity);
    }

    const unitPrice = parseFloat(quantityInput.dataset.rlUnitPrice || '0') || 0;
    const totalPrice = formatMoneyValue(unitPrice * quantity);
    if (priceElement.textContent.trim() !== totalPrice) {
        priceElement.textContent = totalPrice;
    }
}

function setupProductQuantityPrice() {
    const quantityInput = getProductQuantityInput();
    if (!quantityInput) return;

    const runPriceUpdate = () => {
        updateProductTotalPrice();
        window.setTimeout(updateProductTotalPrice, 60);
        window.setTimeout(updateProductTotalPrice, 180);
        window.setTimeout(updateProductTotalPrice, 420);
    };

    updateProductTotalPrice();
    quantityInput.addEventListener('input', runPriceUpdate);
    quantityInput.addEventListener('change', runPriceUpdate);

    const quantityBox = quantityInput.closest('.css_quantity') || quantityInput.parentElement;
    if (quantityBox) {
        quantityBox.addEventListener('click', runPriceUpdate);
    }

    const priceElement = findProductPriceValueElement();
    const priceContainer = priceElement?.closest('.product_price, .oe_price, #product_detail, #product_details');
    if (priceContainer && 'MutationObserver' in window) {
        const observer = new MutationObserver(() => window.requestAnimationFrame(updateProductTotalPrice));
        observer.observe(priceContainer, { childList: true, characterData: true, subtree: true });
    }

}

function setupHomepageHeroSlider() {
    const slider = document.querySelector('[data-rl-home-slider]');
    if (!slider) return;

    const slides = Array.from(slider.querySelectorAll('.rl-home-hero-content-slide'));
    if (!slides.length) return;

    const prevButton = slider.querySelector('[data-rl-home-prev]');
    const nextButton = slider.querySelector('[data-rl-home-next]');
    const dots = Array.from(slider.querySelectorAll('[data-rl-home-dot]'));
    const autoplayInterval = Math.max(2500, parseInt(slider.dataset.rlHomeInterval || '4500', 10) || 4500);
    let activeIndex = slides.findIndex((slide) => slide.classList.contains('is-active'));
    let timer = null;
    activeIndex = activeIndex >= 0 ? activeIndex : 0;

    function getActiveAccent() {
        const activeSlide = slides[activeIndex];
        return activeSlide
            ? getComputedStyle(activeSlide).getPropertyValue('--rl-slide-accent').trim() || '#D9B777'
            : '#D9B777';
    }

    function syncHeroTheme() {
        const activeSlide = slides[activeIndex];
        if (!activeSlide) return;

        Array.from(slider.classList).forEach((className) => {
            if (className.indexOf('rl-home-active-style-') === 0) {
                slider.classList.remove(className);
            }
        });

        const styleClass = Array.from(activeSlide.classList).find((className) => className.indexOf('rl-home-hero-style-') === 0);
        if (styleClass) {
            slider.classList.add(styleClass.replace('rl-home-hero-style-', 'rl-home-active-style-'));
        }

        const activeStyle = getComputedStyle(activeSlide);
        ['--rl-slide-bg', '--rl-slide-bg-2', '--rl-slide-text', '--rl-slide-accent', '--rl-slide-overlay'].forEach((propertyName) => {
            const value = activeStyle.getPropertyValue(propertyName).trim();
            if (value) {
                slider.style.setProperty(propertyName, value);
            } else {
                slider.style.removeProperty(propertyName);
            }
        });
    }

    function paintDots() {
        const activeAccent = getActiveAccent();
        dots.forEach((dot, dotIndex) => {
            const isActive = dotIndex === activeIndex;
            dot.removeAttribute('aria-current');
            dot.style.width = isActive ? '2rem' : '0.62rem';
            dot.style.height = '0.62rem';
            dot.style.borderRadius = '999px';
            dot.style.background = isActive ? activeAccent : 'rgba(255, 253, 249, 0.42)';
            dot.style.boxShadow = 'none';
            dot.style.outline = '0';
            if (isActive) {
                dot.setAttribute('aria-current', 'true');
            }
        });
    }

    function showSlide(index) {
        activeIndex = (index + slides.length) % slides.length;
        slides.forEach((slide) => slide.classList.remove('is-active'));
        slides[activeIndex]?.classList.add('is-active');
        syncHeroTheme();
        paintDots();
    }

    function startAutoplay() {
        if (reduceMotion || timer) return;
        timer = window.setInterval(() => showSlide(activeIndex + 1), autoplayInterval);
    }

    function stopAutoplay() {
        if (!timer) return;
        window.clearInterval(timer);
        timer = null;
    }

    prevButton?.addEventListener('click', () => {
        stopAutoplay();
        showSlide(activeIndex - 1);
        startAutoplay();
    });

    nextButton?.addEventListener('click', () => {
        stopAutoplay();
        showSlide(activeIndex + 1);
        startAutoplay();
    });

    showSlide(activeIndex);

    if (slides.length <= 1) return;

    dots.forEach((dot) => {
        dot.addEventListener('focus', paintDots);
        dot.addEventListener('blur', paintDots);
        dot.addEventListener('mouseenter', paintDots);
        dot.addEventListener('mouseleave', paintDots);
        dot.addEventListener('click', () => {
            const index = parseInt(dot.dataset.rlHomeDot || '0', 10);
            stopAutoplay();
            showSlide(index);
            startAutoplay();
        });
    });

    slider.addEventListener('mouseenter', stopAutoplay);
    slider.addEventListener('mouseleave', startAutoplay);
    showSlide(activeIndex);
    startAutoplay();
}

function restoreShopSearchBar() {
    if (!window.location.pathname.startsWith('/shop')) return;

    var searchForm = document.querySelector('.o_wsale_products_searchbar_form');
    if (!searchForm) return;

    var input = searchForm.querySelector('input[name="search"], .search-query');
    if (!input) return;

    function dimGrid() {
        var grid = document.getElementById('products_grid');
        if (grid) { grid.style.transition = 'opacity 0.1s'; grid.style.opacity = '0.25'; }
    }

    function navToShop() {
        var url = new URL(window.location.href);
        url.searchParams.delete('search');
        url.searchParams.delete('page');
        dimGrid();
        window.location.href = url.toString();
    }

    // Guard flag: prevents MutationObserver from re-entering ensureVisible
    // while ensureVisible itself is modifying style/class. Without this the
    // observer fires in a tight loop and freezes the browser tab.
    var _restoring = false;
    function ensureVisible() {
        if (_restoring) return;
        _restoring = true;
        searchForm.classList.remove('d-none', 'collapse');
        if (window.getComputedStyle(searchForm).display === 'none') {
            searchForm.style.display = 'inline-flex';
        }
        _restoring = false;
    }

    ensureVisible();

    if (window.MutationObserver) {
        new MutationObserver(ensureVisible).observe(searchForm, {
            attributes: true,
            attributeFilter: ['class', 'style'],
        });
    }

    // Intercept form submit when field is empty: go straight to /shop instead
    // of submitting ?search= which triggers a heavy server query and can hang.
    searchForm.addEventListener('submit', function (e) {
        if (input.value.trim() !== '') return;
        e.preventDefault();
        e.stopImmediatePropagation();
        navToShop();
    }, true);

    // Navigate immediately when the field is cleared - capture phase so we
    // run before Odoo's own input handler (which would fire an AJAX search).
    input.addEventListener('input', function (e) {
        if (input.value.trim() !== '') return;
        if (!new URLSearchParams(window.location.search).has('search')) return;
        e.stopImmediatePropagation();
        navToShop();
    }, true);

    // Escape: clear the field and go back to all products immediately.
    input.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        input.value = '';
        input.blur();
        navToShop();
    }, true);

    // Auto-focus after arriving on /shop from a search page.
    var params = new URLSearchParams(window.location.search);
    var referrer = document.referrer || '';
    if (referrer.includes('/shop') && referrer.includes('search=') && !params.has('search')) {
        window.setTimeout(function () { input.focus(); input.select(); }, 120);
    }
}

function setupContactFormValidation() {
    // Odoo submits s_website_form via AJAX, bypassing browser required-field popups.
    // Intercept in capture phase (before Odoo's handler) to show a friendly message instead.
    document.addEventListener('submit', function (e) {
        const form = e.target;
        if (!form || form.tagName !== 'FORM') return;
        if (!form.classList.contains('s_website_form') && !form.closest('.s_website_form')) return;

        const requiredInputs = Array.from(
            form.querySelectorAll('input[required], textarea[required], select[required]')
        );
        requiredInputs.forEach(function (el) { el.classList.remove('is-invalid'); });

        const emptyFields = requiredInputs.filter(function (el) {
            return el.type === 'checkbox' ? !el.checked : !el.value.trim();
        });

        let msg = form.querySelector('.rl-form-val-msg');

        if (emptyFields.length === 0) {
            if (msg) msg.style.display = 'none';
            return;
        }

        e.preventDefault();
        e.stopImmediatePropagation();

        emptyFields.forEach(function (el) { el.classList.add('is-invalid'); });

        if (!msg) {
            msg = document.createElement('p');
            msg.className = 'rl-form-val-msg text-danger small mt-2 mb-0';
            const btn = form.querySelector('[type="submit"], .s_website_form_send');
            if (btn && btn.parentElement) {
                btn.parentElement.insertBefore(msg, btn.nextSibling);
            } else {
                form.appendChild(msg);
            }
        }
        msg.textContent = 'Please fill in all required fields before sending your message.';
        msg.style.display = '';

        emptyFields[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
        emptyFields[0].focus();
    }, true);

    // Clear the red border as soon as the user starts typing in a flagged field.
    document.addEventListener('input', function (e) {
        if (e.target.classList.contains('is-invalid') && e.target.value.trim()) {
            e.target.classList.remove('is-invalid');
        }
    });
}

function setupSaveForLaterRedirect() {
    if (!window.location.pathname.startsWith('/shop/cart')) return;
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.o_add_wishlist.js_delete_product')) return;
        // Odoo's handlers (add to wishlist + remove from cart) run async via RPC.
        // Wait for them to finish, then navigate to the wishlist page.
        window.setTimeout(function () {
            window.location.href = '/shop/wishlist';
        }, 900);
    });
}


function getStoredJson(key, fallback) {
    try {
        return JSON.parse(window.localStorage.getItem(key) || JSON.stringify(fallback));
    } catch (error) {
        return fallback;
    }
}

function setStoredJson(key, value) {
    try {
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        // Browser storage may be disabled; the shop still works without it.
    }
}

function moneyLabel(value) {
    const numeric = parseFloat(value || '0') || 0;
    return `Rs. ${formatMoneyValue(numeric)}`;
}


function rememberCurrentProduct() {
    // Detect product page by presence of the add-to-cart form, not by URL.
    // Odoo 19 uses SEO slugs like /shop/bed-1, not /shop/product/..., so
    // a URL-based check misses all products.
    const isProductPage = !!(
        document.getElementById('product_detail') ||
        document.getElementById('product_details') ||
        document.querySelector('form[action*="add_to_cart"], #add_to_cart')
    );
    if (!isProductPage) return;

    const name = document.querySelector(
        '#product_detail h1, #product_details h1, .product-name, h1'
    )?.textContent?.trim();
    if (!name) return;

    const price = findProductPriceValueElement()?.textContent?.trim();
    const image = document.querySelector(
        '#product_detail img, #product_details img, .product-image img, #o_product_main_image img'
    )?.getAttribute('src');

    let items = getStoredJson('rl_recent_products', []);
    const current = { name, price: price || '', image: image || '', url: window.location.pathname };
    items = items.filter((item) => item.url !== current.url);
    items.unshift(current);
    setStoredJson('rl_recent_products', items.slice(0, 4));
}

function renderRecentlyViewed() {
    // Only show on the shop listing page - detect by absence of product detail.
    const isProductPage = !!(
        document.getElementById('product_detail') ||
        document.getElementById('product_details') ||
        document.querySelector('form[action*="add_to_cart"], #add_to_cart')
    );
    if (isProductPage) return;

    const grid = document.getElementById('products_grid');
    if (!grid) return;

    const items = getStoredJson('rl_recent_products', []).slice(0, 3);
    if (!items.length) return;

    const section = document.createElement('section');
    section.className = 'rl-recently-viewed';
    section.innerHTML = '<h5 class="rl-recently-viewed-title">Recently Viewed</h5><div class="rl-recent-links"></div>';
    const links = section.querySelector('.rl-recent-links');
    items.forEach((item) => {
        const link = document.createElement('a');
        link.href = item.url || '#';
        link.innerHTML = `<img src="${item.image || '/web/static/img/placeholder.png'}" alt=""><div><strong>${item.name}</strong><span>${item.price || ''}</span></div>`;
        links.appendChild(link);
    });
    grid.appendChild(section);
}

// Floating back-to-top button for long product lists.
function setupBackToTop() {
    if (!window.location.pathname.startsWith('/shop')) return;
    if (document.querySelector('.rl-back-to-top')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rl-back-to-top';
    btn.setAttribute('aria-label', 'Back to top');
    btn.innerHTML = '<i class="fa fa-arrow-up"></i>';
    document.body.appendChild(btn);
    btn.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    var onScroll = function () {
        btn.classList.toggle('is-visible', window.scrollY > 600);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
}

function setupMobileShopFilters() {
    if (!window.location.pathname.startsWith('/shop')) return;
    const rail = document.querySelector('.o_wsale_products_grid_before_rail');
    if (!rail || document.querySelector('.rl-mobile-filter-toggle')) return;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'rl-mobile-filter-toggle';
    button.innerHTML = '<i class="fa fa-sliders"></i><span>Filters</span>';
    document.body.appendChild(button);

    button.addEventListener('click', () => {
        rail.classList.toggle('rl-mobile-filters-open');
        button.classList.toggle('is-active');
    });
}
// Guests must sign in before adding to cart: orders need a real account so
// stage updates can reach the customer (app push or email) and the portal
// shows their order. Must be registered BEFORE setupColorSelection so its
// stopImmediatePropagation wins over the color add-to-cart interceptor.
// Login/signup polish: customers must never see the technical database
// selector, and the card gets a friendly subtitle under the heading.
function setupLoginPagePolish() {
    var path = window.location.pathname;
    if (!path.startsWith('/web/login') && !path.startsWith('/web/signup')
        && !path.startsWith('/web/reset_password')) return;
    var dbInput = document.querySelector('input[name="db"]');
    if (dbInput) {
        // Climb to the field wrapper (the div holding both the label and
        // the input group) and hide the whole block.
        var node = dbInput.parentElement;
        for (var i = 0; i < 4 && node; i++) {
            if (node.querySelector('label')) break;
            node = node.parentElement;
        }
        (node || dbInput).style.setProperty('display', 'none', 'important');
    }
    var form = document.querySelector('.oe_login_form, .oe_signup_form, .oe_reset_password_form');
    if (form && !form.querySelector('.rl-login-subtitle')) {
        var sub = document.createElement('p');
        sub.className = 'rl-login-subtitle';
        sub.textContent = path.startsWith('/web/signup')
            ? 'Create an account to order, save favorites, and track every delivery.'
            : 'Sign in to shop, track your orders, and check out faster.';
        form.insertBefore(sub, form.firstChild);
    }
}

function setupRequireLoginForCart() {
    if (!window.location.pathname.startsWith('/shop')) return;
    // Cache the status so the guard is armed instantly on later pages -
    // otherwise a fast first click can slip through before the check returns.
    var loggedIn = null; // unknown until the status call returns
    try {
        var cached = window.sessionStorage.getItem('rlLoggedIn');
        if (cached !== null) { loggedIn = cached === '1'; }
    } catch (e) { /* storage unavailable */ }
    fetch('/shop/rl_login_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 31, params: {} }),
    }).then(function (res) { return res.json(); }).then(function (data) {
        var result = (data && data.result) || {};
        loggedIn = !!result.logged_in;
        try { window.sessionStorage.setItem('rlLoggedIn', loggedIn ? '1' : '0'); } catch (e) {}
    }).catch(function () {});

    document.addEventListener('click', function (e) {
        if (loggedIn !== false) return; // logged in, or status unknown: let it through
        var btn = e.target.closest(
            '#add_to_cart, [name="add_to_cart"], ' +
            '.js_add_cart, .o_website_sale_main_product_cart_btn, ' +
            '.o_wsale_product_btn a, .o_wsale_product_btn button, ' +
            'form#product_detail_form button[type="submit"]'
        );
        if (!btn) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        window.location.href = '/web/login?redirect='
            + encodeURIComponent(window.location.pathname + window.location.search);
    }, true);
}

function setupColorSelection() {
    const swatches = Array.from(document.querySelectorAll('#rl_color_picker .rl-pd-swatch[data-color]'));
    if (!swatches.length) return;

    let selectedColor = '';
    const label = document.getElementById('rl_color_chosen');
    const labelName = document.getElementById('rl_color_chosen_name');

    function ensureColorInput() {
        // Always inject into the cart form so the value is submitted with the POST.
        // The #rl_selected_color_input in the template lives outside the form, so
        // returning it directly meant the color was never included in the submission.
        const form = document.querySelector('#product_detail form[action*="/shop/cart/update"]') ||
            document.querySelector('#product_details form[action*="/shop/cart/update"]') ||
            document.querySelector('form[action*="/shop/cart/update"]') ||
            document.querySelector('form#product_detail_form');
        if (form) {
            let inp = form.querySelector('[name="lifestyle_color"]');
            if (!inp) {
                inp = document.createElement('input');
                inp.type = 'hidden';
                inp.name = 'lifestyle_color';
                form.appendChild(inp);
            }
            return inp;
        }
        return document.getElementById('rl_selected_color_input');
    }

    // Try to find the main product image element (Odoo uses several selectors).
    function findMainProductImage() {
        return document.querySelector(
            '.o_carousel_product_img .img-fluid, ' +
            '.o_carousel_product_img img, ' +
            '.product_detail_img img, ' +
            'img[itemprop="image"], ' +
            '.oe_product_image img'
        );
    }

    function selectSwatch(swatch) {
        swatches.forEach(function (s) {
            s.classList.remove('rl-selected');
            s.setAttribute('aria-checked', 'false');
        });
        swatch.classList.add('rl-selected');
        swatch.setAttribute('aria-checked', 'true');
        selectedColor = swatch.dataset.color || '';
        if (label && labelName) {
            labelName.textContent = selectedColor;
            label.style.display = '';
        }
        const colorInput = ensureColorInput();
        if (colorInput) {
            colorInput.value = selectedColor;
        }
        // Swap main product image if this color has one configured.
        var imgUrl = swatch.dataset.imageUrl;
        if (imgUrl) {
            var mainImg = findMainProductImage();
            if (mainImg) {
                if (!mainImg.dataset.rlOrigSrc) {
                    mainImg.dataset.rlOrigSrc = mainImg.src;
                }
                mainImg.src = imgUrl;
            }
        } else {
            // No color image - restore the original product photo.
            var mainImgRestore = findMainProductImage();
            if (mainImgRestore && mainImgRestore.dataset.rlOrigSrc) {
                mainImgRestore.src = mainImgRestore.dataset.rlOrigSrc;
            }
        }
        // Store in session immediately on swatch click.
        if (selectedColor) {
            fetch('/shop/select_color', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0', method: 'call', id: 1,
                    params: { color: selectedColor, product_id: productTmplId ? parseInt(productTmplId, 10) : null },
                }),
            }).catch(function () {});
        }
    }

    ensureColorInput();

    function persistSelectedColor() {
        if (!selectedColor) { return Promise.resolve(); }
        const colorInput = ensureColorInput();
        if (colorInput) { colorInput.value = selectedColor; }
        return fetch('/shop/select_color', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0', method: 'call', id: 11,
                params: { color: selectedColor, product_id: productTmplId ? parseInt(productTmplId, 10) : null },
            }),
            keepalive: true,
        }).catch(function () {});
    }

    swatches.forEach(function (swatch) {
        swatch.addEventListener('click', function () { selectSwatch(swatch); });
        swatch.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectSwatch(swatch); }
        });
    });

    document.addEventListener('click', function (e) {
        var btn = e.target.closest(
            '#add_to_cart, [name="add_to_cart"], ' +
            'button.o_website_sale_main_product_cart_btn, ' +
            'button.js_add_cart, ' +
            'form#product_detail_form button[type="submit"]'
        );
        if (!btn || !selectedColor || btn.dataset.rlColorPrepared === '1') { return; }
        e.preventDefault();
        e.stopImmediatePropagation();
        btn.dataset.rlColorPrepared = '1';
        persistSelectedColor().then(function () {
            btn.click();
            window.setTimeout(function () { delete btn.dataset.rlColorPrepared; }, 800);
        });
    }, true);

    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!selectedColor || !form || form.dataset.rlColorPrepared === '1') { return; }
        if (!form.matches('form[action*="/shop/cart/update"], form#product_detail_form')) { return; }
        e.preventDefault();
        e.stopImmediatePropagation();
        form.dataset.rlColorPrepared = '1';
        persistSelectedColor().then(function () {
            if (form.requestSubmit) { form.requestSubmit(); }
            else { form.submit(); }
            window.setTimeout(function () { delete form.dataset.rlColorPrepared; }, 800);
        });
    }, true);

    // ── Approach 2: intercept the cart-update fetch to grab line_id from response ──
    // Covers both /shop/cart/update_json and /web/dataset/call_kw/_cart_update
    // (Odoo 19 uses call_kw; the body check catches that case).
    if (!window._rlCartFetchPatched) {
        window._rlCartFetchPatched = true;
        var _origFetch = window.fetch;
        window.fetch = function (input, init) {
            var url = typeof input === 'string' ? input : (input && input.url) || '';
            var body = (init && typeof init.body === 'string') ? init.body : '';
            var p = _origFetch.apply(window, arguments);
            var isCartUpdate = url.indexOf('cart/update') !== -1
                || url.indexOf('_cart_update') !== -1
                || (body && body.indexOf('_cart_update') !== -1);
            if (isCartUpdate) {
                p.then(function (res) {
                    res.clone().json().then(function (data) {
                        // JSON-RPC wraps result; plain endpoints return it directly.
                        var result = (data && data.result) || data || {};
                        var lineId = result.line_id;
                        if (!lineId || !selectedColor) { return; }
                        _origFetch('/shop/apply_line_color', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                jsonrpc: '2.0', method: 'call', id: 2,
                                params: { line_id: lineId, color: selectedColor },
                            }),
                        }).catch(function () {});
                    }).catch(function () {});
                }).catch(function () {});
            }
            return p;
        };
    }

    // ── Approach 3: click-listener on Add to Cart — most reliable fallback ──
    // Fires 1.2 s after the button click (enough for the cart update to finish)
    // and asks the server to apply the color to the most recently added line for
    // this product, regardless of which URL or format Odoo used for the cart call.
    var colorPicker = document.getElementById('rl_color_picker');
    var productTmplId = colorPicker && colorPicker.dataset.productTmplId;
    if (productTmplId) {
        document.addEventListener('click', function (e) {
            var btn = e.target.closest(
                '#add_to_cart, [name="add_to_cart"], ' +
                'button.o_website_sale_main_product_cart_btn, ' +
                'button.js_add_cart, ' +
                'form#product_detail_form button[type="submit"]'
            );
            if (!btn || !selectedColor) { return; }
            var colorAtClick = selectedColor;
            setTimeout(function () {
                fetch('/shop/apply_color_to_cart', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        jsonrpc: '2.0', method: 'call', id: 3,
                        params: { product_id: parseInt(productTmplId, 10), color: colorAtClick },
                    }),
                }).catch(function () {});
            }, 1200);
        }, true);

        // Pre-select the color remembered in the session (e.g. picked
        // before a login round-trip): the cart would apply it anyway, so
        // the swatch UI should show it too.
        fetch('/shop/rl_selected_color', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0', method: 'call', id: 32,
                params: { product_id: parseInt(productTmplId, 10) },
            }),
        }).then(function (res) { return res.json(); }).then(function (data) {
            var remembered = ((data && data.result) || {}).color;
            if (!remembered || selectedColor) return;
            var match = swatches.find(function (s) { return (s.dataset.color || '') === remembered; });
            if (match) { selectSwatch(match); }
        }).catch(function () {});
    }
}

// The order line description contains a raw "Color: X" text line (that is
// what makes the color show up in the backend, emails and invoices), but in
// the cart it renders as cramped plain text. Restyle it in place into the
// rl-cart-line-color pill with a swatch dot.
function rlBeautifyCartColorText() {
    var scope = document.querySelector('.oe_website_sale') || document.body;
    Array.from(scope.querySelectorAll('div, span, p, small, dd')).forEach(function (el) {
        if (el.childElementCount || el.classList.contains('rl-cart-line-color')) return;
        var match = (el.textContent || '').trim().match(/^Color:\s*(.{1,40})$/);
        if (!match) return;
        var color = match[1].trim();
        el.classList.add('rl-cart-line-color');
        el.textContent = '';
        var dot = document.createElement('span');
        dot.className = 'rl-cart-color-dot';
        dot.style.backgroundColor = color.toLowerCase();
        var name = document.createElement('strong');
        name.textContent = color;
        el.appendChild(dot);
        el.appendChild(name);
    });
    rlDedupeCartColorPills();
}

// Odoo renders the line description in more than one spot (e.g. under the
// product name and again inside the quantity control). Keep one pill per
// cart line - preferring the one outside the quantity widget - and hide
// the rest.
function rlDedupeCartColorPills() {
    var kept = new Map();
    Array.from(document.querySelectorAll('.rl-cart-line-color')).forEach(function (el) {
        var root = el.closest('[data-line-id], tr, li, .o_cart_product') || el.closest('.row') || document.body;
        var inQty = !!el.closest('.input-group, .css_quantity, [class*="quantity" i], [name*="quantity" i]');
        // The pill CSS uses display:inline-flex !important, so hiding must
        // be !important as well or it loses the cascade.
        function hide(node) { node.style.setProperty('display', 'none', 'important'); }
        function show(node) { node.style.removeProperty('display'); }
        var current = kept.get(root);
        if (!current) {
            kept.set(root, { el: el, inQty: inQty });
            show(el);
            return;
        }
        if (current.inQty && !inQty) {
            hide(current.el);
            kept.set(root, { el: el, inQty: inQty });
            show(el);
        } else {
            hide(el);
        }
    });
}

// Dress up the plain "Thank you for your order." confirmation page: a
// confirmed-hero with check mark, the build/delivery journey the brand
// promises, and clear next actions.
function setupOrderConfirmation() {
    if (!window.location.pathname.startsWith('/shop/confirmation')) return;
    document.documentElement.classList.add('rl-confirm-page');
    if (document.querySelector('.rl-confirm-wrap')) return;

    // Never inject into Odoo's own confirmation markup (its flex rows do
    // not wrap and squeeze anything we add). Render one self-contained
    // banner ABOVE the whole layout instead.
    var heading = Array.from(document.querySelectorAll('h1, h2, h3, .h1, .h2, .h3'))
        .find(function (el) { return /thank you/i.test(el.textContent || ''); });
    var host = (heading && heading.closest('.container, .container-fluid'))
        || document.querySelector('#wrap .container, #wrap .container-fluid')
        || document.getElementById('wrap');
    if (!host) return;

    var wrap = document.createElement('div');
    wrap.className = 'rl-confirm-wrap';

    var hero = document.createElement('div');
    hero.className = 'rl-confirm-hero';
    hero.innerHTML =
        '<div class="rl-confirm-check"><i class="fa fa-check"></i></div>' +
        '<div class="rl-confirm-hero-text">' +
        '<span>Order confirmed</span>' +
        '<p>We’ve received your order. Follow every step — build, packing and delivery — from your account.</p>' +
        '</div>';
    wrap.appendChild(hero);

    var steps = document.createElement('div');
    steps.className = 'rl-confirm-steps';
    [
        ['fa-clipboard', 'Order placed', 'We prepare your pieces', true],
        ['fa-wrench', 'Build & packing', 'Workshop photos as we go', false],
        ['fa-truck', 'Delivery', 'Straight to your door', false],
    ].forEach(function (step) {
        var item = document.createElement('div');
        item.className = 'rl-confirm-step' + (step[3] ? ' is-active' : '');
        item.innerHTML = '<i class="fa ' + step[0] + '"></i><strong></strong><span></span>';
        item.querySelector('strong').textContent = step[1];
        item.querySelector('span').textContent = step[2];
        steps.appendChild(item);
    });
    wrap.appendChild(steps);

    var actions = document.createElement('div');
    actions.className = 'rl-confirm-actions';
    actions.innerHTML =
        '<a class="btn btn-primary" href="/my/orders"><i class="fa fa-map-marker"></i> Track your order</a>' +
        '<a class="btn btn-outline-secondary" href="/shop"><i class="fa fa-arrow-left"></i> Continue shopping</a>';
    wrap.appendChild(actions);

    host.insertBefore(wrap, host.firstChild);
}

function setupCartLineColors() {
    var path = window.location.pathname;
    if (!path.startsWith('/shop/cart') && !path.startsWith('/shop/checkout')
        && !path.startsWith('/shop/address') && !path.startsWith('/shop/payment')) return;
    rlBeautifyCartColorText();
    // The cart re-renders lines after quantity changes; keep the pill styled.
    if (!window._rlCartColorObserver) {
        window._rlCartColorObserver = new MutationObserver(function () {
            window.clearTimeout(window._rlCartColorTimer);
            window._rlCartColorTimer = window.setTimeout(rlBeautifyCartColorText, 120);
        });
        window._rlCartColorObserver.observe(document.body, { childList: true, subtree: true });
    }
    fetch('/shop/cart_line_colors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 21, params: {} }),
    }).then(function (res) { return res.json(); }).then(function (data) {
        var result = (data && data.result) || data || {};
        var lines = result.lines || [];
        if (!lines.length) return;
        lines.forEach(function (line) {
            if (!line.color) return;
            var lineSelectors = [
                '[data-line-id="' + line.line_id + '"]',
                '[data-line_id="' + line.line_id + '"]',
                '[data-id="' + line.line_id + '"]',
            ];
            var host = null;
            lineSelectors.some(function (selector) {
                host = document.querySelector(selector);
                return !!host;
            });
            if (!host) {
                var names = [line.product, line.template].filter(Boolean);
                var targets = Array.from(document.querySelectorAll('a, strong, h6, .h6, .td-product_name, [class*="product_name"]'));
                var match = targets.find(function (el) {
                    var text = (el.textContent || '').trim();
                    return names.some(function (name) { return text === name || text.indexOf(name) !== -1; });
                });
                if (!match) return;
                host = match.closest('.td-product_name, td, .row, li, tr, div') || match.parentElement;
            }
            if (!host) return;
            // Skip if this cart line already shows the color (either injected
            // before, or restyled from the raw description text).
            var lineRoot = host.closest('tr, li, .row, [data-line-id]') || host;
            if (lineRoot.querySelector('.rl-cart-line-color') || host.querySelector('.rl-cart-line-color')) return;
            var anchor = host.querySelector('a, strong, h6, .h6, .td-product_name, [class*="product_name"]') || host;
            var detail = document.createElement('div');
            detail.className = 'rl-cart-line-color';
            var dot = document.createElement('span');
            dot.className = 'rl-cart-color-dot';
            dot.style.backgroundColor = String(line.color).toLowerCase();
            var name = document.createElement('strong');
            name.textContent = line.color;
            detail.appendChild(dot);
            detail.appendChild(name);
            anchor.insertAdjacentElement('afterend', detail);
        });
    }).catch(function () {});
}
function hideProductPolicies() {
    if (!window.location.pathname.startsWith('/shop/')) return;
    // Try the standard Odoo ID first.
    var section = document.getElementById('o_product_terms_and_share');
    if (section) { section.style.display = 'none'; return; }
    // Fallback: walk paragraphs and hide any that contain the policy text.
    document.querySelectorAll('p, small').forEach(function (el) {
        var t = el.textContent || '';
        if (t.indexOf('money-back') !== -1 || t.indexOf('Business Day') !== -1) {
            el.style.display = 'none';
        }
    });
}

function setupNotifyStock() {
    var btn = document.querySelector('.rl-notify-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
        var productId = btn.dataset.productId;
        var emailInput = document.querySelector('.rl-notify-email');
        var email = emailInput ? emailInput.value.trim() : '';
        if (emailInput && !email) {
            emailInput.classList.add('is-invalid');
            emailInput.focus();
            return;
        }
        if (emailInput) { emailInput.classList.remove('is-invalid'); }
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Saving…';
        fetch('/shop/notify_stock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0', method: 'call', id: 1,
                params: { product_id: parseInt(productId, 10), email: email },
            }),
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.result && data.result.ok) {
                var form = document.getElementById('rl_notify_form');
                var success = document.getElementById('rl_notify_success');
                if (form) { form.style.display = 'none'; }
                if (success) { success.style.display = ''; }
            } else {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa fa-bell"></i> Notify Me';
            }
        })
        .catch(function () {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-bell"></i> Notify Me';
        });
    });
}

function enhanceWebsite() {
    document.documentElement.classList.add('rl-site-ready');
    markShopPage();
    keepShopClean();
    setupProductQuantityPrice();
    setupHomepageHeroSlider();
    restoreShopSearchBar();
    hideProductPolicies();
    setupContactFormValidation();
    setupSaveForLaterRedirect();
    setupLoginPagePolish();
    setupRequireLoginForCart();
    setupColorSelection();
    setupCartLineColors();
    setupOrderConfirmation();
    setupNotifyStock();
    rememberCurrentProduct();
    renderRecentlyViewed();
    setupMobileShopFilters();
    setupBackToTop();
    const targets = prepareRevealTargets();
    setupRevealObserver(targets);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceWebsite, { once: true });
} else {
    enhanceWebsite();
}

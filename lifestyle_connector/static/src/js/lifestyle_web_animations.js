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

function setupProductCompare() {
    if (!window.location.pathname.startsWith('/shop')) return;

    const buttons = Array.from(document.querySelectorAll('[data-rl-compare-id]'));
    if (!buttons.length) return;

    let compareItems = getStoredJson('rl_compare_items', []);
    const tray = document.createElement('div');
    tray.className = 'rl-compare-tray';
    tray.innerHTML = '<h4>Compare furniture</h4><div class="rl-compare-list"></div><div class="rl-compare-actions"><button type="button" class="btn btn-primary btn-sm" data-rl-compare-open>Open Selected</button><button type="button" class="btn btn-outline-secondary btn-sm" data-rl-compare-clear>Clear</button></div>';
    document.body.appendChild(tray);

    const render = () => {
        const list = tray.querySelector('.rl-compare-list');
        list.innerHTML = '';
        compareItems.slice(0, 3).forEach((item) => {
            const row = document.createElement('div');
            row.className = 'rl-compare-item';
            row.innerHTML = `<div><strong>${item.name}</strong><span>${moneyLabel(item.price)}${item.room ? ' Â· ' + item.room : ''}</span></div><button type="button" class="btn btn-link btn-sm" data-rl-remove-compare="${item.id}">Remove</button>`;
            list.appendChild(row);
        });
        tray.classList.toggle('is-visible', compareItems.length > 0);
        setStoredJson('rl_compare_items', compareItems.slice(0, 3));
    };

    buttons.forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            const item = {
                id: button.dataset.rlCompareId,
                name: button.dataset.rlCompareName || 'Product',
                price: button.dataset.rlComparePrice || '0',
                url: button.dataset.rlCompareUrl || '#',
                room: button.dataset.rlCompareRoom || '',
            };
            compareItems = compareItems.filter((existing) => existing.id !== item.id);
            compareItems.unshift(item);
            compareItems = compareItems.slice(0, 3);
            render();
        });
    });

    tray.addEventListener('click', (event) => {
        const removeId = event.target.closest('[data-rl-remove-compare]')?.dataset.rlRemoveCompare;
        if (removeId) {
            compareItems = compareItems.filter((item) => item.id !== removeId);
            render();
            return;
        }
        if (event.target.closest('[data-rl-compare-clear]')) {
            compareItems = [];
            render();
            return;
        }
        if (event.target.closest('[data-rl-compare-open]') && compareItems[0]?.url) {
            window.location.href = compareItems[0].url;
        }
    });

    render();
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
function setupColorSelection() {
    const swatches = Array.from(document.querySelectorAll('#rl_color_picker .rl-pd-swatch[data-color]'));
    if (!swatches.length) return;

    let selectedColor = '';
    const label = document.getElementById('rl_color_chosen');
    const labelName = document.getElementById('rl_color_chosen_name');

    function ensureColorInput() {
        let input = document.getElementById('rl_selected_color_input');
        const form = document.querySelector('#product_detail form[action*="/shop/cart/update"]') ||
            document.querySelector('#product_details form[action*="/shop/cart/update"]') ||
            document.querySelector('form[action*="/shop/cart/update"]');
        if (!input && form) {
            input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'lifestyle_color';
            input.id = 'rl_selected_color_input';
            form.appendChild(input);
        } else if (input && form && input.form !== form) {
            form.appendChild(input);
        }
        return input;
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
                    params: { color: selectedColor },
                }),
            }).catch(function () {});
        }
    }

    ensureColorInput();

    swatches.forEach(function (swatch) {
        swatch.addEventListener('click', function () { selectSwatch(swatch); });
        swatch.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectSwatch(swatch); }
        });
    });

    // Intercept Odoo's cart-update fetch so we can apply the color to the exact
    // line_id that Odoo returns - belt-and-suspenders on top of the session approach.
    // Guard prevents double-patching if the function is called more than once.
    if (!window._rlCartFetchPatched) {
        window._rlCartFetchPatched = true;
        var _origFetch = window.fetch;
        window.fetch = function (input, init) {
            var url = typeof input === 'string' ? input : (input && input.url) || '';
            var p = _origFetch.apply(window, arguments);
            if (url.indexOf('cart/update') !== -1 || url.indexOf('_cart_update') !== -1) {
                p.then(function (res) {
                    res.clone().json().then(function (data) {
                        var lineId = data && data.result && data.result.line_id;
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
    setupColorSelection();
    rememberCurrentProduct();
    renderRecentlyViewed();
    setupProductCompare();
    setupMobileShopFilters();
    const targets = prepareRevealTargets();
    setupRevealObserver(targets);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceWebsite, { once: true });
} else {
    enhanceWebsite();
}


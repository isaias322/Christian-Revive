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
    window.setTimeout(hideShopCategoryTabs, 120);
    window.setTimeout(hideShopCategoryTabs, 650);

    if (!window.location.pathname.startsWith('/shop') || !('MutationObserver' in window)) return;
    const scope = document.querySelector('#wrap') || document.body;
    const observer = new MutationObserver(() => hideShopCategoryTabs());
    observer.observe(scope, { childList: true, subtree: true });
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
    if (slides.length <= 1) return;

    const prevButton = slider.querySelector('[data-rl-home-prev]');
    const nextButton = slider.querySelector('[data-rl-home-next]');
    const dots = Array.from(slider.querySelectorAll('[data-rl-home-dot]'));
    const autoplayInterval = Math.max(2500, parseInt(slider.dataset.rlHomeInterval || '4500', 10) || 4500);
    let activeIndex = slides.findIndex((slide) => slide.classList.contains('is-active'));
    let timer = null;
    activeIndex = activeIndex >= 0 ? activeIndex : 0;

    function paintDots() {
        const activeSlide = slides[activeIndex];
        const activeAccent = activeSlide
            ? getComputedStyle(activeSlide).getPropertyValue('--rl-slide-accent').trim() || '#D9B777'
            : '#D9B777';
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

function enhanceWebsite() {
    document.documentElement.classList.add('rl-site-ready');
    markShopPage();
    keepShopClean();
    setupProductQuantityPrice();
    setupHomepageHeroSlider();
    setupSaveForLaterRedirect();
    const targets = prepareRevealTargets();
    setupRevealObserver(targets);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceWebsite, { once: true });
} else {
    enhanceWebsite();
}

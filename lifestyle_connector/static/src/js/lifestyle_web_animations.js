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

function enhanceWebsite() {
    document.documentElement.classList.add('rl-site-ready');
    const targets = prepareRevealTargets();
    setupRevealObserver(targets);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceWebsite, { once: true });
} else {
    enhanceWebsite();
}

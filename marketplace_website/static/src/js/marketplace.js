/* Marketplace storefront interactions (vanilla JS, no framework deps). */
(function () {
    'use strict';

    function onReady(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    onReady(function () {
        // ------------------------------------------------------------
        // Scroll-reveal: fade+rise elements in as they enter view
        // ------------------------------------------------------------
        var revealTargets = document.querySelectorAll(
            '.mk-card, .mk-shop-tile, .mk-hero *, .mk-trust > div, .mk-stat, .mk-order-card');
        revealTargets.forEach(function (el) { el.classList.add('mk-reveal'); });
        if ('IntersectionObserver' in window && revealTargets.length) {
            var revealObserver = new IntersectionObserver(function (entries, obs) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('mk-visible');
                        obs.unobserve(entry.target);
                    }
                });
            }, {rootMargin: '0px 0px -40px 0px', threshold: .05});
            revealTargets.forEach(function (el) { revealObserver.observe(el); });
        } else {
            revealTargets.forEach(function (el) { el.classList.add('mk-visible'); });
        }

        // ------------------------------------------------------------
        // Fade images in once loaded instead of popping in abruptly,
        // and hide the skeleton shimmer behind them.
        // ------------------------------------------------------------
        document.querySelectorAll('.mk-card-img, .mk-gallery-main').forEach(
            function (img) {
                var markLoaded = function () {
                    img.classList.add('mk-loaded');
                    var wrap = img.closest('.mk-card-img-wrap');
                    if (wrap) { wrap.classList.add('mk-loaded'); }
                };
                if (img.complete && img.naturalWidth > 0) {
                    markLoaded();
                } else {
                    img.addEventListener('load', markLoaded);
                    img.addEventListener('error', markLoaded);
                }
            });

        // Note: Odoo's own frontend JS already disables the submit button
        // and shows a spinner (o_btn_loading) on form submit site-wide, so
        // no custom handling is needed here.

        // ------------------------------------------------------------
        // Item gallery: click a thumbnail to swap the main image
        // ------------------------------------------------------------
        var mainImg = document.getElementById('mkMainImage');
        if (mainImg) {
            var thumbs = document.querySelectorAll('.mk-gallery-thumb');
            thumbs.forEach(function (thumb) {
                thumb.addEventListener('click', function () {
                    mainImg.src = thumb.dataset.full || thumb.src;
                    thumbs.forEach(function (t) { t.classList.remove('active'); });
                    thumb.classList.add('active');
                });
            });
        }

        // ------------------------------------------------------------
        // Favourite toggle
        // ------------------------------------------------------------
        var favBtn = document.getElementById('mkFavBtn');
        if (favBtn) {
            favBtn.addEventListener('click', function () {
                var id = favBtn.dataset.listingId;
                fetch('/market/item/' + id + '/favorite', {method: 'POST'})
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        var icon = favBtn.querySelector('i');
                        var count = document.getElementById('mkFavCount');
                        icon.className = data.favorite ? 'fa fa-heart' : 'fa fa-heart-o';
                        if (count) { count.textContent = data.count; }
                        icon.classList.remove('mk-fav-pop');
                        // Force reflow so the animation replays on repeat clicks.
                        void icon.offsetWidth;
                        icon.classList.add('mk-fav-pop');
                    });
            });
        }

        // ------------------------------------------------------------
        // Follow toggle
        // ------------------------------------------------------------
        var followBtn = document.getElementById('mkFollowBtn');
        if (followBtn) {
            followBtn.addEventListener('click', function () {
                var id = followBtn.dataset.sellerId;
                fetch('/market/shop/' + id + '/follow', {method: 'POST'})
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        followBtn.textContent = data.following ? 'Following' : 'Follow';
                        followBtn.className = 'btn ' + (data.following ? 'btn-dark' : 'mk-btn');
                        var count = document.getElementById('mkFollowCount');
                        if (count) { count.textContent = data.count; }
                    });
            });
        }

        // ------------------------------------------------------------
        // Phone-type fields: strip anything that isn't a digit or basic
        // formatting character (+, -, space, parens) as the user types.
        // The server validates the same way regardless, but stopping
        // stray letters from being typed at all is the friendlier fix.
        // ------------------------------------------------------------
        document.querySelectorAll('.mk-phone-input').forEach(function (input) {
            input.addEventListener('input', function () {
                var cleaned = input.value.replace(/[^0-9+\-\s()]/g, '');
                if (cleaned !== input.value) { input.value = cleaned; }
            });
        });

        // ------------------------------------------------------------
        // Listing form: auto-calculate the sale price from Original
        // price + Discount %, so a seller never has to do the maths
        // themselves. The server recomputes this again on save
        // regardless — this is purely a live preview.
        // ------------------------------------------------------------
        var origPriceInput = document.getElementById('mkOriginalPrice');
        var discountInput = document.getElementById('mkDiscountPct');
        var priceInput = document.getElementById('mkPrice');
        if (origPriceInput && discountInput && priceInput) {
            var recalcPrice = function () {
                var original = parseFloat(origPriceInput.value);
                var discount = parseFloat(discountInput.value);
                if (original > 0 && discount > 0) {
                    priceInput.value = (original * (1 - discount / 100)).toFixed(2);
                }
            };
            origPriceInput.addEventListener('input', recalcPrice);
            discountInput.addEventListener('input', recalcPrice);
        }

        // ------------------------------------------------------------
        // Chat: scroll to bottom + poll for new messages
        // ------------------------------------------------------------
        var chatBox = document.getElementById('mkChatBox');
        if (chatBox) {
            chatBox.scrollTop = chatBox.scrollHeight;
            var threadId = chatBox.dataset.threadId;
            var lastId = parseInt(chatBox.dataset.lastId || '0', 10);

            function escapeHtml(text) {
                var div = document.createElement('div');
                div.appendChild(document.createTextNode(text));
                return div.innerHTML;
            }

            setInterval(function () {
                fetch('/market/messages/thread/' + threadId + '/poll?after=' + lastId)
                    .then(function (r) { return r.json(); })
                    .then(function (messages) {
                        messages.forEach(function (m) {
                            if (m.id <= lastId) { return; }
                            lastId = m.id;
                            var wrap = document.createElement('div');
                            wrap.className = 'mk-msg' + (m.mine ? ' mine' : '');
                            var photoHtml = m.image_url
                                ? '<img src="' + escapeHtml(m.image_url) + '" class="mk-msg-photo" alt="photo"/>'
                                : '';
                            wrap.innerHTML =
                                '<div class="mk-msg-bubble">' + photoHtml +
                                escapeHtml(m.body) + '</div>' +
                                '<div class="mk-msg-meta small text-muted">' +
                                escapeHtml(m.author) + '</div>';
                            chatBox.appendChild(wrap);
                        });
                        if (messages.length) {
                            chatBox.scrollTop = chatBox.scrollHeight;
                        }
                    })
                    .catch(function () { /* offline; retry next tick */ });
            }, 5000);
        }
    });
})();

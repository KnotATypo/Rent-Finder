(function () {
    // Simple touch-enabled carousel.
    const carousel = document.getElementById('carousel');
    if (!carousel) return;

    const slides = Array.from(carousel.querySelectorAll('.carousel-slide'));
    const prevBtn = carousel.querySelector('.carousel-prev');
    const nextBtn = carousel.querySelector('.carousel-next');
    const dots = Array.from(carousel.querySelectorAll('.dot'));
    let index = 0;

    function show(i) {
        index = (i + slides.length) % slides.length;
        slides.forEach((s, idx) => s.style.display = (idx === index) ? 'block' : 'none');
        dots.forEach((d, idx) => d.classList.toggle('active', idx === index));
    }

    function next() {
        show(index + 1);
    }

    function prev() {
        show(index - 1);
    }

    if (nextBtn) nextBtn.addEventListener('click', next);
    if (prevBtn) prevBtn.addEventListener('click', prev);
    dots.forEach((d, idx) => d.addEventListener('click', () => show(idx)));

    // touch handling: detect horizontal swipe only
    let startX = 0, startY = 0, isMoving = false;
    carousel.addEventListener('touchstart', function (e) {
        const t = e.touches[0];
        startX = t.clientX;
        startY = t.clientY;
        isMoving = true;
    }, {passive: true});

    carousel.addEventListener('touchmove', function (e) {
        if (!isMoving) return;
        const t = e.touches[0];
        const dx = t.clientX - startX;
        const dy = t.clientY - startY;
        // if vertical movement is larger than horizontal, don't treat as swipe
        if (Math.abs(dy) > Math.abs(dx)) {
            isMoving = false;
            return;
        }
        // prevent horizontal scroll of page
        e.preventDefault();
    }, {passive: false});

    carousel.addEventListener('touchend', function (e) {
        if (!isMoving) return;
        const t = e.changedTouches[0];
        const dx = t.clientX - startX;
        const dy = t.clientY - startY;
        if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) {
            if (dx < 0) next(); else prev();
        }
        isMoving = false;
    });

    // Initialize
    show(0);
})();

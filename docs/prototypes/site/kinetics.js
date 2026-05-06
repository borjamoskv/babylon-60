(() => {
    const root = document.documentElement;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const updatePointer = (event) => {
        root.style.setProperty('--kx', `${event.clientX}px`);
        root.style.setProperty('--ky', `${event.clientY}px`);
    };

    window.addEventListener('pointermove', updatePointer, { passive: true });

    document.querySelectorAll('.btn, .card, .grid article').forEach((element) => {
        element.addEventListener('pointermove', (event) => {
            const rect = element.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * 100;
            const y = ((event.clientY - rect.top) / rect.height) * 100;
            element.style.setProperty('--btn-x', `${x}%`);
            element.style.setProperty('--btn-y', `${y}%`);
            element.style.setProperty('--kx-local', `${x}%`);
            element.style.setProperty('--ky-local', `${y}%`);
        }, { passive: true });
    });

    if (!reduce) {
        const field = document.createElement('div');
        field.className = 'kinetic-field';
        field.setAttribute('aria-hidden', 'true');
        for (let i = 0; i < 42; i += 1) {
            const bit = document.createElement('span');
            bit.className = 'kinetic-bit';
            bit.style.left = `${Math.random() * 100}%`;
            bit.style.setProperty('--duration', `${9 + Math.random() * 13}s`);
            bit.style.setProperty('--delay', `${Math.random() * -16}s`);
            bit.style.setProperty('--drift', `${-90 + Math.random() * 180}px`);
            field.appendChild(bit);
        }
        document.body.prepend(field);

        const revealItems = document.querySelectorAll('.hero, .card, .grid article, .cta, .langbar');
        revealItems.forEach((element) => element.classList.add('reveal-ready'));
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('reveal-in');
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.12 });
        revealItems.forEach((element, index) => {
            element.style.transitionDelay = `${Math.min(index * 45, 320)}ms`;
            observer.observe(element);
        });
    }
})();

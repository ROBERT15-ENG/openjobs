(function () {
  'use strict';

  const header = document.querySelector('.site-header');
  const navToggle = document.querySelector('.nav-toggle');
  const siteNav = document.querySelector('.site-nav');
  const navLinks = siteNav.querySelectorAll('a');
  const form = document.getElementById('quote-form');
  const formStatus = document.getElementById('form-status');

  /* Scroll: header shadow */
  function onScroll() {
    header.classList.toggle('scrolled', window.scrollY > 20);
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* Mobile navigation */
  navToggle.addEventListener('click', function () {
    const expanded = navToggle.getAttribute('aria-expanded') === 'true';
    navToggle.setAttribute('aria-expanded', String(!expanded));
    navToggle.setAttribute('aria-label', expanded ? 'Open menu' : 'Close menu');
    siteNav.classList.toggle('open', !expanded);
  });

  navLinks.forEach(function (link) {
    link.addEventListener('click', function () {
      navToggle.setAttribute('aria-expanded', 'false');
      navToggle.setAttribute('aria-label', 'Open menu');
      siteNav.classList.remove('open');
    });
  });

  /* Quote form */
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      formStatus.className = 'form-note';
      formStatus.textContent = '';

      const name = form.name.value.trim();
      const email = form.email.value.trim();
      const phone = form.phone.value.trim();
      const message = form.message.value.trim();

      if (!name || !email || !phone || !message) {
        formStatus.className = 'form-note error';
        formStatus.textContent = 'Please fill in all required fields.';
        return;
      }

      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        formStatus.className = 'form-note error';
        formStatus.textContent = 'Please enter a valid email address.';
        return;
      }

      const subject = encodeURIComponent('Quote Request from ' + name);
      const body = encodeURIComponent(
        'Name: ' + name + '\n' +
        'Company: ' + (form.company.value.trim() || 'N/A') + '\n' +
        'Email: ' + email + '\n' +
        'Phone: ' + phone + '\n' +
        'Service: ' + (form.service.value || 'Not specified') + '\n\n' +
        'Message:\n' + message
      );

      window.location.href = 'mailto:info@cleanscapesolutions.com.au?subject=' + subject + '&body=' + body;

      formStatus.className = 'form-note success';
      formStatus.textContent = 'Thank you! Your email client should open shortly. We\'ll be in touch within 24 hours.';
      form.reset();
    });
  }

  /* Fade-in on scroll */
  const observerTargets = document.querySelectorAll(
    '.service-card, .testimonial, .feature, .industry-tag, .about-card'
  );

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
    );

    observerTargets.forEach(function (el, i) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity 0.5s ease ' + (i % 6) * 0.06 + 's, transform 0.5s ease ' + (i % 6) * 0.06 + 's';
      observer.observe(el);
    });
  }
})();

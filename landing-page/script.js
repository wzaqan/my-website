(function () {
  const root = document.documentElement;
  const themeToggleButton = document.getElementById('themeToggle');
  const menu = document.getElementById('menu');
  const navToggle = document.querySelector('.nav-toggle');
  const yearEl = document.getElementById('year');

  // Year
  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }

  // Theme
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'light' || savedTheme === 'dark') {
    if (savedTheme === 'light') {
      root.setAttribute('data-theme', 'light');
    } else {
      root.removeAttribute('data-theme');
    }
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    root.setAttribute('data-theme', 'light');
  }

  function toggleTheme() {
    const isLight = root.getAttribute('data-theme') === 'light';
    if (isLight) {
      root.removeAttribute('data-theme');
      localStorage.setItem('theme', 'dark');
    } else {
      root.setAttribute('data-theme', 'light');
      localStorage.setItem('theme', 'light');
    }
  }

  if (themeToggleButton) {
    themeToggleButton.addEventListener('click', toggleTheme);
  }

  // Mobile menu
  if (navToggle && menu) {
    navToggle.addEventListener('click', () => {
      const isOpen = menu.style.display === 'flex';
      menu.style.display = isOpen ? 'none' : 'flex';
      navToggle.setAttribute('aria-expanded', String(!isOpen));
    });

    menu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 720) {
          menu.style.display = 'none';
          navToggle.setAttribute('aria-expanded', 'false');
        }
      });
    });
  }

  // Smooth reveal on scroll
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );
  document.querySelectorAll('[data-animate]').forEach((el) => observer.observe(el));

  // Form handling
  const leadForm = document.getElementById('leadForm');
  const emailInput = document.getElementById('email');

  function isValidEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  if (leadForm && emailInput) {
    leadForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = emailInput.value.trim();
      if (!isValidEmail(email)) {
        emailInput.setCustomValidity('يرجى إدخال بريد إلكتروني صالح');
        emailInput.reportValidity();
        return;
      }
      emailInput.setCustomValidity('');
      const btn = leadForm.querySelector('button[type="submit"]');
      const original = btn.textContent;
      btn.disabled = true;
      btn.textContent = '...يتم الإرسال';

      // Mock async submit
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = original;
        leadForm.reset();
        alert('شكرًا لك! سنرسل لك الدعوة قريبًا.');
      }, 900);
    });
  }
})();
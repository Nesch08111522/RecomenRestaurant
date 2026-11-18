/* SmartResto · Experiencia de autenticación: transición horizontal,
   validación en tiempo real, fortaleza de contraseña, parallax y envío seguro. */
(() => {
  const stage = document.getElementById('ax-stage');
  if (!stage) return;

  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const DURATION = 820;
  const panes = { login: stage.querySelector('[data-pane="login"]'), register: stage.querySelector('[data-pane="register"]') };
  const titles = { login: 'Iniciar sesión · SmartResto', register: 'Crear cuenta · SmartResto' };
  let locked = false;

  /* == Transición login <-> registro == */
  function applyMode(mode) {
    stage.dataset.mode = mode;
    for (const [name, pane] of Object.entries(panes)) {
      const active = name === mode;
      pane.toggleAttribute('inert', !active);
      pane.setAttribute('aria-hidden', String(!active));
    }
    document.title = titles[mode];
  }

  function switchMode(mode, push) {
    if (locked || stage.dataset.mode === mode) return;
    locked = true;
    applyMode(mode);
    if (push) {
      const url = (mode === 'register' ? stage.dataset.registerUrl : stage.dataset.loginUrl) + location.search;
      history.pushState({ axMode: mode }, '', url);
    }
    setTimeout(() => { locked = false; }, reduceMotion.matches ? 0 : DURATION);
  }

  stage.querySelectorAll('[data-ax-switch]').forEach(link => {
    link.addEventListener('click', event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
      event.preventDefault();
      switchMode(link.dataset.axSwitch, true);
    });
  });

  window.addEventListener('popstate', () => {
    const mode = location.pathname.replace(/\/+$/, '').endsWith('/register') ? 'register' : 'login';
    locked = false;
    applyMode(mode);
  });

  applyMode(stage.dataset.mode === 'register' ? 'register' : 'login');

  /* == Mostrar / ocultar contraseña == */
  stage.querySelectorAll('[data-toggle-password]').forEach(button => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.togglePassword);
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.setAttribute('aria-pressed', String(show));
      button.setAttribute('aria-label', show ? 'Ocultar contraseña' : 'Mostrar contraseña');
      button.querySelector('[data-eye-open]').hidden = show;
      button.querySelector('[data-eye-closed]').hidden = !show;
      input.focus({ preventScroll: true });
    });
  });

  /* == Validación en tiempo real == */
  const messages = {
    'ax-login-username': 'Ingresa tu usuario o correo.',
    'ax-login-password': 'Ingresa tu contraseña.',
    'ax-reg-name': 'Ingresa tu nombre completo.',
    'ax-reg-username': 'Usa de 3 a 80 caracteres: letras, números o guión bajo.',
    'ax-reg-email': 'Ingresa un correo electrónico válido.',
    'ax-reg-password': 'Mínimo 8 caracteres, con letras y números.',
    'ax-reg-confirm': 'Las contraseñas no coinciden.'
  };

  function errorNode(input) { return stage.querySelector(`[data-error-for="${input.id}"]`); }

  function customError(input) {
    const value = input.value;
    switch (input.id) {
      case 'ax-reg-username':
        return value && !/^[a-zA-Z0-9_]{3,80}$/.test(value) ? messages[input.id] : '';
      case 'ax-reg-email':
        return value && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) ? messages[input.id] : '';
      case 'ax-reg-password':
        return value && !(value.length >= 8 && /[a-zA-Z]/.test(value) && /\d/.test(value)) ? messages[input.id] : '';
      case 'ax-reg-confirm': {
        const password = document.getElementById('ax-reg-password');
        return value && value !== password.value ? messages[input.id] : '';
      }
      default:
        return '';
    }
  }

  function paint(input, message) {
    const node = errorNode(input);
    if (node) { node.textContent = message; node.hidden = !message; }
    if (message) input.setAttribute('aria-invalid', 'true');
    else input.removeAttribute('aria-invalid');
  }

  function validate(input, reportEmpty) {
    let message = customError(input);
    if (!message && reportEmpty && input.required && !input.value.trim()) message = messages[input.id] || 'Este campo es obligatorio.';
    paint(input, message);
    return !message;
  }

  const fields = [...stage.querySelectorAll('.ax-form input:not([type="hidden"])')];
  fields.forEach(input => {
    input.addEventListener('blur', () => { if (input.value || input.dataset.touched) { input.dataset.touched = '1'; validate(input, true); } });
    input.addEventListener('input', () => {
      if (input.dataset.touched) validate(input, false);
      if (input.id === 'ax-reg-password') {
        updateStrength(input.value);
        const confirm = document.getElementById('ax-reg-confirm');
        if (confirm.dataset.touched) validate(confirm, false);
      }
    });
  });

  /* == Fortaleza de contraseña == */
  const strength = document.getElementById('ax-strength');
  const strengthText = document.getElementById('ax-strength-text');
  const strengthLabels = ['Usa al menos 8 caracteres con letras y números.', 'Débil: añade letras y números.', 'Aceptable: prueba con más longitud.', 'Buena: casi lista.', 'Excelente: contraseña robusta.'];
  function updateStrength(value) {
    if (!strength) return;
    let score = 0;
    if (value.length >= 8) score++;
    if (/[a-zA-Z]/.test(value) && /\d/.test(value)) score++;
    if (value.length >= 12) score++;
    if (/[^a-zA-Z0-9]/.test(value) || (/[a-z]/.test(value) && /[A-Z]/.test(value))) score++;
    if (!value) score = 0;
    strength.dataset.score = String(score);
    strengthText.textContent = strengthLabels[score];
  }

  /* == Indicaciones según el tipo de cuenta == */
  const roleSelect = document.getElementById('ax-reg-role');
  const roleHint = document.getElementById('ax-role-hint');
  const roleHints = {
    user: 'Como cliente podrás guardar favoritos, pedir en el mercado y reseñar restaurantes.',
    business_owner: 'Como empresario podrás agregar y gestionar tus propios restaurantes.'
  };
  if (roleSelect && roleHint) {
    roleSelect.addEventListener('change', () => { roleHint.textContent = roleHints[roleSelect.value] || roleHints.user; });
  }

  /* == Envío: validar y prevenir duplicados == */
  stage.querySelectorAll('.ax-form').forEach(form => {
    form.addEventListener('submit', event => {
      const inputs = [...form.querySelectorAll('input:not([type="hidden"])')];
      let firstInvalid = null;
      inputs.forEach(input => {
        input.dataset.touched = '1';
        if (!validate(input, true) && !firstInvalid) firstInvalid = input;
      });
      const otp = form.querySelector('[name="otp"]');
      if (otp && otp.value && !/^[0-9]{6}$/.test(otp.value)) {
        paint(otp, 'El código debe tener seis dígitos.');
        firstInvalid = firstInvalid || otp;
      }
      if (firstInvalid) {
        event.preventDefault();
        firstInvalid.focus();
        return;
      }
      const button = form.querySelector('.ax-submit');
      if (button.disabled) { event.preventDefault(); return; }
      button.classList.add('is-loading');
      button.setAttribute('aria-busy', 'true');
      setTimeout(() => { button.disabled = true; }, 0);
    });
  });

  /* == Parallax sutil del panel 3D == */
  const finePointer = matchMedia('(pointer: fine)');
  let frame = null;
  stage.addEventListener('pointermove', event => {
    if (reduceMotion.matches || !finePointer.matches || innerWidth < 900 || frame) return;
    frame = requestAnimationFrame(() => {
      const rect = stage.getBoundingClientRect();
      stage.style.setProperty('--ax-px', ((event.clientX - rect.left) / rect.width * 2 - 1).toFixed(3));
      stage.style.setProperty('--ax-py', ((event.clientY - rect.top) / rect.height * 2 - 1).toFixed(3));
      frame = null;
    });
  });
  stage.addEventListener('pointerleave', () => {
    stage.style.setProperty('--ax-px', '0');
    stage.style.setProperty('--ax-py', '0');
  });
})();
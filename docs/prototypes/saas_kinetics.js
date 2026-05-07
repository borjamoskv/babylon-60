(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const nav = document.getElementById('nav');
  const hero = document.querySelector('.hero-awwwards h1');

  if (!reduce && hero && !hero.dataset.kineticWords) {
    const words = hero.textContent.trim().split(/\s+/);
    hero.textContent = '';
    words.forEach((word, index) => {
      const span = document.createElement('span');
      span.className = 'kinetic-word';
      span.style.setProperty('--word-index', index);
      span.textContent = word + (index === words.length - 1 ? '' : ' ');
      hero.appendChild(span);
    });
    hero.dataset.kineticWords = 'true';
  }

  if (!reduce && !document.querySelector('.kinetic-marquee')) {
    const marquee = document.createElement('div');
    marquee.className = 'kinetic-marquee';
    marquee.setAttribute('aria-hidden', 'true');
    marquee.innerHTML = '<span>VERIFIABLE MEMORY / CRYPTO AUDIT / NFT EVIDENCE / AGENT TRUST / VERIFIABLE MEMORY / CRYPTO AUDIT / NFT EVIDENCE / AGENT TRUST / </span>';
    document.querySelector('.metrics')?.before(marquee);
  }

  const revealTargets = document.querySelectorAll('section, .metric-card, .api-card, .research-card, .plan, .crypto-tax-grid article, .reference-agent-flow article, .compare-table-wrap');
  revealTargets.forEach((el, index) => {
    el.dataset.reveal = '';
    el.style.transitionDelay = `${Math.min(index % 8, 7) * 55}ms`;
  });
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    revealTargets.forEach((el) => observer.observe(el));
  } else {
    revealTargets.forEach((el) => el.classList.add('is-visible'));
  }

  const tiltTargets = document.querySelectorAll('.feature-card, .api-card, .research-card, .plan, .tax-ledger-card, .reference-agent-passport, .evidence-console');
  tiltTargets.forEach((el) => {
    el.dataset.tilt = '';
    if (reduce) return;
    el.addEventListener('pointermove', (event) => {
      const rect = el.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      el.style.transform = `perspective(1100px) rotateX(${(-y * 5).toFixed(2)}deg) rotateY(${(x * 7).toFixed(2)}deg) translateY(-4px)`;
    });
    el.addEventListener('pointerleave', () => {
      el.style.transform = '';
    });
  });

  if (!reduce) {
    const cursor = document.createElement('div');
    cursor.className = 'kinetic-cursor';
    document.body.appendChild(cursor);
    let cx = window.innerWidth / 2;
    let cy = window.innerHeight / 2;
    let tx = cx;
    let ty = cy;
    window.addEventListener('pointermove', (event) => {
      tx = event.clientX;
      ty = event.clientY;
      cursor.classList.add('active');
    }, { passive: true });
    const tick = () => {
      cx += (tx - cx) * 0.12;
      cy += (ty - cy) * 0.12;
      cursor.style.transform = `translate3d(${cx - 130}px, ${cy - 130}px, 0)`;
      requestAnimationFrame(tick);
    };
    tick();
  }

  const onScroll = () => {
    if (nav) nav.classList.toggle('nav-kinetic', window.scrollY > 18);
    if (!reduce) {
      const y = window.scrollY;
      document.documentElement.style.setProperty('--scroll-glow', `${Math.min(y / 900, 1)}`);
      document.querySelectorAll('.proof-orbit').forEach((el) => {
        el.style.translate = `0 ${Math.min(y * 0.04, 24)}px`;
      });
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();

(() => {
  const cases = {
    crypto: {
      kicker: 'Fiscal evidence pack',
      title: 'Auditoría blockchain y NFTs para revisión fiscal.',
      copy: 'Reconstruye wallets, exchanges, swaps, ventas NFT, royalties, fees y gaps de custodia en un expediente técnico trazable para asesor fiscal.',
      tags: ['wallet graph', 'tx hash', 'cost basis', 'PDF + CSV'],
      score: 96,
      checks: ['Hay múltiples fuentes que reconciliar.', 'Necesitas explicar decisiones meses después.', 'Un tercero revisará la evidencia.'],
      input: 'Wallets + exchange CSVs + NFT marketplaces',
      process: 'Classify, hash, flag gaps, seal evidence',
      output: 'Advisor-ready PDF, CSV, manifest'
    },
    agent: {
      kicker: 'Agent memory passport',
      title: 'Un agente que recuerda sin inventarse el pasado.',
      copy: 'CORTEX separa memoria útil de hechos admitidos: preferencias, decisiones, tareas, handoffs y contexto de proyecto con alcance por tenant.',
      tags: ['preferences', 'handoff', 'tenant scope', 'ledger'],
      score: 91,
      checks: ['El agente opera durante semanas o meses.', 'Hay decisiones que no pueden perderse.', 'Necesitas transferir contexto entre herramientas.'],
      input: 'Chats, project decisions, tasks, agent events',
      process: 'Guard, scope, persist, retrieve, verify',
      output: 'Portable memory passport for the agent'
    },
    research: {
      kicker: 'Deep research crystallization',
      title: 'Investigación que no muere en un transcript.',
      copy: 'Convierte auditorías, comparativas, análisis de repos y research competitivo en cristales de conocimiento con fuente, fecha y trazabilidad.',
      tags: ['source trail', 'findings', 'crystals', 'exports'],
      score: 88,
      checks: ['Hay fuentes y conclusiones que separar.', 'El informe se reutilizará después.', 'Importa distinguir evidencia de hipótesis.'],
      input: 'Sources, repos, notes, audit prompts',
      process: 'Acquire, analyze, classify, crystallize',
      output: 'Reusable evidence-backed research pack'
    },
    incident: {
      kicker: 'Incident reconstruction',
      title: 'Reconstruir qué sabía el sistema cuando falló.',
      copy: 'Para bugs, incidentes de seguridad o decisiones automáticas, CORTEX ayuda a reconstruir memoria, timeline, validaciones y estado persistido.',
      tags: ['timeline', 'guards', 'audit log', 'postmortem'],
      score: 93,
      checks: ['Hay una decisión automatizada en disputa.', 'Necesitas timeline verificable.', 'La respuesta debe sobrevivir a una auditoría.'],
      input: 'Events, memory writes, guard failures, ledger entries',
      process: 'Replay, verify chain, identify divergence',
      output: 'Postmortem timeline with proof anchors'
    }
  };
  const root = document.querySelector('[data-usecase-console]');
  if (!root) return;
  const els = {
    tabs: root.querySelectorAll('.usecase-tab'),
    main: root.querySelector('.usecase-main'),
    proof: root.querySelector('.usecase-proof'),
    flow: root.querySelector('.usecase-flow'),
    kicker: document.getElementById('usecase-kicker'),
    title: document.getElementById('usecase-title'),
    copy: document.getElementById('usecase-copy'),
    tags: document.getElementById('usecase-tags'),
    score: document.getElementById('usecase-score'),
    meter: document.getElementById('usecase-meter'),
    checks: document.getElementById('usecase-checks'),
    input: document.getElementById('usecase-input'),
    process: document.getElementById('usecase-process'),
    output: document.getElementById('usecase-output')
  };
  const render = (key) => {
    const item = cases[key] || cases.crypto;
    els.tabs.forEach((tab) => {
      const active = tab.dataset.usecase === key;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    [els.main, els.proof, els.flow].forEach((el) => {
      el.classList.remove('is-swapping');
      void el.offsetWidth;
      el.classList.add('is-swapping');
    });
    els.kicker.textContent = item.kicker;
    els.title.textContent = item.title;
    els.copy.textContent = item.copy;
    els.tags.innerHTML = item.tags.map((tag) => `<em>${tag}</em>`).join('');
    els.score.textContent = item.score;
    els.meter.style.width = `${item.score}%`;
    els.checks.innerHTML = item.checks.map((check) => `<li>${check}</li>`).join('');
    els.input.textContent = item.input;
    els.process.textContent = item.process;
    els.output.textContent = item.output;
  };
  els.tabs.forEach((tab) => tab.addEventListener('click', () => render(tab.dataset.usecase)));
})();

(() => {
  const root = document.querySelector('[data-fiscal-checklist]');
  if (!root) return;
  const inputs = [...root.querySelectorAll('input[type="checkbox"]')];
  const count = document.getElementById('fiscal-check-count');
  const meter = document.getElementById('fiscal-check-meter');
  const update = () => {
    const checked = inputs.filter((input) => input.checked).length;
    count.textContent = String(checked);
    meter.style.width = `${Math.round((checked / inputs.length) * 100)}%`;
  };
  inputs.forEach((input) => input.addEventListener('change', update));
  update();
})();

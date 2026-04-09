/**
 * Digital Services CM — Enterprise JS v3.0
 * Fonctions globales : horloge, sidebar stats, recherche, utils
 */

'use strict';

/* ═══════════════════════════════════════════
   HORLOGE LIVE
═══════════════════════════════════════════ */
function updateClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  const date = `${pad(now.getDate())}/${pad(now.getMonth()+1)}/${now.getFullYear()}`;
  const time = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  el.textContent = `${date}  ${time}`;
}
setInterval(updateClock, 1000);
updateClock();


/* ═══════════════════════════════════════════
   SIDEBAR STATS — mise à jour depuis l'API
═══════════════════════════════════════════ */
function fmt(v) {
  return new Intl.NumberFormat('fr-FR').format(Math.round(v));
}

function fmtShort(v) {
  const a = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (a >= 1_000_000) return sign + (a / 1_000_000).toFixed(1) + 'M';
  if (a >= 1_000)     return sign + Math.round(a / 1000) + 'K';
  return sign + Math.round(a);
}

async function updateSidebar() {
  try {
    const res  = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();

    // KPI total
    const totalEl = document.getElementById('sb-total-val');
    const margeEl = document.getElementById('sb-marge-val');
    if (totalEl) {
      totalEl.textContent   = fmt(data.total_benefice) + ' FCFA';
      totalEl.style.color   = data.total_benefice >= 0 ? 'var(--gold)' : 'var(--danger)';
    }
    if (margeEl) {
      margeEl.textContent = `Marge : ${data.marge_moy}%`;
      margeEl.style.color = data.marge_moy >= 50 ? 'var(--success)' : 'var(--warn)';
    }

    // Mini stats
    const setEl = (id, val, color) => {
      const el = document.getElementById(id);
      if (el) { el.textContent = val; if (color) el.style.color = color; }
    };

    setEl('sb-jour',    fmtShort(data.benefice_jour) + ' FCFA',
          data.benefice_jour >= 0 ? 'var(--success)' : 'var(--danger)');
    setEl('sb-mois',    fmtShort(data.benefice_mois) + ' FCFA',
          data.benefice_mois >= 0 ? 'var(--blue)'    : 'var(--danger)');
    setEl('sb-clients', data.clients_count);
    setEl('sb-txs',     data.total_transactions);

    // Badge transactions nav
    const badgeTx = document.getElementById('sb-badge-tx');
    if (badgeTx) badgeTx.textContent = data.total_transactions;

    // Badge alertes (rail + sidebar)
    const badgeAlerts  = document.getElementById('sb-badge-alerts');
    const railBadge    = document.getElementById('rail-alert-badge');
    if (badgeAlerts) {
      badgeAlerts.textContent = data.alertes || '0';
      badgeAlerts.style.display = data.alertes > 0 ? '' : 'none';
    }
    if (railBadge) {
      if (data.alertes > 0) {
        railBadge.textContent = data.alertes;
        railBadge.style.display = 'flex';
      } else {
        railBadge.style.display = 'none';
      }
    }

    // Statusbar
    setEl('status-tx', data.total_transactions + ' transactions');

  } catch (e) {
    console.warn('Sidebar stats error:', e);
  }
}

// ── Badge messages support (admin seulement) ─────────────────────────────────
async function updateSupportBadge() {
  try {
    const resp = await fetch('/support/api/count');
    if (!resp.ok) return;
    const data = await resp.json();
    const badge = document.getElementById('sb-badge-support');
    if (!badge) return;
    if (data.count > 0) {
      badge.textContent = data.count;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  } catch(e) {}
}

// Lancer au chargement + toutes les 30 secondes
document.addEventListener('DOMContentLoaded', () => {
  updateSidebar();
  updateSupportBadge();
  setInterval(updateSidebar, 30_000);
  setInterval(updateSupportBadge, 60_000);
});


/* ═══════════════════════════════════════════
   RECHERCHE GLOBALE → redirect transactions
═══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('global-search');
  if (!searchInput) return;

  let debounceTimer;
  searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const q = searchInput.value.trim();
      if (q) {
        window.location.href = `/transactions/?search=${encodeURIComponent(q)}`;
      }
    }
  });

  // Debounce pour redirect automatique après 600ms
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = searchInput.value.trim();
    if (q.length >= 3) {
      debounceTimer = setTimeout(() => {
        // Ne redirige pas automatiquement, attend Enter
      }, 600);
    }
  });
});


/* ═══════════════════════════════════════════
   FLASH MESSAGES — auto-dismiss
═══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });
});


/* ═══════════════════════════════════════════
   CONFIRM SUPPRESSION — boutons danger
═══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      if (!confirm(el.dataset.confirm)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });
});


/* ═══════════════════════════════════════════
   STATUS MESSAGE
═══════════════════════════════════════════ */
function setStatus(msg, color) {
  const el = document.getElementById('status-msg');
  if (!el) return;
  el.textContent = msg;
  if (color) el.style.color = color;
  setTimeout(() => {
    el.textContent = 'Prêt.';
    el.style.color = '';
  }, 4000);
}


/* ═══════════════════════════════════════════
   TOOLTIP RAIL — positionner correctement
═══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.rail-icon').forEach(icon => {
    icon.addEventListener('mouseenter', () => {
      const tooltip = icon.querySelector('.rail-tooltip');
      if (!tooltip) return;
      const rect = icon.getBoundingClientRect();
      tooltip.style.top = `${rect.top + rect.height / 2 - tooltip.offsetHeight / 2}px`;
    });
  });
});

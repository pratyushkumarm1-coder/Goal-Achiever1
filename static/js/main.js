// ── Theme Toggle (Dark Mode) ─────────────────────────
const THEME_KEY = 'ga_theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-bs-theme', theme);
  document.querySelectorAll('#themeToggle').forEach(btn => {
    btn.innerHTML = theme === 'dark' ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
  });
}

document.querySelectorAll('#themeToggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  });
});
applyTheme(localStorage.getItem(THEME_KEY) || 'light');

// ── Sidebar Toggle ───────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('sidebarToggle');

if (toggleBtn && sidebar) {
  toggleBtn.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      sidebar.classList.toggle('mobile-open');
    } else {
      sidebar.classList.toggle('collapsed');
      const main = document.querySelector('.main-wrapper');
      if (main) main.classList.toggle('sidebar-collapsed');
    }
  });
}

// Auto-dismiss alerts
document.querySelectorAll('.custom-alert').forEach(el => {
  setTimeout(() => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
    if (bsAlert) bsAlert.close();
  }, 4000);
});

// ── Toggle Habit (AJAX) ──────────────────────────────────
function toggleHabit(habitId, csrfToken) {
  fetch(`/habits/${habitId}/toggle/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
  })
  .then(res => res.json())
  .then(data => {
    const card = document.getElementById(`habit-card-${habitId}`);
    const buttons = document.querySelectorAll(`[onclick*="toggleHabit(${habitId}"]`);

    if (data.status === 'completed') {
      if (card) card.classList.add('completed');
      buttons.forEach(btn => {
        btn.classList.add('completed');
        const icon = btn.querySelector('i');
        if (icon) { icon.className = 'bi bi-check-circle-fill'; }
        if (btn.id === 'mainToggleBtn') btn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Completed! 🎉';
      });
      showXPToast(data.xp_earned, data.total_xp, data.level);
      showConfetti();
    } else {
      if (card) card.classList.remove('completed');
      buttons.forEach(btn => {
        btn.classList.remove('completed');
        const icon = btn.querySelector('i');
        if (icon) { icon.className = 'bi bi-circle'; }
        if (btn.id === 'mainToggleBtn') btn.innerHTML = '<i class="bi bi-circle me-2"></i>Mark Complete';
      });
    }

    // Update streak displays
    const streakEls = document.querySelectorAll(`[data-streak-habit="${habitId}"]`);
    streakEls.forEach(el => { el.textContent = `🔥 ${data.streak}d`; });
  })
  .catch(err => console.error('Toggle error:', err));
}

// ── XP Toast ─────────────────────────────────────────────
function showXPToast(xpEarned, totalXp, level) {
  const container = document.getElementById('xpToastContainer');
  if (!container) return;

  const toastEl = document.createElement('div');
  toastEl.className = 'xp-toast fade show';
  toastEl.innerHTML = `
    <div class="d-flex align-items-center gap-2">
      <span style="font-size:1.4rem">⭐</span>
      <div>
        <div class="fw-bold">+${xpEarned} XP Earned!</div>
        <small class="text-muted">Total: ${totalXp} XP · Level ${level}</small>
      </div>
    </div>`;
  container.appendChild(toastEl);
  setTimeout(() => { toastEl.style.opacity = '0'; toastEl.style.transition = 'opacity 0.5s'; setTimeout(() => toastEl.remove(), 500); }, 3000);
}

// ── Confetti ──────────────────────────────────────────────
function showConfetti() {
  const colors = ['#6c5ce7','#fd79a8','#00b894','#fdcb6e','#a29bfe'];
  for (let i = 0; i < 30; i++) {
    const el = document.createElement('div');
    const size = Math.random() * 8 + 4;
    el.style.cssText = `
      position:fixed; top:-10px; left:${Math.random()*100}vw;
      width:${size}px; height:${size}px; border-radius:${Math.random()>0.5?'50%':'2px'};
      background:${colors[Math.floor(Math.random()*colors.length)]};
      z-index:9999; pointer-events:none;
      animation: confetti-fall ${Math.random()*2+1}s linear forwards;
      animation-delay:${Math.random()*0.5}s;`;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }
}

// Add confetti keyframes dynamically
if (!document.getElementById('confettiStyle')) {
  const style = document.createElement('style');
  style.id = 'confettiStyle';
  style.textContent = `
    @keyframes confetti-fall {
      to { transform: translateY(100vh) rotate(720deg); opacity: 0; }
    }`;
  document.head.appendChild(style);
}

// ── Tooltip Init ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[title]').forEach(el => {
    if (!el.classList.contains('no-tooltip')) {
      new bootstrap.Tooltip(el, { trigger: 'hover' });
    }
  });
});

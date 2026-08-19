// ── Spotify Web Playback SDK Player Widget ─────────────
(function () {
  const widget = document.getElementById('spotifyPlayerWidget');
  if (!widget) return;

  const csrf = widget.dataset.csrf || '';
  const badge = document.getElementById('spBadge');
  const setup = document.getElementById('spSetup');
  const nowPlaying = document.getElementById('spNowPlaying');
  const art = document.getElementById('spArt');
  const titleEl = document.getElementById('spTitle');
  const artistEl = document.getElementById('spArtist');
  const progressEl = document.getElementById('spProgress');
  const search = document.getElementById('spSearch');
  const results = document.getElementById('spResults');
  const toggleBtn = document.getElementById('spToggle');
  const prevBtn = document.getElementById('spPrev');
  const nextBtn = document.getElementById('spNext');

  let player = null;
  let deviceId = null;
  let isMock = false;
  let lastTracks = [];
  let mockTimer = null;

  function setBadge(text, cls) {
    badge.textContent = text;
    badge.className = 'badge border px-3 py-2 ' + cls;
  }

  function escapeHtml(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderNowPlaying(track) {
    nowPlaying.classList.remove('d-none');
    titleEl.textContent = track ? track.name : 'No song playing';
    artistEl.textContent = track ? track.artists : '—';
    if (track && track.image) {
      art.innerHTML = `<img src="${track.image}" alt="">`;
    } else {
      art.innerHTML = '<i class="bi bi-music-note-beamed"></i>';
    }
    progressEl.style.width = '0%';
  }

  function setProgress(position, duration) {
    const pct = duration ? Math.min(100, (position / duration) * 100) : 0;
    progressEl.style.width = pct + '%';
  }

  function setPlayIcon(playing) {
    toggleBtn.innerHTML = playing ? '<i class="bi bi-pause-fill"></i>' : '<i class="bi bi-play-fill"></i>';
  }

  // ── Real mode: Web Playback SDK ─────────────────────────
  function initPlayer(token) {
    player = new Spotify.Player({
      name: 'GoalAchiever Player',
      getOAuthToken: cb => cb(token),
      volume: 0.6,
    });

    player.addListener('ready', ({ device_id }) => {
      deviceId = device_id;
      setBadge('Connected', 'bg-success-subtle text-success border-success');
    });

    player.addListener('not_ready', () => {
      setBadge('Offline', 'bg-secondary-subtle text-secondary');
    });

    ['initialization_error', 'authentication_error', 'account_error', 'playback_error'].forEach(evt => {
      player.addListener(evt, ({ message }) => {
        setBadge('Player Error', 'bg-danger-subtle text-danger border-danger');
        console.error('Spotify ' + evt + ':', message);
      });
    });

    player.addListener('player_state_changed', state => {
      if (!state || !state.track_window || !state.track_window.current_track) {
        renderNowPlaying(null);
        return;
      }
      const t = state.track_window.current_track;
      renderNowPlaying({
        name: t.name,
        artists: (t.artists || []).map(a => a.name).join(', '),
        image: t.album && t.album.images && t.album.images[0] ? t.album.images[0].url : '',
      });
      setPlayIcon(!state.paused);
      setProgress(state.position || 0, state.duration || 0);
    });

    player.connect();
  }

  function loadSDK(token) {
    if (window.Spotify && window.Spotify.Player) { initPlayer(token); return; }
    window.onSpotifyWebPlaybackSDKReady = () => initPlayer(token);
    const s = document.createElement('script');
    s.src = 'https://sdk.scdn.co/spotify-player.js';
    document.body.appendChild(s);
  }

  async function playUris(uris) {
    if (!isMock && !deviceId) {
      setBadge('Connecting...', 'bg-info-subtle text-info border-info');
      return;
    }
    try {
      const res = await fetch('/spotify/play/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: deviceId, uris }),
      }).then(r => r.json());
      if (!res.success) setBadge('Playback failed', 'bg-danger-subtle text-danger border-danger');
    } catch (e) {
      setBadge('Network error', 'bg-danger-subtle text-danger border-danger');
    }
  }

  // ── Mock mode (no real Spotify): simulated demo ──────────
  function mockPlay(track) {
    renderNowPlaying(track);
    setPlayIcon(true);
    setBadge('Demo Mode · playing (no audio)', 'bg-warning-subtle text-warning border-warning');
    clearInterval(mockTimer);
    let pos = 0;
    mockTimer = setInterval(() => {
      pos += 1;
      progressEl.style.width = Math.min(100, pos) + '%';
      if (pos >= 100) { setPlayIcon(false); clearInterval(mockTimer); }
    }, 400);
  }

  function enableMockMode() {
    isMock = true;
    setBadge('Demo Mode', 'bg-warning-subtle text-warning border-warning');
    setup.classList.remove('d-none');
    renderNowPlaying(null);
  }

  // ── Search ────────────────────────────────────────────────
  let searchTimer = null;
  async function doSearch() {
    const q = search.value.trim();
    if (!q) { results.classList.add('d-none'); results.innerHTML = ''; return; }
    let data;
    try {
      data = await fetch('/spotify/search/?q=' + encodeURIComponent(q)).then(r => r.json());
    } catch (e) { data = { tracks: [] }; }
    lastTracks = data.tracks || [];
    renderResults(lastTracks);
  }

  function renderResults(tracks) {
    if (!tracks.length) {
      results.innerHTML = '<div class="text-muted small p-2">No songs found.</div>';
    } else {
      results.innerHTML = tracks.map(t => `
        <button type="button" class="sp-result" data-uri="${t.uri}">
          ${t.image ? `<img src="${t.image}" alt="">` : '<i class="bi bi-music-note-beamed"></i>'}
          <span class="flex-grow-1" style="min-width:0">
            <span class="d-block fw-semibold text-truncate">${escapeHtml(t.name)}</span>
            <small class="text-muted text-truncate">${escapeHtml(t.artists)}</small>
          </span>
          <i class="bi bi-play-circle sp-result-play"></i>
        </button>`).join('');
    }
    results.classList.remove('d-none');
  }

  // ── Events ────────────────────────────────────────────────
  search.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(doSearch, 300);
  });

  results.addEventListener('click', e => {
    const btn = e.target.closest('.sp-result');
    if (!btn) return;
    const uri = btn.dataset.uri;
    if (player) { try { player.activateElement(); } catch (err) {} }
    if (isMock) {
      const track = lastTracks.find(t => t.uri === uri) || lastTracks[0];
      if (track) mockPlay(track);
    } else {
      playUris([uri]);
    }
  });

  toggleBtn.addEventListener('click', () => {
    if (isMock) {
      if (mockTimer) { clearInterval(mockTimer); mockTimer = null; setPlayIcon(false); }
      return;
    }
    if (player) { try { player.activateElement(); } catch (e) {} player.togglePlay(); }
  });

  prevBtn.addEventListener('click', () => { if (player) player.previousTrack(); });
  nextBtn.addEventListener('click', () => { if (player) player.nextTrack(); });

  // ── Init ──────────────────────────────────────────────────
  (async () => {
    let data;
    try {
      data = await fetch('/spotify/token/').then(r => r.json());
    } catch (e) {
      setBadge('Offline', 'bg-secondary-subtle text-secondary');
      return;
    }
    if (data.access_token) {
      setup.classList.add('d-none');
      setBadge('Connecting...', 'bg-info-subtle text-info border-info');
      loadSDK(data.access_token);
    } else {
      enableMockMode();
    }
  })();
})();

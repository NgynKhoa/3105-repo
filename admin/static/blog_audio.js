/* ============================================================
 * blog_audio.js
 * Standalone audio glue cho các trang KHÔNG phải Front repo
 * (blog.html, hoặc bất kỳ trang nào có Settings panel + Now Playing).
 *
 * - Rain audio (light + heavy): dùng TrackPlayer (MP3 / YouTube / Spotify).
 *   Sync với toggle qua localStorage key `rainEnabled` / `heavyRain` /
 *   `repo_rainAudioLight` / `repo_rainAudioHeavy` / `rain_volume`.
 *
 * - Music player: load playlist, render Now Playing UI mini
 *   (đồng bộ với Front repo). Sync với toggle qua:
 *     `admin_playlist`, `mp_volume`, `mp_loop`, `mp_playing`
 *
 * Cross-tab sync: storage event khi user bật/tắt ở tab khác.
 * Autoplay policy: nếu browser block → resume on first click/scroll/key.
 * ============================================================ */
(function () {
  'use strict';

  // ======= Window globals exposed cho blog page =======
  window.__blogRainLightPlayer = null;
  window.__blogRainHeavyPlayer = null;
  window.__blogMusicPlayer = null;
  window.__blogAudioReady = false;

  // ======= UTILS =======
  function _parseBool(v, def) {
    if (v === null || v === undefined) return !!def;
    if (v === true || v === false) return v;
    return String(v).toLowerCase() === 'true';
  }

  function _rainEffectiveVolume(kind) {
    var rainVol = parseInt(localStorage.getItem('rain_volume') || '70', 10);
    if (isNaN(rainVol)) rainVol = 70;
    var ratio = rainVol / 100;
    return kind === 'heavy' ? 0.75 * ratio : 0.6 * ratio;
  }

  function _currentRainSrc(kind) {
    var key = kind === 'heavy' ? 'repo_rainAudioHeavy' : 'repo_rainAudioLight';
    var def = kind === 'heavy' ? '/assets/rain_heavy.mp3' : '/assets/rain.mp3';
    return localStorage.getItem(key) || def;
  }

  // ======= RAIN AUDIO INIT =======
  function _initRainPlayers() {
    if (typeof window.MultiPlayer === 'undefined' ||
        typeof window.MultiPlayer.TrackPlayer !== 'function') {
      // retry
      setTimeout(_initRainPlayers, 300);
      return;
    }
    if (window.__blogRainLightPlayer) return; // already

    var MP = window.MultiPlayer;
    var lightEl = document.getElementById('blogRainAudio');
    var heavyEl = document.getElementById('blogRainHeavyAudio');
    if (!lightEl || !heavyEl) return;

    window.__blogRainLightPlayer = new MP.TrackPlayer({
      audioEl: lightEl,
      ytContainer: document.getElementById('blog-rain-yt-host') || document.body,
      spotifyContainer: document.getElementById('blog-rain-yt-host') || document.body,
      onReady: function () {
        if (window.__blogRainOn) {
          window.__blogRainLightPlayer.setLoop(true);
          window.__blogRainLightPlayer.setVolume(_rainEffectiveVolume('light'));
          window.__blogRainLightPlayer.play();
        }
      },
      onError: function (e) {
        console.warn('[blog-rain-light] error:', e && e.message);
      },
    });

    window.__blogRainHeavyPlayer = new MP.TrackPlayer({
      audioEl: heavyEl,
      ytContainer: document.getElementById('blog-rain-heavy-yt-host') || document.body,
      spotifyContainer: document.getElementById('blog-rain-heavy-yt-host') || document.body,
      onReady: function () {
        if (window.__blogRainOn && window.__blogHeavyOn) {
          window.__blogRainHeavyPlayer.setLoop(true);
          window.__blogRainHeavyPlayer.setVolume(_rainEffectiveVolume('heavy'));
          window.__blogRainHeavyPlayer.play();
        }
      },
      onError: function (e) {
        console.warn('[blog-rain-heavy] error:', e && e.message);
      },
    });

    // Initial load
    var lightSrc = _currentRainSrc('light');
    var heavySrc = _currentRainSrc('heavy');
    var infoL = MP.parseTrackUrl ? MP.parseTrackUrl(lightSrc) : { type: 'mp3' };
    var infoH = MP.parseTrackUrl ? MP.parseTrackUrl(heavySrc) : { type: 'mp3' };
    window.__blogRainLightPlayer.load({
      src: lightSrc, type: infoL.type, title: 'Rain Light', artist: '', cover: ''
    }).catch(function (e) { console.warn('[blog-rain-light] load failed:', e && e.message); });
    window.__blogRainHeavyPlayer.load({
      src: heavySrc, type: infoH.type, title: 'Rain Heavy', artist: '', cover: ''
    }).catch(function (e) { console.warn('[blog-rain-heavy] load failed:', e && e.message); });

    window.__blogAudioReady = true;
    _syncRainAudio();
    _bindRainGestureResume();
  }

  function _bindRainGestureResume() {
    if (window.__blogRainGestureBound) return;
    window.__blogRainGestureBound = true;
    function resume() {
      var needResume = false;
      // Rain audio
      ['__blogRainLightPlayer', '__blogRainHeavyPlayer'].forEach(function (name) {
        var pp = window[name];
        var aa = pp && pp.audio;
        if (pp && aa && aa.dataset && aa.dataset.pendingPlay === '1') {
          needResume = true;
          delete aa.dataset.pendingPlay;
          var pr = pp.play();
          if (pr && pr.catch) {
            pr.catch(function () {
              if (aa) aa.dataset.pendingPlay = '1';
            });
          }
        }
      });
      // Music player — nếu audio.src rỗng (chưa load xong), phải gọi lại playCurrent
      // thay vì play() đơn thuần (sẽ fail vì src chưa có).
      var mp = window.__blogMusicPlayer;
      if (mp && mp.audio) {
        var mpAudio = mp.audio;
        var mpPending = mpAudio.dataset && mpAudio.dataset.pendingPlay === '1';
        var mpSrcEmpty = !mpAudio.src || mpAudio.src === '' || mpAudio.src.indexOf(window.location.origin) < 0 && mpAudio.src !== '';
        // Nếu src rỗng + đã có user gesture → thử load + play lại từ track hiện tại
        if (mpPending && (!mpAudio.src || mpAudio.src === '')) {
          needResume = true;
          delete mpAudio.dataset.pendingPlay;
          // Re-trigger playCurrent: nó sẽ load() nếu src rỗng
          if (typeof window.__blogPlayCurrent === 'function') {
            try { window.__blogPlayCurrent(); } catch (e) { console.warn('[blog-music] resume err:', e); }
          }
        } else if (mpPending) {
          needResume = true;
          delete mpAudio.dataset.pendingPlay;
          var pr2 = mp.play();
          if (pr2 && pr2.catch) {
            pr2.catch(function () {
              if (mp.audio) mp.audio.dataset.pendingPlay = '1';
            });
          }
        }
      }
      if (!needResume) {
        ['click', 'keydown', 'scroll', 'touchstart'].forEach(function (ev) {
          document.removeEventListener(ev, resume);
        });
        window.__blogRainGestureBound = false;
      }
    }
    ['click', 'keydown', 'scroll', 'touchstart'].forEach(function (ev) {
      document.addEventListener(ev, resume);
    });
  }

  function _tryPlay(player) {
    if (!player || !player.audio) return;
    try {
      var pr = player.audio.play();
      if (pr && pr.catch) {
        pr.catch(function () {
          player.audio.dataset.pendingPlay = '1';
          _bindRainGestureResume();
        });
      }
    } catch (e) {}
    if (player.audio.paused) {
      player.audio.dataset.pendingPlay = '1';
      _bindRainGestureResume();
    }
  }

  function _stopRainLight() {
    if (!window.__blogRainLightPlayer) return;
    try {
      window.__blogRainLightPlayer.pause();
      var a = window.__blogRainLightPlayer.audio;
      if (a) { try { a.pause(); } catch (e) {} }
    } catch (e) {}
  }
  function _stopRainHeavy() {
    if (!window.__blogRainHeavyPlayer) return;
    try {
      window.__blogRainHeavyPlayer.pause();
      var a = window.__blogRainHeavyPlayer.audio;
      if (a) { try { a.pause(); } catch (e) {} }
    } catch (e) {}
  }

  function _syncRainAudio() {
    if (!window.__blogRainLightPlayer) return;
    var rainOn = window.__blogRainOn !== false;
    var heavyOn = !!window.__blogHeavyOn;
    var lightSrc = _currentRainSrc('light');
    var heavySrc = _currentRainSrc('heavy');

    // Heavy uses light's player (chỉ 1 player phát tại 1 thời điểm)
    if (rainOn) {
      var wantSrc = heavyOn ? heavySrc : lightSrc;
      var targetPlayer = heavyOn ? window.__blogRainHeavyPlayer : window.__blogRainLightPlayer;
      var otherPlayer = heavyOn ? window.__blogRainLightPlayer : window.__blogRainHeavyPlayer;
      _stopRainLight();
      _stopRainHeavy();
      if (typeof window.MultiPlayer !== 'undefined' && window.MultiPlayer.parseTrackUrl) {
        var info = window.MultiPlayer.parseTrackUrl(wantSrc);
        var cur = targetPlayer.audio && targetPlayer.audio.src;
        if (!cur || cur.indexOf(wantSrc) < 0) {
          targetPlayer.load({
            src: wantSrc, type: info.type, title: heavyOn ? 'Rain Heavy' : 'Rain Light',
            artist: '', cover: ''
          }).then(function () {
            targetPlayer.setLoop(true);
            targetPlayer.setVolume(_rainEffectiveVolume(heavyOn ? 'heavy' : 'light'));
            _tryPlay(targetPlayer);
          }).catch(function () {
            // fallback: set src directly
            var a = targetPlayer.audio;
            if (a) {
              a.src = wantSrc;
              a.load();
              a.volume = _rainEffectiveVolume(heavyOn ? 'heavy' : 'light');
              a.loop = true;
              _tryPlay(targetPlayer);
            }
          });
        } else {
          targetPlayer.setLoop(true);
          targetPlayer.setVolume(_rainEffectiveVolume(heavyOn ? 'heavy' : 'light'));
          _tryPlay(targetPlayer);
        }
      }
    } else {
      _stopRainLight();
      _stopRainHeavy();
    }
  }

  // ======= MUSIC PLAYER (Now Playing) =======
  function _getPlaylist() {
    try {
      if (Array.isArray(window.PUBLIC_PLAYLIST) && window.PUBLIC_PLAYLIST.length) {
        return window.PUBLIC_PLAYLIST.map(function (t) {
          return {
            title: t.title || 'Untitled',
            artist: t.artist || '',
            src: t.src || t.url || '',
            cover: t.cover || t.image || '',
          };
        });
      }
      var raw = localStorage.getItem('admin_playlist');
      if (raw) {
        var parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length) return parsed;
      }
    } catch (e) {}
    return [
      { title: 'Synthwave Drift', artist: 'Owen · 80s Mix', src: '', cover: '' },
      { title: 'Neon Rain', artist: 'Cyber Lo-fi', src: '', cover: '' },
      { title: 'Hanoi Midnight', artist: 'Phase FM', src: '', cover: '' },
      { title: 'CRT Memories', artist: 'Analog Tape', src: '', cover: '' },
    ];
  }

  function _initMusicPlayer() {
    if (typeof window.MultiPlayer === 'undefined' ||
        typeof window.MultiPlayer.TrackPlayer !== 'function') {
      setTimeout(_initMusicPlayer, 300);
      return;
    }
    if (window.__blogMusicPlayer) return;
    var audioEl = document.getElementById('mpAudio');
    if (!audioEl) return;
    var ytHost = document.getElementById('mp-yt-host') || document.body;
    var spHost = document.getElementById('mp-spotify-host') || document.body;
    var MP = window.MultiPlayer;

    var barFill = document.getElementById('mpBarFill');
    var elCur   = document.getElementById('mpCur');
    var elDur   = document.getElementById('mpDur');
    var cover   = document.getElementById('mpCover');
    var titleEl = document.getElementById('mpTitle');
    var artistEl = document.getElementById('mpArtist');
    var btnPlay = document.getElementById('mpPlay');
    var btnPrev = document.getElementById('mpPrev');
    var btnNext = document.getElementById('mpNext');
    var btnLoop = document.getElementById('mpLoop');
    var btnVol  = document.getElementById('mpVolumeBtn');
    var volPanel = document.getElementById('mpVolumePanel');
    var volRange = document.getElementById('mpVolumeRange');
    var volVal   = document.getElementById('mpVolumeVal');
    var playerBox = document.getElementById('mpPlayer');
    var bigCover = document.getElementById('mpBigCover');

    var PLAY_SVG  = '<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg"><path d="M2 1 L7 4 L2 7 Z"/></svg>';
    var PAUSE_SVG = '<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg"><path d="M2 1 H3.5 V7 H2 Z M4.5 1 H6 V7 H4.5 Z"/></svg>';

    var tracks = _getPlaylist();
    // Khôi phục vị trí/loop/playing từ localStorage để tiếp tục bài đang phát khi user
    // navigate từ Front repo (/blog). Front repo lưu mp_currentIdx + mp_playing.
    var savedIdx = parseInt(localStorage.getItem('mp_currentIdx') || '0', 10);
    var idx = (isNaN(savedIdx) || savedIdx < 0 || savedIdx >= tracks.length) ? 0 : savedIdx;
    var playing = _parseBool(localStorage.getItem('mp_playing'), false);
    var mediaReady = false;
    var loop = _parseBool(localStorage.getItem('mp_loop'), true);
    var volHideTimer = null;

    function fmt(s) {
      s = Math.max(0, Math.floor(s || 0));
      return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
    }
    function applyCover(t) {
      // Trên Blog page không có #mpCover (chỉ có #mpBigCover = disc nhỏ).
      // Cover (ảnh lớn) chỉ render trên Front page. Ở đây set background cho disc thôi.
      var url = (t && t.cover) || '';
      if (!url && t && t.src && MP && MP.parseTrackUrl) {
        var info = MP.parseTrackUrl(t.src);
        if (info.type === 'youtube' && info.providerId) url = MP.ytThumb(info.providerId);
      }
      if (bigCover) {
        if (url) {
          bigCover.style.backgroundImage = 'url(' + url + ')';
          bigCover.classList.add('has-image');
        } else {
          bigCover.style.backgroundImage = '';
          bigCover.classList.remove('has-image');
        }
      }
      if (cover) {
        if (url) {
          cover.classList.add('has-image');
          cover.style.backgroundImage = 'url(' + url + ')';
        } else {
          cover.classList.remove('has-image');
          cover.style.backgroundImage = '';
        }
      }
    }
    function renderMeta() {
      var t = tracks[idx] || {};
      if (titleEl)  titleEl.textContent = t.title || '—';
      if (artistEl) artistEl.textContent = t.artist || '';
      applyCover(t);
    }
    function setPlayIcon() {
      if (!btnPlay) return;
      // Icon swap dựa trên `playing` (user intent) — KHÔNG phụ thuộc mediaReady
      // vì khi user bấm play, intent là true ngay cả khi audio chưa ready.
      btnPlay.innerHTML = playing ? PAUSE_SVG : PLAY_SVG;
      // .playing class cho CSS animation (chỉ khi audio thực sự play)
      if (playerBox) {
        playerBox.classList.toggle('playing', playing && mediaReady);
        // Title cập nhật cho tooltip
        btnPlay.title = playing ? 'Dừng' : 'Phát';
      }
      // Loop button aria-pressed + visual state
      if (btnLoop) {
        btnLoop.title = loop ? 'Lặp lại (BẬT)' : 'Lặp lại (TẮT)';
      }
    }

    var trackPlayer = new MP.TrackPlayer({
      audioEl: audioEl,
      ytContainer: ytHost,
      spotifyContainer: spHost,
      onTime: function (cur, dur) {
        // onTime là callback DUY NHẤT TrackPlayer.fire — track progress ở đây.
        // Detect mediaReady: nếu cur > 0 hoặc audio đang phát → audio đã chạy thật.
        if (cur > 0 || (audioEl && !audioEl.paused)) {
          if (!mediaReady) { mediaReady = true; setPlayIcon(); }
        } else {
          if (mediaReady) { mediaReady = false; setPlayIcon(); }
        }
        if (dur > 0) {
          if (barFill) barFill.style.width = (cur / dur * 100) + '%';
          if (elCur) elCur.textContent = fmt(cur);
          if (elDur) elDur.textContent = fmt(dur);
        }
      },
      onPlay: function () {
        // TrackPlayer KHÔNG fire onPlay (chỉ có onTime + onEnded), nhưng ta vẫn
        // giữ callback này để tương thích nếu future-proof.
        mediaReady = true;
        setPlayIcon();
      },
      onPause: function () {
        mediaReady = false;
        setPlayIcon();
      },
      onEnded: function () {
        if (!loop) {
          playing = false;
          mediaReady = false;
          setPlayIcon();
          return;
        }
        idx = (idx + 1) % tracks.length;
        playCurrent();
      },
      onReady: function () {},
      onError: function (e) {
        console.warn('[blog-music] error:', e && e.message);
        playing = false;
        mediaReady = false;
        setPlayIcon();
      },
    });
    // Polling fallback: nếu audio.paused=false nhưng onTime không fire (track
    // không progress, e.g. mp3 ngắn 5s đã phát xong) → check mỗi 300ms.
    setInterval(function () {
      if (!audioEl) return;
      var actuallyPlaying = !audioEl.paused && audioEl.currentTime > 0;
      if (actuallyPlaying && !mediaReady) {
        mediaReady = true;
        setPlayIcon();
      } else if (!actuallyPlaying && mediaReady && playing) {
        // Audio playing bị pause do buffering/network → giữ .playing để user
        // thấy intent (đừng nhảy .playing class lung tung).
        // Chỉ flip khi đã thực sự pause (paused=true)
        if (audioEl.paused) {
          mediaReady = false;
          setPlayIcon();
        }
      }
    }, 300);
    window.__blogMusicPlayer = trackPlayer;

    var savedVol = parseInt(localStorage.getItem('mp_volume') || '80', 10);
    var initialVol = isNaN(savedVol) ? 80 : Math.max(0, Math.min(100, savedVol));
    if (audioEl) audioEl.volume = initialVol / 100;
    if (volRange) {
      volRange.value = String(initialVol);
      if (volVal) volVal.textContent = String(initialVol);
    }
    try { trackPlayer.setVolume(initialVol / 100); } catch (e) {}

    function playCurrent() {
      var t = tracks[idx] || {};
      if (!t.src) {
        // playlist item without src: still toggle play visual
        if (playing) {
          mediaReady = true;
          setPlayIcon();
        }
        return;
      }
      renderMeta();
      trackPlayer.setLoop(loop);
      // Expose ra window để _bindRainGestureResume có thể gọi lại khi autoplay bị block
      window.__blogPlayCurrent = playCurrent;
      try {
        // Nếu src chưa set hoặc đổi → load() trước rồi play()
        // (TrackPlayer.play() không auto-load khi audio.src rỗng).
        var currentSrc = trackPlayer.audio && trackPlayer.audio.src;
        var info = MP.parseTrackUrl(t.src);
        var needLoad = !currentSrc || currentSrc.indexOf(t.src) < 0;
        if (needLoad) {
          trackPlayer.load({
            src: t.src, type: info.type, title: t.title || '', artist: t.artist || '', cover: t.cover || ''
          }).then(function () {
            try { trackPlayer.play(); } catch (e) { console.warn('[blog-music] play err:', e); }
            _tryPlay(trackPlayer);
          }).catch(function (e) {
            console.warn('[blog-music] load failed:', e && e.message);
            // fallback: set src directly
            var a = trackPlayer.audio;
            if (a) {
              a.src = t.src;
              a.load();
              a.volume = (parseInt(localStorage.getItem('mp_volume') || '70', 10) || 70) / 100;
              a.loop = loop;
              _tryPlay(trackPlayer);
            }
          });
        } else {
          try { trackPlayer.play(); } catch (e) { console.warn('[blog-music] play err:', e); }
          _tryPlay(trackPlayer);
        }
      } catch (e) {
        console.warn('[blog-music] play error:', e && e.message);
      }
    }

    function scheduleVolHide() {
      if (volHideTimer) clearTimeout(volHideTimer);
      volHideTimer = setTimeout(function () {
        if (volPanel) volPanel.style.display = 'none';
        if (btnVol) btnVol.setAttribute('aria-pressed', 'false');
      }, 1000);
    }
    function showVolPanel() {
      if (!volPanel) return;
      volPanel.style.display = 'flex';
      if (btnVol) btnVol.setAttribute('aria-pressed', 'true');
      if (volHideTimer) { clearTimeout(volHideTimer); volHideTimer = null; }
    }

    if (volRange) {
      volRange.addEventListener('input', function (e) {
        var v = parseInt(e.target.value, 10);
        if (isNaN(v)) v = 80;
        v = Math.max(0, Math.min(100, v));
        if (audioEl) audioEl.volume = v / 100;
        try { trackPlayer.setVolume(v / 100); } catch (e) {}
        if (volVal) volVal.textContent = String(v);
        localStorage.setItem('mp_volume', String(v));
      });
      volRange.addEventListener('mouseup', scheduleVolHide);
      volRange.addEventListener('touchend', scheduleVolHide);
    }
    if (volPanel) {
      volPanel.addEventListener('mouseenter', function () {
        if (volHideTimer) { clearTimeout(volHideTimer); volHideTimer = null; }
      });
      volPanel.addEventListener('mouseleave', scheduleVolHide);
    }
    if (btnVol) {
      btnVol.addEventListener('click', function (e) {
        e.stopPropagation();
        if (volPanel.style.display === 'flex') {
          volPanel.style.display = 'none';
          btnVol.setAttribute('aria-pressed', 'false');
        } else {
          showVolPanel();
        }
      });
    }
    document.addEventListener('click', function (e) {
      if (!volPanel || volPanel.style.display === 'none') return;
      if (volPanel.contains(e.target) || (btnVol && btnVol.contains(e.target))) return;
      if (volHideTimer) clearTimeout(volHideTimer);
      volPanel.style.display = 'none';
      if (btnVol) btnVol.setAttribute('aria-pressed', 'false');
    });

    if (btnPlay) {
      btnPlay.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        // Toggle user intent TRƯỚC, setPlayIcon NGAY để đổi icon tức thì
        // (không đợi trackPlayer.onPlay callback — vì autoplay block thì
        // callback không fire → icon không swap).
        playing = !playing;
        setPlayIcon();
        if (playing) {
          playCurrent();
        } else {
          try { trackPlayer.pause(); } catch (err) { console.warn('[blog-music] pause err:', err); }
        }
        try { localStorage.setItem('mp_playing', playing ? 'true' : 'false'); } catch (err) {}
      });
    }
    if (btnPrev) {
      btnPrev.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        idx = (idx - 1 + tracks.length) % tracks.length;
        playing = true;
        setPlayIcon();
        try { localStorage.setItem('mp_currentIdx', String(idx)); } catch (err) {}
        try { localStorage.setItem('mp_playing', 'true'); } catch (err) {}
        playCurrent();
      });
    }
    if (btnNext) {
      btnNext.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        idx = (idx + 1) % tracks.length;
        playing = true;
        setPlayIcon();
        try { localStorage.setItem('mp_currentIdx', String(idx)); } catch (err) {}
        try { localStorage.setItem('mp_playing', 'true'); } catch (err) {}
        playCurrent();
      });
    }
    if (btnLoop) {
      btnLoop.addEventListener('click', function () {
        loop = !loop;
        trackPlayer.setLoop(loop);
        btnLoop.setAttribute('aria-pressed', loop ? 'true' : 'false');
        btnLoop.classList.toggle('on', loop);
        try { localStorage.setItem('mp_loop', loop ? 'true' : 'false'); } catch (e) {}
      });
      btnLoop.setAttribute('aria-pressed', loop ? 'true' : 'false');
      btnLoop.classList.toggle('on', loop);
    }

    renderMeta();
    setPlayIcon();
    if (playing) playCurrent();
  }

  // ======= SYNC state from localStorage =======
  function _applyState() {
    window.__blogRainOn = _parseBool(localStorage.getItem('rainEnabled'), true);
    window.__blogHeavyOn = _parseBool(localStorage.getItem('heavyRain'), false);
    var togRain = document.getElementById('toggleRain');
    if (togRain) togRain.checked = window.__blogRainOn;
    var togHeavy = document.getElementById('toggleHeavyRain');
    if (togHeavy) togHeavy.checked = window.__blogHeavyOn;
  }

  // ======= HOOKUP toggle UI (if exists in page) =======
  function _hookRainToggles() {
    var togRain = document.getElementById('toggleRain');
    var togHeavy = document.getElementById('toggleHeavyRain');
    if (togRain) {
      togRain.addEventListener('change', function () {
        window.__blogRainOn = togRain.checked;
        localStorage.setItem('rainEnabled', String(window.__blogRainOn));
        _syncRainAudio();
      });
    }
    if (togHeavy) {
      togHeavy.addEventListener('change', function () {
        window.__blogHeavyOn = togHeavy.checked;
        localStorage.setItem('heavyRain', String(window.__blogHeavyOn));
        _syncRainAudio();
      });
    }
  }

  // ======= BOOT =======
  // Expose global sync hook so other scripts (existing toggle handlers in blog.html)
  // can trigger rain audio sync without depending on storage events.
  window.__blogSyncRain = function () {
    _applyState();
    if (window.__blogAudioReady) _syncRainAudio();
  };
  // Mark body so CSS can fade-in #mpPlayer
  function boot() {
    document.body.classList.add('audio-ready');
    _applyState();
    _hookRainToggles();
    _initRainPlayers();
    _initMusicPlayer();

    // Cross-tab sync via storage event
    window.addEventListener('storage', function (e) {
      if (!e.key) return;
      if (e.key === 'rainEnabled' || e.key === 'heavyRain' ||
          e.key === 'repo_rainAudioLight' || e.key === 'repo_rainAudioHeavy' ||
          e.key === 'rain_volume') {
        _applyState();
        _syncRainAudio();
      } else if (e.key === 'admin_playlist' || e.key === 'mp_playing' ||
                 e.key === 'mp_volume' || e.key === 'mp_loop') {
        // music state changed in another tab — apply without restart
        if (e.key === 'mp_volume') {
          var v = parseInt(localStorage.getItem('mp_volume') || '80', 10);
          if (!isNaN(v)) {
            var audioEl = document.getElementById('mpAudio');
            if (audioEl) audioEl.volume = v / 100;
            try { window.__blogMusicPlayer && window.__blogMusicPlayer.setVolume(v / 100); } catch (er) {}
            var volRange = document.getElementById('mpVolumeRange');
            if (volRange) volRange.value = String(v);
            var volVal = document.getElementById('mpVolumeVal');
            if (volVal) volVal.textContent = String(v);
          }
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();

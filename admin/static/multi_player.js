/* ===============================================================
   MULTI_PLAYER.JS — TrackPlayer class
   Hỗ trợ 3 loại source cho Now Playing widget:
     - type: 'mp3'    → <audio src="...">
     - type: 'youtube'→ YouTube IFrame API (hidden iframe 0×0)
     - type: 'spotify'→ Spotify Embed iframe + postMessage control
   Dùng ở cả index.html (Now Playing) và dashboard.html (preview).
   =============================================================== */

(function (global) {
  'use strict';

  // ---------- URL PARSER ----------
  function parseTrackUrl(rawUrl) {
    if (!rawUrl) return { type: 'mp3', src: '', providerId: null };
    const url = String(rawUrl).trim();

    // YouTube
    let m;
    if ((m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([A-Za-z0-9_-]{11})/))) {
      return { type: 'youtube', src: url, providerId: m[1] };
    }
    // Spotify
    if ((m = url.match(/open\.spotify\.com\/(track|album|playlist|episode|show)\/([A-Za-z0-9]+)/))) {
      return { type: 'spotify', src: url, providerId: m[2], subType: m[1] };
    }
    // SoundCloud (basic — không làm full API, chỉ embed widget)
    if ((m = url.match(/soundcloud\.com\/[\w-]+\/[\w-]+/))) {
      return { type: 'soundcloud', src: url, providerId: url };
    }
    // Default: MP3 / direct stream
    return { type: 'mp3', src: url, providerId: null };
  }

  // ---------- YOUTUBE THUMB ----------
  function ytThumb(videoId) {
    return videoId ? `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg` : '';
  }

  // ---------- LOAD YOUTUBE IFRAME API (lazy, singleton) ----------
  let _ytApiPromise = null;
  function loadYTApi() {
    if (_ytApiPromise) return _ytApiPromise;
    _ytApiPromise = new Promise(function (resolve, reject) {
      if (global.YT && global.YT.Player) return resolve(global.YT);
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      tag.async = true;
      let timeout = setTimeout(function () {
        reject(new Error('YT API load timeout'));
      }, 10000);
      global.onYouTubeIframeAPIReady = function () {
        clearTimeout(timeout);
        resolve(global.YT);
      };
      tag.onerror = function () {
        clearTimeout(timeout);
        reject(new Error('YT API load failed'));
      };
      document.head.appendChild(tag);
    });
    return _ytApiPromise;
  }

  // ---------- TRACKPLAYER CLASS ----------
  class TrackPlayer {
    constructor(opts) {
      // opts: { audioEl, ytContainer, spotifyContainer, onTime, onEnded, onReady, onError }
      this.audio = opts.audioEl;
      this.ytContainer = opts.ytContainer || document.createElement('div');
      this.spotifyContainer = opts.spotifyContainer || document.createElement('div');
      this.onTime = opts.onTime || function () {};
      this.onEnded = opts.onEnded || function () {};
      this.onReady = opts.onReady || function () {};
      this.onError = opts.onError || function () {};

      this.ytPlayer = null;
      this.spotifyIframe = null;
      this.currentType = null;
      this.pollTimer = null;
      this._destroyed = false;

      // Spotify Embed controller state
      this._spotifyReady = false;
      this._ytLoadingTrack = null;
      this._ytReady = false;

      // Common state
      this.isPlaying = false;
      this.loop = true;

      // Audio events
      if (this.audio) {
        this.audio.addEventListener('timeupdate', () => {
          if (this.currentType !== 'mp3') return;
          this.onTime(this.audio.currentTime, this.audio.duration || 0);
        });
        this.audio.addEventListener('loadedmetadata', () => {
          if (this.currentType !== 'mp3') return;
          if (!isNaN(this.audio.duration)) {
            this.onTime(this.audio.currentTime || 0, this.audio.duration);
          }
        });
        this.audio.addEventListener('ended', () => {
          if (this.currentType !== 'mp3') return;
          if (!this.loop) this.onEnded();
        });
        this.audio.addEventListener('play',  () => { if (this.currentType === 'mp3') this.isPlaying = true; });
        this.audio.addEventListener('pause', () => { if (this.currentType === 'mp3') this.isPlaying = false; });
      }
    }

    destroy() {
      this._destroyed = true;
      this._stopPolling();
      try { this.audio && this.audio.pause(); } catch(e) {}
      try { this.ytPlayer && this.ytPlayer.destroy(); } catch(e) {}
      this.ytPlayer = null;
      this.ytContainer.innerHTML = '';
      this.spotifyContainer.innerHTML = '';
    }

    // --- Load a track (returns Promise) ---
    load(track) {
      const info = parseTrackUrl(track && (track.url || track.src || track.id));
      // normalize: track.url may be youtube/spotify id
      let type = track && track.type ? track.type : info.type;
      // Auto-detect from id-like values (YouTube/Spotify embed URLs)
      if (type === 'mp3' && info.type !== 'mp3') {
        type = info.type;
        // Use parsed provider info
        track = Object.assign({}, track, { src: info.src, providerId: info.providerId, subType: info.subType });
      }
      const src = info.src || (track && track.src) || '';
      const providerId = info.providerId || (track && (track.youtubeId || track.spotifyId)) || '';

      // OPTIMIZATION: skip load() nếu cùng src + type đang phát → tránh pause+reset
      if (this.currentType === type && src && this._lastLoadedSrc === src) {
        return Promise.resolve();
      }
      this._lastLoadedSrc = src;

      this.currentType = type;
      this._stopPolling();

      // Cleanup previous
      try { this.audio.pause(); } catch(e) {}
      this.ytContainer.innerHTML = '';
      if (this.ytPlayer) { try { this.ytPlayer.destroy(); } catch(e) {} this.ytPlayer = null; }
      this.spotifyContainer.innerHTML = '';
      this.spotifyIframe = null;
      this._spotifyReady = false;
      this._ytReady = false;

      if (type === 'mp3') {
        if (this.audio) {
          try { this.audio.pause(); } catch(e) {}
          this.audio.removeAttribute('src');
          this.audio.load();
          if (src) {
            this.audio.src = src;
            this.audio.loop = this.loop;
            this.audio.load();
          }
        }
        this.onReady && this.onReady({ type: 'mp3', src: src });
        return Promise.resolve();
      }

      if (type === 'youtube') {
        const ytId = providerId;
        if (!ytId) {
          this.onError && this.onError(new Error('YouTube: missing video id'));
          return Promise.reject(new Error('YouTube: missing video id'));
        }
        this._ytLoadingTrack = ytId;
        return loadYTApi().then((YT) => {
          if (this._destroyed) return;
          if (this._ytLoadingTrack !== ytId) return;
          // Tạo hidden host
          this.ytContainer.innerHTML = '';
          const host = document.createElement('div');
          host.id = 'yt-player-host-' + Date.now();
          host.style.cssText = 'position:absolute;left:-9999px;top:-9999px;width:1px;height:1px;pointer-events:none;';
          this.ytContainer.appendChild(host);
          this.ytPlayer = new YT.Player(host.id, {
            videoId: ytId,
            playerVars: {
              autoplay: 0,
              controls: 0,
              disablekb: 1,
              fs: 0,
              modestbranding: 1,
              playsinline: 1,
              rel: 0,
            },
            events: {
              onReady: (ev) => {
                this._ytReady = true;
                this.onReady && this.onReady({ type: 'youtube', src: src, ytId: ytId });
              },
              onStateChange: (ev) => {
                // YT.PlayerState.ENDED = 0
                if (ev.data === 0) {
                  if (this.loop) {
                    // Loop → restart video (seekTo 0 + playVideo)
                    try { this.ytPlayer.seekTo(0, true); this.ytPlayer.playVideo(); } catch(e) {}
                  } else {
                    this.onEnded && this.onEnded();
                  }
                }
              },
              onError: () => {
                this.onError && this.onError(new Error('YouTube player error'));
              },
            },
          });
          // Poll currentTime
          this._startPolling(() => {
            if (!this.ytPlayer || !this.ytPlayer.getCurrentTime) return [0, 0];
            try {
              const t = this.ytPlayer.getCurrentTime() || 0;
              const d = this.ytPlayer.getDuration() || 0;
              return [t, d];
            } catch(e) { return [0, 0]; }
          });
        }).catch((e) => {
          this.onError && this.onError(e);
        });
      }

      if (type === 'spotify') {
        // Spotify Embed iframe — phải giữ DOM visible (không display:none) để load.
        // Dùng position:absolute, opacity:0, width:1, height:1, pointer-events:none.
        const spId = providerId;
        const subType = info.subType || 'track';
        if (!spId) {
          this.onError && this.onError(new Error('Spotify: missing id'));
          return Promise.reject(new Error('Spotify: missing id'));
        }
        const iframeSrc = `https://open.spotify.com/embed/${subType}/${spId}?utm_source=oembed&theme=0`;
        this.spotifyContainer.innerHTML = `<iframe src="${iframeSrc}"
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
          loading="lazy"
          style="position:absolute;left:-2px;bottom:-2px;width:1px;height:1px;opacity:0.01;pointer-events:none;border:0;"
          width="1" height="1" frameborder="0"></iframe>`;
        this.spotifyIframe = this.spotifyContainer.querySelector('iframe');
        // Lắng nghe READY từ Spotify (Spotify iframe postMessage 'ready')
        const onSpotifyMsg = (ev) => {
          try {
            const data = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data;
            if (!data) return;
            if (data.type === 'ready' || (data.context && data.context.metadata)) {
              this._spotifyReady = true;
              this.onReady && this.onReady({ type: 'spotify', src: src, spId: spId, subType: subType });
            }
          } catch(e) {}
        };
        window.addEventListener('message', onSpotifyMsg);
        this._spotifyMsgHandler = onSpotifyMsg;
        // Fallback: timeout 3s coi như ready (cover hiển thị)
        setTimeout(() => {
          if (!this._spotifyReady && !this._destroyed) {
            this._spotifyReady = true;
            this.onReady && this.onReady({ type: 'spotify', src: src, spId: spId, subType: subType });
          }
        }, 3000);
        // Spotify không cho biết currentTime trực tiếp → tick đều để giữ UI sống.
        this._startPolling(() => [0, 0]);
        return Promise.resolve();
      }

      this.onError && this.onError(new Error('Unsupported track type: ' + type));
      return Promise.reject(new Error('Unsupported'));
    }

    play() {
      this.isPlaying = true;
      if (this.currentType === 'mp3' && this.audio && this.audio.src) {
        const p = this.audio.play();
        if (p && p.catch) p.catch(() => { /* autoplay blocked */ });
        return;
      }
      if (this.currentType === 'youtube' && this.ytPlayer && this._ytReady) {
        try { this.ytPlayer.playVideo(); } catch(e) {}
        return;
      }
      if (this.currentType === 'spotify' && this.spotifyIframe) {
        // Spotify embed: postMessage controller.
        // Phương pháp: thay src thêm &autoplay=true
        try {
          const url = new URL(this.spotifyIframe.src);
          if (!url.searchParams.has('autoplay')) {
            url.searchParams.set('autoplay', '1');
            this.spotifyIframe.src = url.toString();
          }
        } catch(e) {}
        return;
      }
    }

    pause() {
      this.isPlaying = false;
      if (this.currentType === 'mp3' && this.audio) {
        try { this.audio.pause(); } catch(e) {}
        return;
      }
      if (this.currentType === 'youtube' && this.ytPlayer && this._ytReady) {
        try { this.ytPlayer.pauseVideo(); } catch(e) {}
        return;
      }
      if (this.currentType === 'spotify') {
        // Reload iframe without autoplay để pause
        try {
          if (this.spotifyIframe) {
            const url = new URL(this.spotifyIframe.src);
            url.searchParams.delete('autoplay');
            this.spotifyIframe.src = url.toString();
          }
        } catch(e) {}
      }
    }

    setLoop(l) {
      this.loop = !!l;
      if (this.currentType === 'mp3' && this.audio) this.audio.loop = this.loop;
      // YouTube: loop tự xử lý ở onStateChange
      // Spotify: không hỗ trợ loop qua embed dễ
    }

    setVolume(v) {
      // v: 0..1
      if (this.audio) {
        try { this.audio.volume = Math.max(0, Math.min(1, v)); } catch(e) {}
      }
      if (this.currentType === 'youtube' && this.ytPlayer && this._ytReady) {
        try { this.ytPlayer.setVolume(Math.round(v * 100)); } catch(e) {}
      }
      // Spotify embed không hỗ trợ setVolume qua postMessage ổn định
    }

    seek(seconds) {
      if (this.currentType === 'mp3' && this.audio) {
        try { this.audio.currentTime = seconds; } catch(e) {}
        return;
      }
      if (this.currentType === 'youtube' && this.ytPlayer && this._ytReady) {
        try { this.ytPlayer.seekTo(seconds, true); } catch(e) {}
      }
    }

    _startPolling(probe) {
      this._stopPolling();
      this._pollProbe = probe;
      this.pollTimer = setInterval(() => {
        if (this._destroyed) return this._stopPolling();
        try {
          const [t, d] = (this._pollProbe && this._pollProbe()) || [0, 0];
          this.onTime(t, d);
        } catch(e) {}
      }, 250);
    }

    _stopPolling() {
      if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
      if (this._spotifyMsgHandler) {
        window.removeEventListener('message', this._spotifyMsgHandler);
        this._spotifyMsgHandler = null;
      }
    }
  }

  // ---------- UTILS ----------
  function autoFillTitleFromUrl(rawUrl) {
    const info = parseTrackUrl(rawUrl);
    if (info.type === 'youtube' && info.providerId) {
      return { title: '', cover: ytThumb(info.providerId) };
    }
    if (info.type === 'spotify') {
      return { title: 'Spotify ' + (info.subType || 'track'), cover: '' };
    }
    return { title: '', cover: '' };
  }

  global.MultiPlayer = {
    parseTrackUrl: parseTrackUrl,
    ytThumb: ytThumb,
    TrackPlayer: TrackPlayer,
    autoFillTitleFromUrl: autoFillTitleFromUrl,
  };
})(window);

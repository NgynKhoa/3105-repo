/* ============================================================
 *  Sync Module — Real-time sync local admin → GitHub Pages
 * ============================================================
 *
 *  Flow:
 *   1. Auto-poll mỗi 30s để check có thay đổi không
 *   2. Nếu có → tự động mở modal diff preview
 *   3. User confirm → POST /api/sync/push
 *   4. Sau khi push xong → workflow build-public.yml tự rebuild Pages (30-60s)
 *
 *  Hooks exposed:
 *   window.SyncModule.openDiffModal()  — mở modal thủ công (gắn vào btnSyncPages)
 *   window.SyncModule.startAutoPoll()  — bật auto-poll
 *   window.SyncModule.refreshStatus()  — refresh badge status
 */

(function () {
  'use strict';

  const POLL_INTERVAL_MS = 30 * 1000; // 30 giây
  const GH_PAGES_URL = 'https://ngynkhoa.github.io/3105-repo/';

  let pollTimer = null;
  let lastKnownDiffCount = -1;
  let isPushing = false;

  // ============== Helpers ==============

  async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(path, opts);
    const txt = await r.text();
    let data;
    try { data = JSON.parse(txt); } catch { data = { ok: false, error: txt }; }
    if (!r.ok && !data.ok) {
      throw new Error(data.error || `HTTP ${r.status}`);
    }
    return data;
  }

  function setBadge(state, label) {
    // state: 'idle' | 'dirty' | 'syncing' | 'synced' | 'error'
    const badge = document.getElementById('syncBadge');
    const lbl = document.getElementById('syncLabel');
    if (!badge || !lbl) return;
    const colors = {
      idle: '#888',
      dirty: '#ffcc00',
      syncing: '#00c8ff',
      synced: '#39ff14',
      error: '#ff4444',
    };
    badge.style.background = colors[state] || colors.idle;
    lbl.textContent = label;
  }

  function fmtTime(iso) {
    if (!iso) return 'chưa từng';
    const d = new Date(iso);
    const diff = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diff < 60) return `${diff}s trước`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m trước`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h trước`;
    return d.toLocaleDateString('vi-VN');
  }

  // ============== Diff Modal ==============

  function openModal() {
    const m = document.getElementById('syncModal');
    if (m) m.style.display = 'flex';
  }
  function closeModal() {
    const m = document.getElementById('syncModal');
    if (m) m.style.display = 'none';
  }

  function renderDiff(data) {
    const body = document.getElementById('syncModalBody');
    if (!body) return;
    const diff = data.diff || {};
    const total = (diff.added || []).length + (diff.modified || []).length + (diff.deleted || []).length;

    if (total === 0) {
      body.innerHTML = `
        <div style="text-align:center;padding:20px;color:#39ff14;">
          ✅ <strong>Đã đồng bộ hoàn toàn!</strong><br>
          <span style="color:var(--muted);font-size:12px;">
            ${data.local_files_count} files local = ${data.remote_files_count} files GitHub
          </span>
        </div>`;
      const btn = document.getElementById('syncModalConfirm');
      if (btn) btn.disabled = true;
      return;
    }

    const renderRow = (path, status, size) => {
      const colors = { added: '#39ff14', modified: '#ffcc00', deleted: '#ff4444' };
      const labels = { added: '+ ADDED', modified: '~ MODIFIED', deleted: '− DELETED' };
      return `<tr>
        <td style="color:${colors[status]};font-weight:600;padding:4px 8px;">${labels[status]}</td>
        <td style="padding:4px 8px;word-break:break-all;">${path}</td>
        <td style="padding:4px 8px;color:var(--muted);text-align:right;">${size || ''}</td>
      </tr>`;
    };

    body.innerHTML = `
      <div style="margin-bottom:12px;color:var(--muted);">
        Repo: <code style="color:var(--neon);">${data.full_name || '—'}</code><br>
        Local: ${data.local_files_count} files · Remote: ${data.remote_files_count} files ·
        <strong style="color:var(--neon);">${total} thay đổi</strong>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead>
          <tr style="border-bottom:1px solid #333;text-align:left;color:var(--muted);">
            <th style="padding:4px 8px;width:90px;">Status</th>
            <th style="padding:4px 8px;">Path</th>
            <th style="padding:4px 8px;width:80px;">Size</th>
          </tr>
        </thead>
        <tbody>
          ${(diff.added || []).map(f => renderRow(f.path, 'added', f.size + ' B')).join('')}
          ${(diff.modified || []).map(f => renderRow(f.path, 'modified', f.local_size + ' B')).join('')}
          ${(diff.deleted || []).map(f => renderRow(f.path, 'deleted', f.remote_size + ' B')).join('')}
        </tbody>
      </table>
      <div style="margin-top:12px;padding:8px;background:rgba(0,200,255,0.08);border-left:3px solid var(--neon);font-size:11px;color:var(--muted);">
        💡 Sau khi push, GitHub Actions <code>build-public.yml</code> sẽ rebuild Pages trong ~30-60s.
        Bạn có thể theo dõi tại: <a href="${GH_PAGES_URL}" target="_blank" style="color:var(--neon);">${GH_PAGES_URL}</a>
      </div>`;
    const btn = document.getElementById('syncModalConfirm');
    if (btn) btn.disabled = false;
  }

  // ============== Core Actions ==============

  async function computeDiff() {
    setBadge('syncing', '⏳ Đang check...');
    try {
      const data = await api('POST', '/api/sync/diff', { slug: 'demo' });
      return data;
    } catch (e) {
      setBadge('error', `❌ ${e.message.slice(0, 30)}`);
      throw e;
    }
  }

  async function openDiffModal(autoTriggered) {
    if (isPushing) return;
    try {
      const data = await computeDiff();
      const total = (data.diff?.added?.length || 0) + (data.diff?.modified?.length || 0) + (data.diff?.deleted?.length || 0);
      renderDiff(data);
      if (total > 0 || !autoTriggered) {
        openModal();
      }
      return data;
    } catch (e) {
      console.error('[sync] diff failed:', e);
      return null;
    }
  }

  async function doPush() {
    if (isPushing) return;
    isPushing = true;
    setBadge('syncing', '⏳ Đang push...');
    const btn = document.getElementById('syncModalConfirm');
    const cancelBtn = document.getElementById('syncModalCancel');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Đang push...'; }
    if (cancelBtn) cancelBtn.disabled = true;

    try {
      const result = await api('POST', '/api/sync/push', {
        slug: 'demo',
        message: 'chore(sync): update from local admin via 3105 Builder',
        mode: 'direct',
      });
      console.log('[sync] push result:', result);

      if (result.ok) {
        setBadge('synced', `✅ ${result.pushed}/${result.pushed}`);
        // Cập nhật body modal thành success
        const body = document.getElementById('syncModalBody');
        if (body) {
          body.innerHTML = `
            <div style="text-align:center;padding:20px;color:#39ff14;">
              ✅ <strong>Push thành công!</strong><br>
              <span style="color:var(--muted);font-size:12px;">
                ${result.pushed} files đã commit lên GitHub.
              </span><br><br>
              <span style="color:#ffcc00;font-size:11px;">
                ⏳ GitHub Pages đang rebuild (~30-60s)...
              </span><br>
              <a href="${GH_PAGES_URL}" target="_blank" style="color:var(--neon);font-size:11px;">
                → Mở ${GH_PAGES_URL}
              </a>
            </div>`;
        }
        // Auto-close modal sau 3s
        setTimeout(() => {
          closeModal();
          if (btn) btn.textContent = '🚀 Push lên GitHub';
          if (cancelBtn) cancelBtn.disabled = false;
          isPushing = false;
          // Reset badge sau 5s
          setTimeout(() => setBadge('idle', '🚀 Sync'), 5000);
        }, 3000);
      } else {
        setBadge('error', '❌ Lỗi');
        const body = document.getElementById('syncModalBody');
        if (body) {
          body.innerHTML = `
            <div style="color:#ff4444;padding:12px;">
              ❌ <strong>Push thất bại:</strong><br>
              ${(result.errors || []).map(e => `<div style="font-size:11px;margin-top:6px;">• ${e.path}: ${e.error}</div>`).join('')}
            </div>`;
        }
        if (btn) { btn.disabled = false; btn.textContent = '🚀 Push lên GitHub'; }
        if (cancelBtn) cancelBtn.disabled = false;
        isPushing = false;
      }
    } catch (e) {
      console.error('[sync] push failed:', e);
      setBadge('error', `❌ ${e.message.slice(0, 30)}`);
      if (btn) { btn.disabled = false; btn.textContent = '🚀 Push lên GitHub'; }
      if (cancelBtn) cancelBtn.disabled = false;
      isPushing = false;
    }
  }

  async function refreshStatus() {
    try {
      const data = await api('GET', '/api/sync/status');
      if (data.last_pushed_at) {
        setBadge('synced', `🟢 ${fmtTime(data.last_pushed_at)}`);
      } else {
        setBadge('idle', '🚀 Sync');
      }
    } catch (e) {
      // Ignore — không cần spam UI
    }
  }

  // ============== Auto-poll ==============

  async function pollOnce() {
    if (isPushing) return;
    try {
      const data = await computeDiff();
      const total = (data.diff?.added?.length || 0) + (data.diff?.modified?.length || 0) + (data.diff?.deleted?.length || 0);

      if (total === 0) {
        if (data.last_pushed_at) {
          setBadge('synced', `🟢 ${fmtTime(data.last_pushed_at)}`);
        } else {
          setBadge('idle', '🚀 Sync');
        }
        lastKnownDiffCount = 0;
        return;
      }

      // Có thay đổi mới?
      if (total !== lastKnownDiffCount) {
        setBadge('dirty', `🟡 ${total} thay đổi`);
        // Auto-open modal chỉ khi lần đầu detect (không spam mỗi 30s)
        if (lastKnownDiffCount === 0 || lastKnownDiffCount === -1) {
          // Lần đầu: mở modal để user biết
          await openDiffModal(true);
        }
        lastKnownDiffCount = total;
      } else {
        setBadge('dirty', `🟡 ${total} thay đổi`);
      }
    } catch (e) {
      // Network/GitHub error — giữ badge hiện tại
    }
  }

  function startAutoPoll() {
    if (pollTimer) return;
    refreshStatus();
    pollOnce();
    pollTimer = setInterval(pollOnce, POLL_INTERVAL_MS);
    console.log('[sync] auto-poll started (every 30s)');
  }

  function stopAutoPoll() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  // ============== Wire-up ==============

  function wire() {
    const btn = document.getElementById('btnSyncPages');
    if (btn) {
      btn.addEventListener('click', () => openDiffModal(false));
    }
    const closeBtn = document.getElementById('syncModalClose');
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    const cancelBtn = document.getElementById('syncModalCancel');
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
    const confirmBtn = document.getElementById('syncModalConfirm');
    if (confirmBtn) confirmBtn.addEventListener('click', doPush);

    // Click ngoài modal để đóng
    const modal = document.getElementById('syncModal');
    if (modal) {
      modal.addEventListener('click', e => {
        if (e.target === modal) closeModal();
      });
    }

    // Start auto-poll
    startAutoPoll();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }

  // Expose
  window.SyncModule = {
    openDiffModal,
    startAutoPoll,
    stopAutoPoll,
    refreshStatus,
    pollOnce,
  };
})();

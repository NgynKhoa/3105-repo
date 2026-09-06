/* =====================================================================
 * 3105 Repo Builder - Frontend logic
 * ===================================================================== */

const state = {
  repositories: [],
  currentRepo: null,
  repoMeta: {},
  packages: [],
  packagesMeta: [],
  sharedScreens: [],
  sharedOS: [],
  assets: [],
  packageFiles: [],
  editingIndex: null,
};

// ---------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return Array.from(document.querySelectorAll(sel)); }

function toast(msg, type = 'info') {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'fixed bottom-5 right-5 px-4 py-2 rounded-lg shadow-lg text-sm z-50 text-white';
  el.classList.add(type === 'error' ? 'bg-red-600' : type === 'success' ? 'bg-emerald-600' : 'bg-slate-900');
  el.classList.remove('hidden');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add('hidden'), 3500);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.description || data.message || `HTTP ${res.status}`);
  }
  return data;
}

// replaceAll không có sẵn ở một số trình duyệt cũ — dùng replace + regex /g.
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatSize(bytes) {
  if (bytes === null || bytes === undefined) return '0 B';
  bytes = Number(bytes);
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes.toFixed(bytes >= 100 ? 0 : 1)} ${units[i]}`;
}

// SHA-256 hex 64 ký tự, in hoa
function normalizeSha256(s) {
  return String(s || '').trim().toUpperCase();
}

// ---------------------------------------------------------------------
// Load repositories
// ---------------------------------------------------------------------

async function loadRepositories() {
  try {
    const data = await api('/api/repositories');
    state.repositories = data.repositories || [];
    const sel = $('#repoSelect');
    sel.innerHTML = '';
    if (state.repositories.length === 0) {
      sel.innerHTML = '<option value="">— không có repo —</option>';
      toast('Chưa có repo nào dưới thư mục repositories/.', 'error');
      return;
    }
    state.repositories.forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      sel.appendChild(opt);
    });
    if (state.repositories.includes('demo')) {
      sel.value = 'demo';
    } else {
      sel.value = state.repositories[0];
    }
    state.currentRepo = sel.value;
    await loadRepo();
  } catch (err) {
    toast(`Lỗi: ${err.message}`, 'error');
  }
}

async function loadRepo() {
  const repo = state.currentRepo;
  if (!repo) return;

  try {
    // Load packages + meta
    const data = await api(`/api/repo/${repo}/packages`);
    state.repoMeta = data.repoMeta || {};
    state.sharedScreens = data.sharedScreens || (window.DEFAULT_SCREENSHOTS || []);
    state.sharedOS = data.sharedOS || (window.DEFAULT_OS_RULES || []);
    // packagesMeta đi kèm từ backend — dùng để ghi lại YAML đúng anchor
    state.packagesMeta = Array.isArray(data.packagesMeta) ? data.packagesMeta : [];
    state.packages = (data.packages || []).map(normalizePackage);

    // Load file listings
    const files = await api(`/api/repo/${repo}/files`);
    state.assets = files.assets || [];
    state.packageFiles = files.packages || [];

    renderMeta();
    renderPackageList();
    toast(`Đã tải ${state.packages.length} package từ repo "${repo}".`, 'success');
  } catch (err) {
    toast(`Lỗi tải repo: ${err.message}`, 'error');
  }
}

function normalizePackage(pkg, idx) {
  // Giữ nguyên cờ anchor từ backend; chỉ thêm default nếu backend không cung cấp.
  const meta = state.packagesMeta[idx] || {};
  return {
    ...pkg,
    __use_default_os: !!meta.use_anchor_os,
    __use_default_screens: !!meta.use_anchor_screens,
  };
}

// ---------------------------------------------------------------------
// Render: repo meta
// ---------------------------------------------------------------------

function renderMeta() {
  $('#meta_identifier').value = state.repoMeta.identifier || '';
  $('#meta_name').value = state.repoMeta.name || '';
  $('#meta_description').value = state.repoMeta.description || '';
  $('#meta_accentColor').value = state.repoMeta.accentColor || '#FF3B30';

  const iconSel = $('#meta_icon');
  iconSel.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = '— chọn ảnh —';
  iconSel.appendChild(placeholder);
  state.assets.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p;
    opt.textContent = p;
    iconSel.appendChild(opt);
  });
  // Đảm bảo icon hiện tại được chọn dù có/không có trong danh sách scan
  if (state.repoMeta.icon) {
    const exists = Array.from(iconSel.options).some(o => o.value === state.repoMeta.icon);
    if (!exists) {
      const opt = document.createElement('option');
      opt.value = state.repoMeta.icon;
      opt.textContent = `${state.repoMeta.icon} (không tìm thấy)`;
      iconSel.appendChild(opt);
    }
    iconSel.value = state.repoMeta.icon;
  }
}

// ---------------------------------------------------------------------
// Render: package list
// ---------------------------------------------------------------------

function renderPackageList() {
  const list = $('#packageList');
  list.innerHTML = '';
  $('#packageCount').textContent = `${state.packages.length} package`;
  $('#emptyHint').classList.toggle('hidden', state.packages.length > 0);

  state.packages.forEach((pkg, idx) => {
    const row = document.createElement('div');
    row.className = 'px-5 py-3 hover:bg-slate-50 flex items-center gap-3';
    row.innerHTML = `
      <div class="flex-shrink-0 w-10 h-10 rounded-md bg-slate-200 overflow-hidden flex items-center justify-center">
        ${pkg.icon
          ? `<img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(pkg.icon)}" class="w-full h-full object-cover" onerror="this.style.display='none'" />`
          : '<span class="text-slate-400 text-xs">no img</span>'}
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="font-medium truncate">${escapeHtml(pkg.name || '(chưa có tên)')}</span>
          ${pkg.featured ? '<span class="bg-yellow-100 text-yellow-800 text-xs px-2 py-0.5 rounded-full">featured</span>' : ''}
          ${pkg.isPrivate ? '<span class="bg-slate-200 text-slate-700 text-xs px-2 py-0.5 rounded-full">private</span>' : ''}
          ${pkg.kind ? `<span class="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full">${escapeHtml(pkg.kind)}</span>` : ''}
        </div>
        <div class="text-xs text-slate-500 truncate">
          <code>${escapeHtml(pkg.identifier)}</code> · v${escapeHtml(pkg.version || '?')} · ${escapeHtml(pkg.category || '—')}
        </div>
      </div>
      <div class="text-xs text-slate-500 text-right">
        <div>${formatSize(pkg.size)}</div>
        <div class="truncate max-w-[120px]" title="${escapeHtml(pkg.sha256 || '')}">${escapeHtml((pkg.sha256 || '').slice(0, 10))}…</div>
      </div>
      <div class="flex gap-1">
        <button data-action="edit" data-idx="${idx}" class="px-2 py-1 text-xs rounded border border-slate-300 hover:bg-slate-100">Sửa</button>
        <button data-action="duplicate" data-idx="${idx}" class="px-2 py-1 text-xs rounded border border-slate-300 hover:bg-slate-100" title="Sao chép package này để tạo bản mới">Sao chép</button>
        <button data-action="delete" data-idx="${idx}" class="px-2 py-1 text-xs rounded border border-red-200 text-red-600 hover:bg-red-50">Xoá</button>
      </div>
    `;
    list.appendChild(row);
  });

  $$('#packageList [data-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx, 10);
      const action = btn.dataset.action;
      if (action === 'edit') openModal(idx);
      else if (action === 'delete') deletePackage(idx);
      else if (action === 'duplicate') duplicatePackage(idx);
    });
  });
}

// ---------------------------------------------------------------------
// Modal: thêm / sửa package
// ---------------------------------------------------------------------

function openModal(editIdx = null) {
  state.editingIndex = editIdx;
  const isEdit = editIdx !== null;
  $('#modalTitle').textContent = isEdit ? `Sửa package #${editIdx + 1}` : 'Thêm package mới';
  $('#modalStatus').textContent = isEdit
    ? `Đang sửa: ${state.packages[editIdx].identifier || '(chưa có id)'}`
    : 'Điền thông tin bên dưới, sau đó bấm Lưu package.';

  const pkg = isEdit
    ? { ...state.packages[editIdx] }
    : newPackageTemplate();

  $('#modalBody').innerHTML = buildFormHtml(pkg);
  bindFormEvents();
  $('#modal').classList.remove('hidden');
  $('#modal').classList.add('flex');
}

function closeModal() {
  $('#modal').classList.add('hidden');
  $('#modal').classList.remove('flex');
  state.editingIndex = null;
}

function newPackageTemplate() {
  // Sinh identifier tự động dựa trên packages hiện có
  const used = new Set(state.packages.map(p => p.identifier));
  let next = state.packages.length + 1;
  while (used.has(`owen-${String(next).padStart(3, '0')}`)) next++;
  const id = `owen-${String(next).padStart(3, '0')}`;
  return {
    identifier: id,
    name: '',
    author: '@owenindahouse',
    version: '1.0.0',
    summary: '',
    category: 'Customization',
    tags: ['CUSTOM'],
    icon: '',
    banner: 'assets/banner.png',
    screenshots: [],
    download: '',
    sha256: '',
    size: 0,
    password: '',
    featured: false,
    isPrivate: false,
    description: '',
    changelog: '🎉 v1.0.0 — Phát hành lần đầu',
    __use_default_os: true,
    __use_default_screens: true,
  };
}

function buildFormHtml(pkg) {
  const options = (items, selected) => items.map(it =>
    `<option value="${escapeHtml(it)}" ${it === selected ? 'selected' : ''}>${escapeHtml(it)}</option>`
  ).join('');

  const assetOptions = (current) => {
    const opts = ['<option value="">— chọn ảnh —</option>'];
    state.assets.forEach(p => {
      const sel = p === current ? 'selected' : '';
      opts.push(`<option value="${escapeHtml(p)}" ${sel}>${escapeHtml(p)}</option>`);
    });
    if (current && !state.assets.includes(current)) {
      opts.push(`<option value="${escapeHtml(current)}" selected>${escapeHtml(current)} (không tìm thấy)</option>`);
    }
    return opts.join('');
  };

  const packageOptions = (current) => {
    const opts = ['<option value="">— chọn file .3105 —</option>'];
    state.packageFiles.forEach(p => {
      const sel = p === current ? 'selected' : '';
      opts.push(`<option value="${escapeHtml(p)}" ${sel}>${escapeHtml(p)}</option>`);
    });
    if (current && !state.packageFiles.includes(current)) {
      opts.push(`<option value="${escapeHtml(current)}" selected>${escapeHtml(current)} (không tìm thấy)</option>`);
    }
    return opts.join('');
  };

  const defaultScreens = window.DEFAULT_SCREENSHOTS || [];

  return `
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">File .3105 (chọn để tự động điền SHA-256 + size)</span>
        <div class="flex gap-2 mt-1">
          <select id="f_download" class="flex-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">${packageOptions(pkg.download)}</select>
          <button id="btnAutoFill" type="button" class="px-3 py-1.5 rounded-md bg-blue-500 hover:bg-blue-600 text-white text-sm whitespace-nowrap">⚡ Tự động điền</button>
        </div>
      </label>

      <label class="block">
        <span class="text-xs text-slate-500">Identifier *</span>
        <input id="f_identifier" value="${escapeHtml(pkg.identifier)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Tên hiển thị *</span>
        <input id="f_name" value="${escapeHtml(pkg.name)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Phiên bản *</span>
        <input id="f_version" value="${escapeHtml(pkg.version)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Tác giả *</span>
        <input id="f_author" value="${escapeHtml(pkg.author)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>
      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">Tóm tắt (summary) *</span>
        <input id="f_summary" value="${escapeHtml(pkg.summary)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>

      <label class="block">
        <span class="text-xs text-slate-500">Category *</span>
        <select id="f_category" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">
          ${options(window.CATEGORIES || [], pkg.category)}
        </select>
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Tags (phân cách bằng dấu phẩy)</span>
        <input id="f_tags" value="${escapeHtml((pkg.tags || []).join(', '))}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>

      <label class="block">
        <span class="text-xs text-slate-500">Kind (để trống = package thường)</span>
        <input id="f_kind" value="${escapeHtml(pkg.kind || '')}" placeholder="vd: wallpaper" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">PublishedAt (ISO 8601, tuỳ chọn)</span>
        <input id="f_publishedAt" value="${escapeHtml(pkg.publishedAt || '')}" placeholder="2026-09-06T10:00:00Z" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>

      <label class="block">
        <span class="text-xs text-slate-500">Icon</span>
        <select id="f_icon" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">${assetOptions(pkg.icon)}</select>
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Banner</span>
        <select id="f_banner" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">${assetOptions(pkg.banner)}</select>
      </label>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_use_default_screens" ${pkg.__use_default_screens ? 'checked' : ''} />
          Dùng danh sách screenshot mặc định
          <span class="text-slate-400">(4 ảnh: preview-first → preview-four)</span>
        </span>
      </label>
      <label class="block md:col-span-2" id="screensListWrap" style="${pkg.__use_default_screens ? 'display:none' : ''}">
        <span class="text-xs text-slate-500">Screenshot tuỳ chỉnh (mỗi dòng 1 path)</span>
        <textarea id="f_screenshots" rows="3" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono">${escapeHtml((pkg.screenshots || []).join('\n'))}</textarea>
      </label>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_use_default_os" ${pkg.__use_default_os ? 'checked' : ''} />
          Dùng iOS rule mặc định (17.0 → 27.0)
        </span>
      </label>

      <label class="block">
        <span class="text-xs text-slate-500">SHA-256 *</span>
        <input id="f_sha256" value="${escapeHtml(pkg.sha256)}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>
      <label class="block">
        <span class="text-xs text-slate-500">Size (bytes) *</span>
        <input id="f_size" type="number" value="${pkg.size || 0}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">Password (để trống nếu không cần)</span>
        <input id="f_password" value="${escapeHtml(pkg.password || '')}" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono" />
      </label>

      <label class="block md:col-span-2 flex items-center gap-4">
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_featured" ${pkg.featured ? 'checked' : ''} /> Featured
        </span>
        <span class="text-xs text-slate-500 flex items-center gap-2">
          <input type="checkbox" id="f_isPrivate" ${pkg.isPrivate ? 'checked' : ''} /> Riêng tư
        </span>
      </label>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">Description (mô tả dài, xuống dòng thoải mái)</span>
        <textarea id="f_description" rows="6" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">${escapeHtml(pkg.description || '')}</textarea>
      </label>

      <label class="block md:col-span-2">
        <span class="text-xs text-slate-500">Changelog</span>
        <textarea id="f_changelog" rows="3" class="w-full mt-1 border border-slate-300 rounded-md px-3 py-1.5 text-sm">${escapeHtml(pkg.changelog || '')}</textarea>
      </label>

      <details class="md:col-span-2 text-xs text-slate-500">
        <summary class="cursor-pointer text-slate-600 hover:text-slate-900">📂 Mặc định dùng chung</summary>
        <div class="mt-2 p-3 bg-slate-50 rounded-md font-mono text-[11px] whitespace-pre-wrap">iOS rules:
${(window.DEFAULT_OS_RULES || []).map(r => '  - minimum: ' + r.minimum + ', maximum: ' + r.maximum + (r.builds ? ', builds: ' + JSON.stringify(r.builds) : '')).join('\n')}

Screenshots mặc định:
${(defaultScreens).map(s => '  - ' + s).join('\n')}</div>
      </details>
    </div>
  `;
}

function bindFormEvents() {
  $('#btnAutoFill')?.addEventListener('click', async () => {
    const path = $('#f_download').value;
    if (!path) { toast('Chọn file .3105 trước đã.', 'error'); return; }
    try {
      const r = await api(`/api/repo/${state.currentRepo}/hash`, {
        method: 'POST',
        body: JSON.stringify({ path }),
      });
      $('#f_download').value = r.path;
      $('#f_sha256').value = r.sha256;
      $('#f_size').value = r.size;
      toast(`Đã điền SHA-256 + size cho ${r.path}`, 'success');
    } catch (err) {
      toast(`Lỗi: ${err.message}`, 'error');
    }
  });

  $('#f_use_default_screens')?.addEventListener('change', e => {
    $('#screensListWrap').style.display = e.target.checked ? 'none' : 'block';
  });

  $('#btnSavePackage').onclick = savePackageFromForm;
  $('#btnCancel').onclick = closeModal;
  $('#btnCloseModal').onclick = closeModal;
}

function readFormToPackage() {
  return {
    identifier: $('#f_identifier').value.trim(),
    name: $('#f_name').value.trim(),
    version: $('#f_version').value.trim(),
    author: $('#f_author').value.trim(),
    summary: $('#f_summary').value.trim(),
    category: $('#f_category').value,
    tags: $('#f_tags').value.split(',').map(s => s.trim()).filter(Boolean),
    kind: $('#f_kind').value.trim(),
    publishedAt: $('#f_publishedAt').value.trim(),
    icon: $('#f_icon').value,
    banner: $('#f_banner').value,
    __use_default_screens: $('#f_use_default_screens').checked,
    screenshots: $('#f_screenshots').value.split('\n').map(s => s.trim()).filter(Boolean),
    download: $('#f_download').value,
    sha256: normalizeSha256($('#f_sha256').value),
    size: parseInt($('#f_size').value, 10) || 0,
    password: $('#f_password').value,
    featured: $('#f_featured').checked,
    isPrivate: $('#f_isPrivate').checked,
    __use_default_os: $('#f_use_default_os').checked,
    description: $('#f_description').value,
    changelog: $('#f_changelog').value,
  };
}

function savePackageFromForm() {
  const pkg = readFormToPackage();
  // Validate
  if (!pkg.identifier) return toast('Thiếu identifier.', 'error');
  if (!/^[a-z0-9][a-z0-9._-]{1,63}$/.test(pkg.identifier)) return toast('Identifier không hợp lệ.', 'error');
  if (!pkg.name) return toast('Thiếu tên.', 'error');
  if (!pkg.download) return toast('Thiếu file .3105.', 'error');
  if (!pkg.sha256) return toast('Thiếu SHA-256 (bấm "Tự động điền").', 'error');
  if (!/^[0-9A-F]{64}$/.test(pkg.sha256)) return toast('SHA-256 phải là hex 64 ký tự.', 'error');
  if (!pkg.size || pkg.size <= 0) return toast('Size không hợp lệ.', 'error');

  // Trùng identifier với package khác?
  const dup = state.packages.findIndex((p, i) =>
    p.identifier === pkg.identifier && i !== state.editingIndex);
  if (dup >= 0) return toast(`Identifier "${pkg.identifier}" đã tồn tại ở package #${dup + 1}.`, 'error');

  // Tách các trường nội bộ ra khỏi object lưu trữ
  const useOs = pkg.__use_default_os;
  const useScreens = pkg.__use_default_screens;
  const pkgClean = { ...pkg };
  delete pkgClean.__use_default_os;
  delete pkgClean.__use_default_screens;

  if (state.editingIndex === null) {
    state.packages.push(pkgClean);
    state.packagesMeta.push({
      use_anchor_os: useOs,
      use_anchor_screens: useScreens,
    });
  } else {
    state.packages[state.editingIndex] = pkgClean;
    state.packagesMeta[state.editingIndex] = {
      use_anchor_os: useOs,
      use_anchor_screens: useScreens,
    };
  }
  closeModal();
  renderPackageList();
  toast('Đã lưu package vào bộ nhớ tạm. Bấm "💾 Lưu & ghi file" để ghi ra repo.yml.', 'success');
}

function deletePackage(idx) {
  if (!confirm(`Xoá package "${state.packages[idx].identifier}"?`)) return;
  state.packages.splice(idx, 1);
  state.packagesMeta.splice(idx, 1);
  renderPackageList();
  toast('Đã xoá khỏi bộ nhớ tạm.', 'info');
}

function duplicatePackage(idx) {
  const src = state.packages[idx];
  const used = new Set(state.packages.map(p => p.identifier));
  let n = 1;
  let newId = `${src.identifier}-copy`;
  while (used.has(newId)) {
    n += 1;
    newId = `${src.identifier}-copy${n}`;
  }
  const copy = {
    ...src,
    identifier: newId,
    name: `${src.name} (bản sao)`,
    sha256: '',
    size: 0,
    download: '',
  };
  state.packages.splice(idx + 1, 0, copy);
  state.packagesMeta.splice(idx + 1, 0, {
    use_anchor_os: state.packagesMeta[idx]?.use_anchor_os ?? true,
    use_anchor_screens: state.packagesMeta[idx]?.use_anchor_screens ?? true,
  });
  renderPackageList();
  toast(`Đã sao chép package → ${newId}. Mở Sửa để điền SHA-256/file mới.`, 'success');
}

// ---------------------------------------------------------------------
// Save to YAML
// ---------------------------------------------------------------------

async function saveAll() {
  if (!state.currentRepo) return toast('Chưa chọn repo.', 'error');
  if (state.packages.length === 0) {
    if (!confirm('Repo không có package nào. Vẫn ghi file?')) return;
  }

  // Đồng bộ meta packagesMeta cho khớp số lượng
  while (state.packagesMeta.length < state.packages.length) {
    state.packagesMeta.push({ use_anchor_os: true, use_anchor_screens: true });
  }
  if (state.packagesMeta.length > state.packages.length) {
    state.packagesMeta.length = state.packages.length;
  }

  // Đọc meta từ form
  const repoMeta = {
    schemaVersion: 1,
    identifier: $('#meta_identifier').value.trim() || `com.owen.${state.currentRepo}`,
    name: $('#meta_name').value.trim() || `${state.currentRepo} Repository`,
    description: $('#meta_description').value.trim(),
    icon: $('#meta_icon').value,
    accentColor: $('#meta_accentColor').value.trim() || '#FF3B30',
  };

  try {
    const r = await api(`/api/repo/${state.currentRepo}/save`, {
      method: 'POST',
      body: JSON.stringify({
        repoMeta,
        packages: state.packages,
        packagesMeta: state.packagesMeta,
      }),
    });
    const anchors = r.anchors || {};
    const anchorInfo = (anchors.os || anchors.screens) ? ` (anchor: ${[anchors.os && 'os', anchors.screens && 'screens'].filter(Boolean).join('+')})` : '';
    toast(`✓ Đã ghi file ${r.saved} (${r.count} package)${anchorInfo}.`, 'success');
    if (r.next) {
      console.log('Bước tiếp theo:\n' + r.next.join('\n'));
    }
  } catch (err) {
    toast(`Lỗi: ${err.message}`, 'error');
  }
}

// ---------------------------------------------------------------------
// Bind events
// ---------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  $('#repoSelect').addEventListener('change', e => {
    state.currentRepo = e.target.value;
    if (state.currentRepo) loadRepo();
  });
  $('#btnReload').addEventListener('click', loadRepo);
  $('#btnAdd').addEventListener('click', () => openModal(null));
  $('#btnSave').addEventListener('click', saveAll);

  // Phím tắt: ESC đóng modal
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !$('#modal').classList.contains('hidden')) {
      closeModal();
    }
  });

  loadRepositories();
});

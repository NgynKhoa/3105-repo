# 3105-repo

Kho lưu trữ custom iOS jailbreak repo (Sileo/TrollStore) + Admin Dashboard
local + phiên bản **public read-only** deploy tự động lên GitHub Pages.

## 🏗️ Kiến trúc

```
3105-repo/
├── repositories/           # Data repo (YAML + assets)
│   └── demo/
│       ├── repo.yml        # Schema: name, packages, blog, screenshots...
│       └── assets/         # icon, banner, screenshots, dialer, hdr_120...
├── admin/                  # LOCAL Flask admin (không public)
│   ├── app.py              # Server + API (read + write)
│   ├── templates/          # index.html (Front Repo), dashboard.html (Admin)
│   ├── static/             # app.js (chứa publicApiMock cho read-only build)
│   └── fe_checklist.py     # MCP integration
├── public/                 # BUILD OUTPUT cho GitHub Pages (auto-generated)
│   ├── index.html          # Front Repo read-only
│   ├── static/             # JS, CSS đã mirror
│   ├── repo.json           # snapshot từ repo.yml
│   ├── assets/             # 45 asset files mirrored
│   ├── 404.html
│   └── .nojekyll
├── tools/
│   └── build_public.py     # Sync admin → public
└── .github/workflows/
    └── build-public.yml    # GitHub Actions: build + deploy
```

## 🔐 Phân quyền

### Public (GitHub Pages)
- Ai cũng xem được: https://\<user\>.github.io/3105-repo
- Browse packages, blog, screenshots
- Tải file `.3105` qua link download
- ❌ KHÔNG có `/dashboard`, `/api/admin/*`, GitHub OAuth

### Local Admin (Flask)
- Chỉ chạy trên máy dev/admin: `python admin/app.py`
- Mở http://127.0.0.1:5050
- Toàn quyền: sửa repo.yml, layout, backgrounds, push lên GitHub
- ❌ KHÔNG deploy lên public (chỉ dành cho owner)

### Dev Patch (tương lai — Phase 2-4)
- Login GitHub OAuth → verify là owner/maintainer repo
- Mở admin panel trên web public → chỉnh sửa YAML qua Monaco editor
- Nút "💾 Save & Create PR" → GitHub App tự tạo PR
- Nút "⬇️ Export to IDE" → download file repo.yml

## 🚀 Cách deploy public

### Tự động (đã setup)
Mỗi khi push lên `main` mà có thay đổi trong:
- `repositories/**`  (repo.yml + assets)
- `admin/templates/index.html`
- `admin/static/**`
- `tools/build_public.py`

→ GitHub Actions `.github/workflows/build-public.yml` chạy:
1. Cài PyYAML
2. `python tools/build_public.py` — render index.html + copy static/assets
3. Upload artifact → Deploy lên GitHub Pages

Xem logs: https://github.com/NgynKhoa/3105-repo/actions

### Manual (debug local)
```bash
# Build
python tools/build_public.py

# Serve local
cd public && python -m http.server 8000
# Mở http://127.0.0.1:8000
```

## 🛠️ Cách dev local

```bash
# Clone
git clone https://github.com/NgynKhoa/3105-repo.git
cd 3105-repo

# Cài deps cho admin
pip install -r admin/requirements.txt  # flask, pyyaml

# Chạy admin local
python admin/app.py
# Mở http://127.0.0.1:5050 (Front Repo) hoặc /dashboard (Admin)

# Test public build local
python tools/build_public.py
cd public && python -m http.server 8001
# Mở http://127.0.0.1:8001 (Public read-only)
```

## 📦 Cách thêm repo mới

1. Tạo folder `repositories/<repo-slug>/` với `repo.yml` + `assets/`
2. Thêm vào `sources.json` nếu dùng remote sources
3. Commit + push → GitHub Actions tự build + deploy

## 🗺️ Roadmap

- [x] **Phase 1**: Tách public/admin, deploy read-only lên GitHub Pages ✅
- [ ] **Phase 2**: GitHub OAuth login flow (admin local + future public)
- [ ] **Phase 3**: Verify user là owner/maintainer repo qua GitHub API
- [ ] **Phase 4**: Monaco editor + Save/Create PR flow cho dev patch

## ⚠️ Lưu ý quan trọng

- **KHÔNG commit** `admin/.cache/` (cache MCP) — đã có trong `.gitignore`
- **KHÔNG commit** `admin.log`, `admin.err` — log runtime
- **KHÔNG sửa** trực tiếp file trong `public/` — sẽ bị build script ghi đè
- Repo `repositories/demo/repo.yml` là default build — thay đổi ở đây sẽ
  ảnh hưởng public site ngay sau khi push.

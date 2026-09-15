# Public Front Repo (read-only, deploy lên GitHub Pages)

Folder này chứa phiên bản **read-only** của Front Repo, được build tự động
từ `admin/templates/index.html` + `admin/static/*` + `repositories/*/repo.yml`
bởi script `tools/build_public.py` (chạy local + GitHub Actions).

## Nội dung (sau khi build)
- `index.html`           — phiên bản public của Front Repo
- `static/`              — JS, CSS, fonts, images đã bundle
- `repo.json`            — snapshot từ repo.yml (chỉ repo demo mặc định)
- `assets/`              — icon/banner/screenshot từng repo
- `404.html`             — fallback cho GitHub Pages
- `.nojekyll`            — tắt Jekyll processing

## KHÔNG có ở đây (chỉ dành cho admin)
- `/dashboard`           → chỉ chạy local Flask admin
- `/api/admin/*`         → write API (backgrounds upload, edit layout...)
- GitHub OAuth flow      → chỉ chạy local + tương lai Phase 2-4

## Workflow
1. User sửa repo qua admin local hoặc qua IDE + push lên GitHub
2. GitHub Actions `.github/workflows/build-public.yml` chạy mỗi push
   lên `main`, gọi `tools/build_public.py`
3. Script sync `index.html` + `static/*` + snapshot repo.yml + assets
   vào `public/`
4. Job thứ 2 deploy `public/` lên GitHub Pages (branch `gh-pages`)

## Local test
```bash
python tools/build_public.py
cd public && python -m http.server 8000
# mở http://127.0.0.1:8000
```

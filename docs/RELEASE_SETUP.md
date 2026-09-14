# Hướng dẫn setup GitHub Releases cho 3105 Builder

## Tổng quan

**3105 Builder** hỗ trợ 3 cách phát hành file `.3105` cho user download:

1. **Raw file trong repo** (mặc định, **khuyến nghị cho hầu hết trường hợp**)
2. **GitHub Releases** (dùng khi cần version tracking chuyên nghiệp)
3. **Auto** (thử raw trước, fallback releases)

## Cách 1: Raw file trong repo (MẶC ĐỊNH)

Đơn giản nhất, không cần setup gì.

### Cấu trúc folder

```
your-repo/
└── 3105-repo/repositories/demo/
    ├── repo.json
    └── packages/
        ├── com.example.pkg1-1.2.0.3105
        ├── com.example.pkg2-2.0.1.3105
        └── com.example.pkg3.3105
```

### Quy tắc đặt tên file

Front Repo auto-detect file `.3105` theo `package_id` (trong `repo.json`):

| File | Match `package_id` |
|------|-------------------|
| `{package_id}.3105` | exact |
| `{package_id}-1.2.0.3105` | versioned |
| `{package_id}-v1.2.0.3105` | versioned với v prefix |
| `com.example.pkg1-1.2.0-beta.3105` | semver pre-release |

### URL download tự động

```
https://raw.githubusercontent.com/{owner}/{repo}/main/3105-repo/repositories/demo/packages/{file}.3105
```

### Path candidates được quét

Server thử các folder theo thứ tự:
1. `3105-repo/repositories/demo/packages/`
2. `3105-repo/repositories/{slug}/packages/`
3. `repositories/demo/packages/`
4. `repositories/{slug}/packages/`
5. `packages/`
6. `dist/`, `build/packages/`, `src/packages/`
7. `.3105/packages/`

→ Repo đổi tên `3105-repo` → vẫn hoạt động nhờ các path fallback.

## Cách 2: GitHub Releases

Khi cần:
- Track version chuyên nghiệp (vd v1.0.0, v1.1.0, v1.2.0...)
- Auto-build qua GitHub Actions
- Phát hành file lớn (>10MB) với CDN GitHub
- Cho user subscribe release qua RSS

### Setup 1 lần: Workflow GitHub Actions

Tạo file `.github/workflows/release.yml` trong repo của admin:

```yaml
name: Build & Release 3105 Packages

on:
  push:
    tags: ['v*']
  workflow_dispatch:
    inputs:
      package_id:
        description: 'Package identifier (vd com.example.pkg1)'
        required: true
      version:
        description: 'Version (vd 1.2.0)'
        required: true

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Cần để tạo release
    steps:
      - uses: actions/checkout@v4

      - name: Build package
        run: |
          # Logic build .3105 file cho package
          # (bạn tự implement theo project)
          mkdir -p dist
          echo "FAKE BINARY CONTENT" > dist/output.3105

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ github.ref_name || format('v{0}', inputs.version) }}
          name: Release ${{ github.ref_name || format('v{0}', inputs.version) }}
          body: |
            Released by 3105 Builder.
            Package: ${{ inputs.package_id }}
            Version: ${{ inputs.version }}
          files: |
            dist/output.3105
```

### Setup OAuth Token (optional - cho admin upload qua web)

Nếu muốn upload file `.3105` trực tiếp từ web UI của 3105 Builder (không qua Git command):

1. **Không cần** thêm gì — OAuth token của GitHub đã có scope `public_repo`
2. Test thử bằng cách vào `localhost:5050` → login → Admin Dashboard → Packages → click "📦 Upload"
3. Điền version + file → submit → server tạo release + upload asset

### Path tới repo.json

Admin Settings lưu file `.3105/admin-settings.json`. Cần thêm vào repo của bạn:

```bash
mkdir -p .3105
cat > .3105/admin-settings.json <<EOF
{
  "download_mode": "releases",
  "theme": "default"
}
EOF
git add .3105/admin-settings.json
git commit -m "init admin-settings"
git push
```

## Cách 3: Auto (Hybrid)

Mặc định khi bạn không set `download_mode` trong admin-settings. Flow:

1. User click "⬇ Tìm" hoặc "⬇ Tải"
2. Server check `repo.json.download_paths[]` trước (manual override)
3. Nếu không có → auto-scan folder `packages/`
4. Nếu vẫn không có → fallback GitHub Releases (match by filename)

## Cú pháp `repo.json`

```json
{
  "slug": "demo",
  "identifier": "com.example.demo",
  "name": "Demo",
  "owner_github": "NgynKhoa",

  "download_mode": "auto",

  "download_paths": [
    {
      "package_id": "com.example.pkg1",
      "path": "3105-repo/repositories/demo/packages/pkg1-v1.2.0.3105",
      "raw_url": "https://raw.githubusercontent.com/NgynKhoa/3105-repo/main/3105-repo/repositories/demo/packages/pkg1-v1.2.0.3105",
      "asset_name": "pkg1-v1.2.0.3105",
      "size_bytes": 12345,
      "sha": "abc123..."
    }
  ],

  "releases": [
    {
      "package_id": "com.example.pkg1",
      "version": "1.3.0",
      "tag": "v1.3.0",
      "asset_name": "pkg1-v1.3.0.3105",
      "download_url": "https://github.com/.../releases/download/v1.3.0/pkg1-v1.3.0.3105",
      "size_bytes": 12345,
      "sha256": "abc..."
    }
  ]
}
```

## So sánh 3 cách

| | Raw file | GitHub Releases | Auto |
|---|----------|-----------------|------|
| Setup | Không | Workflow + OAuth | Không |
| Version tracking | Qua filename | Qua git tag | Cả 2 |
| Update UI | Re-build repo.json | Auto (qua web upload) | Auto |
| Multi-device | Qua git | Qua GitHub Releases | Qua git |
| CDN | GitHub raw (chậm cho VN) | GitHub CDN (nhanh hơn) | Best of both |
| Giới hạn size | 100MB/file | 2GB/asset | Inherit |
| Lý tưởng cho | Dev/internal | Production/public | Most users |

## Câu hỏi thường gặp

### Tôi muốn đổi tên folder `3105-repo` thành `my-awesome-repo`?

Đổi được. Path candidates có 8 lựa chọn:
- `3105-repo/repositories/demo/packages/` (YangJii fork)
- `3105-repo/repositories/{slug}/packages/`
- `repositories/demo/packages/`
- `repositories/{slug}/packages/`
- `packages/`
- `dist/`, `build/packages/`, `src/packages/`

Chỉ cần đặt file `.3105` ở 1 trong các path trên. Server tự detect.

### File `.3105` upload lên Releases có giới hạn size không?

- GitHub Releases: ≤2GB/asset
- Web UI upload: ≤95MB (giới hạn của GitHub Contents API, server enforce)
- Raw file qua git push: ≤100MB (khuyến nghị), thực tế GitHub giới hạn 100MB

### User download qua raw có cần auth không?

**Không**. raw.githubusercontent.com là public CDN cho repo public.
Anonymous user vẫn thấy nút "⬇ Tải" và download được.

### Có cache không?

- Server cache `repo.json`, `admin-settings.json`, release lookup 5 phút
- raw URL không cache (GitHub raw cache ở CDN level)

### Tôi cần thay đổi UI download mode?

Admin vào Settings → mục "🎨 Theme (chỉ Admin)" → chọn **download_mode** dropdown → save:
- `auto`: raw trước, fallback Releases
- `raw`: chỉ dùng raw
- `releases`: chỉ dùng Releases

Save → push lên `.3105/admin-settings.json` qua GitHub PR.

### Frontend không hiện nút "Tải xuống"?

Kiểm tra:
1. `repo.json` đã có chưa? (xem [TROUBLESHOOTING](./TROUBLESHOOTING.md))
2. Build với `--owner-github`: `python tools/build_public.py --repo demo --owner-github NgynKhoa`
3. File `.3105` có đúng naming convention không?
4. Mở DevTools → Network → click "⬇ Tìm" → xem response

### Tôi muốn test local trước khi push?

```bash
# 1. Tạo file .3105 dummy
mkdir -p 3105-repo/repositories/demo/packages
echo "TEST" > 3105-repo/repositories/demo/packages/com.example.pkg1-1.0.0.3105

# 2. Update repo.json packages section
# 3. Restart server
python -m admin.app

# 4. Test
curl http://localhost:5050/api/public/raw-assert/YOUR_USERNAME/REPO/demo/com.example.pkg1
# → raw_url trỏ tới file dummy của bạn
```

## Tài liệu liên quan

- [OAUTH_SETUP.md](./OAUTH_SETUP.md) — Setup GitHub OAuth App
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) — Debug khi repo không hiện
- [README.md](../README.md) — Overview

---

**Khuyến nghị cuối cùng**: bắt đầu với **raw file** (Cách 1). Khi nào cần version tracking chuyên nghiệp hoặc GitHub Actions build pipeline, chuyển sang **Auto**.

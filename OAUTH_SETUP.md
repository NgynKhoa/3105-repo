# OAuth GitHub Setup Guide

Triển khai OAuth GitHub để admin repo có thể đăng nhập trực tiếp trên Front Repo,
chỉnh sửa package, theme, meta — không cần SSH key hay local clone.

## Kiến trúc

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Front Repo UI  │   │  Flask Backend  │   │  GitHub.com     │
│  (Browser)      │   │  (localhost)    │   │                 │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         │ 1. Click "Đăng     │                     │
         │    nhập GitHub"     │                     │
         ├────────────────────►│                     │
         │                     │ 2. Redirect GitHub  │
         │                     │    authorize page   │
         │◄────────────────────┤                     │
         │                                            │
         │ 3. Authorize app                           │
         ├───────────────────────────────────────────►│
         │                                            │
         │ 4. Callback /auth/github/callback          │
         │◄───────────────────────────────────────────┤
         │  + code + state                            │
         │                     │ 5. Exchange code     │
         │                     ├────────────────────►│
         │                     │ 6. access_token      │
         │                     │◄────────────────────┤
         │                     │                     │
         │                     │ 7. GET /user         │
         │                     ├────────────────────►│
         │                     │ 8. user info         │
         │                     │◄────────────────────┤
         │                     │                     │
         │                     │ 9. GET /users/       │
         │                     │     {login}/repos    │
         │                     ├────────────────────►│
         │                     │ 10. list repos       │
         │                     │◄────────────────────┤
         │                     │                     │
         │                     │ 11. Tìm repo có      │
         │                     │     repo.json        │
         │                     │                     │
         │ 12. Session cookie  │                     │
         │     + redirect FE   │                     │
         │◄────────────────────┤                     │
         │                                            │
         │ 13. Gọi /auth/me                          │
         ├────────────────────►│                     │
         │ 14. is_owner_of     │                     │
         │◄────────────────────┤                     │
         │                                            │
         │ 15. Save package                           │
         │     POST /api/github/write                  │
         ├────────────────────►│                     │
         │                     │ 16. PUT contents     │
         │                     ├────────────────────►│
         │                     │ 17. Commit + PR      │
         │                     │◄────────────────────┤
         │ 18. PR URL          │                     │
         │◄────────────────────┤                     │
         │                                            │
         ▼                                            ▼
```

## Files

| File | Vai trò |
|------|---------|
| `admin/config.py` | Load env vars + validate cấu hình |
| `admin/auth.py` | Blueprint `/auth/*` — login, callback, me, logout |
| `admin/repo_discovery.py` | Scan GitHub repos + tìm `repo.json` |
| `admin/github_write.py` | Ghi file qua Contents API (PR hoặc direct push) |
| `admin/app.py` | Đăng ký blueprint + thêm `/api/github/write` |
| `admin/templates/index.html` | UI: login button + RBAC dynamic |
| `tools/build_public.py` | Inject `hideLoginForStatic()` cho GH Pages |
| `.env.example` | Template cho `.env` (KHÔNG commit `.env` thật) |

## Setup từng bước

### Bước 1: Tạo GitHub OAuth App

1. Mở https://github.com/settings/developers
2. Tab **"OAuth Apps"** → **"New OAuth App"**
3. Điền:
   - **Application name**: `3105-repo-builder` (tên hiển thị khi user authorize)
   - **Homepage URL**: `http://localhost:5050`
   - **Application description**: (tuỳ chọn) `Builder cho custom repository`
   - **Authorization callback URL**: `http://localhost:5050/auth/github/callback`
4. Bấm **"Register application"**
5. Trang hiển thị **Client ID** → copy vào `GITHUB_CLIENT_ID`
6. Bấm **"Generate a new client secret"** → copy **Client secret** vào `GITHUB_CLIENT_SECRET` (CHỈ hiện 1 lần)

> ⚠️ Không commit Client Secret lên git. `.env` đã có trong `.gitignore`.

### Bước 2: Tạo `.env`

```bash
# Trong thư mục gốc repo (cùng cấp admin/)
cp .env.example .env

# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
# → copy output dán vào SECRET_KEY trong .env
```

Sửa `.env`:
```env
GITHUB_CLIENT_ID=Iv1.xxxxxxxxxxxxxxxx
GITHUB_CLIENT_SECRET=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SECRET_KEY=<output từ lệnh trên>
OAUTH_CALLBACK_URL=http://localhost:5050/auth/github/callback
FRONTEND_BASE_URL=http://localhost:5050
```

### Bước 3: Chạy server

```bash
python -m admin.app
```

Console sẽ in:
```
[config] OAuth GitHub: ENABLED
[3105 Repo Builder] dang chay tai: http://127.0.0.1:5050
```

### Bước 4: Test OAuth flow

1. Mở `http://localhost:5050/`
2. Bấm nút ⚙️ (Settings) → **"Đăng nhập GitHub"**
3. Authorize trên GitHub
4. Redirect về Front Repo → toast "✅ Đăng nhập thành công"
5. Settings giờ hiển thị avatar + username + role

Nếu bạn **CÓ** repo có `repo.json`:
- Role: "🔓 admin của \"<slug>\""
- Admin Dashboard link hiện
- Packages có nút Sửa/Xóa
- Meta box không bị khoá

Nếu bạn **KHÔNG** có repo có `repo.json`:
- Role: "không có repo.json nào"
- Vẫn là user thường (RBAC giữ nguyên)

### Bước 5: Tạo repo có `repo.json`

Repo của admin cần có file `repo.json` ở **một trong các path**:
- `repo.json` (root, phổ biến nhất)
- `.3105/repo.json`
- `config/repo.json`
- `src/repo.json`

Schema:
```json
{
  "slug": "my-cool-repo",
  "identifier": "com.example.myrepo",
  "name": "My Cool Repository",
  "owner_github": "your-github-username"
}
```

- `slug`: required, unique, dùng để identify repo trong URL/API
- `identifier`: required, package identifier (vd `com.xxx`)
- `name`: optional
- `owner_github`: optional, GitHub username của admin (để verify)

Ví dụ tạo repo mới:
```bash
mkdir my-cool-repo && cd my-cool-repo
git init
echo '{"slug":"my-cool-repo","identifier":"com.example.myrepo","owner_github":"YOUR_GITHUB_USERNAME"}' > repo.json
git add repo.json
git commit -m "init: add repo.json"
gh repo create my-cool-repo --public --source=. --remote=origin --push
```

Sau đó trên Front Repo, bấm "Đăng nhập GitHub" → bạn sẽ thấy repo này trong list → có full admin controls.

## Scope

OAuth scope: `read:user public_repo`
- `read:user`: lấy username, avatar, email
- `public_repo`: push vào repo public (theo lựa chọn user)

**Không bao gồm** scope `repo` → không thể truy cập private repo.
Nếu admin cần push vào repo private → phải thêm scope `repo` và user phải approve GitHub (cần paid plan cho org).

## Production deployment

Cho HTTPS production:
1. Đăng ký domain + SSL cert
2. Cập nhật GitHub OAuth App:
   - Homepage URL: `https://your-domain.com`
   - Callback URL: `https://your-domain.com/auth/github/callback`
3. Cập nhật `.env`:
   ```env
   OAUTH_CALLBACK_URL=https://your-domain.com/auth/github/callback
   FRONTEND_BASE_URL=https://your-domain.com
   SESSION_COOKIE_SECURE=true   # cookie chỉ gửi qua HTTPS
   ```
4. Set `SECRET_KEY` cố định (không ephemeral)
5. Đảm bảo `.env` ở server, KHÔNG commit lên git

## Troubleshooting

### "OAuth chưa cấu hình"
→ `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` chưa set. Sửa `.env` và restart server.

### "State mismatch — có thể là CSRF attack"
→ Session bị expire giữa authorize và callback. Thử lại.

### "Bạn không phải owner của repo"
→ Repo không có `repo.json` ở 4 path candidates. Hoặc user login không phải owner (có thể là collaborator — chỉ owner mới được phép).

### "Token không hợp lệ hoặc đã hết hạn"
→ Token GitHub bị revoke. Bấm logout rồi login lại.

### Nút "Đăng nhập GitHub" không hiện trên GH Pages
→ Đúng — static hosting không có backend. Login chỉ hoạt động khi self-host (vd `python -m admin.app`). Trên GH Pages chỉ có build `--owner` để hiện controls (statically).

### Rate limit hit
→ GitHub OAuth token có 5000 req/h. Repo discovery scan 100 repos × 4 paths = 400 req, cache 5 phút → không vượt limit. Nếu vẫn hit, tăng `REPO_DISCOVERY_CACHE_TTL` trong `.env`.

## Bảo mật

- **Access token KHÔNG BAO GIỜ trả về client.** Chỉ set trong session server-side.
- **Session cookie HttpOnly** (JS không đọc được → chống XSS).
- **SameSite=Lax** (chống CSRF cho top-level nav).
- **State parameter** (CSRF protection trên OAuth).
- **Scope `public_repo`** (không có `repo` → user an tâm không lộ private repo).
- **Owner verification**: User phải CÓ repo.json mới được coi là admin. Không ai có thể giả danh.
- **Validation**: slug, path, content, commit_message đều được validate (regex + length limit) trước khi gửi GitHub.

## API Reference

| Endpoint | Method | Auth | Mô tả |
|---------|--------|------|-------|
| `/auth/github/login` | GET | - | Bắt đầu OAuth flow → redirect GitHub |
| `/auth/github/callback` | GET | - | GitHub redirect về (verify state, exchange code) |
| `/auth/me?slug=X` | GET | session | Trả thông tin user + `is_owner_of` (slug nào user là owner) |
| `/auth/logout` | POST/GET | session | Xoá session |
| `/api/repositories` | GET | optional | Local repos + merge `github_owned` nếu authenticated |
| `/api/github/write` | POST | required + owner | Body: `{slug, path, content, message, mode}` → ghi file vào GitHub |

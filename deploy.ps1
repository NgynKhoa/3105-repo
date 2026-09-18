# ============================================================
# deploy.ps1 — 1-click deploy Front admin → GitHub Pages
# ============================================================
# Chạy lệnh này SAU KHI bạn đã thay đổi Settings Front admin
# (theme, shadow, sizes, ...) và muốn đẩy lên GitHub Pages.
#
# Công việc:
#   1. Lọc admin-settings.json → public-defaults.json
#   2. Build public/index.html từ public-defaults.json + repo.yml
#   3. Git add + commit + push
#   4. Mở GitHub Actions để xem tiến trình rebuild Pages
#
# Cách dùng:
#   cd "C:\Users\NK\Desktop\MOD\3105-repo"
#   .\deploy.ps1                  # push lên branch hiện tại
#   .\deploy.ps1 -Message "fix"   # commit message tuỳ chỉnh
# ============================================================

param(
    [string]$Message = "chore(deploy): update Front admin via Settings",
    [switch]$SkipPush = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot

Write-Host ""
Write-Host "🚀 DEPLOY Front admin → GitHub Pages" -ForegroundColor Cyan
Write-Host "   Repo: $RepoRoot" -ForegroundColor Gray
Write-Host ""

# === Bước 1: bake_defaults.py ===
Write-Host "▶ [1/3] bake_defaults.py ..." -ForegroundColor Yellow
Push-Location $RepoRoot
try {
    python bake_defaults.py
    if ($LASTEXITCODE -ne 0) {
        throw "bake_defaults.py failed (exit $LASTEXITCODE)"
    }
} finally {
    Pop-Location
}

# === Bước 2: build_public.py ===
Write-Host ""
Write-Host "▶ [2/3] tools\build_public.py ..." -ForegroundColor Yellow
Push-Location $RepoRoot
try {
    python tools\build_public.py
    if ($LASTEXITCODE -ne 0) {
        throw "tools\build_public.py failed (exit $LASTEXITCODE)"
    }
} finally {
    Pop-Location
}

# === Bước 3: git add + commit + push ===
if (-not $SkipPush) {
    Write-Host ""
    Write-Host "▶ [3/3] git add + commit + push ..." -ForegroundColor Yellow

    # Kiểm tra có thay đổi không
    $gitStatus = git status --porcelain
    if ([string]::IsNullOrWhiteSpace($gitStatus)) {
        Write-Host "⚠ Không có thay đổi nào để commit." -ForegroundColor DarkYellow
        Write-Host "   (Bạn đã lưu Settings trên Front admin chưa?)" -ForegroundColor DarkYellow
    } else {
        git add .
        git commit -m $Message
        if ($LASTEXITCODE -ne 0) {
            throw "git commit failed (exit $LASTEXITCODE)"
        }
        git push
        if ($LASTEXITCODE -ne 0) {
            throw "git push failed (exit $LASTEXITCODE)"
        }
        Write-Host ""
        Write-Host "✅ Push thành công!" -ForegroundColor Green
        Write-Host ""
        Write-Host "   Bước tiếp theo:" -ForegroundColor Cyan
        Write-Host "   1. Mở https://github.com/NgynKhoa/3105-repo/actions" -ForegroundColor White
        Write-Host "   2. Đợi workflow 'Build Public' tick xanh (~1-2 phút)" -ForegroundColor White
        Write-Host "   3. Reload https://ngynkhoa.github.io/3105-repo/ (Ctrl+Shift+R)" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "✅ DONE." -ForegroundColor Green

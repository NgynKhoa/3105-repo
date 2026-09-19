@echo off
cd /d C:\Users\NK\Desktop\MOD\3105-repo
git add admin/templates/index.html admin/templates/blog.html .3105/public-defaults.json public/
git status --short
echo.
git commit -F - <<'EOF'
fix(public): 3 GH Pages bugs

1. SHADOW THEME khong apply cho user thuong
   - applyUserShadow dung sai CSS vars (--shadow-theme thay vi --logo-shadow-color)
   - Logo text khong update vi shadow style nam o --logo-shadow-color
   - Fix: dung dung vars giong applyShadowTheme (admin)
   - Test: user_shadowTheme=pink -> --logo-shadow-color=#ff2d7b

2. MUSIC COVER IMAGE 404
   - Playlist covers dung URL localhost (http://127.0.0.1:5050/assets/...)
   - Tren GH Pages URL nay 404 vi khong co Flask server
   - Fix: rewrite thanh relative ./assets/... trong PUBLIC_MODE
   - Test: bgImage=url(./assets/blog/fb0f4549800b.png)

3. BLOG BACK BUTTON 404
   - back-btn href=/, /blog -> absolute path -> tro ve github root
   - Tren GH Pages do la https://ngynkhoa.github.io/ -> 404
   - Fix: thay bang ./ va ./blog.html
   - Test: click back-btn -> ve index OK
EOF
git stash push -m "oauth" -- .oauth_cache/
git pull --rebase
git push
git stash pop

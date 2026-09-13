# Front-End Checklist (MCP) — Project Rule

## Khi nào áp dụng

Bất kỳ khi nào bạn (Agent) **review / implement / debug / audit** code
frontend của repo này (`admin/templates/*.html`, `admin/static/*.js`,
`admin/static/*.css`, hay front-page repo nào user đề cập), PHẢI dùng
Front-End Checklist MCP server trước khi đưa ra nhận xét.

MCP server đã được cấu hình trong `.cursor/mcp.json`:
- Name: `frontend-checklist`
- URL: `https://mcp.frontendchecklist.io`
- 11 tools exposed: `review_code`, `audit_url`, `get_workflow`,
  `get_checklist_rules`, `get_quick_reference`, `get_rule`,
  `search_rules`, `check_rule`, `fix_rule`, `explain_rule`,
  `list_categories`.

## Workflow bắt buộc cho mọi tác vụ frontend

1. **Static pass trước**: gọi `review_code` cho HTML/CSS/JS/React/Next.js
   paste hoặc file đính kèm. Đây là conservative static heuristic.
2. **Nếu không có issue**, vẫn gọi `search_rules` với keyword liên quan +
   `get_rule` cho từng rule nghi ngờ trước khi kết luận code "clean".
3. **Audit live URL**: gọi `audit_url` cho mọi URL public user đưa ra.
4. **Broad audit**: gọi `get_workflow` (launch / accessibility / seo /
   security / performance) trước khi check từng rule riêng lẻ.
5. **Explain + Fix**: dùng `explain_rule` để giải thích tại sao rule quan
   trọng, `fix_rule` để sinh code sửa lỗi.

## Categories bao phủ

`accessibility` (111) · `seo` (102) · `performance` (65) · `html` (58) ·
`css` (42) · `javascript` (32) · `images` (26) · `security` (24) ·
`testing` (13) · `privacy` (5) · `internationalization` (5) — tổng ~514 rules.

## Priority legend (mức độ ưu tiên khi review)

- 🔴 **Critical**: site-breaking, compliance, security — fix đầu tiên.
- 🟠 **High**: UX/a11y/perf/discoverability — fix ngay trong PR.
- 🟡 **Medium**: best practice thường trực — nên part of normal review.
- 🔵 **Low**: situational — fix khi có context phù hợp.

## Local proxy (khi không có MCP client)

Repo có 1 admin panel tích hợp sẵn tại `/fe-checklist` (qua
`http://127.0.0.1:5050/fe-checklist`) cho phép user **browse 514 rules +
chạy audit** không cần Cursor MCP. Code ở `admin/fe_checklist.py` +
`admin/static/fe_checklist.{js,css}` + routes trong `admin/app.py`
prefix `/api/fe-checklist/*`. Cache rules trong
`admin/.cache/fe-checklist/`.

Khi user hỏi "check page / repo này theo Front-End Checklist":
- Nếu đã paste code → dùng `review_code` qua MCP.
- Nếu có URL public → dùng `audit_url` qua MCP.
- Nếu user đang ở trong admin → gợi ý mở `/fe-checklist` để browse +
  chạy thủ công.

## Tips

- Có thể search rules theo keyword + filter category.
- Khi fix bug, ưu tiên các rule 🔴 Critical trước 🟠 High rồi 🟡 Medium.
- Mỗi rule có slug ổn định (vd: `html/viewport`, `css/css-minification`,
  `accessibility/aria-required-attributes`) — dùng slug để gọi
  `get_rule` / `fix_rule` / `explain_rule` chính xác.

## Đừng làm

- ❌ Không tự claim "code đã clean" nếu chưa qua `review_code` + rule
  search.
- ❌ Không recommend rule/fix mà chưa `get_rule` xác nhận còn hiệu lực.
- ❌ Không bỏ qua category nào — repo này có cả i18n + privacy + testing
  nên không thể chỉ check HTML/CSS.

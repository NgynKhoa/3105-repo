"""Entry point: cho phép `python -m admin` thay vì `python -m admin.app`.

Khi Flask app chạy qua `python admin/app.py` trực tiếp sẽ lỗi
`attempted relative import with no known parent package` vì các import
trong app.py đều ở dạng relative (`from .config import Config`).

Để support cả 3 cách chạy:
  1. cd 3105-repo && python admin/app.py
  2. cd 3105-repo && python -m admin.app
  3. cd 3105-repo && python -m admin
ta bọc ở đây: chèn sys.path để `admin.xxx` resolve được như package.
"""
import os
import sys

# Đảm bảo parent of admin/ có trong sys.path (khi chạy `python -m admin`)
HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

# Set __package__ thành "admin" để relative imports trong admin/app.py hoạt động
__package__ = "admin"

# Import module app để nó đăng ký routes + side-effects
from admin.app import app  # noqa: E402,F401

if __name__ == "__main__":
    # Tái tạo logic entry-point của admin/app.py (không gọi hàm main() vì không tồn tại)
    port = int(os.environ.get("PORT", 5050))
    auto_open = os.environ.get("AUTO_OPEN_BROWSER", "1") not in ("0", "false", "False", "no", "NO")

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Lấy ROOT + ROOT_PATH từ admin.app đã import
    from admin.app import ROOT  # noqa: E402

    print("=" * 60)
    print(f"[3105 Repo Builder] dang chay tai: http://127.0.0.1:{port}")
    print(f"Thu muc repo goc: {ROOT}")
    print(f"Auto-open trinh duyet: {'bat' if auto_open else 'tat'}")
    print("Nhan Ctrl+C de dung.")
    print("=" * 60)

    if auto_open:
        import threading
        import webbrowser

        def _open_browser():
            url = f"http://127.0.0.1:{port}"
            try:
                webbrowser.open(url)
                print(f"[3105 Repo Builder] da tu mo trinh duyet: {url}")
            except Exception as exc:
                print(f"[3105 Repo Builder] khong the mo trinh duyet tu dong: {exc}")
                print(f"  -> Hay tu mo: {url}")

        threading.Timer(1.0, _open_browser).start()

    # Tắt debug/reloader để không mở trình duyệt 2 lần.
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

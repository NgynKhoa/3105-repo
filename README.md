# 3105 Repository Catalog

Kho này chỉ chứa danh sách nguồn và dữ liệu package dành cho ứng dụng 3105.
Source code của ứng dụng không nằm trong repository này.

## Danh sách nguồn mặc định

Ứng dụng đọc `sources.json` khi làm mới nguồn. Để thêm một repository mới,
thêm URL HTTPS đầy đủ của `repo.json` vào mảng `sources`:

```json
{
  "schemaVersion": 1,
  "sources": [
    "repositories/demo/repo.json",
    "https://example.com/3105/repo.json"
  ]
}
```

URL tương đối được tính từ vị trí của `sources.json`. URL HTTP, localhost,
địa chỉ IP và URL chứa credentials sẽ bị ứng dụng từ chối.

## Nguồn thử nghiệm

`repositories/demo/repo.json` là nguồn mẫu có:

- Metadata, tác giả, phiên bản và changelog.
- Icon và hai ảnh preview cho CapCut Pro.
- Một package `.3105`: CapCut Pro.
- SHA-256 và kích thước package đã khai báo để kiểm tra khi tải.

## Nguồn wallpaper

130 wallpaper trong `repositories/demo/repo.json` được đồng bộ từ catalog
[SerStars/Nugget-Wallpapers](https://github.com/SerStars/Nugget-Wallpapers).
Mỗi gói được khai báo với `kind: "wallpaper"`, ảnh preview nằm trong phần mô
tả package và file `.tendies` được ghim vào một commit upstream bất biến. Sau
khi tải, 3105 xác thực và đưa gói vào mục **Đã cài** để người dùng mở và áp dụng.

Chạy `python3 scripts/sync_nugget_wallpapers.py` để cập nhật các wallpaper trong
repo chính lên commit upstream mới nhất. Script giữ nguyên các patch `.3105`,
thay danh sách wallpaper hiện tại và chỉ nhận file nằm trong commit GitHub đã
ghim; URL ngoài commit bị bỏ qua để không làm yếu kiểm tra nguồn.

## Thêm package

1. Đặt gói `.3105` trong thư mục `packages` của repository tương ứng.
2. Đặt icon và ảnh preview trong thư mục `assets`.
3. Thêm metadata vào `repo.json`.
4. Tính SHA-256 bằng `shasum -a 256 <package.3105>`.
5. Khai báo dung lượng và dải iOS. Không cần nhập `packageID` hoặc
   `bundleIdentifiers`; ứng dụng đọc các thông tin này từ gói `.3105`.

Package `.3105` có mật khẩu có thể khai báo thêm `"password": "..."` nếu chủ
repo muốn chia sẻ công khai để ứng dụng tự mở khoá. Nếu không khai báo, 3105 sẽ
yêu cầu người dùng liên hệ chủ repo và tự nhập mật khẩu. Mật khẩu không áp dụng
cho package `wallpaper`.

Wallpaper `.tendies` dùng `kind: "wallpaper"`. SHA-256 vẫn được khuyến nghị;
ngoại lệ duy nhất là URL `SerStars/Nugget-Wallpapers` được ghim vào commit
GitHub bất biến và tiếp tục qua bộ kiểm tra archive/descriptor của 3105.

## Xuống dòng trong nội dung

Trong chuỗi JSON, dùng `\n` để xuống dòng. Không dùng `/n`.

```json
{
  "description": "Dòng đầu tiên.\nDòng thứ hai."
}
```

Ứng dụng sẽ hiển thị hai dòng sau khi tải `repo.json`.

Mỗi `repo.json` phải được phục vụ qua HTTPS và tuân theo định dạng repository
3105 schema version 1.

## Quản lý repo qua web (Repo Builder)

Thay vì sửa `repo.yml` tay rồi `git push`, bạn có thể dùng trang web chạy
local để thêm/sửa/xoá package. Công cụ này tự tính SHA-256 + size, tự sinh
anchor YAML chuẩn, không bao giờ làm hỏng format.

### Cài đặt

```bash
pip install -r admin/requirements.txt
```

### Chạy

```bash
python admin/app.py
```

Mở trình duyệt: <http://localhost:5000>

### Cách dùng

1. **Chọn repo** trong dropdown (mặc định là `demo`). Tool hỗ trợ nhiều repo
   con — nếu sau này tạo thêm `repositories/beta/` thì chỉ cần chọn trong
   dropdown là chuyển sang repo đó.
2. **Bấm `+ Thêm package`** để thêm mới, hoặc **Sửa** / **Xoá** trên từng dòng.
3. Trong form, **chọn file `.3105`** trong dropdown rồi bấm **`⚡ Tự động điền`**
   → SHA-256 và size sẽ được tính và điền tự động (không cần chạy `shasum` tay).
4. Tick chọn `Dùng danh sách screenshot mặc định` và `Dùng iOS rule mặc định`
   để giữ file YAML gọn (tool sẽ dùng anchor `*screens` / `*os_rules`).
5. Bấm **`💾 Lưu & ghi file`** → tool ghi đè `repositories/<repo>/repo.yml`.
6. Tự push lên GitHub bằng SSH (tool không tự push để bạn kiểm soát):

   ```bash
   git add repositories/<repo>/repo.yml
   git commit -m "feat: thêm/sửa package"
   git push
   ```

GitHub Action `build.yml` sẽ tự convert YAML → JSON, app 3105 refresh sau vài giây.

### Vì sao chạy local (không host web công khai)?

Repo có chứa **mật khẩu package** (`password: "..."`) — không thể để lộ trên
web public. Khi chạy local, mật khẩu chỉ nằm trên máy bạn.

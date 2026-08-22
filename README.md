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

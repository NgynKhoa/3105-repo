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
- Icon, banner và hai ảnh preview.
- Một package `.3105` demo không chứa quy tắc thay thế tệp.
- SHA-256 và kích thước package đã khai báo để kiểm tra khi tải.

## Thêm package

1. Đặt gói `.3105` trong thư mục `packages` của repository tương ứng.
2. Đặt icon và ảnh preview trong thư mục `assets`.
3. Thêm metadata vào `repo.json`.
4. Tính SHA-256 bằng `shasum -a 256 <package.3105>`.
5. Khai báo đúng UUID của package, dung lượng, bundle đích và dải iOS.

Mỗi `repo.json` phải được phục vụ qua HTTPS và tuân theo định dạng repository
3105 schema version 1.

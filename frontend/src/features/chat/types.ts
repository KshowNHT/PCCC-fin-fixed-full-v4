export interface QuickPromptItem {
  id: string;
  label: string;
  category: string;
  prompt: string;
}

export const QUICK_PROMPTS: QuickPromptItem[] = [
  {
    id: "karaoke-3t",
    label: "Quán Karaoke 3 tầng (600m²)",
    category: "Dịch vụ giải trí",
    prompt:
      "Kiểm duyệt giúp tôi thiết kế quán Karaoke quy mô 3 tầng nổi, tổng diện tích xây dựng là 600m2, chiều cao PCCC là 10.5m. Chủ đầu tư là Vũ trường Kinh doanh Hà Nội. Đã có mặt đứng thiết kế ban đầu.",
  },
  {
    id: "nha-o-kd-4t",
    label: "Nhà ở kết hợp KD 4 tầng (400m²)",
    category: "Nhà ở hỗn hợp",
    prompt:
      "Tôi muốn thẩm duyệt hồ sơ công trình của Nguyễn Văn A: loại nhà ở riêng lẻ kết hợp kinh doanh dịch vụ tại tầng 1, quy mô 4 tầng nổi, diện tích xây dựng 400 m2 (bậc chịu lửa dự kiến là bậc III), chiều cao công trình 12m, không có tầng hầm. Hãy rà soát xem có đạt tiêu chuẩn không và có thuộc diện thẩm định bắt buộc không?",
  },
  {
    id: "kho-ke-cao-1t",
    label: "Nhà kho kệ cao chứa hàng (18m)",
    category: "Công nghiệp",
    prompt:
      "Rà soát giúp tôi phương án an toàn PCCC nhà kho xếp hàng trên giá đỡ bán tự động, quy mô 1 tầng cao 18m, diện tích xây dựng 1.200m2. Đơn vị thiết kế là công ty PQC.",
  },
];


export interface ProjectInfo {
  name: string;
  location: string;
  investor: string;
  designer: string;
  stage: string;
  type: string; // e.g. Nhà ở riêng lẻ, Nhà ở kết hợp kinh doanh, Văn phòng, Trường học, Gara...
  length: number;
  width: number;
  height: number;
  pcccHeight: number;
  floorArea: number;
  totalFloorArea: number;
  floors: number;
  basements: number;
  fireRating: string; // e.g. Bậc I, II, III, IV, V
  commercialDetails: string; // e.g. Tầng 1 - văn phòng/dịch vụ nhẹ
  floorFunctions?: string[];
  basementFunctions?: string[];
  basementHeights?: number[];
  basementAreas?: number[];
  basementFootprints?: number[];
}

export interface DocumentItem {
  id: string;
  code: string;
  title: string;
  type: "LUẬT" | "Nghị định" | "Thông tư" | "QCVN" | "TCVN" | "Khác";
  link: string;
  content?: string;
  isCustom?: boolean;
  uploadedAt?: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
}

export interface ChecklistItem {
  stt: number;
  category: string;
  criteria: string;
  requirement: string;
  result: "Đạt" | "Không đạt" | "Không bắt buộc" | "Khuyến nghị mạnh" | "Khuyến nghị" | "Cần xem xét" | "Cần đo đạc";
  note: string;
  reference: string;
}

export interface AssessmentResult {
  isSubjectToAppraisal: boolean;
  appraisalReason: string;
  checklist: ChecklistItem[];
  generalConclusion: string;
  warnings: string[];
}

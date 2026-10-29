export interface BuildingComponent {
  id: string;
  name: string;
  type: string;
  floors: number;
  basements: number;
  height: number;
  pcccHeight: number;
  floorArea: number;
  totalFloorArea: number;
  volume: number;
  hazardClass: string;
  industrialSubtype: string;
  fireRating: string;
  commercialDetails: string;
  sourcePages: number[];
  sourceText: string;
}

export interface ProjectInfo {
  components?: BuildingComponent[];
  componentsComplete?: boolean | null;
  sharedSystems?: boolean | null;
  concurrentDesign?: boolean | null;
  volume?: number | null;
  hazardClass?: string | null;
  industrialSubtype?: string | null;
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
  commercialDetails: string;
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
  result:
    | "Đạt"
    | "Không đạt"
    | "Không bắt buộc"
    | "Khuyến nghị mạnh"
    | "Khuyến nghị"
    | "Cần xem xét"
    | "Cần đo đạc";
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

/** Căn cứ pháp lý có cấu trúc do BACKEND tính (rules_engine/appraisal_basis.py) */
export type AppraisalStatus = "required" | "not_required" | "insufficient_data";

export interface AppraisalThresholdRow {
  key: "floors" | "totalFloorArea" | "height" | "volume";
  label: string;
  limitText: string;
  actualText: string;
  state: "met" | "not_met" | "missing";
}

export interface AppraisalBasis {
  componentResults?: Array<{
    id: string;
    name: string;
    appraisalBasis: AppraisalBasis;
  }>;
  status: AppraisalStatus;
  category: string;
  categoryLabel: string;
  categoryEvidence: string;
  ruleMode: "always" | "threshold" | "manual_review";
  thresholdSource:
    | "manual_review"
    | "statutory"
    | "scale_independent"
    | "conservative_estimate"
    | "reference_general";
  legalText: string;
  thresholds: AppraisalThresholdRow[];
  triggeredBy: string[];
  missingFields: string[];
  summary: string;
  conclusion: string;
  actualScale: string;
  minFireRatingText?: string;
}

export interface Session {
  id: string;
  title: string;
  projectInfo: ProjectInfo;
  messages: ChatMessage[];
  updatedAt: string;
  revision: string;
  reviewState?: "draft" | "reviewed";
  checklist?: ChecklistItem[];
  isSubjectToAppraisal?: boolean;
  appraisalReason?: string;
  appraisalBasis?: AppraisalBasis | null;
  warnings?: string[];
}

export type ActiveTab = "chat" | "checklist" | "verdict";

export const EMPTY_PROJECT: ProjectInfo = {
  name: "",
  location: "",
  investor: "",
  designer: "",
  stage: "",
  type: "",
  length: 0,
  width: 0,
  height: 0,
  pcccHeight: 0,
  floorArea: 0,
  totalFloorArea: 0,
  floors: 0,
  basements: 0,
  fireRating: "",
  commercialDetails: "",
  floorFunctions: [],
  basementFunctions: [],
  basementHeights: [],
  basementAreas: [],
  basementFootprints: [],
};

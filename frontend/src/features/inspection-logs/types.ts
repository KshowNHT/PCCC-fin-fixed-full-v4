export interface LegalBasisInfo {
  lawDocument?: string;
  article?: string;
  legalExcerpt?: string;
  thresholdUsed?: string;
  appendix?: string;
}

export interface ChecklistSnapshotItem {
  category?: string;
  item?: string;
  standard?: string;
  requirement?: string;
  result?: string;
  note?: string;
  reviewedBasis?: LegalBasisInfo;
}

export type AppraisalStatus = "required" | "not_required" | "insufficient_data";

export interface InspectionLogEntry {
  id: string;
  sessionId: string;
  triggerSource: string;
  isSubjectToAppraisal: boolean;
  appraisalReason: string;
  appraisalStatus?: AppraisalStatus;
  appraisalBasis?: LegalBasisInfo | null;
  checklist?: ChecklistSnapshotItem[];
  warnings?: string[];
  compliantCount: number;
  nonCompliantCount: number;
  createdAt: string;
}

export type InspectionLogScope = "session" | "all";


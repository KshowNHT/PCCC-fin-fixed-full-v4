import React, { useRef, useState, useEffect } from "react";
import {
  Flame,
  Plus,
  Trash2,
  Upload,
  RefreshCw,
  History,
  FileText,
  Compass,
  FileBadge,
  Eye,
  X,
  Download,
  ShieldCheck,
  Loader2,
  Search
} from "lucide-react";
import { ProjectInfo, DocumentItem } from "../types";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

const apiUrl = (path: string) =>
  `${API_BASE_URL}${path.startsWith("/") ? path : "/" + path}`;

interface SidebarProps {
  project: ProjectInfo;
  onUpdateProject: (info: Partial<ProjectInfo>) => void;
  documents: DocumentItem[];
  onUploadDocument: (files: File[], code: string, title: string, type: string) => Promise<DocumentItem[]>;
  onDeleteDocument: (id: string) => void;
  onResetDocuments: () => void;
  sessions: Array<{ id: string; title: string; updatedAt: string; projectInfo?: ProjectInfo }>;
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (id: string) => void;
  onTriggerAppraisal: () => void;
  isPending: boolean;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (open: boolean) => void;
}

export function Sidebar({
  project,
  onUpdateProject,
  documents,
  onUploadDocument,
  onDeleteDocument,
  onResetDocuments,
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onTriggerAppraisal,
  isPending,
  isSidebarOpen,
  setIsSidebarOpen
}: SidebarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [docCode, setDocCode] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [docType, setDocType] = useState("TCVN");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [docSearchQuery, setDocSearchQuery] = useState("");
  const [uploadProgress, setUploadProgress] = useState<{ [filename: string]: number }>({});

  // Local temporary states for input fields to prevent typing lag
  const [localName, setLocalName] = useState(project.name || "");
  const [localInvestor, setLocalInvestor] = useState(project.investor || "");
  const [localLocation, setLocalLocation] = useState(project.location || "");
  const [localFloors, setLocalFloors] = useState<string | number>(project.floors ?? "");
  const [localBasements, setLocalBasements] = useState<string | number>(project.basements ?? "");
  const [localPcccHeight, setLocalPcccHeight] = useState<string | number>(project.pcccHeight ?? "");
  const [localFloorArea, setLocalFloorArea] = useState<string | number>(project.floorArea ?? "");
  const [localTotalFloorArea, setLocalTotalFloorArea] = useState<string | number>(project.totalFloorArea ?? "");
  const [localCommDetails, setLocalCommDetails] = useState(project.commercialDetails || "");
  const [localFloorFunctions, setLocalFloorFunctions] = useState<string[]>(project.floorFunctions || []);
  const [localBasementFunctions, setLocalBasementFunctions] = useState<string[]>(project.basementFunctions || []);
  const [localBasementHeights, setLocalBasementHeights] = useState<number[]>(project.basementHeights || []);
  const [localBasementAreas, setLocalBasementAreas] = useState<number[]>(project.basementAreas || []);
  const [localBasementFootprints, setLocalBasementFootprints] = useState<number[]>(project.basementFootprints || []);
  const [showSuccessUpload, setShowSuccessUpload] = useState(false);

  // States for session history limit and offset
  const [sessionLimit, setSessionLimit] = useState<number>(5);
  const [sessionPage, setSessionPage] = useState<number>(0);

  // Sync state when active project changes (e.g., loaded session or AI-extracted values)
  useEffect(() => {
    if (document.activeElement?.id !== "input-name") setLocalName(project.name || "");
    if (document.activeElement?.id !== "input-investor") setLocalInvestor(project.investor || "");
    if (document.activeElement?.id !== "input-location") setLocalLocation(project.location || "");
    
    // FIX B08/B09 (Bao_Cao_QA_Lan_2.md): trước đây có logic "sticky" cố tình
    // GIỮ localFloors/localBasements cũ khi project.floors mới = 0, trừ khi
    // giá trị cũ đã <= 1 (`else if (Number(localFloors) <= 1)`). Khi bấm
    // "Thẩm định Hồ sơ Mới", session mới có project.floors = 0 nhưng
    // localFloors cũ (vd 5) > 1 nên KHÔNG BAO GIỜ được set về 0 — field
    // "Số tầng nổi" bị kẹt giá trị cũ trong khi mọi field khác (DT, chiều
    // cao...) đã reset đúng. Xoá điều kiện "sticky" này, đồng bộ thẳng như
    // các field khác — vẫn giữ nguyên guard "không ghi đè khi đang gõ".
    if (document.activeElement?.id !== "input-floors") {
      setLocalFloors(project.floors ?? "");
    }

    if (document.activeElement?.id !== "input-basements") {
      setLocalBasements(project.basements ?? "");
    }
    
    if (document.activeElement?.id !== "input-pccc-height") setLocalPcccHeight(project.pcccHeight ?? "");
    if (document.activeElement?.id !== "input-floor-area") setLocalFloorArea(project.floorArea ?? "");
    if (document.activeElement?.id !== "input-total-floor-area") setLocalTotalFloorArea(project.totalFloorArea ?? "");
    if (document.activeElement?.id !== "input-comm-details") setLocalCommDetails(project.commercialDetails || "");
    
    // FIX B08/B09 (tiếp): cùng loại lỗi — các mảng công năng/tầng hầm chỉ
    // đồng bộ khi project có dữ liệu MỚI (length > 0), nhưng khi tạo session
    // mới (mảng rỗng) thì state cục bộ cũ vẫn bị giữ nguyên thay vì xoá theo.
    setLocalFloorFunctions(project.floorFunctions || []);
    setLocalBasementFunctions(project.basementFunctions || []);
    setLocalBasementHeights(project.basementHeights || []);
    setLocalBasementAreas(project.basementAreas || []);
    setLocalBasementFootprints(project.basementFootprints || []);
  }, [project]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const files = Array.from(fileList) as File[];

    setIsUploading(true);
    setUploadError("");

    // Initialize progress for each file
    const initialProgress: { [filename: string]: number } = {};
    files.forEach(f => {
      initialProgress[f.name] = 5;
    });
    setUploadProgress(initialProgress);

    // Simulated interval to mimic uploading progress increment
    const intervalsList: any[] = [];
    files.forEach(f => {
      let currentProgress = 5;
      const interval = setInterval(() => {
        if (currentProgress < 92) {
          currentProgress += Math.floor(Math.random() * 15) + 5;
          if (currentProgress > 92) currentProgress = 92;
          setUploadProgress(prev => ({
            ...prev,
            [f.name]: currentProgress
          }));
        }
      }, 150);
      intervalsList.push(interval);
    });

    try {
      const code = docCode || (files.length === 1 ? files[0].name.split(".")[0] : "");
      const title = docTitle || (files.length === 1 ? `Tài liệu: ${files[0].name}` : "");
      const uploadedDocs = await onUploadDocument(files, code, title, docType);
      
      // Stop simulated timers and complete progress
      intervalsList.forEach(clearInterval);
      
      const completedProgress: { [filename: string]: number } = {};
      files.forEach(f => {
        completedProgress[f.name] = 100;
      });
      setUploadProgress(completedProgress);

      // Auto-preview first document upon successful upload
      if (uploadedDocs && uploadedDocs.length > 0) {
        setPreviewDoc(uploadedDocs[0]);
      }
      setShowSuccessUpload(true);
      setTimeout(() => setShowSuccessUpload(false), 3500);
      
      // Keep showing 100% completion state for 1.5 seconds then clear
      setTimeout(() => {
        setUploadProgress(prev => {
          const next = { ...prev };
          files.forEach(f => {
            delete next[f.name];
          });
          return next;
        });
      }, 1500);

      setDocCode("");
      setDocTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: any) {
      intervalsList.forEach(clearInterval);
      setUploadProgress({});
      setUploadError(err.message || "Lỗi tải file");
    } finally {
      setIsUploading(false);
    }
  };

  const filteredDocuments = documents.filter((doc) => {
    const q = docSearchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      (doc.code && doc.code.toLowerCase().includes(q)) ||
      (doc.title && doc.title.toLowerCase().includes(q))
    );
  });

  return (
    <div id="app-sidebar" className={`fixed lg:relative inset-y-0 left-0 z-45 transform ${
      isSidebarOpen 
        ? "translate-x-0 lg:w-80 lg:opacity-100 lg:border-r" 
        : "-translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0 lg:border-r-0 lg:overflow-hidden"
    } w-80 bg-white text-black flex flex-col h-full flex-shrink-0 transition-all duration-300 ease-in-out shadow-lg lg:shadow-none border-slate-200 print:hidden`}>
      {/* App Header Branded */}
      <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-brand-orange flex items-center justify-center text-white shadow-md shadow-brand-orange/25">
            <Flame className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h1 className="font-display font-black text-[18px] leading-tight tracking-tight text-black flex items-center gap-1">
              AI Expert PCCC <span className="text-brand-orange font-mono text-[10px] font-bold px-1 rounded bg-brand-orange/15 border border-brand-orange/20">v1.0</span>
            </h1>
            <p className="text-[14.5px] text-black font-black font-mono">Hệ thống thẩm định chuyên gia</p>
          </div>
        </div>

        {/* Mobile close sidebar button */}
        <button
          onClick={() => setIsSidebarOpen(false)}
          className="lg:hidden p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 cursor-pointer"
          title="Đóng thanh thông số"
        >
          <X className="w-5 h-5 animate-none" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
        {/* SECTION 1: PROJECT SPECS */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 border-b-2 border-slate-350 pb-1.5">
            <Compass className="w-4.5 h-4.5 text-brand-orange shrink-0" />
            <h2 className="text-[16px] font-black uppercase tracking-wider text-black font-display">Thông số Công trình</h2>
          </div>

          <div className="space-y-2.5 text-xs text-black">
            <div>
              <label className="block text-[10.5px] uppercase font-black text-black mb-1">Tên công trình</label>
              <input
                type="text"
                value={localName}
                id="input-name"
                onChange={(e) => setLocalName(e.target.value)}
                onBlur={() => onUpdateProject({ name: localName })}
                className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-bold border border-slate-300 focus:border-brand-orange transition-all text-sm font-sans"
                placeholder="Ví dụ: Nhà ở kết hợp kinh doanh 4 Tầng"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Chủ đầu tư</label>
                <input
                  type="text"
                  value={localInvestor}
                  id="input-investor"
                  onChange={(e) => setLocalInvestor(e.target.value)}
                  onBlur={() => onUpdateProject({ investor: localInvestor })}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-bold border border-slate-300 focus:border-brand-orange transition-all text-sm font-sans"
                  placeholder="Ông Nguyễn Văn A"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Địa điểm</label>
                <input
                  type="text"
                  value={localLocation}
                  id="input-location"
                  onChange={(e) => setLocalLocation(e.target.value)}
                  onBlur={() => onUpdateProject({ location: localLocation })}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-bold border border-slate-300 focus:border-brand-orange transition-all text-sm font-sans"
                  placeholder="Hà Nội"
                />
              </div>
            </div>

            <div>
              <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Loại & Công năng công trình</label>
              <select
                value={project.type}
                id="input-type"
                onChange={(e) => onUpdateProject({ type: e.target.value })}
                className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-bold border border-slate-300 focus:border-brand-orange transition-all text-sm font-sans"
              >
                <option value="Nhà ở riêng lẻ kết hợp kinh doanh">Nhà ở kết hợp kinh doanh</option>
                <option value="Nhà ở riêng lẻ">Nhà ở riêng lẻ dân dụng</option>
                <option value="Cơ sở kinh doanh Karaoke, Vũ trường">Cơ sở kinh doanh dịch vụ Karaoke</option>
                <option value="Gara ô tô">Gara ô-tô chuyên dụng</option>
                <option value="Văn phòng, khách sạn công cộng">Văn phòng, công sở, khách sạn</option>
                <option value="Nhà kho xếp giá đỡ kệ cao">Nhà kho chứa hàng hóa</option>
                <option value="Chợ, Trung tâm thương mại">Chợ, Trung tâm thương mại</option>
                <option value="Nhà máy, nhà xưởng sản xuất">Nhà máy, nhà xưởng</option>
                <option value="Cơ sở giáo dục, trường học">Trường học, cơ sở giáo dục</option>
                <option value="Rạp hát, hội trường, trung tâm tổ chức sự kiện">Rạp hát, hội trường</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Số tầng nổi</label>
                <input
                  type="number"
                  min={0}
                  value={localFloors}
                  id="input-floors"
                  onChange={(e) => {
                    // FIX B03: chặn số âm ngay tại UI (Math.max(0, ...)),
                    // đồng bộ với validation ge=0 phía backend.
                    const raw = e.target.value === "" ? "" : Math.max(0, Number(e.target.value));
                    const parsed = raw;
                    setLocalFloors(parsed);
                    const num = parsed === "" ? 0 : Number(parsed);
                    let nextList = [...localFloorFunctions];
                    if (nextList.length < num) {
                      while (nextList.length < num) {
                        nextList.push("Nhà ở riêng lẻ / Dân dụng");
                      }
                    } else if (nextList.length > num) {
                      nextList.splice(num);
                    }
                    setLocalFloorFunctions(nextList);
                    onUpdateProject({ 
                      floors: num,
                      floorFunctions: nextList
                    });
                  }}
                  onBlur={() => {
                    const num = localFloors === "" ? 0 : Number(localFloors);
                    let nextList = [...localFloorFunctions];
                    if (nextList.length < num) {
                      while (nextList.length < num) {
                        nextList.push("Nhà ở riêng lẻ / Dân dụng");
                      }
                    } else if (nextList.length > num) {
                      nextList.splice(num);
                    }
                    setLocalFloorFunctions(nextList);
                    onUpdateProject({ 
                      floors: num,
                      floorFunctions: nextList
                    });
                  }}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-mono text-sm font-bold border border-slate-300 focus:border-brand-orange transition-all"
                  placeholder="4"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Số tầng hầm</label>
                <input
                  type="number"
                  min={0}
                  value={localBasements}
                  id="input-basements"
                  onChange={(e) => {
                    // FIX B03: chặn số âm ngay tại UI.
                    const parsed = e.target.value === "" ? "" : Math.max(0, Number(e.target.value));
                    setLocalBasements(parsed);
                    const num = parsed === "" ? 0 : Number(parsed);
                    let nextFns = [...localBasementFunctions];
                    let nextHeights = [...localBasementHeights];
                    let nextAreas = [...localBasementAreas];
                    let nextFootprints = [...localBasementFootprints];

                    if (nextFns.length < num) {
                      while (nextFns.length < num) {
                        nextFns.push("Bãi đỗ xe hầm");
                        nextHeights.push(3.3);
                        nextAreas.push(Number(localFloorArea) || 400);
                        nextFootprints.push(Number(localFloorArea) || 400);
                      }
                    } else if (nextFns.length > num) {
                      nextFns.splice(num);
                      nextHeights.splice(num);
                      nextAreas.splice(num);
                      nextFootprints.splice(num);
                    }

                    setLocalBasementFunctions(nextFns);
                    setLocalBasementHeights(nextHeights);
                    setLocalBasementAreas(nextAreas);
                    setLocalBasementFootprints(nextFootprints);

                    onUpdateProject({ 
                      basements: num,
                      basementFunctions: nextFns,
                      basementHeights: nextHeights,
                      basementAreas: nextAreas,
                      basementFootprints: nextFootprints
                    });
                  }}
                  onBlur={() => {
                    const num = localBasements === "" ? 0 : Number(localBasements);
                    let nextFns = [...localBasementFunctions];
                    let nextHeights = [...localBasementHeights];
                    let nextAreas = [...localBasementAreas];
                    let nextFootprints = [...localBasementFootprints];

                    if (nextFns.length < num) {
                      while (nextFns.length < num) {
                        nextFns.push("Bãi đỗ xe hầm");
                        nextHeights.push(3.3);
                        nextAreas.push(Number(localFloorArea) || 400);
                        nextFootprints.push(Number(localFloorArea) || 400);
                      }
                    } else if (nextFns.length > num) {
                      nextFns.splice(num);
                      nextHeights.splice(num);
                      nextAreas.splice(num);
                      nextFootprints.splice(num);
                    }

                    setLocalBasementFunctions(nextFns);
                    setLocalBasementHeights(nextHeights);
                    setLocalBasementAreas(nextAreas);
                    setLocalBasementFootprints(nextFootprints);

                    onUpdateProject({ 
                      basements: num,
                      basementFunctions: nextFns,
                      basementHeights: nextHeights,
                      basementAreas: nextAreas,
                      basementFootprints: nextFootprints
                    });
                  }}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-mono text-sm font-bold border border-slate-300 focus:border-brand-orange transition-all"
                  placeholder="0"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Chiều cao PCCC (m)</label>
                <input
                  type="number"
                  min={0}
                  value={localPcccHeight}
                  id="input-pccc-height"
                  onChange={(e) => {
                    // FIX B03: chặn số âm ngay tại UI.
                    const parsed = e.target.value === "" ? "" : Math.max(0, Number(e.target.value));
                    setLocalPcccHeight(parsed);
                  }}
                  onBlur={() => onUpdateProject({ pcccHeight: localPcccHeight === "" ? 0 : Number(localPcccHeight) })}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-mono text-sm font-bold border border-slate-300 focus:border-brand-orange transition-all"
                  placeholder="12"
                />
              </div>
            </div>

            {/* Chi tiết công năng cho từng loại tầng hầm */}
            {Number(localBasements) >= 1 && (
              <div className="bg-slate-50 border border-slate-150 rounded-xl p-3 space-y-2.5 mt-2">
                <span className="block text-[14px] uppercase font-black text-black">Thông số & công năng hầm ({localBasements} tầng hầm)</span>
                <div className="space-y-3 max-h-56 overflow-y-auto custom-scrollbar pr-1">
                  {Array.from({ length: Number(localBasements) }).map((_, idx) => {
                    const bNum = idx + 1;
                    const curFn = localBasementFunctions[idx] || "Bãi đỗ xe hầm";
                    const curHeight = localBasementHeights[idx] ?? 3.3;
                    const curArea = localBasementAreas[idx] ?? (Number(localFloorArea) || 400);
                    const curFootprint = localBasementFootprints[idx] ?? (Number(localFloorArea) || 400);
                    return (
                      <div key={idx} className="bg-white p-2.5 rounded border border-slate-200/80 space-y-2 text-[14.5px]">
                        <div className="font-black text-black border-b border-slate-105 pb-1 flex justify-between items-center font-sans">
                          <span>Tầng hầm {bNum}:</span>
                        </div>
                        <div className="space-y-1">
                          <label className="block text-[12.5px] font-black text-black uppercase">Công năng hầm</label>
                          <select
                            value={curFn}
                            onChange={(e) => {
                              const next = [...localBasementFunctions];
                              next[idx] = e.target.value;
                              setLocalBasementFunctions(next);
                              onUpdateProject({ basementFunctions: next });
                            }}
                            className="w-full px-1.5 py-1 bg-white outline-none rounded text-black font-bold border border-slate-300 focus:border-brand-orange text-[14.5px] font-sans"
                          >
                            <option value="Bãi đỗ xe hầm">Bãi đỗ xe dưới hầm</option>
                            <option value="Gian kĩ thuật hầm">Gian kỹ thuật / Máy phát</option>
                            <option value="Thương mại hầm">Thương mại / Dịch vụ</option>
                            <option value="Kho dưới hầm">Kho tàng / Kho chứa</option>
                            <option value="Khu vực sản xuất dưới hầm">Khu vực sản xuất</option>
                            <option value="Công năng hỗn hợp khác hầm">Hỗn hợp khác</option>
                          </select>
                        </div>
                        <div className="grid grid-cols-3 gap-1">
                          <div>
                            <span className="block text-[12px] font-black text-black leading-tight">Chiều cao (m)</span>
                            <input
                              type="number"
                              min={0}
                              value={curHeight}
                              step="0.1"
                              onChange={(e) => {
                                // FIX B03: chặn số âm ngay tại UI.
                                const nextVal = e.target.value === "" ? 0 : Math.max(0, Number(e.target.value));
                                const next = [...localBasementHeights];
                                next[idx] = nextVal;
                                setLocalBasementHeights(next);
                                onUpdateProject({ basementHeights: next });
                              }}
                              className="w-full px-1.5 py-0.5 border border-slate-250 bg-white hover:bg-slate-50 rounded text-center text-black font-mono text-[14.5px] font-black"
                            />
                          </div>
                          <div>
                            <span className="block text-[12px] font-black text-black leading-tight">DT sàn (m²)</span>
                            <input
                              type="number"
                              min={0}
                              value={curArea}
                              onChange={(e) => {
                                // FIX B03: chặn số âm ngay tại UI.
                                const nextVal = e.target.value === "" ? 0 : Math.max(0, Number(e.target.value));
                                const next = [...localBasementAreas];
                                next[idx] = nextVal;
                                setLocalBasementAreas(next);
                                onUpdateProject({ basementAreas: next });
                              }}
                              className="w-full px-1.5 py-0.5 border border-slate-250 bg-white hover:bg-slate-50 rounded text-center text-black font-mono text-[14.5px] font-black"
                            />
                          </div>
                          <div>
                            <span className="block text-[12px] font-black text-black leading-tight">DT xây d.(m²)</span>
                            <input
                              type="number"
                              min={0}
                              value={curFootprint}
                              onChange={(e) => {
                                // FIX B03: chặn số âm ngay tại UI.
                                const nextVal = e.target.value === "" ? 0 : Math.max(0, Number(e.target.value));
                                const next = [...localBasementFootprints];
                                next[idx] = nextVal;
                                setLocalBasementFootprints(next);
                                onUpdateProject({ basementFootprints: next });
                              }}
                              className="w-full px-1.5 py-0.5 border border-slate-250 bg-white hover:bg-slate-50 rounded text-center text-black font-mono text-[14.5px] font-black"
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Chi tiết công năng cho từng loại tầng nổi */}
            {Number(localFloors) > 1 && (
              <div className="bg-slate-50 border border-slate-150 rounded-xl p-3 space-y-2 mt-2">
                <span className="block text-[14px] uppercase font-black text-black">Phân biệt công năng từng tầng ({localFloors} tầng nổi)</span>
                <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar pr-1">
                  {Array.from({ length: Number(localFloors) }).map((_, idx) => {
                    const floorNum = idx + 1;
                    const currentVal = localFloorFunctions[idx] || "Nhà ở riêng lẻ / Dân dụng";
                    return (
                      <div key={idx} className="flex items-center gap-1.5 justify-between">
                        <span className="text-[14px] font-black text-black w-18 shrink-0">Tầng {floorNum}:</span>
                        <select
                          value={currentVal}
                          onChange={(e) => {
                            const nextList = [...localFloorFunctions];
                            nextList[idx] = e.target.value;
                            setLocalFloorFunctions(nextList);
                            onUpdateProject({ floorFunctions: nextList });
                          }}
                          className="flex-1 px-1.5 py-1 bg-white outline-none rounded text-black font-black border border-slate-300 focus:border-brand-orange text-[15px] font-sans"
                        >
                          <option value="Nhà ở riêng lẻ / Dân dụng">Nhà ở dân dụng</option>
                          <option value="Kinh doanh thương mại / Dịch vụ nhẹ">Cửa hàng / Kinh doanh</option>
                          <option value="Dịch vụ giải trí Karaoke, Vũ trường">Cơ sở Karaoke / Bar</option>
                          <option value="Văn phòng, Phòng làm việc">Văn phòng làm việc</option>
                          <option value="Nhà kho lưu trữ hàng hóa">Kho chứa đồ / Kệ chứa</option>
                          <option value="Bãi đỗ xe hoặc gian kĩ thuật">Gara / Kỹ thuật</option>
                          <option value="Xưởng sản xuất / Dây chuyền công nghệ">Xưởng sản xuất</option>
                          <option value="Lớp học / Phòng thí nghiệm">Lớp học / Giáo dục</option>
                          <option value="Khán phòng / Rạp hát / Khu vực khán giả">Hội trường / Rạp hát</option>
                          <option value="Khu vực bếp ăn / Căng tin tập thể">Bếp ăn / Căng tin</option>
                        </select>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">DT xây dựng (m²)</label>
                <input
                  type="number"
                  min={0}
                  value={localFloorArea}
                  id="input-floor-area"
                  onChange={(e) => {
                    // FIX B03: chặn số âm ngay tại UI.
                    const parsed = e.target.value === "" ? "" : Math.max(0, Number(e.target.value));
                    setLocalFloorArea(parsed);
                  }}
                  onBlur={() => onUpdateProject({ floorArea: localFloorArea === "" ? 0 : Number(localFloorArea) })}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-mono text-sm font-bold border border-slate-300 focus:border-brand-orange transition-all"
                  placeholder="400"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Tổng DT sàn (m²)</label>
                <input
                  type="number"
                  min={0}
                  value={localTotalFloorArea}
                  id="input-total-floor-area"
                  onChange={(e) => {
                    // FIX B03: chặn số âm ngay tại UI.
                    const parsed = e.target.value === "" ? "" : Math.max(0, Number(e.target.value));
                    setLocalTotalFloorArea(parsed);
                  }}
                  onBlur={() => onUpdateProject({ totalFloorArea: localTotalFloorArea === "" ? 0 : Number(localTotalFloorArea) })}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-mono text-sm font-bold border border-slate-300 focus:border-brand-orange transition-all"
                  placeholder="1600"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Bậc chịu lửa thiết kế</label>
                <select
                  value={project.fireRating || "Chưa lựa chọn"}
                  id="input-fire-rating"
                  onChange={(e) => onUpdateProject({ fireRating: e.target.value })}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-bold border border-slate-300 focus:border-brand-orange transition-all text-sm font-sans"
                >
                  <option value="Chưa lựa chọn">Không lựa chọn</option>
                  <option value="Bậc I">Bậc I (Cao cấp)</option>
                  <option value="Bậc II">Bậc II</option>
                  <option value="Bậc III">Bậc III (Trung bình)</option>
                  <option value="Bậc IV">Bậc IV</option>
                  <option value="Bậc V">Bậc V (Thấp)</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] uppercase font-extrabold text-black mb-1">Chi tiết kinh doanh</label>
                <input
                  type="text"
                  value={localCommDetails}
                  id="input-comm-details"
                  onChange={(e) => setLocalCommDetails(e.target.value)}
                  onBlur={() => onUpdateProject({ commercialDetails: localCommDetails })}
                  className="w-full px-2.5 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded text-black font-bold border border-slate-300 focus:border-brand-orange transition-all text-sm font-sans"
                  placeholder="Tầng 1 văn phòng"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Nút Thẩm định và Kiểm duyệt hồ sơ */}
        <div className="pt-2 space-y-2">
          <button
            onClick={onCreateSession}
            id="btn-new-appraisal"
            className="w-full flex items-center justify-center gap-1.5 py-2 px-3 bg-slate-100 hover:bg-slate-200 text-black rounded-lg text-sm font-bold border border-slate-300 transition-all active:scale-[0.98] cursor-pointer shadow-sm"
          >
            <Plus className="w-3.5 h-3.5 text-brand-orange" /> Thẩm định Hồ sơ Mới
          </button>

          <button
            onClick={onTriggerAppraisal}
            disabled={isPending || !activeSessionId}
            id="btn-trigger-appraisal-side"
            className="w-full flex items-center justify-center gap-2 py-2.5 px-3 bg-brand-orange hover:bg-brand-orange/90 text-white rounded-lg text-sm font-black transition-all shadow-md shadow-brand-orange/15 hover:shadow-brand-orange/25 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ShieldCheck className="w-4.5 h-4.5" />
            )}
            Kiểm duyệt hồ sơ
          </button>
        </div>

        {/* SECTION 2: RAG META MANAGEMENT */}
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b-2 border-slate-350 pb-1.5">
            <div className="flex items-center gap-2">
              <FileBadge className="w-4.5 h-4.5 text-brand-orange" />
              <h2 className="text-[16px] font-black uppercase tracking-wider text-black font-display">Cơ sở dữ liệu pháp lý</h2>
            </div>
            <button
              onClick={onResetDocuments}
              id="btn-reset-kb"
              title="Khôi phục mặc định"
              className="text-black hover:text-red-650 transition-colors cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {/* Doc List Summary */}
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-[15px] space-y-1 font-sans text-black">
            <div className="flex justify-between text-black font-black">
              <span>Tổng số văn bản hiện có:</span>
              <span className="font-mono font-black text-brand-orange text-[16px]">{documents.length}</span>
            </div>
            <div className="flex justify-between text-black font-black">
              <span>Văn bản tùy chỉnh bổ sung:</span>
              <span className="font-mono font-black text-emerald-600 text-[16px]">
                {documents.filter((d) => d.isCustom).length}
              </span>
            </div>
          </div>

          {/* Search Input Filter for Legal Database */}
          <div className="relative">
            <input
              type="text"
              placeholder="Tìm kiếm theo ký hiệu hoặc tên văn bản..."
              value={docSearchQuery}
              onChange={(e) => setDocSearchQuery(e.target.value)}
              id="doc-search-input"
              className="w-full pl-8 pr-8 py-1.5 bg-white hover:bg-slate-50 focus:bg-white outline-none rounded border border-slate-300 focus:border-brand-orange text-xs text-black font-semibold transition-all"
            />
            <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            {docSearchQuery && (
              <button
                type="button"
                onClick={() => setDocSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-650 cursor-pointer p-1"
                title="Xóa tìm kiếm"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Mini Document Scroller */}
          <div className="max-h-32 overflow-y-auto custom-scrollbar border border-slate-200 rounded-lg bg-slate-50 p-1.5 space-y-1.5 text-[15px] font-sans">
            {filteredDocuments.length === 0 ? (
              <div className="p-4 text-center text-slate-500 font-bold text-xs select-none">
                Không tìm thấy văn bản pháp quy phù hợp.
              </div>
            ) : (
              filteredDocuments.map((doc) => {
                const isTcvnOrQcvn = doc.type === "TCVN" || doc.type === "QCVN" || doc.code.toUpperCase().includes("TCVN") || doc.code.toUpperCase().includes("QCVN");
                const displayedTitle = isTcvnOrQcvn ? doc.code : doc.title;
                const badgeText = isTcvnOrQcvn ? doc.type : doc.code;
                const hoverTitle = isTcvnOrQcvn 
                  ? `${doc.code} - ${doc.title} - Click để xem trước`
                  : `${doc.title} (${doc.code}) - Click để xem trước`;

                const isCurrentlyPreviewed = previewDoc && previewDoc.id === doc.id;

                return (
                  <div
                    key={doc.id}
                    onClick={() => setPreviewDoc(doc)}
                    className={`document-item flex items-center justify-between p-1.5 hover:bg-white rounded group cursor-pointer transition-all duration-200 hover:scale-[1.02] select-none ${
                      isCurrentlyPreviewed
                        ? "border border-brand-orange shadow-md bg-white"
                        : "border border-transparent hover:border-slate-200 hover:shadow-md"
                    }`}
                    title={hoverTitle}
                  >
                    <div className="truncate pr-1 flex items-center gap-1.5 min-w-0">
                      <span className="bg-brand-orange/15 text-brand-orange font-black font-mono text-[12.5px] rounded px-1.5 py-0.5 uppercase shrink-0 border border-brand-orange/20">
                        {badgeText}
                      </span>
                      <span className={`truncate text-[14.5px] group-hover:text-black transition-colors ${doc.isCustom ? "font-black text-slate-950" : "text-black font-bold"}`}>
                        {displayedTitle}
                      </span>
                    </div>
                    <div 
                      className="flex items-center gap-1 shrink-0 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => setPreviewDoc(doc)}
                        title="Xem chi tiết"
                        className="text-slate-500 hover:text-slate-950 p-0.5 rounded hover:bg-slate-200 transition-colors cursor-pointer"
                      >
                        <Eye className="w-3" />
                      </button>
                      <a
                        href={apiUrl(`/api/documents/${doc.id}/download?format=pdf`)}
                        download
                        title="Tải xuống tài liệu PDF"
                        className="text-slate-500 hover:text-emerald-600 p-0.5 rounded hover:bg-slate-200 transition-colors cursor-pointer flex items-center justify-center"
                      >
                        <Download className="w-3" />
                      </a>
                      <button
                        onClick={() => onDeleteDocument(doc.id)}
                        title="Xóa tài liệu"
                        className="text-slate-500 hover:text-brand-orange p-0.5 rounded hover:bg-slate-200 transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Custom RAG File Upload Panel */}
          <div className="bg-slate-50 border border-dashed border-slate-350 rounded-lg p-3 space-y-2">
            <h3 className="text-[15px] font-black text-black">Tải lên văn bản pháp luật (.pdf, .docx, .txt)</h3>
            <div className="grid grid-cols-2 gap-1.5 font-sans">
              <input
                type="text"
                placeholder="Mã/Ký hiệu"
                value={docCode}
                onChange={(e) => setDocCode(e.target.value)}
                className="px-2 py-1 bg-white border border-slate-250 rounded text-[14px] text-black font-bold outline-none focus:border-brand-orange transition-all font-mono"
              />
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="px-1.5 py-1 bg-white border border-slate-250 rounded text-[14px] text-black font-bold outline-none focus:border-brand-orange"
              >
                <option value="LUẬT">Luật</option>
                <option value="Nghị định">Nghị định</option>
                <option value="Thông tư">Thông tư</option>
                <option value="QCVN">QCVN</option>
                <option value="TCVN">TCVN</option>
              </select>
            </div>
            <input
              type="text"
              placeholder="Tên văn bản chi tiết (chỉ cho 1 file)"
              value={docTitle}
              onChange={(e) => setDocTitle(e.target.value)}
              className="w-full px-2 py-1 bg-white border border-slate-250 rounded text-[14px] text-black font-bold outline-none focus:border-brand-orange font-sans"
            />
            <div className="relative">
              <input
                type="file"
                ref={fileInputRef}
                accept=".pdf,.docx,.txt"
                multiple
                onChange={handleFileUpload}
                disabled={isUploading}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                style={{ textShadow: "0 1px 2px rgba(0,0,0,0.2)" }}
                className="w-full flex items-center justify-center gap-2.5 py-3 px-4 bg-brand-orange hover:bg-brand-orange/95 text-white rounded-xl border-b-[4px] border-[#9E3600] shadow-[0_4px_12px_rgba(234,88,12,0.3),inset_0_1px_0_rgba(255,255,255,0.2)] hover:translate-y-[1px] hover:border-b-[3px] active:translate-y-[4px] active:border-b-0 active:shadow-none transition-all cursor-pointer text-[15px] font-black uppercase tracking-wider text-center"
              >
                <Flame className="w-5 h-5 text-amber-300 animate-pulse shrink-0" />
                <Upload className="w-4.5 h-4.5 text-white shrink-0" />
                <span>{isUploading ? "Đang xử lý tải..." : "+ Tải lên tài liệu mới"}</span>
              </button>
            </div>
            {/* Active upload list showing progress percentages */}
            {Object.keys(uploadProgress).length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-slate-205">
                {Object.entries(uploadProgress).map(([filename, prg]) => (
                  <div key={filename} className="text-[10px] bg-white border border-slate-200 rounded-lg p-2 animate-fade-in shadow-xs">
                    <div className="flex justify-between text-[9px] mb-1 font-sans">
                      <span className="text-slate-805 truncate max-w-[145px] font-bold" title={filename}>{filename}</span>
                      <span className="text-brand-orange font-mono font-bold shrink-0">{prg}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* SECTION 3: APPRAISAL SESSIONS HISTORY */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 border-b-2 border-slate-350 pb-1.55">
            <History className="w-4.5 h-4.5 text-brand-orange shrink-0" />
            <h2 className="text-[16px] font-black uppercase tracking-wider text-black font-display">Lịch sử thẩm định gần đây</h2>
          </div>

          <div className="space-y-2.5 text-[16px] text-black font-bold">
            {(() => {
              const displayedSessions = sessions.slice(sessionPage * sessionLimit, (sessionPage + 1) * sessionLimit);
              return displayedSessions.length === 0 ? (
                <p className="text-[14px] text-black text-center py-2.5 italic font-sans animate-fade-in font-bold">Chưa có phiên thẩm định nào</p>
              ) : (
                displayedSessions.map((sess) => {
                  const isActive = sess.id === activeSessionId;
                  const displayTitle = sess.projectInfo?.name || sess.title || "Dự án Chưa đặt tên";
                  return (
                    <div
                      key={sess.id}
                      className={`flex items-center justify-between p-2.5 rounded-lg group cursor-pointer transition-all border ${
                        isActive ? "bg-brand-orange/[0.08] border-brand-orange/40 text-black shadow-sm" : "bg-white border-transparent hover:bg-slate-50 hover:border-slate-200 text-black"
                      }`}
                    >
                      <div onClick={() => onSelectSession(sess.id)} className="flex-1 min-w-0 pr-1">
                        <div className={`font-black truncate text-[16px] flex items-center gap-1.5 ${isActive ? "text-black" : "text-black group-hover:text-black"}`}>
                          <FileText className="w-4.5 h-4.5 text-black inline-shrink shrink-0" />
                          <span className="truncate" title={displayTitle}>
                            {displayTitle}
                          </span>
                        </div>
                        <div className="text-[14px] text-black font-mono font-bold mt-1 flex justify-between pr-2 border-t border-slate-100/50 pt-1">
                          <span>{new Date(sess.updatedAt).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}</span>
                          <span>{new Date(sess.updatedAt).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })}</span>
                        </div>
                      </div>
                      {sessions.length > 1 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(sess.id);
                          }}
                          className="text-slate-400 hover:text-brand-orange transition-colors opacity-0 group-hover:opacity-100 shrink-0 cursor-pointer p-1 rounded hover:bg-slate-200/50"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  );
                })
              );
            })()}
          </div>

          {/* Pagination limit and buttons controller */}
          {sessions.length > 0 && (
            <div className="flex items-center justify-between pt-2.5 border-t border-slate-200 text-[14px] font-sans text-black font-bold">
              <div className="flex items-center gap-1.5 text-black font-bold">
                <span>Hiển thị:</span>
                <select
                  value={sessionLimit}
                  onChange={(e) => {
                    setSessionLimit(Number(e.target.value));
                    setSessionPage(0);
                  }}
                  className="bg-white hover:bg-slate-50 text-black font-black px-1.5 py-0.5 rounded outline-none border border-slate-350 cursor-pointer text-[14px]"
                >
                  <option value={5}>5 dự án</option>
                  <option value={10}>10 dự án</option>
                  <option value={20}>20 dự án</option>
                </select>
              </div>
              
              <div className="flex items-center gap-1 font-sans text-black">
                <button
                  type="button"
                  disabled={sessionPage === 0}
                  onClick={() => setSessionPage((prev) => Math.max(0, prev - 1))}
                  className="px-2 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-40 disabled:hover:bg-slate-100 border border-slate-300 rounded text-black transition cursor-pointer text-[13.5px] font-black"
                >
                  Trước
                </button>
                <span className="text-black font-mono text-[13px] px-1.5 font-black">
                  {sessionPage + 1}/{Math.ceil(sessions.length / sessionLimit)}
                </span>
                <button
                  type="button"
                  disabled={(sessionPage + 1) * sessionLimit >= sessions.length}
                  onClick={() => setSessionPage((prev) => prev + 1)}
                  className="px-2 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-40 disabled:hover:bg-slate-100 border border-slate-300 rounded text-black transition cursor-pointer text-[13.5px] font-black"
                >
                  Kế tiếp
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Centered Document Quick-View Modal */}
      {previewDoc && (
        <div 
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4 md:p-6 z-50 select-none animate-in fade-in duration-200"
          onClick={() => setPreviewDoc(null)}
        >
          <div 
            className="bg-white rounded-2xl w-full max-w-3xl max-h-[85vh] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.35)] flex flex-col overflow-hidden border border-slate-200/60 animate-in zoom-in-95 duration-200 text-black text-left"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="p-5 border-b border-slate-150 bg-slate-50 flex items-center justify-between shrink-0">
              <div className="min-w-0 pr-4">
                <span className="inline-block bg-brand-orange/10 text-brand-orange font-black font-mono text-[11px] rounded px-2.5 py-0.5 uppercase tracking-wide mb-1.5 border border-brand-orange/20">
                  {previewDoc.type || "TÀI LIỆU"}
                </span>
                <h3 className="font-display font-black text-sm md:text-base text-black truncate" title={previewDoc.title}>
                  [{previewDoc.code}] {previewDoc.title}
                </h3>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="text-slate-500 hover:text-black p-2 hover:bg-slate-200 rounded-xl transition-all cursor-pointer shrink-0 flex items-center justify-center"
                title="Đóng bản xem trước"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-5 text-sm font-sans select-text">
              {/* Context Metadata GRID */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50/80 border border-slate-200/80 rounded-xl p-4 text-[12.5px] font-sans">
                <div className="flex flex-col gap-0.5 sm:border-r border-slate-200/65 pr-2">
                  <span className="text-slate-500 font-medium">Ký hiệu pháp lý:</span>
                  <span className="font-mono text-brand-orange font-black text-sm">{previewDoc.code}</span>
                </div>
                <div className="flex flex-col gap-0.5 sm:border-r border-slate-200/65 sm:px-2">
                  <span className="text-slate-500 font-medium">Loại văn bản:</span>
                  <span className="text-slate-900 font-black text-sm uppercase">{previewDoc.type}</span>
                </div>
                {previewDoc.uploadedAt ? (
                  <div className="flex flex-col gap-0.5 sm:pl-2">
                    <span className="text-slate-500 font-medium">Ngày cập nhật:</span>
                    <span className="text-slate-800 font-bold">
                      {new Date(previewDoc.uploadedAt).toLocaleDateString("vi-VN") + " " + new Date(previewDoc.uploadedAt).toLocaleTimeString("vi-VN", {hour: "2-digit", minute: "2-digit"})}
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-col gap-0.5 sm:pl-2">
                    <span className="text-slate-500 font-medium">Trạng thái xác thực:</span>
                    <span className="text-emerald-600 font-bold flex items-center gap-1">Chính thức</span>
                  </div>
                )}
              </div>

              {/* Content preview heading */}
              <div className="space-y-3 flex-1 flex flex-col min-h-0 text-left">
                <div className="flex items-center gap-2 text-slate-850 bg-slate-100 p-2 rounded-lg border border-slate-200">
                  <FileText className="w-4 h-4 text-brand-orange shrink-0" />
                  <h4 className="text-[11px] uppercase font-black tracking-wider text-slate-950">Nội dung chi tiết - trích lục văn bản pháp luật:</h4>
                </div>
                <div className="bg-white border border-slate-200/80 rounded-xl p-4.5 text-slate-900 font-medium font-sans leading-relaxed text-[13px] whitespace-pre-wrap max-h-[380px] overflow-y-auto custom-scrollbar border-l-4 border-l-brand-orange shadow-inner text-left">
                  {previewDoc.content || "Văn bản này hiện chưa có nội dung trích lục chi tiết."}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-150 bg-slate-50 flex items-center justify-between text-[12px] text-slate-600 font-sans shrink-0">
              <span className="font-bold text-slate-700 hidden sm:inline">Cơ sở dữ liệu pháp luật phòng cháy chữa cháy</span>
              <div className="flex items-center gap-2.5 ml-auto sm:ml-0">
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(`[${previewDoc.code}] ${previewDoc.title}\n\nNội dung:\n${previewDoc.content || ""}`);
                    alert("Đã sao chép nội dung vào bộ nhớ tạm!");
                  }}
                  className="px-4 py-2 border border-slate-350 bg-white hover:bg-slate-100 rounded-xl text-slate-950 font-black tracking-wide uppercase text-[11px] cursor-pointer transition-all"
                >
                  Sao chép nội dung
                </button>
                <a 
                  href={apiUrl(`/api/documents/${previewDoc.id}/download?format=pdf`)}
                  download
                  className="flex items-center gap-1.5 px-4 py-2 bg-brand-orange hover:bg-brand-orange/95 text-white font-black tracking-wide uppercase text-[11px] rounded-xl transition-all cursor-pointer shadow-md shadow-brand-orange/15"
                >
                  <Download className="w-3.5 h-3.5" />
                  Tải văn bản (PDF)
                </a>
              </div>
            </div>
          </div>
        </div>
      )}



      {/* FLOAT SUCCESS TOAST POPUP FOR DOCUMENTS */}
      {showSuccessUpload && (
        <div className="fixed top-4 left-4 z-50 bg-emerald-600 text-white rounded-xl shadow-xl p-4 flex items-center gap-3 border border-emerald-500 animate-in fade-in duration-300">
          <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center text-white shrink-0">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h4 className="text-[11px] font-bold font-display uppercase tracking-wider text-left">Tải lên thành công!</h4>
            <p className="text-[10px] text-emerald-100 mt-0.5 font-sans">Đã lưu trữ tài liệu vào CSDL pháp lý PCCC.</p>
          </div>
          <button 
            type="button"
            onClick={() => setShowSuccessUpload(false)} 
            className="text-emerald-300 hover:text-white transition-colors cursor-pointer pl-2 ml-auto p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
// Dòng này để Push code lại 
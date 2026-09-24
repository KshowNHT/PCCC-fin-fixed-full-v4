import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Loader2,
  FileDown,
  MessageSquare,
  ClipboardCheck,
  Award,
  AlertTriangle,
  Sparkles,
  Info,
  CheckCircle,
  XCircle,
  X,
  FileCheck,
  Filter,
  Download,
  Ruler,
  Menu,
  ChevronDown,
  ChevronUp,
  Search,
  ArrowUpDown,
  Maximize2,
  Eye,
  EyeOff
} from "lucide-react";
import { ChatMessage, ChecklistItem, ProjectInfo } from "../types";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

interface MainAreaProps {
  sessionTitle: string;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  onTriggerAppraisal: () => void;
  isPending: boolean;
  onCancelPending?: () => void;
  checklist: ChecklistItem[];
  isSubjectToAppraisal: boolean;
  appraisalReason: string;
  warnings: string[];
  projectInfo: ProjectInfo;
  onExportReport: () => void;
  isExporting: boolean;
  onExportReportPdf: () => void;
  isExportingPdf: boolean;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
}

const QUICK_PROMPTS = [
  {
    label: "Nhà ở kết hợp kinh doanh 4 tầng (400m²)",
    prompt: "Tôi muốn thẩm duyệt hồ sơ công trình của Nguyễn Văn A: loại nhà ở riêng lẻ kết hợp kinh doanh dịch vụ tại tầng 1, quy mô 4 tầng nổi, diện tích xây dựng 400 m2 (bậc chịu lửa dự kiến là bậc III), chiều cao công trình 12m, không có tầng hầm. Hãy rà soát xem có đạt tiêu chuẩn không và có thuộc diện thẩm định bắt buộc không?"
  },
  {
    label: "Quán Karaoke 3 tầng kinh doanh dịch vụ",
    prompt: "Kiểm duyệt giúp tôi thiết kế quán Karaoke quy mô 3 tầng nổi, tổng diện tích xây dựng là 600m2, chiều cao PCCC là 10.5m. Chủ đầu tư là Vũ trường Kinh doanh Hà Nội. Đã có mặt đứng thiết kế ban đầu."
  },
  {
    label: "Nhà kho kệ cao chứa hàng 20m cao",
    prompt: "Rà soát giúp tôi phương án an toàn PCCC nhà kho xếp hàng trên giá đỡ bán tự động, quy mô 1 tầng cao 18m, diện tích xây dựng 1.200m2. Đơn vị thiết kế là công ty PQC."
  }
];

export function MainArea({
  sessionTitle,
  messages,
  onSendMessage,
  onTriggerAppraisal,
  isPending,
  onCancelPending,
  checklist,
  isSubjectToAppraisal,
  appraisalReason,
  warnings,
  projectInfo,
  onExportReport,
  isExporting,
  onExportReportPdf,
  isExportingPdf,
  isSidebarOpen,
  onToggleSidebar
}: MainAreaProps) {
  const [activeTab, setActiveTab] = useState<"chat" | "checklist" | "verdict" | "full-checklist" | "full-verdict">("chat");
  const [inputText, setInputText] = useState("");
  const [quickSearchText, setQuickSearchText] = useState("");
  const [filterResult, setFilterResult] = useState<string>("all");
  const [isSpecsExpanded, setIsSpecsExpanded] = useState(true);
  const [isLegendVisible, setIsLegendVisible] = useState(true);
  const [isComplianceExpanded, setIsComplianceExpanded] = useState(true);
  const [isWarningsExpanded, setIsWarningsExpanded] = useState(true);
  const [sortColumn, setSortColumn] = useState<"stt" | "criteria" | "result" | null>("stt");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // FIX B19 (Bao_Cao_QA_Lan_3.md — Trung bình): trước đây banner cảnh báo
  // mâu thuẫn diện tích chỉ dựa vào `warnings` — 1 state CHỈ cập nhật SAU
  // khi nhận phản hồi từ server (PUT /project), nên luôn "trễ 1 nhịp" so
  // với giá trị người dùng vừa gõ (sửa 2 ô liên tiếp trước khi request đầu
  // kịp trả lời → banner hiện cảnh báo cho state CŨ). Tính lại CỤC BỘ, tức
  // thời, dùng CHÍNH `projectInfo` (props hiện tại, luôn mới nhất) — công
  // thức giống hệt backend rules_engine.py để không lệch kết quả.
  const hasAreaContradiction = React.useMemo(() => {
    const floors = projectInfo.floors || 0;
    const floorArea = projectInfo.floorArea || 0;
    const totalFloorArea = projectInfo.totalFloorArea || 0;
    return floors > 0 && floorArea > 0 && Math.abs(totalFloorArea - floorArea * floors) > 10;
  }, [projectInfo.floors, projectInfo.floorArea, projectInfo.totalFloorArea]);

  // FIX B19 (tiếp): danh sách cảnh báo hiển thị = cảnh báo mâu thuẫn diện
  // tích LUÔN tính tức thời (không đợi server) + các cảnh báo KHÁC từ server
  // (vd cảnh báo B12 về nhóm công năng chưa phân loại) — lọc bỏ dòng mâu
  // thuẫn diện tích cũ do server trả về để tránh hiển thị trùng/lệch nhịp.
  const AREA_WARNING_TEXT =
    "Tổng diện tích sàn khai báo không trùng khớp với tích số giữa (diện tích sàn x số tầng), cần đối chiếu kiểm tra thực tế.";
  const displayWarnings = React.useMemo(() => {
    const others = (warnings || []).filter((w) => w !== AREA_WARNING_TEXT);
    return hasAreaContradiction ? [AREA_WARNING_TEXT, ...others] : others;
  }, [warnings, hasAreaContradiction]);
  const [checklistSearchQuery, setChecklistSearchQuery] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isPending]);

  // Collapse indicators automatically when entering full checklist or full verdict modes
  useEffect(() => {
    if (activeTab === "full-checklist" || activeTab === "full-verdict" || activeTab === "checklist" || activeTab === "verdict") {
      setIsComplianceExpanded(false);
      setIsWarningsExpanded(false);
    }
  }, [activeTab]);

  // HTML5 Fullscreen API integration for "full-checklist" and "full-verdict" tabs
  useEffect(() => {
    if (activeTab === "full-checklist" || activeTab === "full-verdict") {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch((err) => {
          console.warn("Unable to enter fullscreen mode:", err);
        });
      }
    } else {
      if (document.fullscreenElement) {
        document.exitFullscreen().catch((err) => {
          console.warn("Unable to exit fullscreen mode:", err);
        });
      }
    }
  }, [activeTab]);

  // Watch for ESC or browser Fullscreen exit event to sync tabs back to standard view
  useEffect(() => {
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) {
        if (activeTab === "full-checklist") {
          setActiveTab("checklist");
        } else if (activeTab === "full-verdict") {
          setActiveTab("verdict");
        }
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, [activeTab]);

  // Press ESC to exit full screen popups
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (activeTab === "checklist" || activeTab === "full-checklist" || activeTab === "verdict" || activeTab === "full-verdict") {
          setActiveTab("chat");
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeTab]);

  // Track auto-collapse of menus and specs when a consultation response (advice) is ready or has loaded
  const lastActiveSessionNameRef = useRef("");
  const collapsedForCountRef = useRef(0);
  // FIX B07 (Bao_Cao_QA_Lan_2.md): "nút thu gọn/mở rộng bấm vào KHÔNG thu
  // lại được về trạng thái cũ". Nguyên nhân: effect bên dưới tự động ép
  // isSpecsExpanded=false mỗi khi có tin nhắn mới, chạy ĐÈ LÊN lựa chọn vừa
  // bấm tay của người dùng (onToggleSidebar là arrow function inline ở
  // App.tsx nên đổi identity mỗi lần render, khiến effect dễ chạy lại hơn
  // dự kiến). Ref này đánh dấu "người dùng đã tự thao tác trong phiên hiện
  // tại" để effect auto-collapse tôn trọng lựa chọn thủ công, không ép lại.
  const userToggledSpecsRef = useRef(false);

  useEffect(() => {
    const assistantMsgs = messages.filter((msg) => msg.sender === "assistant");
    const hasAssistantMsg = assistantMsgs.length > 0;
    
    const isSessionChanged = lastActiveSessionNameRef.current !== sessionTitle;
    const msgCount = messages.length;
    const hasNewMessages = msgCount > collapsedForCountRef.current;

    if (isSessionChanged) {
      // Đổi sang phiên khác: reset "quyền kiểm soát thủ công" để phiên mới
      // vẫn có hành vi auto-collapse mặc định như trước.
      userToggledSpecsRef.current = false;
    }

    if (hasAssistantMsg && (isSessionChanged || hasNewMessages)) {
      // Record this state to prevent duplicate auto-collapses
      lastActiveSessionNameRef.current = sessionTitle;
      collapsedForCountRef.current = msgCount;

      // FIX B07: chỉ auto-collapse nếu người dùng CHƯA từng tự bấm nút
      // thu gọn/mở rộng trong phiên này — tôn trọng lựa chọn thủ công.
      if (!userToggledSpecsRef.current) {
        setIsSpecsExpanded(false);
      }

      // Collapse left sidebar if open
      if (isSidebarOpen) {
        onToggleSidebar();
      }
    }
  }, [messages, sessionTitle, onToggleSidebar, isSidebarOpen]);

  // Dynamic advice text formatting function - splits text to clear newline items and strips all asterisks
  const renderFormattedMessageText = (text: string) => {
    const rawLines = text.split("\n");
    const formattedElements: React.ReactNode[] = [];

    rawLines.forEach((rawLine, idx) => {
      const trimmed = rawLine.trim();
      if (!trimmed) {
        formattedElements.push(<div key={`empty-${idx}`} className="h-2" />);
        return;
      }

      // Check bullet types
      const isBullet = trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("• ");
      const isNumberedList = /^\d+[\.\)]\s+/.test(trimmed);

      // Remove all double and single asterisks completely as requested
      let cleanLine = rawLine.replace(/\*/g, "").trim();

      if (isBullet) {
        const content = cleanLine.replace(/^[-•*]\s*/, "");
        formattedElements.push(
          <div key={`bullet-${idx}`} className="flex items-start gap-2 text-slate-800 pl-4 py-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-orange mt-2 shrink-0" />
            <span className="text-[13px] md:text-sm font-sans leading-relaxed">
              {content}
            </span>
          </div>
        );
        return;
      }

      if (isNumberedList) {
        const match = trimmed.match(/^(\d+[\.\)])\s*(.*)/);
        if (match) {
          const num = match[1];
          const content = match[2].replace(/\*/g, "").trim();
          formattedElements.push(
            <div key={`number-${idx}`} className="flex items-start gap-2 pl-4 py-0.5">
              <span className="font-mono font-bold text-brand-orange text-[13px] mt-0.5 shrink-0 select-none">
                {num}
              </span>
              <span className="text-[13px] md:text-sm font-sans leading-relaxed">
                {content}
              </span>
            </div>
          );
          return;
        }
      }

      // Heading marker detection (ends with colon or starts with markdown hash symbols)
      const isHeading = trimmed.endsWith(":") || trimmed.startsWith("##") || trimmed.startsWith("###");
      if (isHeading) {
        const headingContent = cleanLine.replace(/^#+\s*/, "");
        formattedElements.push(
          <h4
            key={`heading-${idx}`}
            className="text-xs sm:text-sm font-black text-slate-900 mt-4 mb-1.5 first:mt-0 font-sans tracking-tight uppercase"
          >
            {headingContent}
          </h4>
        );
        return;
      }

      // Normal text paragraph
      formattedElements.push(
        <p key={`para-${idx}`} className="text-[13px] md:text-sm text-slate-800 font-sans leading-relaxed">
          {cleanLine}
        </p>
      );
    });

    return <div className="space-y-2 flex flex-col">{formattedElements}</div>;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isPending) return;
    onSendMessage(inputText);
    setInputText("");
  };

  const handleQuickPrompt = (prompt: string) => {
    if (isPending) return;
    onSendMessage(prompt);
  };

  const handleSort = (column: "stt" | "criteria" | "result") => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const getResultRank = (result: string) => {
    switch (result) {
      case "Không đạt": return 1;
      case "Khuyến nghị mạnh": return 2;
      case "Khuyến nghị": return 3;
      case "Cần xem xét": return 3;
      case "Cần đo đạc": return 4;
      case "Không bắt buộc": return 5;
      case "Đạt": return 6;
      default: return 7;
    }
  };

  const filteredAndSortedChecklist = React.useMemo(() => {
    const filtered = checklist.filter((item) => {
      // 1. Dropdown Filter
      if (filterResult !== "all" && item.result !== filterResult) {
        return false;
      }
      
      // 2. Search query filter (matches criteria, requirement, or note)
      const query = checklistSearchQuery.toLowerCase().trim();
      if (!query) return true;
      return (
        item.criteria.toLowerCase().includes(query) ||
        (item.note && item.note.toLowerCase().includes(query)) ||
        (item.requirement && item.requirement.toLowerCase().includes(query)) ||
        item.reference.toLowerCase().includes(query)
      );
    });

    if (!sortColumn) return filtered;

    return [...filtered].sort((a, b) => {
      let valA: any = "";
      let valB: any = "";

      if (sortColumn === "stt") {
        valA = a.stt;
        valB = b.stt;
      } else if (sortColumn === "criteria") {
        valA = a.criteria.toLowerCase();
        valB = b.criteria.toLowerCase();
      } else if (sortColumn === "result") {
        valA = getResultRank(a.result);
        valB = getResultRank(b.result);
      }

      if (valA < valB) return sortDirection === "asc" ? -1 : 1;
      if (valA > valB) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  }, [checklist, filterResult, checklistSearchQuery, sortColumn, sortDirection]);

  return (
    <div id="app-main-area" className="flex-1 flex flex-col min-w-0 bg-slate-50 h-full overflow-hidden relative font-sans print:overflow-visible print:bg-white print:p-0">
      {/* FIX B23 (Bao_Cao_QA_Lan_3.md — Thấp): container ngoài cùng trước
          đây có CẢ `h-full` LẪN `overflow-y-auto` — xung đột với vùng cuộn
          riêng của khung tin nhắn bên trong (dòng ~863, cũng overflow-y-auto).
          Có 2 lớp overflow:auto lồng nhau trong cùng 1 chuỗi flexbox là lỗi
          WebKit di động kinh điển (flex item revert về "min-height: auto",
          co lại theo kích thước NỘI DUNG thay vì lấp đầy chiều cao khả dụng)
          — khớp đúng triệu chứng QA mô tả: nội dung dừng ở ~55% màn hình,
          phần còn lại trắng, khung nhập không neo đáy. Đổi outer container
          thành `overflow-hidden` (không tự cuộn), giao toàn bộ việc cuộn
          cho các vùng con bên trong (đã có sẵn overflow-y-auto riêng). */}
      {/* Top action header bar */}
      <div id="main-action-header" className="sticky top-0 bg-white border-b border-slate-200 px-3 sm:px-6 py-3 sm:py-4 flex flex-col md:flex-row md:items-center justify-between gap-3 sm:gap-4 shadow-sm z-25 flex-shrink-0 print:hidden">
        <div className="flex items-center gap-3">
          {/* Collapse/Expand toggle button */}
          <button
            onClick={onToggleSidebar}
            className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors border border-slate-200 shadow-sm cursor-pointer flex items-center justify-center shrink-0"
            title={isSidebarOpen ? "Thu gọn thanh thông số" : "Mở rộng thanh thông số"}
          >
            <Menu className="w-5 h-5" />
          </button>
          
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display font-black text-slate-950 text-xl md:text-2xl tracking-tight">
                {sessionTitle}
              </h2>
            </div>
            <p className="text-xs text-slate-500 font-sans mt-0.5">
              Chương trình thẩm định hồ sơ phòng cháy chữa cháy
            </p>
          </div>
        </div>

        {/* Word Docx & PDF Download buttons */}
        {/* FIX B07: "các nút chức năng chen chúc khó bấm" trên mobile —
            trước đây 3 nút luôn nằm ngang, tràn/dồn cụm trên màn hình hẹp.
            Thêm flex-wrap để tự xuống dòng khi không đủ chỗ, và tăng
            khoảng chạm (py) tối thiểu cho thân thiện cảm ứng hơn. */}
        <div className="flex items-center flex-wrap gap-2 shrink-0">
          <button
            onClick={onTriggerAppraisal}
            disabled={isPending || hasAreaContradiction}
            title={hasAreaContradiction ? "Vui lòng sửa mâu thuẫn diện tích trước khi thẩm định (xem cảnh báo phía trên)" : undefined}
            id="btn-trigger-appraisal-main"
            className="flex items-center gap-1.5 py-1.5 px-3 bg-[#801818] hover:bg-[#681010] text-white font-bold text-xs rounded-lg shadow-md shadow-red-950/15 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:scale-100 cursor-pointer"
          >
            {isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            Thực hiện kiểm duyệt
          </button>

          {/* FIX B04 (Bao_Cao_QA_Lan_3.md — Chưa fix theo QA lần 3, dù đã có
              code trước đó): thêm nút Huỷ THỨ HAI, đặt CỐ ĐỊNH ngay trong
              thanh hành động trên cùng (luôn hiển thị bất kể vị trí cuộn
              chat), không chỉ phụ thuộc vào bong bóng chat tạm thời có thể
              biến mất nhanh hoặc nằm ngoài vùng nhìn thấy. Tăng độ chắc chắn
              người dùng luôn thấy được nút Huỷ khi isPending=true. */}
          {isPending && onCancelPending && (
            <button
              onClick={onCancelPending}
              id="btn-cancel-pending-main"
              className="flex items-center gap-1.5 py-1.5 px-3 bg-white hover:bg-red-50 text-red-600 font-bold text-xs rounded-lg border border-red-300 shadow-sm transition-all active:scale-[0.98] cursor-pointer"
              title="Huỷ tiến trình phân tích AI đang chạy"
            >
              <XCircle className="w-3.5 h-3.5" />
              Huỷ
            </button>
          )}

          <button
            onClick={onExportReport}
            disabled={isExporting || isExportingPdf || checklist.length === 0 || hasAreaContradiction}
            id="btn-export-word"
            className="flex items-center gap-1.5 py-1.5 px-3 bg-brand-orange hover:bg-brand-orange/90 text-white font-medium text-xs rounded-lg shadow-sm shadow-brand-orange/15 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:scale-100 cursor-pointer"
          >
            {isExporting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <FileDown className="w-3.5 h-3.5" />
            )}
            Xuất Báo cáo (.docx)
          </button>

          <button
            onClick={onExportReportPdf}
            disabled={isExporting || isExportingPdf || checklist.length === 0 || hasAreaContradiction}
            id="btn-export-pdf"
            className="flex items-center gap-1.5 py-1.5 px-3 bg-red-600 hover:bg-red-700 text-white font-medium text-xs rounded-lg shadow-sm shadow-red-600/15 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:scale-100 cursor-pointer"
          >
            {isExportingPdf ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Download className="w-3.5 h-3.5" />
            )}
            Tải Báo cáo (.pdf)
          </button>
        </div>
      </div>

      {/* Real-time Project Specifications Report Table */}
      <div 
        id="project-specs-banner" 
        className={`bg-slate-50 border-b border-slate-200 px-3 sm:px-6 flex-shrink-0 font-sans print:hidden transition-all duration-200 ${
          isSpecsExpanded ? "py-4 animate-fade-in" : "py-1.5"
        }`}
      >
        <div 
          className={
            isSpecsExpanded 
              ? "bg-gradient-to-br from-[#FFEEDC] via-[#FFDFBF] to-[#FDBA74] border-2 border-[#EA580C] rounded-2xl p-4 shadow-[0_8px_30px_rgba(234,88,12,0.15)] relative overflow-hidden transition-all duration-200" 
              : "relative transition-all duration-155"
          }
        >
          {isSpecsExpanded && (
            /* Decorative mesh safety map background */
            <div className="absolute inset-0 opacity-[0.03] bg-[radial-gradient(#000_1px,transparent_1px)] [background-size:12px_12px] pointer-events-none"></div>
          )}

          {/* Quick Report Title & Collapse Trigger Bar */}
          <div 
            className={`relative z-10 flex items-center justify-between gap-2 sm:gap-4 bg-gradient-to-r from-[#7C2D12] to-[#431407] text-white px-3 py-2 rounded-xl shadow-[0_3.5px_0_0_#2B0C04,0_6px_15px_rgba(0,0,0,0.2)] border border-[#9A3412] select-none transform transition-all ${
              isSpecsExpanded ? "mb-3" : "mb-0"
            }`}
          >
            {/* FIX B07 (Bao_Cao_QA_Lan_2.md): "thanh 'Báo cáo nhanh' tràn
                ngang (chữ bị cắt)". Nguyên nhân: div này là flex item nhưng
                thiếu min-w-0 — flex item mặc định min-width:auto khiến nó
                không chịu co lại theo nội dung, đẩy tràn ra ngoài viewport
                trên mobile dù <h3> đã có class truncate (truncate chỉ hoạt
                động khi container CHO PHÉP co nhỏ hơn nội dung). */}
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <Sparkles className="w-4 h-4 text-amber-300 animate-pulse shrink-0" />
              <h3 className="text-[11px] sm:text-[14px] font-black uppercase tracking-wider font-mono text-shadow-sm truncate min-w-0">
                Báo cáo nhanh: BẢNG THÔNG SỐ KỸ THUẬT KIẾN TRÚC CÔNG TRÌNH ĐÃ CHỌN
              </h3>
            </div>
            <button
              type="button"
              onClick={() => {
                userToggledSpecsRef.current = true; // FIX B07: đánh dấu người dùng đã tự thao tác
                setIsSpecsExpanded(!isSpecsExpanded);
              }}
              className="flex items-center gap-1.5 bg-white/10 hover:bg-white/20 hover:scale-[1.03] select-none border border-white/25 px-2.5 py-1 rounded-lg text-xs font-black text-white hover:text-amber-100 transition-all cursor-pointer shadow-md active:scale-95 shrink-0"
              title={isSpecsExpanded ? "Thu gọn bảng" : "Mở rộng bảng"}
            >
              <span className="hidden sm:inline">{isSpecsExpanded ? "Thu gọn" : "Chi tiết"}</span>
              {isSpecsExpanded ? <ChevronUp className="w-3.5 h-3.5 text-amber-300 shrink-0" /> : <ChevronDown className="w-3.5 h-3.5 text-amber-300 shrink-0" />}
            </button>
          </div>

          {isSpecsExpanded && (
            <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 animate-fade-in">
              {/* Box 1: Tên công trình */}
              <div className="bg-gradient-to-b from-indigo-50 to-indigo-100/90 border border-indigo-200/80 p-2.5 rounded-xl shadow-[0_3.5px_0_0_#C7D2FE,inset_0_1px_0_rgba(255,255,255,0.95)] hover:bg-indigo-100/70 transition-all duration-150">
                <span className="text-[8.5px] text-[#283593] uppercase font-black tracking-wider block mb-1">TÊN CÔNG TRÌNH</span>
                <span className="text-[11.5px] font-black text-[#1A237E] truncate block font-sans" title={projectInfo.name}>
                  {projectInfo.name || "Chưa đặt tên"}
                </span>
              </div>

              {/* Box 2: Phân loại */}
              <div className="bg-gradient-to-b from-emerald-50 to-emerald-100/90 border border-emerald-200/80 p-2.5 rounded-xl shadow-[0_3.5px_0_0_#A7F3D0,inset_0_1px_0_rgba(255,255,255,0.95)] hover:bg-emerald-100/70 transition-all duration-150">
                <span className="text-[8.5px] text-[#2E7D32] uppercase font-black tracking-wider block mb-1">PHÂN LOẠI</span>
                <span className="text-[11.5px] font-black text-[#1B5E20] truncate block font-sans" title={projectInfo.type}>
                  {projectInfo.type}
                </span>
              </div>

              {/* Box 3: Sàn xây dựng */}
              <div className="bg-gradient-to-b from-cyan-50 to-cyan-100/90 border border-cyan-200/80 p-2.5 rounded-xl shadow-[0_3.5px_0_0_#A5F3FC,inset_0_1px_0_rgba(255,255,255,0.95)] hover:bg-cyan-100/70 transition-all duration-150">
                <span className="text-[8.5px] text-[#00838F] uppercase font-black tracking-wider block mb-1">SÀN XÂY DỰNG</span>
                <span className="text-[11.5px] font-mono font-black text-[#006064] block truncate">
                  {projectInfo.totalFloorArea.toLocaleString("vi-VN")} m²
                </span>
              </div>

              {/* Box 4: Quy mô tầng */}
              <div className="bg-gradient-to-b from-fuchsia-50 to-fuchsia-100/90 border border-fuchsia-200/80 p-2.5 rounded-xl shadow-[0_3.5px_0_0_#F5D0FE,inset_0_1px_0_rgba(255,255,255,0.95)] hover:bg-fuchsia-100/70 transition-all duration-150">
                <span className="text-[8.5px] text-[#86198F] uppercase font-black tracking-wider block mb-1">QUY MÔ TẦNG</span>
                <span className="text-[11.5px] font-black text-[#4A044E] block font-sans truncate">
                  {projectInfo.floors} nổi
                  {projectInfo.basements && Number(projectInfo.basements) > 0 ? ` / ${projectInfo.basements} hầm` : ""}
                </span>
              </div>

              {/* Box 5: Chiều cao PCCC */}
              <div className="bg-gradient-to-b from-rose-50 to-rose-100/90 border border-rose-200/80 p-2.5 rounded-xl shadow-[0_3.5px_0_0_#FECDD3,inset_0_1px_0_rgba(255,255,255,0.95)] hover:bg-rose-100/70 transition-all duration-150">
                <span className="text-[8.5px] text-[#9D174D] uppercase font-black tracking-wider block mb-1">CHIỀU CAO PCCC</span>
                <span className="text-[11.5px] font-black text-[#881337] block font-sans truncate" title={`${projectInfo.pcccHeight || projectInfo.height} m`}>
                  {projectInfo.pcccHeight || projectInfo.height} m
                </span>
              </div>

              {/* Box 6: Bậc chịu lửa */}
              <div className="bg-gradient-to-b from-amber-50 to-amber-100/90 border border-amber-200/80 p-2.5 rounded-xl shadow-[0_3.5px_0_0_#FDE68A,inset_0_1px_0_rgba(255,255,255,0.95)] hover:bg-amber-100/70 transition-all duration-150">
                <span className="text-[8.5px] text-[#92400E] uppercase font-black tracking-wider block mb-1">BẬC CHỊU LỬA</span>
                <span className="text-[11.5px] font-black text-[#78350F] block font-sans truncate">
                  {projectInfo.fireRating || "Không chọn"}
                </span>
              </div>

              {/* Box 7: Nhà thiết kế */}
              <div className="bg-gradient-to-b from-sky-50 to-sky-100/90 border border-sky-200/80 p-2.5 rounded-xl shadow-[0_3.5px_0_0_#BAE6FD,inset_0_1px_0_rgba(255,255,255,0.95)] hover:bg-sky-100/70 transition-all duration-150">
                <span className="text-[8.5px] text-[#075985] uppercase font-black tracking-wider block mb-1">NHÀ THIẾT KẾ</span>
                <span className="text-[11.5px] font-black text-[#0C4A6E] truncate block font-sans" title={projectInfo.designer}>
                  {projectInfo.designer || "Chưa rõ"}
                </span>
              </div>

              {/* Box 8: Giai đoạn */}
              <div className="bg-gradient-to-b from-purple-50 to-purple-100/90 border border-purple-200/80 p-2.5 rounded-xl shadow-[0_3.5px_0_0_#E9D5FF,inset_0_1px_0_rgba(255,255,255,0.95)] hover:bg-purple-100/70 transition-all duration-150">
                <span className="text-[8.5px] text-[#6B21A8] uppercase font-black tracking-wider block mb-1">GIAI ĐOẠN</span>
                <span className="text-[11.5px] font-black text-[#581C87] block font-sans truncate" title={projectInfo.stage}>
                  {projectInfo.stage || "Thiết kế"}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Warnings & Inconsistencies Alert Zone if any */}
      {displayWarnings && displayWarnings.length > 0 && (
        <div id="project-warnings-banner" className="bg-orange-50/70 border-b border-orange-100 px-6 py-2 flex flex-col flex-shrink-0 print:hidden transition-all duration-200">
          <div className="flex items-center justify-between gap-4">
            <div 
              className="flex items-center gap-2.5 cursor-pointer flex-1 min-w-0"
              onClick={() => setIsWarningsExpanded(!isWarningsExpanded)}
              title="Click để thu gọn/mở rộng cảnh báo mâu thuẫn"
            >
              <AlertTriangle className="w-4 h-4 text-brand-orange shrink-0 animate-pulse" />
              <h3 className="text-[11px] font-semibold text-orange-850 uppercase tracking-wider font-display shrink-0">
                Phát hiện mâu thuẫn cần cảnh báo ({displayWarnings.length}):
              </h3>
              {!isWarningsExpanded && (
                <span className="text-xs text-orange-700 truncate font-medium ml-2 select-none">
                  {displayWarnings.join(" | ")} (Bấm để xem đầy đủ)
                </span>
              )}
            </div>
            <button
              onClick={() => setIsWarningsExpanded(!isWarningsExpanded)}
              className="p-1 hover:bg-orange-100 rounded-lg text-orange-850 transition-colors cursor-pointer shrink-0"
              title={isWarningsExpanded ? "Thu gọn cảnh báo" : "Mở rộng danh sách cảnh báo"}
            >
              {isWarningsExpanded ? <ChevronUp className="w-4.5 h-4.5" /> : <ChevronDown className="w-4.5 h-4.5" />}
            </button>
          </div>
          {isWarningsExpanded && (
            <div className="pl-6.5 mt-1 border-t border-orange-200/40 pt-1.5 animate-fade-in">
              <ul className="list-disc list-inside text-xs text-orange-800 space-y-0.5">
                {displayWarnings.map((warn, i) => (
                  <li key={i}>{warn}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Dynamic dashboard informing status and percentage */}
      {checklist.length > 0 && (() => {
        const totalItems = checklist.length;
        const compliantCount = checklist.filter(item => item.result === "Đạt" || item.result === "Không bắt buộc").length;
        const compliancePercentage = Math.round((compliantCount / totalItems) * 100);

        return (
          <div id="compliance-dashboard-banner" className="bg-white border-b border-slate-200 px-6 py-2 shrink-0 z-0 select-none print:hidden transition-all duration-200">
            <div className="bg-slate-50 border border-slate-150 rounded-xl p-2.5 flex items-center justify-between gap-4 shadow-inner">
              
              {isComplianceExpanded ? (
                /* Expanded view of Compliance bar */
                <div className="flex-1 flex flex-col md:flex-row md:items-center justify-between gap-4 w-full">
                  {/* Compliance gauge */}
                  <div className="flex-1 space-y-1.5">
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="font-extrabold text-slate-705 flex items-center gap-1.5">
                        <Award className="w-4 h-4 text-brand-orange shrink-0 animate-pulse" />
                        TỈ LỆ ĐÁP ỨNG QUY CHUẨN KỸ THUẬT:
                      </span>
                      <span className={`font-mono font-extrabold text-sm ${
                        compliancePercentage >= 80 ? "text-emerald-600" : compliancePercentage >= 50 ? "text-amber-600" : "text-rose-600"
                      }`}>
                        {/* FIX B13 (Bao_Cao_QA_Lan_3.md — Cao): compliantCount
                            đếm gộp cả "Đạt" VÀ "Không bắt buộc" nhưng nhãn cũ
                            ghi "hạng mục đạt" — gây hiểu nhầm là đã kiểm tra
                            và đạt yêu cầu. Đồng bộ nhãn giống tab Kết luận Pháp
                            lý ("Đạt & Không bắt buộc") ở mọi nơi trên giao diện. */}
                        {compliancePercentage}% ({compliantCount}/{totalItems} đạt & không bắt buộc)
                      </span>
                    </div>
                    
                    {/* Visual meter bar */}
                    <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                      <div 
                        style={{ width: `${compliancePercentage}%` }} 
                        className={`h-full rounded-full transition-all duration-550 ease-out ${
                          compliancePercentage >= 80 ? "bg-emerald-500" : compliancePercentage >= 50 ? "bg-amber-500" : "bg-rose-500"
                        }`}
                      />
                    </div>
                  </div>

                  {/* Badges numerical breakout overview */}
                  <div className="flex gap-2 flex-wrap items-center">
                    <div className="bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-lg text-center min-w-14">
                      <div className="text-[8px] text-emerald-600 font-bold uppercase tracking-wider">Đạt</div>
                      <div className="text-xs font-extrabold text-emerald-700 font-mono">
                        {checklist.filter(item => item.result === "Đạt" || item.result === "Không bắt buộc").length}
                      </div>
                    </div>
                    <div className="bg-rose-50 border border-rose-100 px-2 py-0.5 rounded-lg text-center min-w-14">
                      <div className="text-[8px] text-rose-600 font-bold uppercase tracking-wider">Không đạt</div>
                      <div className="text-xs font-extrabold text-rose-700 font-mono">
                        {checklist.filter(item => item.result === "Không đạt").length}
                      </div>
                    </div>
                    <div className="bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-lg text-center min-w-14">
                      <div className="text-[8px] text-amber-600 font-bold uppercase tracking-wider">Xem xét</div>
                      <div className="text-xs font-extrabold text-amber-700 font-mono">
                        {checklist.filter(item => item.result === "Khuyến nghị mạnh" || item.result === "Khuyến nghị" || item.result === "Cần xem xét").length}
                      </div>
                    </div>
                    <div className="bg-cyan-50 border border-cyan-100 px-2 py-0.5 rounded-lg text-center min-w-14">
                      <div className="text-[8px] text-cyan-600 font-bold uppercase tracking-wider">Đo đạc</div>
                      <div className="text-xs font-extrabold text-cyan-700 font-mono">
                        {checklist.filter(item => item.result === "Cần đo đạc").length}
                      </div>
                    </div>
                    
                    {/* Collapse Button */}
                    <button
                      onClick={() => setIsComplianceExpanded(false)}
                      className="p-1 hover:bg-slate-200 rounded-lg text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
                      title="Thu gọn thanh tỉ lệ"
                    >
                      <ChevronUp className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ) : (
                /* Collapsed view of Compliance bar */
                <div 
                  className="flex-1 flex items-center justify-between w-full cursor-pointer select-none" 
                  onClick={() => setIsComplianceExpanded(true)}
                  title="Click để mở rộng bảng tỉ lệ"
                >
                  <div className="flex items-center gap-2">
                    <Award className="w-4 h-4 text-brand-orange shrink-0 animate-pulse" />
                    <span className="text-[11px] font-black text-slate-750 uppercase tracking-tight">
                      TỈ LỆ ĐÁP ỨNG QUY CHUẨN KỸ THUẬT:
                    </span>
                    <span className={`font-mono font-black text-xs ${
                      compliancePercentage >= 80 ? "text-emerald-600" : compliancePercentage >= 50 ? "text-amber-600" : "text-rose-600"
                    }`}>
                      {compliancePercentage}% ({compliantCount}/{totalItems} đạt & không bắt buộc)
                    </span>
                    {/* Mini inline bar */}
                    <div className="w-20 bg-slate-200 h-1.5 rounded-full overflow-hidden hidden sm:block ml-2">
                      <div 
                        style={{ width: `${compliancePercentage}%` }} 
                        className={`h-full rounded-full ${
                          compliancePercentage >= 80 ? "bg-emerald-500" : compliancePercentage >= 50 ? "bg-amber-500" : "bg-rose-500"
                        }`}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded uppercase font-bold tracking-tight">
                      Bấm để mở rộng
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setIsComplianceExpanded(true);
                      }}
                      className="p-1 hover:bg-slate-200/80 rounded-lg text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
                    >
                      <ChevronDown className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* Tabs navigation */}
      {/* FIX B22 (Bao_Cao_QA_Lan_3.md — Thấp): dải tab CÓ cuộn ngang được
          nhưng không có bất kỳ chỉ dấu nào báo còn nội dung bên phải — trên
          màn hình 375px, tab "Kết luận Pháp lý PCCC" nằm ngoài vùng nhìn
          thấy, người dùng tưởng phần mềm thiếu chức năng. Bọc trong wrapper
          `relative` + thêm dải mờ (gradient fade) cố định bên phải, chỉ
          hiện trên màn hình nhỏ (`sm:hidden`), làm tín hiệu thị giác "còn
          nội dung cuộn tiếp" — không cần theo dõi vị trí cuộn bằng JS. */}
      <div className="relative flex-shrink-0">
        <div id="tabs-navigation-bar" className="bg-white border-b border-slate-200 px-6 flex gap-4 overflow-x-auto scrollbar-none whitespace-nowrap print:hidden">
        <button
          onClick={() => setActiveTab("chat")}
          className={`py-3 px-1 font-semibold text-xs flex items-center gap-1.5 border-b-2 transition-all cursor-pointer shrink-0 ${
            activeTab === "chat"
              ? "border-brand-orange text-brand-orange font-bold scale-102"
              : "border-transparent text-slate-500 hover:text-slate-850"
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Hồ sơ Tư vấn & Trò chuyện
        </button>
        <button
          onClick={() => setActiveTab("checklist")}
          className={`py-3 px-1 font-semibold text-xs flex items-center gap-1.5 border-b-2 transition-all cursor-pointer shrink-0 ${
            activeTab === "checklist"
              ? "border-brand-orange text-brand-orange font-bold scale-102"
              : "border-transparent text-slate-500 hover:text-slate-850"
          }`}
        >
          <ClipboardCheck className="w-3.5 h-3.5" />
          Bảng 17 Mục Checklist
          {checklist.length > 0 && (
            <span className="font-mono text-[10px] text-white bg-brand-orange px-1.5 py-0.2 rounded-full">
              {checklist.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("verdict")}
          className={`py-3 px-1 font-semibold text-xs flex items-center gap-1.5 border-b-2 transition-all cursor-pointer shrink-0 ${
            activeTab === "verdict"
              ? "border-brand-orange text-brand-orange font-bold scale-102"
              : "border-transparent text-slate-500 hover:text-slate-850"
          }`}
        >
          <Award className="w-3.5 h-3.5" />
          Kết luận Pháp lý PCCC
        </button>

        {activeTab === "full-checklist" && (
          <button
            onClick={() => setActiveTab("full-checklist")}
            className="py-3 px-2 font-bold text-xs flex items-center gap-1.5 border-b-2 border-brand-orange text-brand-orange bg-brand-orange/5 rounded-t-lg transition-all cursor-pointer shrink-0 animate-fade-in"
          >
            <Maximize2 className="w-3.5 h-3.5 text-brand-orange" />
            <span className="text-slate-900 font-extrabold uppercase">🗂️ [Xem Rộng] 17 Mục Checklist</span>
            <span 
              onClick={(e) => {
                e.stopPropagation();
                setActiveTab("checklist");
              }}
              className="ml-2 bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-red-650 rounded-full p-0.5 transition-colors focus:outline-none cursor-pointer flex items-center justify-center border border-slate-300"
              title="Thoát chế độ rộng"
            >
              <X className="w-3 h-3 font-semibold" />
            </span>
          </button>
        )}

        {activeTab === "full-verdict" && (
          <button
            onClick={() => setActiveTab("full-verdict")}
            className="py-3 px-2 font-bold text-xs flex items-center gap-1.5 border-b-2 border-brand-orange text-brand-orange bg-brand-orange/5 rounded-t-lg transition-all cursor-pointer shrink-0 animate-fade-in"
          >
            <Maximize2 className="w-3.5 h-3.5 text-brand-orange" />
            <span className="text-slate-900 font-extrabold uppercase">📑 [Xem Rộng] Kết luận Pháp lý</span>
            <span 
              onClick={(e) => {
                e.stopPropagation();
                setActiveTab("verdict");
              }}
              className="ml-2 bg-slate-100 hover:bg-slate-200 text-slate-100 hover:text-red-500 rounded-full p-0.5 transition-colors focus:outline-none cursor-pointer flex items-center justify-center border border-slate-300"
              title="Thoát chế độ rộng"
            >
              <X className="w-3 h-3 font-semibold text-slate-800" />
            </span>
          </button>
        )}
        </div>
        {/* FIX B22: dải mờ chỉ báo còn nội dung cuộn ngang, chỉ hiện trên
            màn hình nhỏ (sm:hidden) — không chặn click nhờ pointer-events-none. */}
        <div className="sm:hidden absolute top-0 right-0 bottom-0 w-8 bg-gradient-to-l from-white to-transparent pointer-events-none" />
      </div>

      {/* Dynamic Content Panel area */}
      <div className="flex-1 overflow-hidden flex flex-col relative">
        {/* TAB 1: CONVERSATIONAL CHATBOT FEED */}
        {(activeTab === "chat" || activeTab === "checklist" || activeTab === "full-checklist" || activeTab === "verdict" || activeTab === "full-verdict") && (
          <div className="flex-1 flex flex-col justify-between overflow-hidden">
            {/* Scrollable messages layer */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar bg-slate-50/50">
              {messages.map((msg) => {
                const isAI = msg.sender === "assistant";
                return (
                  <div
                    key={msg.id}
                    className={`flex items-start gap-4 max-w-4xl ${
                      isAI ? "mr-12" : "ml-auto flex-row-reverse pl-12"
                    }`}
                  >
                    {/* Avatar Icon */}
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center text-white flex-shrink-0 shadow-sm ${
                        isAI
                          ? "bg-brand-orange shadow-brand-orange/15"
                          : "bg-slate-700 shadow-slate-200/10 animate-fade-in"
                      }`}
                    >
                      {isAI ? (
                        <Sparkles className="w-4 h-4" />
                      ) : (
                        <span className="font-bold text-xs font-mono">U</span>
                      )}
                    </div>

                    {/* Speech box wrapper */}
                    <div
                      className={`rounded-2xl p-4 shadow-sm border transition-all ${
                        isAI
                          ? "bg-white border-slate-200 text-slate-950 leading-relaxed text-sm font-sans"
                          : "bg-slate-100 border-slate-200 text-slate-950 text-sm font-sans font-medium"
                      }`}
                    >
                      {/* Markdown rendering with asterisk removal and newline paragraph support */}
                      <div className="space-y-2 select-text leading-relaxed">
                        {isAI ? renderFormattedMessageText(msg.text) : (
                          <div className="whitespace-pre-wrap">{msg.text}</div>
                        )}
                      </div>
                      <div
                        className={`text-[10px] mt-2 font-mono flex justify-end ${
                          isAI ? "text-slate-400" : "text-slate-500"
                        }`}
                      >
                        {new Date(msg.timestamp).toLocaleTimeString("vi-VN", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Waiting pending state indicator */}
              {isPending && (
                <div className="flex items-start gap-4 mr-12 max-w-3xl">
                  <div className="w-9 h-9 rounded-xl bg-brand-orange flex items-center justify-center text-white shadow-sm flex-shrink-0 animate-bounce">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl p-4 text-slate-800 text-sm flex items-center gap-3 shadow-sm font-sans font-semibold">
                    <Loader2 className="w-4 h-4 animate-spin text-brand-orange" />
                    Chuyên gia AI đang phân tích rà soát bản thiết kế của bạn...
                    {/* FIX B04 (Bao_Cao_QA_Lan_2.md): "Vẫn KHÔNG có nút hủy;
                        người dùng phải chờ hết tiến trình". */}
                    {onCancelPending && (
                      <button
                        onClick={onCancelPending}
                        className="ml-1 px-2.5 py-1 rounded-md text-xs font-semibold text-red-600 border border-red-200 hover:bg-red-50 transition-colors shrink-0"
                        title="Huỷ phân tích đang chạy"
                      >
                        Huỷ
                      </button>
                    )}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Prompts Panel at the absolute bottom of scroll or over input */}
            {messages.length === 1 && (
              <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex-shrink-0 space-y-2">
                <h3 className="text-xs font-semibold text-slate-500 flex items-center gap-1.5 select-none font-display">
                  <Info className="w-3.5 h-3.5" /> Gợi ý hồ sơ test nhanh thẩm định (Nghiên cứu sâu):
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {QUICK_PROMPTS.map((qp, i) => (
                    <button
                      key={i}
                      onClick={() => handleQuickPrompt(qp.prompt)}
                      disabled={isPending}
                      className="p-2.5 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg text-left text-xs font-medium text-slate-700 transition-all hover:border-slate-300 shadow-sm active:scale-[0.99] disabled:opacity-50 cursor-pointer"
                    >
                      {qp.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat message input form area */}
            <form
              onSubmit={handleSubmit}
              className="p-4 bg-white border-t border-slate-200 flex items-center gap-2 flex-shrink-0 shadow-md"
            >
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                id="chat-textarea"
                disabled={isPending}
                placeholder="Nhập vào thông tin kiến trúc công trình hoặc hỏi chuyên gia về PCCC..."
                className="flex-1 px-4 py-2 bg-slate-50 hover:bg-slate-100 focus:bg-slate-50 border border-slate-200 focus:border-brand-orange text-slate-950 text-sm outline-none resize-none h-11 transition-all custom-scrollbar py-2.5 font-sans"
              />
              <button
                type="submit"
                id="btn-send-message"
                disabled={!inputText.trim() || isPending}
                className="w-11 h-11 rounded-xl bg-brand-orange hover:bg-brand-orange/90 text-white flex items-center justify-center shadow-md hover:shadow-brand-orange/25 active:scale-95 transition-all disabled:opacity-55 disabled:scale-100 cursor-pointer"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>

            {/* FOOTER NẰM DƯỚI THANH CÔNG CỤ NHẬP DỮ LIỆU */}
            <div id="pdtech-wide-footer" className="py-2.5 px-4 bg-slate-50 border-t border-slate-200 text-center text-[10px] sm:text-xs text-slate-500 font-bold select-none shrink-0 font-mono tracking-wide flex items-center justify-center">
              <span>@2026 Tự hào được phát triển bởi PDTech - Giải pháp công nghệ tối ưu</span>
            </div>
          </div>
        )}

        {/* TAB 2: DETAILED CHECKS AND REQUIREMENTS TABLE - DISABLED IN FAVOR OF FULL SCREEN POPUP */}
        {false && (() => {
          return (
            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
              {checklist.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                  <FileCheck className="w-16 h-16 text-slate-300 stroke-[1.5]" />
                  <div>
                    <h3 className="font-semibold text-slate-700">Chưa có kết quả phân tích</h3>
                    <p className="text-slate-400 text-sm max-w-sm mx-auto mt-1">
                      Vui lòng cung cấp hồ sơ hoặc chat với chuyên gia để tự động kích hoạt bảng checklist kiểm duyệt 17 hạng mục đầy đủ.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4 animate-fade-in">
                  <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
                    <div>
                      <h3 className="font-display font-black text-slate-900 text-[20px] uppercase tracking-tight">
                        Bảng kết quả rà soát chi tiết quy chuẩn
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Theo dõi chi tiết mức độ đáp ứng 17 hạng mục quy chuẩn an toàn PCCC
                      </p>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                      {/* Interactive Dropdown Filter */}
                      <div className="interactive-control flex items-center gap-1.5 bg-white border border-slate-250 rounded-xl px-3 py-1.5 shadow-sm text-xs text-slate-655">
                        <Filter className="w-3.5 h-3.5 text-brand-orange" />
                        <span className="font-medium text-slate-500">Lạc trạng:</span>
                        <select
                          id="checklist-filter"
                          value={filterResult}
                          onChange={(e) => setFilterResult(e.target.value)}
                          className="bg-transparent border-none text-slate-800 font-semibold focus:outline-none cursor-pointer pr-1"
                        >
                          <option value="all">Tất cả ({checklist.length})</option>
                          <option value="Không đạt">❌ Không đạt ({checklist.filter((item) => item.result === "Không đạt").length})</option>
                          <option value="Khuyến nghị mạnh">⚠️ Khuyến nghị mạnh ({checklist.filter((item) => item.result === "Khuyến nghị mạnh").length})</option>
                          <option value="Khuyến nghị">⚠️ Khuyến nghị ({checklist.filter((item) => item.result === "Khuyến nghị" || item.result === "Cần xem xét").length})</option>
                          <option value="Cần đo đạc">📏 Cần đo đạc ({checklist.filter((item) => item.result === "Cần đo đạc").length})</option>
                          <option value="Đạt">✅ Đạt ({checklist.filter((item) => item.result === "Đạt" || item.result === "Không bắt buộc").length})</option>
                        </select>
                      </div>

                      <div className="interactive-control text-xs text-slate-500 font-semibold bg-slate-205 py-1.5 px-3 rounded-xl max-w-[200px] text-ellipsis overflow-hidden whitespace-nowrap">
                        Hồ sơ: {projectInfo.name || "Dự án Hiện tại"}
                      </div>
                    </div>
                  </div>

                  {/* Mode announcement / expansion click trigger banner */}
                  <div 
                    onClick={() => setActiveTab("full-checklist")}
                    className="bg-brand-orange/10 hover:bg-brand-orange/18 border border-brand-orange/25 p-2.5 rounded-xl flex items-center justify-between cursor-pointer group transition-all duration-155 active:scale-[0.99] select-none shadow-sm"
                    title="Mở rộng bảng checklist"
                  >
                    <div className="flex items-center gap-2">
                      <Maximize2 className="w-3.5 h-3.5 text-brand-orange shrink-0 animate-pulse" />
                      <span className="text-[11px] sm:text-[12px] font-bold text-brand-orange uppercase tracking-wider font-mono">
                        Có chế độ xem rộng toàn Tab mới! Bấm tại đây hoặc bất kỳ đâu trên bảng để tối ưu hóa góc nhìn
                      </span>
                    </div>
                    <span className="text-[9px] font-black bg-brand-orange text-white px-2 py-0.5 rounded uppercase group-hover:scale-105 transition-transform flex items-center gap-1 shadow">
                      Phóng to Tab <Maximize2 className="w-2.5 h-2.5" />
                    </span>
                  </div>

                  <div 
                    onClick={(e) => {
                      if ((e.target as HTMLElement).closest('.interactive-control')) {
                        return;
                      }
                      setActiveTab("full-checklist");
                    }}
                    className="border border-slate-350 rounded-xl overflow-hidden bg-white shadow-md hover:border-brand-orange/50 cursor-pointer transition-all duration-200 hover:shadow-lg"
                    title="Bấm vào bảng để xem trong tab rộng"
                  >
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-100 text-black font-black border-b-2 border-slate-300">
                          <th 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSort("stt");
                            }}
                            className="interactive-control p-3 w-16 text-center font-black cursor-pointer hover:bg-slate-200 transition-colors select-none"
                            title="Bấm để sắp xếp theo số thứ tự"
                          >
                            <div className="flex items-center justify-center gap-1">
                              STT
                              <ArrowUpDown className={`w-3.5 h-3.5 text-slate-500 shrink-0 ${sortColumn === "stt" ? "text-brand-orange font-bold" : ""}`} />
                            </div>
                          </th>
                          <th 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSort("criteria");
                            }}
                            className="interactive-control p-3 w-48 font-black cursor-pointer hover:bg-slate-200 transition-colors select-none"
                            title="Bấm để sắp xếp theo hạng mục"
                          >
                            <div className="flex items-center gap-1">
                              Hạng mục kiểm tra
                              <ArrowUpDown className={`w-3.5 h-3.5 text-slate-500 shrink-0 ${sortColumn === "criteria" ? "text-brand-orange font-bold" : ""}`} />
                            </div>
                          </th>
                          <th className="p-3 font-black">Yêu cầu tiêu chuẩn quy chuẩn</th>
                          <th className="p-3 font-black">Kết luận chi tiết công trình</th>
                          <th 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSort("result");
                            }}
                            className="interactive-control p-3 w-32 text-center font-black cursor-pointer hover:bg-slate-200 transition-colors select-none"
                            title="Bấm để sắp xếp theo đánh giá"
                          >
                            <div className="flex items-center justify-center gap-1">
                              Đánh giá
                              <ArrowUpDown className={`w-3.5 h-3.5 text-slate-500 shrink-0 ${sortColumn === "result" ? "text-brand-orange font-bold" : ""}`} />
                            </div>
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-250">
                        {filteredAndSortedChecklist.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="p-10 text-center text-black font-sans bg-slate-50/20 font-bold">
                              <Info className="w-8 h-8 text-black mx-auto mb-2" />
                              Không tìm thấy kết quả phù hợp với lọc trạng thái và từ khóa: "{checklistSearchQuery}".
                            </td>
                          </tr>
                        ) : (
                          filteredAndSortedChecklist.map((item) => {
                            let badgeClass = "bg-slate-100 text-black border border-slate-205";
                            let ratingIcon = <Info className="w-3.5 h-3.5 text-black shrink-0" />;

                            if (item.result === "Đạt") {
                              badgeClass = "bg-gradient-to-b from-emerald-500 to-emerald-600 text-white border border-emerald-400 shadow-[0_3px_0_0_#047857,0_4px_8px_rgba(16,185,129,0.25)] rounded-lg px-2.5 py-1 text-[10px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-emerald-400 to-emerald-600 flex items-center justify-center text-white shadow-[0_2px_0_0_#047857,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <CheckCircle className="w-3.5 h-3.5 text-white" />
                                </div>
                              );
                            } else if (item.result === "Không đạt") {
                              badgeClass = "bg-gradient-to-b from-rose-500 to-rose-600 text-white border border-rose-400 shadow-[0_3px_0_0_#9F1239,0_4px_8px_rgba(244,63,94,0.25)] rounded-lg px-2.5 py-1 text-[10px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-rose-400 to-rose-600 flex items-center justify-center text-white shadow-[0_2px_0_0_#9F1239,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <XCircle className="w-3.5 h-3.5 text-white" />
                                </div>
                              );
                            } else if (item.result === "Khuyến nghị mạnh") {
                              badgeClass = "bg-gradient-to-b from-orange-500 to-orange-600 text-white border border-orange-400 shadow-[0_3px_0_0_#C2410C,0_4px_8px_rgba(249,115,22,0.25)] rounded-lg px-2.5 py-1 text-[10px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-orange-400 to-orange-550 flex items-center justify-center text-white shadow-[0_2px_0_0_#C2410C,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <AlertTriangle className="w-3.5 h-3.5 text-white" />
                                </div>
                              );
                            } else if (item.result === "Khuyến nghị" || item.result === "Cần xem xét") {
                              badgeClass = "bg-gradient-to-b from-amber-500 to-amber-600 text-white border border-amber-400 shadow-[0_3px_0_0_#B45309,0_4px_8px_rgba(245,158,11,0.25)] rounded-lg px-2.5 py-1 text-[10px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-amber-400 to-amber-600 flex items-center justify-center text-white shadow-[0_2px_0_0_#B45309,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <AlertTriangle className="w-3.5 h-3.5 text-white" />
                                </div>
                              );
                            } else if (item.result === "Cần đo đạc") {
                              badgeClass = "bg-gradient-to-b from-cyan-500 to-cyan-600 text-white border border-cyan-400 shadow-[0_3px_0_0_#0369A1,0_4px_8px_rgba(6,182,212,0.25)] rounded-lg px-2.5 py-1 text-[10px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-cyan-400 to-cyan-600 flex items-center justify-center text-white shadow-[0_2px_0_0_#0369A1,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <Ruler className="w-3.5 h-3.5 text-white" />
                                </div>
                              );
                            } else if (item.result === "Không bắt buộc") {
                              badgeClass = "bg-gradient-to-b from-slate-500 to-slate-600 text-white border border-slate-400 shadow-[0_3px_0_0_#334155,0_4px_8px_rgba(100,116,139,0.25)] rounded-lg px-2.5 py-1 text-[10px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-slate-400 to-slate-500 flex items-center justify-center text-white shadow-[0_2px_0_0_#334155,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <CheckCircle className="w-3.5 h-3.5 text-white" />
                                </div>
                              );
                            }

                            return (
                              <tr key={item.stt} className="hover:bg-slate-50/75 transition-colors">
                                <td className="p-3 text-center font-mono text-black font-black text-sm">{item.stt}</td>
                                <td className="p-3 font-black text-black text-[13px]">
                                  <div>{item.criteria}</div>
                                  <span className="text-[10px] text-black font-sans font-extrabold italic">
                                    ({item.reference})
                                  </span>
                                </td>
                                <td className="p-3 text-black font-bold text-[12.5px] leading-normal">{item.requirement}</td>
                                <td className="p-3 text-black font-bold text-[12.5px] leading-normal">{item.note}</td>
                                <td className="p-3 text-center">
                                  <div className="flex items-center justify-center gap-1.5 whitespace-nowrap">
                                    {ratingIcon}
                                    <span className={`inline-block px-2.5 py-1 rounded text-[10px] font-bold ${badgeClass}`}>
                                      {item.result}
                                    </span>
                                  </div>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* TAB 2.5: EXPANDED FULL CHECKLIST VIEW */}
        {(activeTab === "checklist" || activeTab === "full-checklist") && (() => {
          return (
            <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-3 sm:p-5 select-none print:static print:bg-white print:p-0 print:z-0 print:block animate-fade-in">
              <div className="bg-white w-full max-w-7xl h-[92vh] rounded-2xl flex flex-col overflow-hidden shadow-2xl border border-slate-350 select-text animate-scale-up print:w-full print:h-auto print:shadow-none print:rounded-none print:overflow-visible print:block">
                {/* Modal Header */}
                <div className="sticky top-0 bg-slate-50 border-b border-slate-205 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 z-10 shrink-0 print:hidden">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-orange-100 flex items-center justify-center text-brand-orange shadow-sm shrink-0">
                      <ClipboardCheck className="w-5 h-5 text-brand-orange animate-pulse" />
                    </div>
                    <div>
                      <h3 className="font-display font-black text-slate-900 text-base md:text-lg uppercase tracking-tight">
                        Bảng 17 Mục Quy Chuẩn PCCC Toàn Màn Hình
                      </h3>
                      <p className="text-[11px] text-slate-500 font-semibold uppercase font-mono tracking-wider">
                        Mức độ đáp ứng điều kiện an toàn &amp; phân tích quy phạm
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={onExportReport}
                      disabled={isExporting || checklist.length === 0 || hasAreaContradiction}
                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-extrabold px-3 py-2 rounded-xl text-xs shadow-md transition-all active:scale-95 cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Thống kê Excel {isExporting && "..."}
                    </button>
                    <button
                      onClick={onExportReportPdf}
                      disabled={isExportingPdf || checklist.length === 0 || hasAreaContradiction}
                      className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-extrabold px-3 py-2 rounded-xl text-xs shadow-md transition-all active:scale-95 cursor-pointer"
                    >
                      <FileDown className="w-3.5 h-3.5" />
                      In báo cáo PDF {isExportingPdf && "..."}
                    </button>
                    <button
                      onClick={() => setActiveTab("chat")}
                      className="flex items-center gap-1.5 bg-rose-500 hover:bg-rose-600 text-white font-black px-4 py-2 rounded-xl text-xs transition-all shadow-md active:scale-95 cursor-pointer ml-1"
                      title="Quay lại Chat chính (ESC)"
                    >
                      <XCircle className="w-4 h-4" />
                      Đóng (X)
                    </button>
                  </div>
                </div>

                {/* Modal Body (Scrollable along vertical axis) */}
                <div id="full-checklist-tab-content" className="flex-1 overflow-y-auto p-6 space-y-5 scrollbar-thin bg-white print:overflow-visible print:p-0 print:m-0 print:bg-white print:h-auto">
              {checklist.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                  <FileCheck className="w-16 h-16 text-slate-300 stroke-[1.5]" />
                  <div>
                    <h3 className="font-semibold text-slate-700">Chưa có kết quả phân tích</h3>
                    <p className="text-slate-400 text-sm max-w-sm mx-auto mt-1">
                      Vui lòng cung cấp hồ sơ hoặc chat với chuyên gia để tự động kích hoạt bảng checklist kiểm duyệt 17 hạng mục đầy đủ.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4 animate-fade-in">


                  <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
                    <div>
                      <h3 className="font-display font-black text-slate-900 text-[22px] uppercase">
                        Bảng 17 Mục Quy chuẩn PCCC (Bản Phóng To)
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Theo dõi đầy đủ mức độ đáp ứng, lọc và tìm kiếm ở màn hình rộng
                      </p>
                    </div>

                    <div className="flex items-center gap-2.5 flex-wrap">
                      {/* Search box */}
                      <div className="relative w-full sm:w-80">
                        <input
                          type="text"
                          placeholder="Tìm kiếm mục quy chuẩn hoặc ghi chú..."
                          value={checklistSearchQuery}
                          onChange={(e) => setChecklistSearchQuery(e.target.value)}
                          className="w-full pl-8 pr-7 py-2 bg-slate-50 hover:bg-slate-100 focus:bg-white border border-slate-300 focus:border-brand-orange outline-none text-xs text-slate-900 rounded-xl font-bold shadow-sm transition-all focus:ring-1 focus:ring-brand-orange/30"
                        />
                        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                        {checklistSearchQuery && (
                          <button
                            type="button"
                            onClick={() => setChecklistSearchQuery("")}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-655 p-0.5 animate-fade-in"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </div>

                      {/* Dropdown status Filter */}
                      <div className="flex items-center gap-1.5 bg-white border border-slate-205 rounded-xl px-3 py-2 shadow-sm text-xs text-slate-650">
                        <Filter className="w-3.5 h-3.5 text-brand-orange" />
                        <span className="font-medium text-slate-500">Trạng thái:</span>
                        <select
                          value={filterResult}
                          onChange={(e) => setFilterResult(e.target.value)}
                          className="bg-transparent border-none text-slate-800 font-semibold focus:outline-none cursor-pointer pr-1"
                        >
                          <option value="all">Tất cả ({checklist.length})</option>
                          <option value="Không đạt">❌ Không đạt ({checklist.filter((item) => item.result === "Không đạt").length})</option>
                          <option value="Khuyến nghị mạnh">⚠️ Khuyến nghị mạnh ({checklist.filter((item) => item.result === "Khuyến nghị mạnh").length})</option>
                          <option value="Khuyến nghị">⚠️ Khuyến nghị ({checklist.filter((item) => item.result === "Khuyến nghị" || item.result === "Cần xem xét").length})</option>
                          <option value="Cần đo đạc">📏 Cần đo đạc ({checklist.filter((item) => item.result === "Cần đo đạc").length})</option>
                          <option value="Đạt">✅ Đạt ({checklist.filter((item) => item.result === "Đạt" || item.result === "Không bắt buộc").length})</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="border border-slate-350 rounded-2xl overflow-hidden bg-white shadow-xl overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs md:text-sm min-w-[800px]">
                      <thead>
                        <tr className="bg-slate-100 text-black font-black border-b-2 border-slate-300">
                          <th 
                            onClick={() => handleSort("stt")}
                            className="p-4 w-16 text-center font-black cursor-pointer hover:bg-slate-200 transition-colors select-none"
                          >
                            <div className="flex items-center justify-center gap-1.5">
                              STT
                              <ArrowUpDown className={`w-4 h-4 text-slate-500 shrink-0 ${sortColumn === "stt" ? "text-brand-orange font-bold" : ""}`} />
                            </div>
                          </th>
                          <th 
                            onClick={() => handleSort("criteria")}
                            className="p-4 w-60 font-black cursor-pointer hover:bg-slate-300 transition-colors select-none"
                          >
                            <div className="flex items-center gap-1.5">
                              Hạng mục kiểm tra
                              <ArrowUpDown className={`w-4 h-4 text-slate-500 shrink-0 ${sortColumn === "criteria" ? "text-brand-orange font-bold" : ""}`} />
                            </div>
                          </th>
                          <th className="p-4 font-black text-slate-850">Yêu cầu tiêu chuẩn quy chuẩn chi tiết</th>
                          <th className="p-4 font-black text-slate-850">Kết luận chi tiết công trình của bạn</th>
                          <th 
                            onClick={() => handleSort("result")}
                            className="p-4 w-40 text-center font-black cursor-pointer hover:bg-slate-200 transition-colors select-none"
                          >
                            <div className="flex items-center justify-center gap-1.5">
                              Đánh giá
                              <ArrowUpDown className={`w-4 h-4 text-slate-500 shrink-0 ${sortColumn === "result" ? "text-brand-orange font-bold" : ""}`} />
                            </div>
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-250 text-[13px]">
                        {filteredAndSortedChecklist.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="p-16 text-center text-slate-600 bg-slate-50 font-sans font-bold">
                              <Info className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                              Không tìm thấy hạng mục quy chuẩn nào tương ứng với bộ lọc quy phạm.
                            </td>
                          </tr>
                        ) : (
                          filteredAndSortedChecklist.map((item) => {
                            let badgeClass = "bg-slate-100 text-black border border-slate-205";
                            let ratingIcon = <Info className="w-4 h-4 text-black shrink-0" />;

                            if (item.result === "Đạt") {
                              badgeClass = "bg-gradient-to-b from-emerald-500 to-emerald-600 text-white border border-emerald-400 shadow-[0_3px_0_0_#047857,0_4px_8px_rgba(16,185,129,0.25)] rounded-lg px-2.5 py-1 text-[11px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-emerald-400 to-emerald-600 flex items-center justify-center text-white shadow-[0_2px_0_0_#047857,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <CheckCircle className="w-4 h-4 text-white" />
                                </div>
                              );
                            } else if (item.result === "Không đạt") {
                              badgeClass = "bg-gradient-to-b from-rose-500 to-rose-600 text-white border border-rose-400 shadow-[0_3px_0_0_#9F1239,0_4px_8px_rgba(244,63,94,0.25)] rounded-lg px-3 py-1 text-[11px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-rose-400 to-rose-600 flex items-center justify-center text-white shadow-[0_2px_0_0_#9F1239,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <XCircle className="w-4 h-4 text-white" />
                                </div>
                              );
                            } else if (item.result === "Khuyến nghị mạnh") {
                              badgeClass = "bg-gradient-to-b from-orange-500 to-orange-600 text-white border border-orange-400 shadow-[0_3px_0_0_#C2410C,0_4px_8px_rgba(249,115,22,0.25)] rounded-lg px-2.5 py-1 text-[11px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-orange-400 to-orange-550 flex items-center justify-center text-white shadow-[0_2px_0_0_#C2410C,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <AlertTriangle className="w-4 h-4 text-white" />
                                </div>
                              );
                            } else if (item.result === "Khuyến nghị" || item.result === "Cần xem xét") {
                              badgeClass = "bg-gradient-to-b from-amber-500 to-amber-600 text-white border border-amber-400 shadow-[0_3px_0_0_#B45309,0_4px_8px_rgba(245,158,11,0.25)] rounded-lg px-2.5 py-1 text-[11px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-amber-400 to-amber-600 flex items-center justify-center text-white shadow-[0_2px_0_0_#B45309,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <AlertTriangle className="w-4 h-4 text-white" />
                                </div>
                              );
                            } else if (item.result === "Cần đo đạc") {
                              badgeClass = "bg-gradient-to-b from-cyan-500 to-cyan-600 text-white border border-cyan-400 shadow-[0_3px_0_0_#0369A1,0_4px_8px_rgba(6,182,212,0.25)] rounded-lg px-2.5 py-1 text-[11px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-cyan-400 to-cyan-600 flex items-center justify-center text-white shadow-[0_2px_0_0_#0369A1,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <Ruler className="w-4 h-4 text-white" />
                                </div>
                              );
                            } else if (item.result === "Không bắt buộc") {
                              badgeClass = "bg-gradient-to-b from-slate-500 to-slate-600 text-white border border-slate-400 shadow-[0_3px_0_0_#334155,0_4px_8px_rgba(100,116,139,0.25)] rounded-lg px-2.5 py-1 text-[11px] font-black tracking-wide uppercase";
                              ratingIcon = (
                                <div className="w-6 h-6 rounded-full bg-gradient-to-b from-slate-400 to-slate-500 flex items-center justify-center text-white shadow-[0_2px_0_0_#334155,0_3px_6px_rgba(0,0,0,0.15)] shrink-0">
                                  <CheckCircle className="w-4 h-4 text-white" />
                                </div>
                              );
                            }

                            return (
                              <tr key={item.stt} className="hover:bg-slate-50/75 transition-colors">
                                <td className="p-4 text-center font-mono text-black font-black text-sm">{item.stt}</td>
                                <td className="p-4 font-black text-black text-[14px] leading-tight">
                                  <div>{item.criteria}</div>
                                  <span className="text-[11px] text-slate-500 font-sans font-semibold italic block mt-1">
                                    Thẩm quyền tham chiếu: {item.reference}
                                  </span>
                                </td>
                                <td className="p-4 text-black font-semibold text-[13.5px] leading-relaxed max-w-md">{item.requirement}</td>
                                <td className="p-4 text-black font-semibold text-[13.5px] leading-relaxed max-w-sm">{item.note}</td>
                                <td className="p-4 text-center">
                                  <div className="flex items-center justify-center gap-2 whitespace-nowrap">
                                    {ratingIcon}
                                    <span className={`inline-block px-3 py-1.5 rounded-lg text-[10px] font-bold ${badgeClass}`}>
                                      {item.result}
                                    </span>
                                  </div>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
                </div>
              </div>
            </div>
          );
        })()}
        {/* TAB 3: LEGAL VERDICT EXPLANATIONS - DISABLED IN FAVOR OF FULL SCREEN POPUP */}
        {false && (
          <div id="verdict-tab-content" className="flex-1 overflow-y-auto p-6 space-y-6 print:overflow-visible print:p-0 print:m-0 print:bg-white">
            {checklist.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                <Award className="w-16 h-16 text-slate-300 stroke-[1.5]" />
                <div>
                  <h3 className="font-semibold text-slate-755">Chưa kết luận</h3>
                  <p className="text-slate-400 text-sm max-w-sm mx-auto mt-1">
                    Vui lòng cung cấp đầy đủ thông tin hoặc chat với chuyên gia để nhận diện tính pháp lý của hồ sơ.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-6 animate-fade-in max-w-4xl">
                {/* Print Only Header */}
                <div className="hidden print:flex flex-col border-b-2 border-slate-900 pb-3 mb-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h1 className="font-display font-black text-lg text-slate-900 uppercase">
                        BÁO CÁO PHÁP LÝ THẨM DUYỆT PCCC (NGHỊ ĐỊNH 105/2025/NĐ-CP)
                      </h1>
                      <p className="text-[10px] font-mono font-bold text-slate-500 uppercase mt-0.5">
                        Chương Trình Thẩm Định Chuyên Gia Phòng Cháy Chữa Cháy Tự Động
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-[9px] font-mono font-bold bg-slate-100 border border-slate-300 px-2 py-0.5 rounded">
                        NGÀY IN: {new Date().toLocaleDateString("vi-VN")}
                      </span>
                    </div>
                  </div>
                  
                  {/* Project metadata row */}
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1 mt-3 pt-2.5 border-t border-dashed border-slate-300 text-[10.5px] text-slate-700">
                    <div>
                      <strong className="text-slate-900">Tên công trình:</strong> {projectInfo.name || "Chưa đặt tên"}
                    </div>
                    <div>
                      <strong className="text-slate-900">Địa điểm:</strong> {projectInfo.location || "Chưa rõ"}
                    </div>
                    <div>
                      <strong className="text-slate-900">Quy mô tầng:</strong> {projectInfo.floors} tầng nổi {projectInfo.basements && Number(projectInfo.basements) > 0 ? `/ ${projectInfo.basements} hầm` : ""}
                    </div>
                    <div>
                      <strong className="text-slate-900">Tổng diện tích xây dựng:</strong> {projectInfo.totalFloorArea || projectInfo.floorArea} m²
                    </div>
                  </div>
                </div>

                {/* Trigger to expand banner */}
                <div 
                  onClick={() => setActiveTab("full-verdict")}
                  className="bg-brand-orange/10 hover:bg-brand-orange/18 border border-brand-orange/25 p-2.5 rounded-xl flex items-center justify-between cursor-pointer group transition-all duration-155 active:scale-[0.99] select-none shadow-sm print:hidden"
                  title="Mở rộng mục kết luận pháp lý này thành tab mới"
                >
                  <div className="flex items-center gap-2">
                    <Maximize2 className="w-3.5 h-3.5 text-brand-orange shrink-0 animate-pulse" />
                    <span className="text-[11px] sm:text-[12px] font-bold text-brand-orange uppercase tracking-wider font-mono">
                      Có Chế độ Xem Rộng (Tab Phóng To)! Click vào đây hoặc bảng kết luận bên dưới để phóng to tối đa
                    </span>
                  </div>
                  <span className="text-[9px] font-black bg-brand-orange text-white px-2 py-0.5 rounded uppercase group-hover:scale-105 transition-transform flex items-center gap-1 shadow">
                    Xem tab rộng <Maximize2 className="w-2.5 h-2.5" />
                  </span>
                </div>

                {/* Large visual badge card */}
                <div
                  id="verdict-badge-card"
                  onClick={() => setActiveTab("full-verdict")}
                  className={`p-6 rounded-2xl border-2 flex items-center gap-5 transition-all duration-205 cursor-pointer hover:scale-[1.01] hover:shadow-lg ${
                    isSubjectToAppraisal
                      ? "bg-gradient-to-b from-orange-50 to-orange-100 border-orange-355 text-orange-950 shadow-[0_5px_0_0_#EA580C,0_8px_20px_rgba(234,88,12,0.15)]"
                      : "bg-gradient-to-b from-emerald-50 to-emerald-100 border-emerald-355 text-emerald-950 shadow-[0_5px_0_0_#059669,0_8px_20px_rgba(5,150,105,0.15)]"
                  }`}
                  title="Click để phóng to kết luận pháp lý dạng Tab mới"
                >
                  <div
                    className={`w-14 h-14 rounded-2xl flex items-center justify-center text-white flex-shrink-0 bg-gradient-to-b ${
                      isSubjectToAppraisal 
                        ? "from-orange-500 to-orange-700 shadow-[0_4px_0_0_#9A3412,0_4px_10px_rgba(0,0,0,0.18)]" 
                        : "from-emerald-500 to-emerald-700 shadow-[0_4px_0_0_#047857,0_4px_10px_rgba(0,0,0,0.18)]"
                    }`}
                  >
                    {isSubjectToAppraisal ? (
                      <XCircle className="w-8 h-8" />
                    ) : (
                      <CheckCircle className="w-8 h-8" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-display font-black text-[20px] uppercase tracking-tight">
                      {isSubjectToAppraisal
                        ? "BẮT BUỘC THẨM DUYỆT THIẾT KẾ PHÒNG CHÁY CHỮA CHÁY"
                        : "KHÔNG THUỘC DIỆN THẨM DUYỆT THIẾT KẾ PCCC BỞI CƠ QUAN CÔNG AN"}
                    </h3>
                    <p className="text-xs mt-1.5 opacity-90 leading-relaxed font-sans font-bold text-black font-semibold">
                      {appraisalReason}
                    </p>
                  </div>
                </div>

                {/* Important legislative notices */}
                <div id="verdict-legislative-notices" className="bg-white border-2 border-slate-350 rounded-xl p-5 space-y-3 shadow-md">
                  <h4 className="font-display font-black text-[#6B0D0D] text-[18px] flex items-center gap-2 uppercase tracking-tight">
                    <div className="w-6 h-6 rounded-lg bg-gradient-to-b from-red-500 to-red-700 flex items-center justify-center text-white shadow-[0_2.5px_0_0_#3B0707,0_2.5px_5px_rgba(0,0,0,0.15)] shrink-0">
                      <Info className="w-3.5 h-3.5" />
                    </div>
                    Lưu ý Pháp lý Quan trọng (Nghị định 105/2025/NĐ-CP):
                  </h4>
                  <p className="text-xs text-black font-bold leading-relaxed">
                    Theo quy định mới tại <strong className="font-black text-black decoration-brand-orange underline">Phụ lục III - Nghị định 105/2025/NĐ-CP</strong>, nhà ở hỗn hợp hoặc nhà ở riêng lẻ có kết hợp mục đích kinh doanh (nằm trong nhóm F1.4) chỉ thuộc diện thẩm duyệt bắt buộc khi đạt ngưỡng quy mô tối thiểu là <strong className="font-black text-black">cao từ 7 tầng nổi trở lên</strong> hoặc <strong className="font-black text-black">tổng diện tích sàn xây dựng từ 3.000 m² trở lên</strong>. 
                  </p>
                  <p className="text-xs text-black font-semibold leading-relaxed">
                    {isSubjectToAppraisal ? (
                      <span className="text-red-750 font-black mb-1 block">
                        ➔ Hiện tại, công trình của bạn ĐẠT HOẶC VƯỢT một trong các ngưỡng pháp lý trên, do đó chủ đầu tư bắt buộc phải chuẩn bị đầy đủ hồ sơ thiết kế kỹ thuật PCCC để đệ trình cơ quan Cảnh sát PCCC chuyên môn phê duyệt trước khi thi công.
                      </span>
                    ) : (
                      <span className="text-emerald-800 font-black mb-1 block">
                        ➔ Công trình của bạn nằm dưới ngưỡng quy phạm trên nên không cần nộp hồ sơ thẩm duyệt cho công an. Tuy nhiên, Điều 20 Nghị định khẳng định chủ đầu tư vẫn hoàn toàn tự chịu trách nhiệm pháp lý thiết kế, xây dựng đạt đầy đủ quy phạm QCVN 06:2022/BXD và QCVN 10:2025/BCA. Hồ sơ PCCC phải lập để Ủy ban Nhân dân và Công an xã/phường kiểm tra định kỳ 3 năm một lần.
                      </span>
                    )}
                  </p>
                </div>

                {/* Distribution of Checklist Results Pie Chart Card */}
                <div id="verdict-pie-chart-card" className="bg-white border-2 border-slate-350 rounded-xl p-5 shadow-lg space-y-4">
                  {/* Card Header with Visibility Toggle */}
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3 flex-wrap gap-2">
                    <div>
                      <h4 className="font-display font-black text-slate-900 text-sm uppercase tracking-tight flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-brand-orange animate-pulse" />
                        Phân bố 17 Hạng mục rà soát
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Tỷ lệ trạng thái an toàn quy chuẩn của dự án: <span className="font-bold text-slate-600">{projectInfo.name || "hiện tại"}</span>
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => setIsLegendVisible(!isLegendVisible)}
                      className="px-2.5 py-1.5 text-[11px] font-black text-[#EA580C] hover:text-white bg-orange-50 hover:bg-[#EA580C] border border-[#EA580C]/85 rounded-lg transition-all flex items-center gap-1.5 shadow-sm active:scale-95 cursor-pointer select-none"
                      title={isLegendVisible ? "Chân dung biểu đồ rộng" : "Kèm danh sách chỉ số chi tiết"}
                    >
                      {isLegendVisible ? (
                        <>
                          <EyeOff className="w-3.5 h-3.5" />
                          <span>Chỉ Xem Biểu Đồ</span>
                        </>
                      ) : (
                        <>
                          <Eye className="w-3.5 h-3.5" />
                          <span>Xem Biểu Đồ &amp; Chỉ Số</span>
                        </>
                      )}
                    </button>
                  </div>

                  <div id="verdict-pie-chart-row" className="flex flex-col md:flex-row items-center gap-6">
                    {/* Left Column: Chart */}
                    <div className={`w-full ${isLegendVisible ? "md:w-1/2" : "max-w-md mx-auto"} h-64 relative flex items-center justify-center transition-all duration-300`}>
                      <ResponsiveContainer width="100%" height={240}>
                        <PieChart>
                          <Pie
                            data={[
                              { name: "Đạt / Không bắt buộc", value: checklist.filter(item => item.result === "Đạt" || item.result === "Không bắt buộc").length, color: "#10B981" },
                              { name: "Không đạt", value: checklist.filter(item => item.result === "Không đạt").length, color: "#F43F5E" },
                              { name: "Cần xem xét", value: checklist.filter(item => item.result === "Khuyến nghị mạnh" || item.result === "Khuyến nghị" || item.result === "Cần xem xét").length, color: "#F59E0B" },
                              { name: "Cần đo đạc", value: checklist.filter(item => item.result === "Cần đo đạc").length, color: "#06B6D4" }
                            ].filter(c => c.value > 0)}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={90}
                            paddingAngle={3}
                            dataKey="value"
                          >
                            {[
                              { name: "Đạt / Không bắt buộc", value: checklist.filter(item => item.result === "Đạt" || item.result === "Không bắt buộc").length, color: "#10B981" },
                              { name: "Không đạt", value: checklist.filter(item => item.result === "Không đạt").length, color: "#F43F5E" },
                              { name: "Cần xem xét", value: checklist.filter(item => item.result === "Khuyến nghị mạnh" || item.result === "Khuyến nghị" || item.result === "Cần xem xét").length, color: "#F59E0B" },
                              { name: "Cần đo đạc", value: checklist.filter(item => item.result === "Cần đo đạc").length, color: "#06B6D4" }
                            ].filter(c => c.value > 0).map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip 
                            formatter={(value: any, name: any) => [`${value} hạng mục`, name]}
                            contentStyle={{ backgroundColor: "#F8FAFC", borderRadius: "12px", border: "1px solid #CBD5E1", fontSize: "12px", fontWeight: "bold" }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                      {/* Centered Total Indicator */}
                      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-2xl font-black text-slate-800 font-mono">
                          {checklist.length}
                        </span>
                        <span className="text-[10px] uppercase font-black text-slate-450 tracking-wider">
                          Hạng mục
                        </span>
                      </div>
                    </div>

                    {/* Right Column: Breakdown List with styled badges */}
                    {isLegendVisible && (
                      <div className="w-full md:w-1/2 space-y-4">
                        <div>
                          <h4 className="font-display font-black text-slate-900 text-sm uppercase tracking-tight">
                            Tỉ lệ phân bố đánh giá
                          </h4>
                          <p className="text-[11px] text-slate-400 mt-0.5">
                            Tổng hợp kết quả rà soát 17 hạng mục của dự án
                          </p>
                        </div>

                        <div className="space-y-2">
                          {/* Đạt */}
                          {(() => {
                            const count = checklist.filter(item => item.result === "Đạt" || item.result === "Không bắt buộc").length;
                            const pct = Math.round((count / checklist.length) * 100) || 0;
                            return (
                              <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-50/50 border border-emerald-100 hover:bg-emerald-50 transition-colors">
                                <div className="flex items-center gap-2">
                                  <span className="w-3 h-3 rounded-full bg-emerald-500 shrink-0" />
                                  <span className="text-xs font-black text-emerald-800">Đạt &amp; Không bắt buộc</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono font-black text-emerald-700">{count} hạng mục</span>
                                  <span className="text-xs font-mono font-black bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded">{pct}%</span>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Không đạt */}
                          {(() => {
                            const count = checklist.filter(item => item.result === "Không đạt").length;
                            const pct = Math.round((count / checklist.length) * 100) || 0;
                            return (
                              <div className="flex items-center justify-between p-2 rounded-lg bg-rose-50/50 border border-rose-100 hover:bg-rose-50 transition-colors">
                                <div className="flex items-center gap-2">
                                  <span className="w-3 h-3 rounded-full bg-rose-500 shrink-0" />
                                  <span className="text-xs font-black text-rose-800">Không đạt</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono font-black text-rose-700">{count} hạng mục</span>
                                  <span className="text-xs font-mono font-black bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded">{pct}%</span>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Cần xem xét */}
                          {(() => {
                            const count = checklist.filter(item => item.result === "Khuyến nghị mạnh" || item.result === "Khuyến nghị" || item.result === "Cần xem xét").length;
                            const pct = Math.round((count / checklist.length) * 100) || 0;
                            return (
                              <div className="flex items-center justify-between p-2 rounded-lg bg-amber-50/50 border border-amber-100 hover:bg-amber-50 transition-colors">
                                <div className="flex items-center gap-2">
                                  <span className="w-3 h-3 rounded-full bg-amber-500 shrink-0" />
                                  <span className="text-xs font-black text-amber-800">Cần xem xét &amp; Khuyến nghị</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono font-black text-amber-700">{count} hạng mục</span>
                                  <span className="text-xs font-mono font-black bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">{pct}%</span>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Cần đo đạc */}
                          {(() => {
                            const count = checklist.filter(item => item.result === "Cần đo đạc").length;
                            const pct = Math.round((count / checklist.length) * 100) || 0;
                            return (
                              <div className="flex items-center justify-between p-2 rounded-lg bg-cyan-50/50 border border-cyan-100 hover:bg-cyan-50 transition-colors">
                                <div className="flex items-center gap-2">
                                  <span className="w-3 h-3 rounded-full bg-cyan-500 shrink-0" />
                                  <span className="text-xs font-black text-cyan-800">Cần đo đạc bổ sung</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono font-black text-cyan-700">{count} hạng mục</span>
                                  <span className="text-xs font-mono font-black bg-cyan-100 text-cyan-800 px-1.5 py-0.5 rounded">{pct}%</span>
                                </div>
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Core regulatory checklist summary charts or indicators */}
                <div id="verdict-summary-cards" className="grid grid-cols-2 gap-4">
                  <div className="bg-white border-2 border-slate-350 rounded-xl p-4 space-y-1.5 text-xs shadow-sm">
                    <span className="text-black font-black font-display uppercase tracking-wider text-[10px]">Bậc chịu lửa yêu cầu xây dựng:</span>
                    <p className="text-black font-black text-sm">
                      {projectInfo.floors <= 4 ? "Bậc III (Tối thiểu theo Phụ lục H QCVN 06:2022)" : "Bậc II (Bản thiết kế cao tầng)"}
                    </p>
                  </div>
                  <div className="bg-white border-2 border-slate-350 rounded-xl p-4 space-y-1.5 text-xs shadow-sm">
                    <span className="text-black font-black font-display uppercase tracking-wider text-[10px]">Công năng nguy hiểm cháy:</span>
                    <p className="text-black font-black text-sm">
                      F1.4 (Nhà ở riêng lẻ, nhà hỗn hợp kinh doanh)
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3.5: EXPANDED FULL LEGAL VERDICT PAGE */}
        {(activeTab === "verdict" || activeTab === "full-verdict") && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-3 sm:p-5 select-none print:static print:bg-white print:p-0 print:z-0 print:block animate-fade-in">
            <div className="bg-white w-full max-w-7xl h-[92vh] rounded-2xl flex flex-col overflow-hidden shadow-2xl border border-slate-350 select-text animate-scale-up print:w-full print:h-auto print:shadow-none print:rounded-none print:overflow-visible print:block">
              {/* Modal Header */}
              <div className="sticky top-0 bg-slate-50 border-b border-slate-205 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 z-10 shrink-0 print:hidden">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-orange-100 flex items-center justify-center text-brand-orange shadow-sm shrink-0">
                    <Award className="w-5 h-5 text-brand-orange animate-pulse" />
                  </div>
                  <div>
                    <h3 className="font-display font-black text-slate-900 text-base md:text-lg uppercase tracking-tight">
                      Kết luận pháp lý PCCC công trình
                    </h3>
                    <p className="text-[11px] text-slate-500 font-semibold uppercase font-mono tracking-wider">
                      Đánh giá theo Nghị định 105/2025/NĐ-CP &amp; QCVN 06:2022
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={onExportReportPdf}
                    disabled={isExportingPdf || checklist.length === 0 || hasAreaContradiction}
                    className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-extrabold px-3 py-2 rounded-xl text-xs shadow-md transition-all active:scale-95 cursor-pointer"
                  >
                    <FileDown className="w-3.5 h-3.5" />
                    In báo cáo PDF {isExportingPdf && "..."}
                  </button>
                  <button
                    onClick={() => setActiveTab("chat")}
                    className="flex items-center gap-1.5 bg-rose-500 hover:bg-rose-600 text-white font-black px-4 py-2 rounded-xl text-xs transition-all shadow-md active:scale-95 cursor-pointer ml-1"
                    title="Quay lại Chat chính (ESC)"
                  >
                    <XCircle className="w-4 h-4" />
                    Đóng (X)
                  </button>
                </div>
              </div>

              {/* Modal Body with vertical scrolling */}
              <div id="full-verdict-tab-content" className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin bg-white print:overflow-visible print:p-0 print:m-0 print:bg-white print:h-auto">
            {checklist.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                <Award className="w-16 h-16 text-slate-300 stroke-[1.5]" />
                <div>
                  <h3 className="font-semibold text-slate-755">Chưa có kết quả</h3>
                  <p className="text-slate-400 text-sm max-w-sm mx-auto mt-1">
                    Vui lòng cung cấp đầy đủ thông tin hoặc chat với chuyên gia để nhận diện tính pháp lý của hồ sơ.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-6 animate-fade-in">
                {/* Print Only Header */}
                <div className="hidden print:flex flex-col border-b-2 border-slate-900 pb-3 mb-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h1 className="font-display font-black text-lg text-slate-900 uppercase">
                        BÁO CÁO PHÁP LÝ THẨM DUYỆT PCCC (NGHỊ ĐỊNH 105/2025/NĐ-CP)
                      </h1>
                      <p className="text-[10px] font-mono font-bold text-slate-500 uppercase mt-0.5">
                        Chương Trình Thẩm Định Chuyên Gia Phòng Cháy Chữa Cháy Tự Động
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-[9px] font-mono font-bold bg-slate-100 border border-slate-300 px-2 py-0.5 rounded">
                        NGÀY IN: {new Date().toLocaleDateString("vi-VN")}
                      </span>
                    </div>
                  </div>
                  
                  {/* Project metadata row */}
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1 mt-3 pt-2.5 border-t border-dashed border-slate-300 text-[10.5px] text-slate-700">
                    <div>
                      <strong className="text-slate-900">Tên công trình:</strong> {projectInfo.name || "Chưa đặt tên"}
                    </div>
                    <div>
                      <strong className="text-slate-900">Địa điểm:</strong> {projectInfo.location || "Chưa rõ"}
                    </div>
                    <div>
                      <strong className="text-slate-900">Quy mô tầng:</strong> {projectInfo.floors} tầng nổi {projectInfo.basements && Number(projectInfo.basements) > 0 ? `/ ${projectInfo.basements} hầm` : ""}
                    </div>
                    <div>
                      <strong className="text-slate-900">Tổng diện tích xây dựng:</strong> {projectInfo.totalFloorArea || projectInfo.floorArea} m²
                    </div>
                  </div>
                </div>



                <div id="full-verdict-grid" className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Left area: big result badge */}
                  <div id="full-verdict-left-column" className="lg:col-span-2 space-y-6">
                    <div
                      id="full-verdict-badge-card"
                      className={`p-8 rounded-3xl border-2 flex flex-col md:flex-row items-start md:items-center gap-6 transition-all duration-200 ${
                        isSubjectToAppraisal
                          ? "bg-gradient-to-b from-orange-50 to-orange-100 border-orange-355 text-orange-950 shadow-[0_5px_0_0_#EA580C,0_8px_20px_rgba(234,88,12,0.15)]"
                          : "bg-gradient-to-b from-emerald-50 to-emerald-100 border-emerald-355 text-emerald-950 shadow-[0_5px_0_0_#059669,0_8px_20px_rgba(5,150,105,0.15)]"
                      }`}
                    >
                      <div
                        className={`w-16 h-16 rounded-3xl flex items-center justify-center text-white flex-shrink-0 bg-gradient-to-b ${
                          isSubjectToAppraisal 
                            ? "from-orange-500 to-orange-700 shadow-[0_4px_0_0_#9A3412,0_4px_10px_rgba(0,0,0,0.18)]" 
                            : "from-emerald-500 to-emerald-700 shadow-[0_4px_0_0_#047857,0_4px_10px_rgba(0,0,0,0.18)]"
                        }`}
                      >
                        {isSubjectToAppraisal ? (
                          <XCircle className="w-10 h-10" />
                        ) : (
                          <CheckCircle className="w-10 h-10" />
                        )}
                      </div>
                      <div>
                        <span className="text-[10px] md:text-[11px] font-black uppercase text-slate-500 tracking-wider">Trạng thái rà soát quy chuẩn</span>
                        <h2 className="font-display font-black text-[22px] md:text-[25px] uppercase tracking-tight mt-1 leading-tight">
                          {isSubjectToAppraisal
                            ? "BẮT BUỘC THẨM DUYỆT THIẾT KẾ PHÒNG CHÁY CHỮA CHÁY"
                            : "KHÔNG THUỘC DIỆN THẨM DUYỆT THIẾT KẾ PCCC BỞI CƠ QUAN CÔNG AN"}
                        </h2>
                        <p className="text-sm mt-2 opacity-95 leading-relaxed font-sans font-bold text-black border-t border-black/15 pt-2">
                          {appraisalReason}
                        </p>
                      </div>
                    </div>

                    {/* Important legislative notices expanded layout */}
                    <div id="full-verdict-legislative-notices" className="bg-white border-2 border-slate-350 rounded-2xl p-6 space-y-4 shadow-lg flex-1">
                      <h4 className="font-display font-black text-[#6B0D0D] text-[20px] flex items-center gap-2 uppercase tracking-tight">
                        <div className="w-7 h-7 rounded-lg bg-gradient-to-b from-red-500 to-red-700 flex items-center justify-center text-white shadow-[0_2.5px_0_0_#3B0707,0_2.5px_5px_rgba(0,0,0,0.15)] shrink-0">
                          <Info className="w-4 h-4" />
                        </div>
                        Lưu ý Pháp lý Quan trọng (Nghị định 105/2025/NĐ-CP):
                      </h4>
                      <p className="text-sm text-black font-semibold leading-relaxed">
                        Theo quy định mới nhất tại <strong className="font-black text-black decoration-brand-orange underline">Phụ lục III - Nghị định 105/2025/NĐ-CP</strong>, nhà ở hỗn hợp hoặc nhà ở riêng lẻ có kết hợp mục đích kinh doanh (nằm trong nhóm F1.4) chỉ thuộc diện thẩm duyệt bắt buộc khi đạt một trong các ngưỡng quy mô tối thiểu sau:
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 rounded-xl border-2 border-dashed border-orange-355 bg-orange-50/50 space-y-1">
                          <span className="text-xs font-black text-orange-950 uppercase">Ngưỡng Số Tầng Nổi:</span>
                          <p className="text-black font-black text-sm">Chiều cao từ 7 tầng nổi trở lên</p>
                          <span className="text-xs text-orange-850 font-bold block">
                            (Công trình của bạn: {projectInfo.floors} tầng)
                          </span>
                        </div>
                        <div className="p-4 rounded-xl border-2 border-dashed border-orange-355 bg-orange-50/50 space-y-1">
                          <span className="text-xs font-black text-orange-950 uppercase">Ngưỡng Diện Tích Sàn:</span>
                          <p className="text-black font-black text-sm">Tổng diện tích từ 3.000 m² trở lên</p>
                          <span className="text-xs text-orange-850 font-bold block">
                            (Công trình của bạn: {projectInfo.totalFloorArea} m²)
                          </span>
                        </div>
                      </div>

                      <p className="text-sm text-black font-bold leading-relaxed pt-2 border-t border-slate-200">
                        {isSubjectToAppraisal ? (
                          <span className="text-red-750 font-black flex items-start gap-2">
                            <span className="shrink-0 text-lg">➔</span> 
                            Hiện tại, công trình của bạn ĐẠT HOẶC VƯỢT một trong các ngưỡng pháp lý trên, do đó chủ đầu tư bắt buộc phải chuẩn bị đầy đủ hồ sơ thiết kế kỹ thuật PCCC để đệ trình cơ quan Cảnh sát PCCC chuyên môn phê duyệt trước khi thi công lắp đặt và khai thác.
                          </span>
                        ) : (
                          <span className="text-emerald-800 font-black flex items-start gap-2">
                            <span className="shrink-0 text-lg">➔</span> 
                            Công trình của bạn nằm dưới cả hai ngưỡng quy phạm trên nên không cần nộp hồ sơ thẩm duyệt cho công an quận huyện hay thành phố. Tuy nhiên, căn cứ Điều 20 Nghị định khẳng định chủ đầu tư vẫn hoàn toàn tự chịu trách nhiệm pháp lý thiết kế, xây dựng đạt đầy đủ quy phạm QCVN 06:2022/BXD và QCVN 10:2025/BCA. Hồ sơ PCCC phải lập để Ủy ban Nhân dân và Công an xã/phường kiểm tra định kỳ định khoản 3 năm một lần.
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Right area: Pie chart and statistics */}
                  <div id="full-verdict-right-column" className="space-y-6">
                    {/* Pie Chart Panel */}
                    <div id="full-verdict-pie-chart-card" className="bg-white border-2 border-slate-350 rounded-2xl p-5 shadow-lg space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-200 pb-3 flex-wrap gap-2">
                        <div className="text-left">
                          <h4 className="font-display font-black text-slate-900 text-sm uppercase tracking-tight">
                            Phân bố 17 Hạng mục rà soát
                          </h4>
                          <p className="text-[11px] text-slate-400 mt-0.5">
                            Tỷ lệ trạng thái an toàn quy chuẩn
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={() => setIsLegendVisible(!isLegendVisible)}
                          className="px-2.5 py-1.5 text-[11px] font-black text-[#EA580C] hover:text-white bg-orange-50 hover:bg-[#EA580C] border border-[#EA580C]/85 rounded-lg transition-all flex items-center gap-1.5 shadow-sm active:scale-95 cursor-pointer select-none"
                          title={isLegendVisible ? "Hiển thị chỉ biểu đồ" : "Hiển thị biểu đồ và các chỉ số"}
                        >
                          {isLegendVisible ? (
                            <>
                              <EyeOff className="w-3.5 h-3.5" />
                              <span>Chỉ Xem Biểu Đồ</span>
                            </>
                          ) : (
                            <>
                              <Eye className="w-3.5 h-3.5" />
                              <span>Xem Biểu Đồ &amp; Chỉ Số</span>
                            </>
                          )}
                        </button>
                      </div>

                      <div className={`h-48 relative flex items-center justify-center transition-all duration-300 ${!isLegendVisible ? "max-w-md mx-auto" : ""}`}>
                        <ResponsiveContainer width="100%" height={180}>
                          <PieChart>
                            <Pie
                              data={[
                                { name: "Đạt / Không bắt buộc", value: checklist.filter(item => item.result === "Đạt" || item.result === "Không bắt buộc").length, color: "#10B981" },
                                { name: "Không đạt", value: checklist.filter(item => item.result === "Không đạt").length, color: "#F43F5E" },
                                { name: "Cần xem xét", value: checklist.filter(item => item.result === "Khuyến nghị mạnh" || item.result === "Khuyến nghị" || item.result === "Cần xem xét").length, color: "#F59E0B" },
                                { name: "Cần đo đạc", value: checklist.filter(item => item.result === "Cần đo đạc").length, color: "#06B6D4" }
                              ].filter(c => c.value > 0)}
                              cx="50%"
                              cy="50%"
                              innerRadius={45}
                              outerRadius={70}
                              paddingAngle={3}
                              dataKey="value"
                              labelLine={false}
                              label={(props: any) => {
                                const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props;
                                if (percent <= 0.05) return null;
                                const RADIAN = Math.PI / 180;
                                const radius = (innerRadius || 0) + ((outerRadius || 0) - (innerRadius || 0)) * 0.45;
                                const x = (cx || 0) + radius * Math.cos(-midAngle * RADIAN);
                                const y = (cy || 0) + radius * Math.sin(-midAngle * RADIAN);
                                return (
                                  <text
                                    x={x}
                                    y={y}
                                    fill="white"
                                    textAnchor="middle"
                                    dominantBaseline="central"
                                    className="text-[10px] font-black font-mono"
                                  >
                                    {`${(percent * 100).toFixed(0)}%`}
                                  </text>
                                );
                              }}
                            >
                              {[
                                { name: "Đạt / Không bắt buộc", value: checklist.filter(item => item.result === "Đạt" || item.result === "Không bắt buộc").length, color: "#10B981" },
                                { name: "Không đạt", value: checklist.filter(item => item.result === "Không đạt").length, color: "#F43F5E" },
                                { name: "Cần xem xét", value: checklist.filter(item => item.result === "Khuyến nghị mạnh" || item.result === "Khuyến nghị" || item.result === "Cần xem xét").length, color: "#F59E0B" },
                                { name: "Cần đo đạc", value: checklist.filter(item => item.result === "Cần đo đạc").length, color: "#06B6D4" }
                              ].filter(c => c.value > 0).map((entry, index) => (
                                <Cell key={`cell-expanded-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip 
                              formatter={(value: any, name: any) => [`${value} hạng mục`, name]}
                              contentStyle={{ backgroundColor: "#F8FAFC", borderRadius: "12px", fontSize: "11px", fontWeight: "bold" }}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                        {/* Centered Total Indicator */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                          <span className="text-xl font-black text-slate-800 font-mono">
                            {checklist.length}
                          </span>
                          <span className="text-[9px] uppercase font-black text-slate-400">
                            Hạng mục
                          </span>
                        </div>
                      </div>

                      {isLegendVisible && (() => {
                        const total = checklist.length;
                        const datCount = checklist.filter(item => item.result === "Đạt" || item.result === "Không bắt buộc").length;
                        const khongDatCount = checklist.filter(item => item.result === "Không đạt").length;
                        const xemSetCount = checklist.filter(item => item.result === "Khuyến nghị mạnh" || item.result === "Khuyến nghị" || item.result === "Cần xem xét").length;
                        // FIX B16 (Bao_Cao_QA_Lan_3.md — Trung bình): chú giải
                        // trước đây thiếu hẳn dòng "Cần đo đạc" — biểu đồ tròn
                        // (data ở trên) đã có đủ 4 phần, nhưng phần chú giải
                        // văn bản chỉ liệt kê 3/4 nhóm nên chỉ cộng ra 15/17.
                        // Thêm biến đếm + dòng chú giải thứ 4 để khớp đủ.
                        const canDoDacCount = checklist.filter(item => item.result === "Cần đo đạc").length;

                        const datPct = total > 0 ? Math.round((datCount / total) * 100) : 0;
                        const khongDatPct = total > 0 ? Math.round((khongDatCount / total) * 100) : 0;
                        const xemSetPct = total > 0 ? Math.round((xemSetCount / total) * 100) : 0;
                        const canDoDacPct = total > 0 ? Math.round((canDoDacCount / total) * 100) : 0;

                        return (
                          <div className="space-y-1.5 pt-2 border-t border-slate-100">
                            {/* Đạt */}
                            <div className="flex items-center justify-between text-xs py-1">
                              <span className="text-slate-600 font-bold">Đạt &amp; Không bắt buộc:</span>
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-black text-emerald-600">
                                  {datCount} / {total} Hạng mục
                                </span>
                                <span className="font-mono font-black bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded text-[10px]">
                                  {datPct}%
                                </span>
                              </div>
                            </div>
                            {/* Không đạt */}
                            <div className="flex items-center justify-between text-xs py-1">
                              <span className="text-slate-600 font-bold">Không đạt:</span>
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-black text-rose-600">
                                  {khongDatCount} / {total} Hạng mục
                                </span>
                                <span className="font-mono font-black bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded text-[10px]">
                                  {khongDatPct}%
                                </span>
                              </div>
                            </div>
                            {/* Khác */}
                            <div className="flex items-center justify-between text-xs py-1">
                              <span className="text-slate-600 font-bold">Cần xem xét bổ sung:</span>
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-black text-amber-600">
                                  {xemSetCount} / {total} Hạng mục
                                </span>
                                <span className="font-mono font-black bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded text-[10px]">
                                  {xemSetPct}%
                                </span>
                              </div>
                            </div>
                            {/* FIX B16: dòng chú giải thứ 4 còn thiếu — Cần đo đạc */}
                            <div className="flex items-center justify-between text-xs py-1">
                              <span className="text-slate-600 font-bold">Cần đo đạc:</span>
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-black text-cyan-600">
                                  {canDoDacCount} / {total} Hạng mục
                                </span>
                                <span className="font-mono font-black bg-cyan-100 text-cyan-800 px-1.5 py-0.5 rounded text-[10px]">
                                  {canDoDacPct}%
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })()}
                    </div>

                    {/* Metadata & Requirements Grid Card */}
                    <div id="full-verdict-metadata-card" className="bg-slate-100 border border-slate-300 rounded-2xl p-5 space-y-3.5 shadow">
                      <h4 className="font-display font-black text-slate-900 text-sm uppercase tracking-tight pb-2 border-b border-slate-300">
                        Thông số kỹ thuật công trình
                      </h4>
                      {/* FIX B14 (Bao_Cao_QA_Lan_3.md — Cao): bảng này trước
                          đây có 3 lỗi: (a) nhãn "Tổng Diện tích xây dựng" nhưng
                          hiện giá trị totalFloorArea (nhầm với floorArea);
                          (b) "Chiều cao số tầng" là nhãn gộp sai — giá trị thật
                          là SỐ TẦNG, còn chiều cao PCCC không hiện ở đâu cả;
                          (c) "Bậc chịu lửa thiết kế tối thiểu" bị HARDCODE
                          theo floors<=4 (luôn suy ra Bậc II/III), HOÀN TOÀN
                          bỏ qua giá trị fireRating thật đã khai báo — mâu
                          thuẫn trực tiếp với mục 2 của bảng 17 hạng mục.
                          Đồng thời sửa luôn dòng "Phân nhóm công năng" vốn
                          cũng hardcode cứng "F1.4" bất kể loại công trình
                          thật (lỗi cùng bản chất với B12 ở tầng hiển thị). */}
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between py-1">
                          <span className="text-slate-500 font-bold">Tên hồ sơ rà soát:</span>
                          <span className="text-slate-800 font-black">{projectInfo.name || "Chưa đặt tên"}</span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-slate-500 font-bold">Diện tích xây dựng (1 tầng):</span>
                          <span className="text-slate-800 font-black">
                            {projectInfo.floorArea ? `${projectInfo.floorArea} m²` : "Chưa nhập"}
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-slate-500 font-bold">Tổng diện tích sàn:</span>
                          <span className="text-slate-800 font-black">
                            {projectInfo.totalFloorArea ? `${projectInfo.totalFloorArea} m²` : "Chưa nhập"}
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-slate-500 font-bold">Số tầng nổi / hầm:</span>
                          <span className="text-slate-800 font-black">
                            {projectInfo.floors || 0} tầng nổi{projectInfo.basements ? ` / ${projectInfo.basements} tầng hầm` : ""}
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-slate-500 font-bold">Chiều cao PCCC:</span>
                          <span className="text-slate-800 font-black">
                            {projectInfo.pcccHeight || projectInfo.height ? `${projectInfo.pcccHeight || projectInfo.height} m` : "Chưa nhập"}
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-slate-500 font-bold">Bậc chịu lửa đã khai báo:</span>
                          <span className="text-slate-800 font-black">
                            {projectInfo.fireRating || "Chưa chọn"}
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-slate-500 font-bold">Loại công trình / Công năng:</span>
                          <span className="text-slate-800 font-black text-right ml-2">
                            {projectInfo.type || "Chưa xác định"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            </div>

          </div>
        </div>
      )}
      </div>
    </div>
  );
}

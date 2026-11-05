import React from "react";
import { Menu, X } from "lucide-react";
import { ActiveTab } from "../../types";
import { useMobileMenu } from "../hooks/useMobileMenu";
import { MobileActionsList } from "./MobileActionsList";

export interface MobileHeaderMenuProps {
  activeTab: ActiveTab;
  onChangeTab: (tab: ActiveTab) => void;
  onOpenOcrUpload: () => void;
  onTriggerAppraisal: () => void;
  isPending: boolean;
  hasAreaContradiction?: boolean;
  hasChecklist?: boolean;
  reviewState: "draft" | "reviewed";
  onExportDocx: () => void;
  onExportPdf: () => void;
  onExportJson: () => void;
  isExportingDocx: boolean;
  isExportingPdf: boolean;
  isExportingJson: boolean;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export const MobileHeaderMenu: React.FC<MobileHeaderMenuProps> = ({
  activeTab,
  onChangeTab,
  onOpenOcrUpload,
  onTriggerAppraisal,
  isPending,
  hasAreaContradiction = false,
  hasChecklist = false,
  reviewState,
  onExportDocx,
  onExportPdf,
  onExportJson,
  isExportingDocx,
  isExportingPdf,
  isExportingJson,
  theme,
  onToggleTheme,
}) => {
  const { isOpen, handleClose, handleToggle, menuRef } = useMobileMenu();

  return (
    <div className="relative md:hidden shrink-0" ref={menuRef}>
      {/* Nút bấm 3 gạch (Hamburger) trên mobile */}
      <button
        id="btn-mobile-menu"
        data-testid="btn-mobile-menu"
        type="button"
        onClick={handleToggle}
        aria-label={isOpen ? "Đóng menu thao tác" : "Mở menu thao tác"}
        aria-expanded={isOpen}
        className="p-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer shadow-xs shrink-0 transition-colors"
      >
        {isOpen ? <X className="w-5 h-5 text-slate-700 dark:text-slate-200" /> : <Menu className="w-5 h-5 text-slate-700 dark:text-slate-200" />}
      </button>

      {/* Menu dropdown hiển thị full options khi bấm vào 3 gạch */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-xs z-40 transition-opacity"
            onClick={handleClose}
            aria-hidden="true"
          />
          <div
            data-testid="mobile-actions-panel"
            className="fixed top-14 left-2 right-2 max-w-sm ml-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl z-50 p-3.5 space-y-3 overflow-y-auto max-h-[calc(100vh-4.5rem)] animate-in fade-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-xs font-bold text-slate-800 dark:text-slate-100">Menu thao tác PCCC</span>
              <button
                type="button"
                onClick={handleClose}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg cursor-pointer"
                aria-label="Đóng menu"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <MobileActionsList
              activeTab={activeTab}
              onChangeTab={onChangeTab}
              onOpenOcrUpload={onOpenOcrUpload}
              onTriggerAppraisal={onTriggerAppraisal}
              isPending={isPending}
              hasAreaContradiction={hasAreaContradiction}
              hasChecklist={hasChecklist}
              reviewState={reviewState}
              onExportDocx={onExportDocx}
              onExportPdf={onExportPdf}
              onExportJson={onExportJson}
              isExportingDocx={isExportingDocx}
              isExportingPdf={isExportingPdf}
              isExportingJson={isExportingJson}
              theme={theme}
              onToggleTheme={onToggleTheme}
              onClose={handleClose}
            />
          </div>
        </>
      )}
    </div>
  );
};


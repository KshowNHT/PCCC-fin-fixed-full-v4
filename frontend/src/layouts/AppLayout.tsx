import React from "react";
import { ActiveTab } from "../types";

interface AppLayoutProps {
  sidebar: React.ReactNode;
  header: React.ReactNode;
  warningBanner?: React.ReactNode;
  activeTab: ActiveTab;
  chatContent: React.ReactNode;
  checklistContent: React.ReactNode;
  verdictContent: React.ReactNode;
  specsDrawer: React.ReactNode;
  modals: React.ReactNode;
  mobileBottomNav?: React.ReactNode;
  isSidebarOpen: boolean;
  onCloseSidebarMobile: () => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  sidebar,
  header,
  warningBanner,
  activeTab,
  chatContent,
  checklistContent,
  verdictContent,
  specsDrawer,
  modals,
  mobileBottomNav,
  isSidebarOpen,
  onCloseSidebarMobile,
}) => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-100 antialiased relative">
      {sidebar}

      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden transition-opacity cursor-pointer"
          onClick={onCloseSidebarMobile}
        />
      )}

      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-slate-50 dark:bg-slate-900 relative">
        {header}
        {warningBanner}

        <div className="flex-1 overflow-hidden relative flex flex-col">
          {activeTab === "chat" && chatContent}
          {activeTab === "checklist" && checklistContent}
          {activeTab === "verdict" && verdictContent}
        </div>

        {mobileBottomNav}
      </main>

      {specsDrawer}
      {modals}
    </div>
  );
};

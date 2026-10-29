import React, { useState, useEffect } from "react";
import { AppLayout } from "./layouts/AppLayout";
import { AppSidebar } from "./layouts/AppSidebar";
import { AppHeader } from "./layouts/AppHeader";
import { MobileBottomNav } from "./layouts/MobileBottomNav";
import { ChatView } from "./features/chat/components/ChatView";
import { ComplianceChecklistView } from "./features/compliance/components/ComplianceChecklistView";
import { LegalBasisTabWrapper } from "./features/compliance/components/LegalBasisTabWrapper";
import { AreaWarningBanner } from "./features/compliance/components/AreaWarningBanner";
import { ProjectSpecsDrawer } from "./features/project-specs/components/ProjectSpecsDrawer";
import { AppModals } from "./components/AppModals";
import { Login } from "./components/Login";
import { DevToolsWarningOverlay } from "./components/DevToolsWarningOverlay";
import { useAppAuth } from "./hooks/useAppAuth";
import { useAppSessions } from "./hooks/useAppSessions";
import { useAppDocuments } from "./hooks/useAppDocuments";
import { useAppExport } from "./hooks/useAppExport";
import { useProjectWarnings } from "./hooks/useProjectWarnings";
import { useTheme } from "./hooks/useTheme";
import { ActiveTab, EMPTY_PROJECT, ProjectInfo } from "./types";

export default function App() {
  const [errorMessage, setErrorMessage] = useState("");
  const { theme, toggleTheme } = useTheme();
  const { currentUser, authChecked, isDevToolsOpen, handleLogout } = useAppAuth();
  const sessionCtrl = useAppSessions(setErrorMessage);
  const docCtrl = useAppDocuments(setErrorMessage);
  const exportCtrl = useAppExport(sessionCtrl.activeSession, sessionCtrl.revisionHeaders, setErrorMessage);

  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSpecsDrawerOpen, setIsSpecsDrawerOpen] = useState(false);
  const [isBlueprintModalOpen, setIsBlueprintModalOpen] = useState(false);
  const [isDocumentsModalOpen, setIsDocumentsModalOpen] = useState(false);
  const [isInspectionLogOpen, setIsInspectionLogOpen] = useState(false);
  const [isUserManagementOpen, setIsUserManagementOpen] = useState(false);

  useEffect(() => {
    if (currentUser) {
      sessionCtrl.fetchSessions();
      docCtrl.fetchDocuments();
    }
  }, [currentUser]);

  const activeProject = sessionCtrl.activeSession?.projectInfo || EMPTY_PROJECT;
  const { hasAreaContradiction, warnings } = useProjectWarnings(sessionCtrl.activeSession, activeProject);

  const handleApplyOcr = async (extracted: Partial<ProjectInfo>) => {
    await sessionCtrl.updateProject(extracted);
    setIsBlueprintModalOpen(false);
  };

  if (!authChecked) {
    return <div className="h-screen w-screen flex items-center justify-center bg-slate-900 text-slate-300 text-sm font-medium">Đang khởi tạo phiên làm việc an toàn...</div>;
  }
  if (!currentUser) return <Login onLogin={() => window.location.reload()} />;

  const sessionList = sessionCtrl.sessions.map((s) => ({ id: s.id, title: s.projectInfo.name || s.title, updatedAt: s.updatedAt }));

  return (
    <>
      {isDevToolsOpen && <DevToolsWarningOverlay />}
      {errorMessage && (
        <div className="fixed top-3 left-1/2 -translate-x-1/2 z-50 max-w-lg w-[92%] bg-red-50 border border-red-300 text-red-700 text-xs font-semibold rounded-xl shadow-lg px-4 py-2.5 flex items-center justify-between gap-2">
          <span>{errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage("")} className="text-red-500 hover:text-red-700 font-bold p-1">×</button>
        </div>
      )}

      <AppLayout
        isSidebarOpen={isSidebarOpen}
        onCloseSidebarMobile={() => setIsSidebarOpen(false)}
        sidebar={
          <AppSidebar
            isOpen={isSidebarOpen}
            onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
            sessions={sessionList}
            activeSessionId={sessionCtrl.activeSessionId}
            onSelectSession={sessionCtrl.setActiveSessionId}
            onCreateSession={sessionCtrl.createSession}
            onDeleteSession={sessionCtrl.deleteSession}
            onRenameSession={sessionCtrl.renameSession}
            onLoadOlderSessions={sessionCtrl.hasMoreSessions ? sessionCtrl.fetchSessions : undefined}
            loadingHistory={sessionCtrl.loadingHistory}
            currentUser={currentUser}
            onOpenDocuments={() => setIsDocumentsModalOpen(true)}
            onOpenInspectionLog={() => setIsInspectionLogOpen(true)}
            onOpenUserManagement={() => setIsUserManagementOpen(true)}
            onLogout={handleLogout}
            disabled={sessionCtrl.isPending}
          />
        }
        header={
          <AppHeader
            onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            project={activeProject}
            reviewState={sessionCtrl.hasLocalDraft ? "draft" : sessionCtrl.activeSession?.reviewState || "draft"}
            activeTab={activeTab}
            onChangeTab={setActiveTab}
            onOpenSpecsDrawer={() => setIsSpecsDrawerOpen(true)}
            onOpenOcrUpload={() => setIsBlueprintModalOpen(true)}
            onTriggerAppraisal={sessionCtrl.triggerAppraisal}
            isPending={sessionCtrl.isPending}
            hasAreaContradiction={hasAreaContradiction}
            hasChecklist={!!sessionCtrl.activeSession?.checklist?.length}
            theme={theme}
            onToggleTheme={toggleTheme}
            onExportDocx={exportCtrl.handleExportDocx}
            onExportPdf={exportCtrl.handleExportPdf}
            onExportJson={exportCtrl.handleExportJson}
            isExportingDocx={exportCtrl.isExportingDocx}
            isExportingPdf={exportCtrl.isExportingPdf}
            isExportingJson={exportCtrl.isExportingJson}
          />
        }
        warningBanner={<AreaWarningBanner warnings={warnings} />}
        activeTab={activeTab}
        chatContent={<ChatView messages={sessionCtrl.activeSession?.messages || []} isPending={sessionCtrl.isPending} onSendMessage={sessionCtrl.sendMessage} onCancelPending={sessionCtrl.cancelPending} onOpenOcrUpload={() => setIsBlueprintModalOpen(true)} />}
        checklistContent={<ComplianceChecklistView checklist={sessionCtrl.hasLocalDraft ? [] : sessionCtrl.activeSession?.checklist || []} />}
        verdictContent={<LegalBasisTabWrapper appraisalBasis={sessionCtrl.hasLocalDraft ? null : sessionCtrl.activeSession?.appraisalBasis} isSubjectToAppraisal={sessionCtrl.activeSession?.isSubjectToAppraisal ?? false} appraisalReason={sessionCtrl.hasLocalDraft ? "Chưa kiểm duyệt các thông số mới." : sessionCtrl.activeSession?.appraisalReason || ""} checklist={sessionCtrl.hasLocalDraft ? [] : sessionCtrl.activeSession?.checklist || []} projectInfo={activeProject} isPending={sessionCtrl.isPending} onTriggerAppraisal={sessionCtrl.triggerAppraisal} />}
        specsDrawer={<ProjectSpecsDrawer isOpen={isSpecsDrawerOpen} onClose={() => setIsSpecsDrawerOpen(false)} project={activeProject} onUpdateProject={sessionCtrl.updateProject} onTriggerAppraisal={sessionCtrl.triggerAppraisal} onReloadSession={sessionCtrl.reloadActiveSession} isPending={sessionCtrl.isPending} isSaving={sessionCtrl.isSaving} hasLocalDraft={sessionCtrl.hasLocalDraft} />}
        mobileBottomNav={<MobileBottomNav activeTab={activeTab} onChangeTab={setActiveTab} checklistCount={sessionCtrl.activeSession?.checklist?.length || 0} />}
        modals={<AppModals isBlueprintOpen={isBlueprintModalOpen} onCloseBlueprint={() => setIsBlueprintModalOpen(false)} sessionId={sessionCtrl.activeSessionId} onApplyOcr={handleApplyOcr} isDocumentsOpen={isDocumentsModalOpen} onCloseDocuments={() => setIsDocumentsModalOpen(false)} documents={docCtrl.documents} onUploadDocument={docCtrl.uploadDocuments} onDeleteDocument={docCtrl.deleteDocument} onResetDocuments={docCtrl.resetDocuments} onDownloadDocument={docCtrl.downloadDocument} isInspectionLogOpen={isInspectionLogOpen} onCloseInspectionLog={() => setIsInspectionLogOpen(false)} isUserManagementOpen={isUserManagementOpen} onCloseUserManagement={() => setIsUserManagementOpen(false)} currentUser={currentUser} onLogout={handleLogout} />}
      />
    </>
  );
}

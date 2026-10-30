import React from "react";
import { BlueprintUploadModal } from "../features/blueprint/components/BlueprintUploadModal";
import { DocumentLibraryModal } from "../features/documents/components/DocumentLibraryModal";
import { DocumentPreviewModal } from "./DocumentPreviewModal";
import { InspectionLogPanel } from "./InspectionLogPanel";
import { UserManagementModal } from "./UserManagementModal";
import { AuthUser } from "../lib/api";
import { DocumentItem, ProjectInfo } from "../types";

interface AppModalsProps {
  isBlueprintOpen: boolean;
  onCloseBlueprint: () => void;
  sessionId: string;
  onApplyOcr: (data: Partial<ProjectInfo>) => Promise<void>;
  isDocumentsOpen: boolean;
  onCloseDocuments: () => void;
  documents: DocumentItem[];
  onUploadDocument: (files: File[], code: string, title: string, type: string) => Promise<DocumentItem[]>;
  onDeleteDocument: (id: string) => void;
  onResetDocuments: () => void;
  onDownloadDocument: (doc: DocumentItem) => void;
  isInspectionLogOpen: boolean;
  onCloseInspectionLog: () => void;
  isUserManagementOpen: boolean;
  onCloseUserManagement: () => void;
  currentUser: AuthUser;
  onLogout: () => void;
  citationDoc?: DocumentItem | null;
  onCloseCitation?: () => void;
}

export const AppModals: React.FC<AppModalsProps> = ({
  isBlueprintOpen,
  onCloseBlueprint,
  sessionId,
  onApplyOcr,
  isDocumentsOpen,
  onCloseDocuments,
  documents,
  onUploadDocument,
  onDeleteDocument,
  onResetDocuments,
  onDownloadDocument,
  isInspectionLogOpen,
  onCloseInspectionLog,
  isUserManagementOpen,
  onCloseUserManagement,
  currentUser,
  onLogout,
  citationDoc,
  onCloseCitation,
}) => {
  return (
    <>
      {isBlueprintOpen && (
        <BlueprintUploadModal
          sessionId={sessionId}
          onClose={onCloseBlueprint}
          onApply={onApplyOcr}
        />
      )}
      <DocumentLibraryModal
        isOpen={isDocumentsOpen}
        onClose={onCloseDocuments}
        documents={documents}
        onUploadDocument={onUploadDocument}
        onDeleteDocument={onDeleteDocument}
        onResetDocuments={onResetDocuments}
        onDownloadDocument={onDownloadDocument}
        isAdmin={currentUser?.role === "admin"}
        userRole={currentUser?.role}
      />
      {/* Modal xem trước trực tiếp PDF luật khi bấm thẻ trích dẫn [Mã văn bản] trong chat (Ngày 4 kế hoạch) */}
      {citationDoc && onCloseCitation && (
        <DocumentPreviewModal
          previewDoc={citationDoc}
          onClose={onCloseCitation}
          onDownload={onDownloadDocument}
        />
      )}
      {isInspectionLogOpen && (
        <InspectionLogPanel
          sessionId={sessionId}
          onClose={onCloseInspectionLog}
        />
      )}
      {isUserManagementOpen && (
        <UserManagementModal
          currentUser={currentUser}
          onClose={onCloseUserManagement}
          onPasswordChanged={onLogout}
        />
      )}
    </>
  );
};

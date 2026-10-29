import React from "react";
import { X, Sparkles, Loader2, AlertCircle, RotateCcw } from "lucide-react";
import { ProjectInfo } from "../../../types";
import { useProjectSpecsForm } from "../hooks/useProjectSpecsForm";
import { SpecsGeneralFields } from "./SpecsGeneralFields";
import { SpecsScaleFields } from "./SpecsScaleFields";
import { FloorFunctionsSubform } from "./FloorFunctionsSubform";
import { BasementFunctionsSubform } from "./BasementFunctionsSubform";
import { BuildingEditor } from "../../../components/BuildingEditor";

interface ProjectSpecsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  project: ProjectInfo;
  onUpdateProject: (info: Partial<ProjectInfo>) => void;
  onDraftChange?: () => void;
  onTriggerAppraisal: () => void;
  onReloadSession?: () => void;
  isPending: boolean;
  isSaving: boolean;
  hasLocalDraft: boolean;
}

export const ProjectSpecsDrawer: React.FC<ProjectSpecsDrawerProps> = ({
  isOpen, onClose, project, onUpdateProject, onDraftChange,
  onTriggerAppraisal, onReloadSession, isPending, isSaving, hasLocalDraft,
}) => {
  const form = useProjectSpecsForm({ project, onUpdateProject, onDraftChange });
  if (!isOpen) return null;

  const handleSubmit = async () => {
    await onUpdateProject({
      name: form.localName, type: form.localType, investor: form.localInvestor, location: form.localLocation,
      floors: Number(form.localFloors) || 0, basements: Number(form.localBasements) || 0,
      pcccHeight: Number(form.localPcccHeight) || 0, floorArea: Number(form.localFloorArea) || 0,
      totalFloorArea: Number(form.localTotalFloorArea) || 0, fireRating: form.localFireRating,
      commercialDetails: form.localCommDetails,
    });
    onTriggerAppraisal();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xs transition-opacity" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <aside className="w-screen max-w-md bg-white shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-250">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div>
              <h2 className="text-sm font-bold text-slate-800">Thông số kỹ thuật công trình</h2>
              <p className="text-[11px] text-slate-500">Cơ sở tính toán các ngưỡng thẩm duyệt PCCC</p>
            </div>
            <button type="button" onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 cursor-pointer">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-5 custom-scrollbar">
            {hasLocalDraft && (
              <div className="flex items-center gap-2 p-2.5 bg-amber-50 text-amber-800 border border-amber-200 rounded-xl text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
                <span>Thông số đang có chỉnh sửa mới chưa kiểm duyệt.</span>
              </div>
            )}
            {!!project.components?.length && (
              <div className="p-2.5 bg-blue-50 text-blue-800 border border-blue-200 rounded-xl text-xs">
                Hồ sơ có {project.components.length} hạng mục độc lập. Thông số từng hạng mục được quản lý bên dưới.
              </div>
            )}
            <SpecsGeneralFields localName={form.localName} setLocalName={form.setLocalName} localInvestor={form.localInvestor} setLocalInvestor={form.setLocalInvestor} localLocation={form.localLocation} setLocalLocation={form.setLocalLocation} localType={form.localType} setLocalType={form.setLocalType} onCommitField={form.handleCommitField} />
            <SpecsScaleFields localFloors={form.localFloors} setLocalFloors={form.setLocalFloors} localBasements={form.localBasements} setLocalBasements={form.setLocalBasements} localPcccHeight={form.localPcccHeight} setLocalPcccHeight={form.setLocalPcccHeight} localFloorArea={form.localFloorArea} setLocalFloorArea={form.setLocalFloorArea} localTotalFloorArea={form.localTotalFloorArea} setLocalTotalFloorArea={form.setLocalTotalFloorArea} localFireRating={form.localFireRating} setLocalFireRating={form.setLocalFireRating} localCommDetails={form.localCommDetails} setLocalCommDetails={form.setLocalCommDetails} onCommitField={form.handleCommitField} />
            <FloorFunctionsSubform floorsCount={Number(form.localFloors) || 0} floorFunctions={form.floorFunctions} onChangeFloorFunction={form.handleFloorFunctionChange} />
            <BasementFunctionsSubform basementsCount={Number(form.localBasements) || 0} functions={form.basementFunctions} heights={form.basementHeights} areas={form.basementAreas} footprints={form.basementFootprints} onChangeField={form.handleBasementFieldChange} />
            <BuildingEditor project={project} onUpdate={onUpdateProject} />
          </div>

          <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between gap-2">
            {onReloadSession && (
              <button type="button" disabled={isPending || isSaving} onClick={onReloadSession} className="inline-flex items-center gap-1.5 px-3 py-2 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 rounded-xl hover:bg-white cursor-pointer" title="Hủy các sửa đổi chưa lưu và tải lại từ máy chủ">
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Tải lại</span>
              </button>
            )}
            <button type="button" disabled={isPending} onClick={handleSubmit} className="ml-auto inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-orange hover:bg-orange-600 disabled:opacity-50 text-white text-xs font-bold shadow-xs transition-all cursor-pointer">
              {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              <span>Kiểm duyệt lại hồ sơ</span>
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
};

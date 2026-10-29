import React, { useMemo } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { LegalBasisPanel, VERDICT_STYLES, VerdictIcon, resolveStatus, verdictHeading } from "../../../components/LegalBasisPanel";
import { AppraisalBasis, ChecklistItem, ProjectInfo } from "../../../types";

interface LegalBasisTabWrapperProps {
  appraisalBasis?: AppraisalBasis | null;
  isSubjectToAppraisal: boolean;
  appraisalReason: string;
  checklist: ChecklistItem[];
  projectInfo: ProjectInfo;
  isPending: boolean;
  onTriggerAppraisal: () => void;
}

const STAT_COLORS = {
  pass: "#10B981",
  fail: "#EF4444",
  review: "#F59E0B",
  measure: "#06B6D4",
};

export const LegalBasisTabWrapper: React.FC<LegalBasisTabWrapperProps> = ({
  appraisalBasis,
  isSubjectToAppraisal,
  appraisalReason,
  checklist,
}) => {
  const status = resolveStatus(appraisalBasis, isSubjectToAppraisal);
  const style = VERDICT_STYLES[status];
  const heading = verdictHeading(status, appraisalBasis);

  const chartData = useMemo(() => {
    const passCount = checklist.filter((i) => i.result === "Đạt" || i.result === "Không bắt buộc").length;
    const failCount = checklist.filter((i) => i.result === "Không đạt").length;
    const reviewCount = checklist.filter((i) => i.result === "Khuyến nghị mạnh" || i.result === "Khuyến nghị" || i.result === "Cần xem xét").length;
    const measureCount = checklist.filter((i) => i.result === "Cần đo đạc").length;

    return [
      { name: "Đạt / Không bắt buộc", value: passCount, color: STAT_COLORS.pass },
      { name: "Không đạt", value: failCount, color: STAT_COLORS.fail },
      { name: "Cần xem xét", value: reviewCount, color: STAT_COLORS.review },
      { name: "Cần đo đạc", value: measureCount, color: STAT_COLORS.measure },
    ].filter((d) => d.value > 0);
  }, [checklist]);

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 custom-scrollbar bg-slate-50/50">
      <div className="max-w-5xl mx-auto space-y-5">
        <div className={`p-6 rounded-2xl border-2 flex flex-col sm:flex-row items-start sm:items-center gap-4 transition-all shadow-md ${style.container}`}>
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-white shrink-0 bg-gradient-to-b ${style.icon}`}>
            <VerdictIcon status={status} className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Kết luận sàng lọc pháp lý</span>
            <h2 className="font-bold text-lg sm:text-xl uppercase tracking-tight text-slate-900 leading-tight">
              {heading}
            </h2>
            <p className="text-xs sm:text-sm font-medium text-slate-700 leading-relaxed pt-1">
              {appraisalReason || "Chưa có thông tin kết luận thẩm duyệt."}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-4">
            <LegalBasisPanel
              basis={appraisalBasis}
              isSubjectToAppraisal={isSubjectToAppraisal}
              variant="full"
            />
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs space-y-3 flex flex-col">
            <div className="border-b border-slate-100 pb-2">
              <h3 className="font-bold text-xs uppercase text-slate-800">Phân bố tiêu chí rà soát</h3>
              <p className="text-[11px] text-slate-400">Tỷ lệ tuân thủ theo 17-38 hạng mục</p>
            </div>

            {chartData.length > 0 ? (
              <>
                <div className="h-44 relative flex items-center justify-center">
                  <ResponsiveContainer width="100%" height={170}>
                    <PieChart>
                      <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={42} outerRadius={68} paddingAngle={3}>
                        {chartData.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: number) => [`${value} hạng mục`, ""]} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-1.5 pt-1 text-xs">
                  {chartData.map((d) => (
                    <div key={d.name} className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-slate-600">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                        {d.name}
                      </span>
                      <span className="font-bold text-slate-800">{d.value}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-slate-400 py-8 text-center">Chưa có dữ liệu tiêu chí.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

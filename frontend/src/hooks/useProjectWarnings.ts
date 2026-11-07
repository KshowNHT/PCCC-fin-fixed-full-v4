import { useMemo } from "react";
import { ProjectInfo, Session } from "../types";

export function useProjectWarnings(
  session: Session | undefined,
  project: ProjectInfo,
  reviewState: "draft" | "reviewed" = "draft"
) {
  const isMultiComponent = Boolean(project.components && project.components.length > 0);
  const floors = isMultiComponent ? 0 : project.floors || 0;
  const floorArea = isMultiComponent ? 0 : project.floorArea || 0;
  const totalFloorArea = isMultiComponent ? 0 : project.totalFloorArea || 0;

  const hasAreaContradiction = useMemo(() => {
    return floorArea > 0 && totalFloorArea > 0 && totalFloorArea < floorArea;
  }, [floorArea, totalFloorArea]);

  const hasAreaMismatch = useMemo(() => {
    return (
      reviewState === "reviewed" &&
      floors > 0 &&
      floorArea > 0 &&
      totalFloorArea > 0 &&
      Math.abs(totalFloorArea - floorArea * floors) > 10
    );
  }, [reviewState, floors, floorArea, totalFloorArea]);

  const warnings = useMemo(() => {
    const list = reviewState === "reviewed" ? session?.warnings || [] : [];
    const areaMsg =
      "Tổng diện tích sàn khai báo không trùng khớp với tích số giữa (diện tích sàn x số tầng), cần đối chiếu kiểm tra thực tế.";
    const contradictionMsg =
      "Tổng diện tích sàn không thể nhỏ hơn diện tích 1 sàn. Vui lòng kiểm tra và điều chỉnh lại thông số diện tích.";
    const others = list.filter((w) => !w.startsWith(areaMsg) && !w.startsWith(contradictionMsg));
    if (hasAreaContradiction) {
      return [contradictionMsg, ...others];
    }
    return hasAreaMismatch ? [areaMsg, ...others] : others;
  }, [session?.warnings, reviewState, hasAreaContradiction, hasAreaMismatch]);

  return { hasAreaContradiction, warnings };
}



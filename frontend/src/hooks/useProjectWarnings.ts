import { useMemo } from "react";
import { ProjectInfo, Session } from "../types";

export function useProjectWarnings(
  session: Session | undefined,
  project: ProjectInfo
) {
  const hasAreaContradiction = useMemo(() => {
    const floors = project.floors || 0;
    const floorArea = project.floorArea || 0;
    const totalFloorArea = project.totalFloorArea || 0;
    return (
      floors > 0 &&
      floorArea > 0 &&
      totalFloorArea > 0 &&
      Math.abs(totalFloorArea - floorArea * floors) > 10
    );
  }, [project.floors, project.floorArea, project.totalFloorArea]);

  const warnings = useMemo(() => {
    const list = session?.warnings || [];
    const areaMsg =
      "Tổng diện tích sàn khai báo không trùng khớp với tích số giữa (diện tích sàn x số tầng), cần đối chiếu kiểm tra thực tế.";
    const others = list.filter((w) => !w.startsWith(areaMsg));
    return hasAreaContradiction ? [areaMsg, ...others] : others;
  }, [session?.warnings, hasAreaContradiction]);

  return { hasAreaContradiction, warnings };
}


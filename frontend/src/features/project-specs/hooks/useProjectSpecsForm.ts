import { useState, useEffect, useCallback } from "react";
import { ProjectInfo } from "../../../types";

interface UseProjectSpecsFormProps {
  project: ProjectInfo;
  onUpdateProject: (info: Partial<ProjectInfo>) => void;
  onDraftChange?: () => void;
}

export function useProjectSpecsForm({
  project,
  onUpdateProject,
  onDraftChange,
}: UseProjectSpecsFormProps) {
  const [localName, setLocalName] = useState(project.name || "");
  const [localInvestor, setLocalInvestor] = useState(project.investor || "");
  const [localLocation, setLocalLocation] = useState(project.location || "");
  const [localType, setLocalType] = useState(project.type || "");
  const [localFloors, setLocalFloors] = useState<string | number>(project.floors ?? "");
  const [localBasements, setLocalBasements] = useState<string | number>(project.basements ?? "");
  const [localPcccHeight, setLocalPcccHeight] = useState<string | number>(project.pcccHeight ?? "");
  const [localFloorArea, setLocalFloorArea] = useState<string | number>(project.floorArea ?? "");
  const [localTotalFloorArea, setLocalTotalFloorArea] = useState<string | number>(project.totalFloorArea ?? "");
  const [localFireRating, setLocalFireRating] = useState(project.fireRating || "");
  const [localCommDetails, setLocalCommDetails] = useState(project.commercialDetails || "");

  const [floorFunctions, setFloorFunctions] = useState<string[]>(project.floorFunctions || []);
  const [basementFunctions, setBasementFunctions] = useState<string[]>(project.basementFunctions || []);
  const [basementHeights, setBasementHeights] = useState<number[]>(project.basementHeights || []);
  const [basementAreas, setBasementAreas] = useState<number[]>(project.basementAreas || []);
  const [basementFootprints, setBasementFootprints] = useState<number[]>(project.basementFootprints || []);

  useEffect(() => {
    if (document.activeElement?.id !== "spec-name") setLocalName(project.name || "");
    if (document.activeElement?.id !== "spec-investor") setLocalInvestor(project.investor || "");
    if (document.activeElement?.id !== "spec-location") setLocalLocation(project.location || "");
    if (document.activeElement?.id !== "spec-type") setLocalType(project.type || "");
    if (document.activeElement?.id !== "spec-floors") setLocalFloors(project.floors ?? "");
    if (document.activeElement?.id !== "spec-basements") setLocalBasements(project.basements ?? "");
    if (document.activeElement?.id !== "spec-pccc-height") setLocalPcccHeight(project.pcccHeight ?? "");
    if (document.activeElement?.id !== "spec-floor-area") setLocalFloorArea(project.floorArea ?? "");
    if (document.activeElement?.id !== "spec-total-floor-area") setLocalTotalFloorArea(project.totalFloorArea ?? "");
    if (document.activeElement?.id !== "spec-fire-rating") setLocalFireRating(project.fireRating || "");
    if (document.activeElement?.id !== "spec-comm-details") setLocalCommDetails(project.commercialDetails || "");
    setFloorFunctions(project.floorFunctions || []);
    setBasementFunctions(project.basementFunctions || []);
    setBasementHeights(project.basementHeights || []);
    setBasementAreas(project.basementAreas || []);
    setBasementFootprints(project.basementFootprints || []);
  }, [project]);

  const handleCommitField = useCallback(
    (field: keyof ProjectInfo, value: unknown) => {
      onDraftChange?.();
      onUpdateProject({ [field]: value });
    },
    [onDraftChange, onUpdateProject]
  );

  const handleFloorFunctionChange = useCallback(
    (index: number, val: string) => {
      onDraftChange?.();
      const next = [...floorFunctions];
      next[index] = val;
      setFloorFunctions(next);
      onUpdateProject({ floorFunctions: next });
    },
    [floorFunctions, onDraftChange, onUpdateProject]
  );

  const handleBasementFieldChange = useCallback(
    (index: number, field: "functions" | "heights" | "areas" | "footprints", val: string | number) => {
      onDraftChange?.();
      if (field === "functions") {
        const next = [...basementFunctions];
        next[index] = String(val);
        setBasementFunctions(next);
        onUpdateProject({ basementFunctions: next });
      } else if (field === "heights") {
        const next = [...basementHeights];
        next[index] = Number(val);
        setBasementHeights(next);
        onUpdateProject({ basementHeights: next });
      } else if (field === "areas") {
        const next = [...basementAreas];
        next[index] = Number(val);
        setBasementAreas(next);
        onUpdateProject({ basementAreas: next });
      } else if (field === "footprints") {
        const next = [...basementFootprints];
        next[index] = Number(val);
        setBasementFootprints(next);
        onUpdateProject({ basementFootprints: next });
      }
    },
    [basementFunctions, basementHeights, basementAreas, basementFootprints, onDraftChange, onUpdateProject]
  );

  return {
    localName,
    setLocalName,
    localInvestor,
    setLocalInvestor,
    localLocation,
    setLocalLocation,
    localType,
    setLocalType,
    localFloors,
    setLocalFloors,
    localBasements,
    setLocalBasements,
    localPcccHeight,
    setLocalPcccHeight,
    localFloorArea,
    setLocalFloorArea,
    localTotalFloorArea,
    setLocalTotalFloorArea,
    localFireRating,
    setLocalFireRating,
    localCommDetails,
    setLocalCommDetails,
    floorFunctions,
    basementFunctions,
    basementHeights,
    basementAreas,
    basementFootprints,
    handleCommitField,
    handleFloorFunctionChange,
    handleBasementFieldChange,
  };
}

"use client";

// App-wide stage state (plan v2 product vision): the pair defined in the design panel —
// preset, STE import or fully parametric — feeds every other panel (contour, mesh, deck,
// variation overlay). Defaults to the validated kst-E example.

import { createContext, useContext, useState, type ReactNode } from "react";
import { KST_E_STAGE, type StageParams } from "@/lib/api";

const StageCtx = createContext<{
  stage: StageParams;
  setStage: (s: StageParams) => void;
  label: string;
  setLabel: (l: string) => void;
}>({ stage: KST_E_STAGE, setStage: () => {}, label: "kst-E", setLabel: () => {} });

export function StageProvider({ children }: { children: ReactNode }) {
  const [stage, setStage] = useState<StageParams>(KST_E_STAGE);
  const [label, setLabel] = useState("kst-E");
  return (
    <StageCtx.Provider value={{ stage, setStage, label, setLabel }}>{children}</StageCtx.Provider>
  );
}

export function useStage() {
  return useContext(StageCtx);
}

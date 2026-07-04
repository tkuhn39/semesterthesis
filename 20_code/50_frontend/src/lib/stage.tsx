"use client";

// Back-compat adapter: the stage now lives in THE workbench store (lib/store.tsx, single
// source of truth). Existing panels keep using useStage()/StageProvider unchanged.

import { type ReactNode } from "react";
import { WorkbenchProvider, useWorkbench } from "@/lib/store";

export function StageProvider({ children }: { children: ReactNode }) {
  return <WorkbenchProvider>{children}</WorkbenchProvider>;
}

export function useStage() {
  const wb = useWorkbench();
  return { stage: wb.stage, setStage: wb.setStage, label: wb.label, setLabel: wb.setLabel };
}

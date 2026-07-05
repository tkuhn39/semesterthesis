// Types + fetch for OUR editor schema (/api/ui-schema — app/services/uimodel).
// The backend is the single source for labels (DE/EN), symbols, units, dropdown options,
// Berechnungsauswahl methods (tab visibility) and the norm-referenced dependency rules.

export interface AttrOption {
  value: string;
  label_de: string;
  label_en: string;
}
export interface AttributeDef {
  id: string;
  label_de: string;
  label_en: string;
  symbol?: string | null;
  unit?: string | null;
  kind: "float" | "int" | "bool" | "enum" | "text" | "action" | "path";
  precision?: number | null;
  options?: AttrOption[] | null;
  per_gear: boolean;
  computed: boolean;
  binding?: string | null;
  bindings?: [string, string] | null;
  // per-column dynamic locking (store paths; truthy = that column renders locked)
  locked_ifs?: [string, string] | null;
  // emptying the field writes null instead of being ignored (reset semantics)
  nullable?: boolean;
  norm_ref?: string | null;
  info_de?: string | null;
  info_en?: string | null;
  step?: number | null;
  min?: number | null;
  max?: number | null;
}
export interface RowRef {
  attr: string;
  visible_if?: string | null;
  locked_if?: string | null;
}
export interface SectionDef {
  id: string;
  title_de: string;
  title_en: string;
  rows: RowRef[];
  info_de?: string | null;
  info_en?: string | null;
  visible_if?: string | null;
}
export interface TabDef {
  id: string;
  title_de: string;
  title_en: string;
  sections: SectionDef[];
  visible_if_method?: string | null;
}
export interface ComponentDef {
  id: string;
  label_de: string;
  label_en: string;
  tabs: TabDef[];
}
export interface DependencyRule {
  id: string;
  when: string;
  when_value?: string | boolean | number | null;
  effect: "lock" | "hide" | "show" | "compute";
  targets: string[];
  description_de: string;
  description_en: string;
  norm_ref?: string | null;
}
export interface CalcMethod {
  id: string;
  label_de: string;
  label_en: string;
  group_de: string;
  group_en: string;
  implemented: boolean;
  always_on: boolean;
  default_on: boolean;
  enables_tabs: [string, string][];
}
export interface UiSchema {
  version: string;
  components: ComponentDef[];
  attributes: Record<string, AttributeDef>;
  rules: DependencyRule[];
  methods: CalcMethod[];
}

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function fetchUiSchema(): Promise<UiSchema> {
  const res = await fetch(`${BASE}/api/ui-schema`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<UiSchema>;
}

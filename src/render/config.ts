// Section layout configuration: column positions, visibility/layout defaults.
// Replaces Python Config with a typed Record<string, SectionConfig>.

export type Visibility = "show" | "hide" | "none" | "unknown";
export type Layout = "wide" | "tall";

export interface SectionConfig {
  column: number;
  order: number;
  defaultVisibility: Visibility;
  defaultLayout?: Layout;
}

export const SECTION_IDS = [
  "hand-opponent",
  "hand-me",
  "score-opponent",
  "score-me",
  "achievements",
  "base-deck",
  "cities-deck",
  "base-list",
  "cities-list",
] as const;

export type SectionId = (typeof SECTION_IDS)[number];

/** Default section configuration. All sections in column 1, ordered sequentially. */
export const DEFAULT_SECTION_CONFIG: Record<SectionId, SectionConfig> = {
  "hand-opponent":  { column: 1, order: 1, defaultVisibility: "show" },
  "hand-me":        { column: 1, order: 2, defaultVisibility: "show" },
  "score-opponent": { column: 1, order: 3, defaultVisibility: "show" },
  "score-me":       { column: 1, order: 4, defaultVisibility: "show" },
  "achievements":   { column: 1, order: 5, defaultVisibility: "show", defaultLayout: "wide" },
  "base-deck":      { column: 1, order: 6, defaultVisibility: "show" },
  "cities-deck":    { column: 1, order: 7, defaultVisibility: "hide" },
  "base-list":      { column: 1, order: 8, defaultVisibility: "none", defaultLayout: "wide" },
  "cities-list":    { column: 1, order: 9, defaultVisibility: "none", defaultLayout: "wide" },
};

/** Visibility toggle options for a section. */
export interface ToggleOption {
  mode: string;
  label: string;
  active: boolean;
}

export interface Toggle {
  targetId: string;
  defaultMode: string;
  options: ToggleOption[];
}

/** Build a visibility toggle config for a section. */
export function visibilityToggle(sectionId: SectionId, defaultVisibility: Visibility, hasUnknown: boolean): Toggle {
  const modeMap: Record<string, string> = { show: "all", hide: "none", none: "none", unknown: "unknown" };
  const defaultMode = modeMap[defaultVisibility] ?? "none";

  const options: ToggleOption[] = hasUnknown
    ? [
        { mode: "none", label: "None", active: defaultMode === "none" },
        { mode: "all", label: "All", active: defaultMode === "all" },
        { mode: "unknown", label: "Unknown", active: defaultMode === "unknown" },
      ]
    : [
        { mode: "none", label: "Hide", active: defaultMode === "none" },
        { mode: "all", label: "Show", active: defaultMode === "all" },
      ];

  return { targetId: sectionId, defaultMode, options };
}

/** Build a layout toggle config for a section. */
export function layoutToggle(sectionId: SectionId, defaultLayout: Layout): Toggle {
  return {
    targetId: sectionId,
    defaultMode: defaultLayout,
    options: [
      { mode: "wide", label: "Wide", active: defaultLayout === "wide" },
      { mode: "tall", label: "Tall", active: defaultLayout === "tall" },
    ],
  };
}

/** Number of columns in tall layout (one per color). */
export const TALL_COLUMNS = 5;

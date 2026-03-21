// Shared localStorage persistence for all side panel settings.
// Each setting has a key and typed defaults; loadSetting merges stored values
// over defaults so new fields are always present.

export function loadSetting<T>(key: string, defaults: T): T {
  try {
    const stored = localStorage.getItem(key);
    if (stored) {
      const parsed = JSON.parse(stored) as T;
      if (typeof defaults === "object" && defaults !== null && !Array.isArray(defaults)) {
        return { ...defaults, ...parsed };
      }
      return parsed;
    }
  } catch { /* ignore malformed data */ }
  if (typeof defaults === "object" && defaults !== null && !Array.isArray(defaults)) {
    return { ...defaults };
  }
  return defaults;
}

export function saveSetting<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch { /* ignore */ }
}

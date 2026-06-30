import { useCallback, useState } from "react";

/**
 * State backed by localStorage, keyed by `key`. Survives reloads and tab
 * switches. Used to keep the last eval result visible after navigating away.
 * Falls back to in-memory only if storage is unavailable (e.g. private mode).
 */
export function usePersistentState<T>(key: string, initial: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw !== null ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });

  const set = useCallback(
    (next: T) => {
      setValue(next);
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* storage unavailable — keep in-memory value */
      }
    },
    [key],
  );

  return [value, set];
}

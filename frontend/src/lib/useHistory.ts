import { useCallback, useRef, useState } from "react";
import type { Spec } from "./types";

/**
 * Edit history for the Canvas spec, with debounced coalescing so a burst of
 * keystrokes/slider drags collapses into a single undo step. `set` records an
 * edit (live, immediate) and schedules a commit; `undo`/`redo` walk committed
 * snapshots. Every committed step is persisted via `onPersist` (autosave).
 */
export interface SpecHistory {
  spec: Spec | null;
  canUndo: boolean;
  canRedo: boolean;
  set: (next: Spec) => void;
  undo: () => void;
  redo: () => void;
  load: (initial: Spec) => void;
  /** Commit any pending edit immediately and return the current spec. */
  flush: () => Spec | null;
}

const CAP = 100;
const DEBOUNCE = 650;

export function useSpecHistory(onPersist: (spec: Spec) => void): SpecHistory {
  const [spec, setSpec] = useState<Spec | null>(null);
  const [, bump] = useState(0);
  const refresh = useCallback(() => bump((n) => n + 1), []);

  const specRef = useRef<Spec | null>(null);
  const baseline = useRef<Spec | null>(null); // last committed snapshot
  const undoStack = useRef<Spec[]>([]);
  const redoStack = useRef<Spec[]>([]);
  const timer = useRef<number | null>(null);
  const persist = useRef(onPersist);
  persist.current = onPersist;

  const commit = useCallback(() => {
    if (timer.current) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    const cur = specRef.current;
    if (!cur || cur === baseline.current) return;
    if (baseline.current) {
      undoStack.current.push(baseline.current);
      if (undoStack.current.length > CAP) undoStack.current.shift();
    }
    redoStack.current = [];
    baseline.current = cur;
    persist.current(cur);
    refresh();
  }, [refresh]);

  const set = useCallback(
    (next: Spec) => {
      specRef.current = next;
      setSpec(next);
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(commit, DEBOUNCE);
    },
    [commit],
  );

  const restore = useCallback(
    (target: Spec) => {
      specRef.current = target;
      baseline.current = target;
      setSpec(target);
      persist.current(target);
      refresh();
    },
    [refresh],
  );

  const undo = useCallback(() => {
    if (timer.current) commit();
    if (undoStack.current.length === 0) return;
    const prev = undoStack.current.pop()!;
    if (baseline.current) redoStack.current.push(baseline.current);
    restore(prev);
  }, [commit, restore]);

  const redo = useCallback(() => {
    if (timer.current) commit();
    if (redoStack.current.length === 0) return;
    const next = redoStack.current.pop()!;
    if (baseline.current) undoStack.current.push(baseline.current);
    restore(next);
  }, [commit, restore]);

  const load = useCallback(
    (initial: Spec) => {
      if (timer.current) {
        window.clearTimeout(timer.current);
        timer.current = null;
      }
      specRef.current = initial;
      baseline.current = initial;
      undoStack.current = [];
      redoStack.current = [];
      setSpec(initial);
      refresh();
    },
    [refresh],
  );

  const flush = useCallback(() => {
    if (timer.current) commit();
    return specRef.current;
  }, [commit]);

  return {
    spec,
    canUndo: undoStack.current.length > 0,
    canRedo: redoStack.current.length > 0,
    set,
    undo,
    redo,
    load,
    flush,
  };
}

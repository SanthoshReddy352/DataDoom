// Minimal classnames joiner (avoids a runtime dependency).
export type ClassValue = string | number | false | null | undefined;

export function clsx(...parts: ClassValue[]): string {
  return parts.filter(Boolean).join(" ");
}

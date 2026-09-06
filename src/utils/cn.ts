/** Tiny `clsx` stand-in — joins truthy class names. */
export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ')
}

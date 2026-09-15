
export function getAsPositiveInteger(
  value: string | null,
  fallback?: number,
): number | null {
  if (value === null) {
    return fallback ?? null;
  }

  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

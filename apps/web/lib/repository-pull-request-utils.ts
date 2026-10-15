const REPOSITORY_PATTERN = /^[^/\s]+\/[^/\s]+$/;

export function normalizeRepository(value: string): string {
  return value
    .trim()
    .replace(/^https?:\/\/github\.com\//i, "")
    .replace(/\.git$/i, "")
    .replace(/^\/+|\/+$/g, "");
}

export function isRepositoryName(value: string): boolean {
  return REPOSITORY_PATTERN.test(value);
}

// SHA-1 (40 character length) or SHA-256 (64 character length)
export const GIT_OBJECT_ID_PATTERN = "^([0-9a-f]{40}|[0-9a-f]{64})$";

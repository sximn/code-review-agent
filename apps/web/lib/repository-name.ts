const REPOSITORY_PATTERN = /^[^/\s]+\/[^/\s]+$/

export function normalizeRepository(value: string): string {
  return value
    .trim()
    .replace(/^https?:\/\/github\.com\//i, "")
    .replace(/\.git$/i, "")
    .replace(/^\/+|\/+$/g, "")
}

export function isRepositoryName(value: string): boolean {
  console.log({value});
  return REPOSITORY_PATTERN.test(value)
}

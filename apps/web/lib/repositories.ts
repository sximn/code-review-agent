import { z } from "zod";
import { isRepositoryName, normalizeRepository } from "./repository-name";

type RepositoryRequest = {
  repository?: unknown;
};

export type PublicRepository = {
  fullName: string;
};

const pullRequestSchema = z
  .object({
    number: z.number().int(),
    html_url: z.url(),
    title: z.string(),
    body: z.string().nullable(),
    updated_at: z.iso.datetime(),
  })
  .transform((pr) => ({
    number: pr.number,
    url: pr.html_url,
    title: pr.title,
    description: pr.body ?? "",
    updatedAt: new Date(pr.updated_at),
  }));

const pullRequestsSchema = z.array(pullRequestSchema);
export type PullRequest = z.output<typeof pullRequestSchema>;

type CheckRepositoryRequestResp =
  { success: false; error: string } | { success: true; repository: string };
export async function checkRepositoryRequest(
  request: Request,
): Promise<CheckRepositoryRequestResp> {
  const body = (await request
    .json()
    .catch(() => null)) as RepositoryRequest | null;
  const searchRepository = new URL(request.url).searchParams.get("repository");

  const input =
    typeof body?.repository === "string"
      ? body.repository
      : (searchRepository ?? "");

  const repository = normalizeRepository(input);

  if (!isRepositoryName(repository)) {
    return {
      success: false,
      error: "Enter a repository in owner/repository format.",
    };
  }

  return { success: true, repository };
}

export async function getPublicRepository(
  repository: string,
): Promise<PublicRepository | null> {
  const [owner, name] = repository.split("/");

  if (!owner || !name) {
    return null;
  }

  const response = await fetch(
    `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(name)}`,
    {
      headers: {
        Accept: "application/vnd.github+json",
        "User-Agent": "REWY",
        "X-GitHub-Api-Version": "2026-03-10",
      },
      cache: "no-store",
    },
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`GitHub returned ${response.status}`);
  }

  const data = (await response.json()) as {
    full_name?: unknown;
    private?: unknown;
  };

  if (typeof data.full_name !== "string" || data.private === true) {
    return null;
  }

  return { fullName: data.full_name };
}

export async function getOpenPullRequests(
  repository: string,
  {
    page,
    perPage,
  }: {
    page: number;
    perPage: number;
  },
): Promise<{ pullRequests: PullRequest[]; hasNextPage: boolean } | null> {
  const [owner, name] = repository.split("/");

  if (!owner || !name) {
    return null;
  }

  if (
    !Number.isInteger(page) ||
    page < 1 ||
    !Number.isInteger(perPage) ||
    perPage < 1 ||
    perPage > 100
  ) {
    throw new Error("Invalid pull request pagination parameters");
  }

  const url = new URL(
    `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(name)}/pulls`,
  );

  url.search = new URLSearchParams({
    state: "open",
    sort: "updated",
    direction: "desc",
    page: String(page),
    per_page: String(perPage),
  }).toString();

  const response = await fetch(url, {
    headers: {
      Accept: "application/vnd.github+json",
      "User-Agent": "REWY",
      "X-GitHub-Api-Version": "2026-03-10",
    },
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`GitHub returned ${response.status}`);
  }

  const data: unknown = await response.json();

  return {
    pullRequests: pullRequestsSchema.parse(data),
    hasNextPage: response.headers.get("link")?.includes('rel="next"') ?? false,
  };
}

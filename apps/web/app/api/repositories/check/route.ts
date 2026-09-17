import { auth } from "@/lib/auth";
import { getPublicRepository } from "@/lib/repositories";
import { isRepositoryName, normalizeRepository } from "@/lib/repository-name";

type RepositoryRequest = {
  repository?: unknown;
};

export async function POST(request: Request) {
  const session = await auth.api.getSession({ headers: request.headers });

  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = (await request
    .json()
    .catch(() => null)) as RepositoryRequest | null;
  const repository =
    typeof body?.repository === "string"
      ? normalizeRepository(body.repository)
      : "";

  if (!isRepositoryName(repository)) {
    return Response.json(
      { error: "Enter a repository in owner/repository format." },
      { status: 400 },
    );
  }

  try {
    const publicRepository = await getPublicRepository(repository);

    if (!publicRepository) {
      return Response.json(
        {
          error:
            "We couldn't find a public repository with that name. Private repositories aren't supported yet.",
        },
        { status: 404 },
      );
    }

    return Response.json({ repository: publicRepository });
  } catch {
    return Response.json(
      { error: "GitHub is unavailable. Please try again shortly." },
      { status: 502 },
    );
  }
}

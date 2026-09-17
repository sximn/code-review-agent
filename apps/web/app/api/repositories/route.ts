import { and, eq } from "drizzle-orm";

import { auth } from "@/lib/auth";
import { db } from "@/db/drizzle";
import { repository as repositoryTable } from "@/db/schema";
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
            "We couldn't verify that public repository. Private repositories aren't supported yet.",
        },
        { status: 404 },
      );
    }

    const [existingRepository] = await db
      .select()
      .from(repositoryTable)
      .where(
        and(
          eq(repositoryTable.userId, session.user.id),
          eq(repositoryTable.fullName, publicRepository.fullName),
        ),
      )
      .limit(1);

    if (existingRepository) {
      return Response.json({ repository: existingRepository });
    }

    const [createdRepository] = await db
      .insert(repositoryTable)
      .values({
        id: crypto.randomUUID(),
        fullName: publicRepository.fullName,
        userId: session.user.id,
      })
      .returning();

    return Response.json({ repository: createdRepository }, { status: 201 });
  } catch {
    return Response.json(
      { error: "We couldn't connect this repository. Please try again." },
      { status: 502 },
    );
  }
}

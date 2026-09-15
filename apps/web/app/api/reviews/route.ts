import { db } from "@/db/drizzle";
import { repository as repositoryTable } from "@/db/schema";
import { auth } from "@/lib/auth"
import { enqueueReviewJob } from "@/lib/queue";
import { checkRepositoryRequest } from "@/lib/repositories"
import { and, eq } from "drizzle-orm";
import env from "@/lib/environment";
import { getAsPositiveInteger } from "@/lib/nums";

export async function POST(request: Request) {
  const session = await auth.api.getSession({ headers: request.headers })

  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 })
  }

  const repoCheck = await checkRepositoryRequest(request);
  if (!repoCheck.success) {
    return Response.json(
      { error: "Enter a repository in owner/repository format." },
      { status: 400 },
    )
  }

  const prInput = new URL(request.url).searchParams.get("pullRequestNumber");
  const pullRequestNumber = getAsPositiveInteger(prInput);
  if (!pullRequestNumber) {
    return Response.json(
      { error: "Missing pull request ID." },
      { status: 400 },
    )
  }

  try {
    const [connectedRepository] = await db
      .select()
      .from(repositoryTable)
      .where(
        and(
          eq(repositoryTable.userId, session.user.id),
          eq(repositoryTable.fullName, repoCheck.repository),
        ),
      )
      .limit(1);

    if (!connectedRepository) {
      return Response.json(
        { error: "Given repository not connected." },
        { status: 400 }
      );
    }

    const jobEnqueue = enqueueReviewJob({
      repository: repoCheck.repository,
      pull_request: pullRequestNumber,
    });

    return Response.json({ text: "created" }, { status: 201 })
  } catch {
    return Response.json(
      { error: "We couldn't connect this repository. Please try again." },
      { status: 502 },
    )
  }
}

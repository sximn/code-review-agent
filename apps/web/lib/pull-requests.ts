import { TransactionType } from "@/db/drizzle";
import { pullRequest, pullRequestVersion } from "@/db/schema";

// caller owns the transaction so a review and its version are saved atomically
export async function recordPullRequestVersion(
  tx: TransactionType,
  repositoryId: string,
  number: number,
  headSha: string,
) {
  const [pr] = await tx
    .insert(pullRequest)
    .values({
      id: crypto.randomUUID(),
      repositoryId,
      number,
    })
    .onConflictDoUpdate({
      target: [pullRequest.repositoryId, pullRequest.number],
      set: { number }, // no-op update, used just to get existing value in the returning() clause
    })
    .returning();

  const [version] = await tx
    .insert(pullRequestVersion)
    .values({
      id: crypto.randomUUID(),
      pullRequestId: pr.id,
      headSha,
    })
    .onConflictDoUpdate({
      target: [pullRequestVersion.pullRequestId, pullRequestVersion.headSha],
      set: { headSha }, // no-op update, used just to get existing value in the returning() clause
    })
    .returning();

  return version;
}

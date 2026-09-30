import { reviewStateSchema } from "@/lib/contracts/review";
import { applyReviewState } from "@/lib/review-state";
import { hasValidWorkerToken } from "@/lib/worker-auth";

export async function PATCH(request: Request) {
  if (!hasValidWorkerToken(request.headers)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const parsed = reviewStateSchema.safeParse(
    await request.json().catch(() => null),
  );
  if (!parsed.success) {
    return Response.json(
      {
        error: "Invalid review state payload.",
        issues: parsed.error.issues,
      },
      { status: 400 },
    );
  }

  const result = await applyReviewState(parsed.data);

  if (result.kind === "updated") {
    return Response.json({ review: result.review, usage: result.usage });
  }
  if (result.kind === "idempotent") {
    return Response.json({ review: result.review });
  }
  if (result.kind === "not-found") {
    return Response.json({ error: "Review not found." }, { status: 404 });
  }

  return Response.json(
    {
      error: `Cannot change review from ${result.currentStatus} to ${parsed.data.status}.`,
    },
    { status: 409 },
  );
}

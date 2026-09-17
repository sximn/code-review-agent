import { auth } from "@/lib/auth";
import { getRecentReviews } from "@/lib/dashboard";

export async function GET(request: Request) {
  const session = await auth.api.getSession({ headers: request.headers });

  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const reviews = await getRecentReviews(session.user.id);

  return Response.json({ reviews });
}

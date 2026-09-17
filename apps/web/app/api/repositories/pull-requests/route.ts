import { auth } from "@/lib/auth";
import { getAsPositiveInteger } from "@/lib/nums";
import {
  checkRepositoryRequest,
  getOpenPullRequests,
} from "@/lib/repositories";

export async function GET(request: Request) {
  const session = await auth.api.getSession({ headers: request.headers });

  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(request.url);
  const page = getAsPositiveInteger(url.searchParams.get("page"), 1);
  const perPage = getAsPositiveInteger(url.searchParams.get("perPage"), 25);

  if (page === null || perPage === null || perPage > 100) {
    return Response.json(
      {
        error:
          "page must be a positive integer and perPage must be between 1 and 100.",
      },
      { status: 400 },
    );
  }

  const repoCheck = await checkRepositoryRequest(request);
  if (!repoCheck.success) {
    return Response.json({ error: repoCheck.error }, { status: 400 });
  }

  try {
    const result = await getOpenPullRequests(repoCheck.repository, {
      page,
      perPage,
    });

    if (!result) {
      return Response.json(
        {
          error:
            "We couldn't fetch open pull requests. Private repositories aren't supported yet.",
        },
        { status: 404 },
      );
    }

    return Response.json({
      pullRequests: result.pullRequests,
      nextPage: result.hasNextPage ? page + 1 : null,
    });
  } catch {
    return Response.json(
      {
        error:
          "We couldn't fetch open pull requests from this repository. Please try again.",
      },
      { status: 502 },
    );
  }
}

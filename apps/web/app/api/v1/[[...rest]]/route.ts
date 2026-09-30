import { OpenAPIHandler } from "@orpc/openapi/fetch";
import { OpenAPIReferenceHandlerPlugin } from "@orpc/openapi/plugins";

import { auth } from "@/lib/auth";
import { errorStatusMap } from "@/lib/orpc/errors";
import { generateOpenAPISpec } from "@/lib/orpc/openapi";
import { apiRouter } from "@/lib/orpc/server/router";
import { hasValidWorkerToken } from "@/lib/worker-auth";

const handler = new OpenAPIHandler(apiRouter, {
  errorStatusMap,
  plugins: [
    new OpenAPIReferenceHandlerPlugin({
      docsPath: "/docs",
      specPath: "/openapi.json",
      provider: "scalar",
      spec: generateOpenAPISpec,
      allow: async ({ context }) => {
        if (process.env.NODE_ENV !== "production") {
          return true;
        }

        if (hasValidWorkerToken(context.headers)) {
          return true;
        }

        return Boolean(await auth.api.getSession({ headers: context.headers }));
      },
    }),
  ],
});

async function handleRequest(request: Request) {
  const { response } = await handler.handle(request, {
    prefix: "/api/v1",
    context: { headers: request.headers },
  });

  return response ?? new Response("Not found", { status: 404 });
}

export const HEAD = handleRequest;
export const GET = handleRequest;
export const POST = handleRequest;
export const PUT = handleRequest;
export const PATCH = handleRequest;
export const DELETE = handleRequest;

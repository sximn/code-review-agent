import { RPCHandler } from "@orpc/server/fetch";

import { errorStatusMap } from "@/lib/orpc/errors";
import { appRouter } from "@/lib/orpc/server/router";

const handler = new RPCHandler(appRouter, { errorStatusMap });

async function handleRequest(request: Request) {
  const { response } = await handler.handle(request, {
    prefix: "/rpc",
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

import { ReadableStream as NodeReadableStream } from "node:stream/web";

import { describe, expect, it } from "vitest";

import { generateOpenAPISpec } from "@/lib/orpc/openapi";

describe("OpenAPI specification", () => {
  it("describes the public and worker APIs with their authentication", async () => {
    globalThis.ReadableStream ??= NodeReadableStream as typeof ReadableStream;
    const spec = await generateOpenAPISpec();

    expect(spec.openapi).toBe("3.1.1");
    expect(spec.servers).toEqual([{ url: "/api/v1" }]);
    expect(spec.paths).toHaveProperty("/repositories/{repositoryId}/reviews");
    expect(spec.paths).toHaveProperty(
      "/internal/reviews/{reviewId}/state.patch.operationId",
      "updateReviewState",
    );
    expect(
      spec.paths?.["/internal/reviews/{reviewId}/state"]?.patch?.security,
    ).toEqual([{ workerBearer: [] }]);
    expect(spec.components?.securitySchemes).toMatchObject({
      sessionCookie: { type: "apiKey", in: "cookie" },
      workerBearer: { type: "http", scheme: "bearer" },
    });
  });
});

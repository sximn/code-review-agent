import { OpenAPIGenerator } from "@orpc/openapi";
import { ZodToJsonSchemaConverter } from "@orpc/zod";

import { apiContract } from "@/lib/orpc/contracts";
import { errorStatusMap } from "@/lib/orpc/errors";

const generator = new OpenAPIGenerator({
  converters: [new ZodToJsonSchemaConverter({ cache: true })],
});

export function generateOpenAPISpec() {
  return generator.generate(apiContract, {
    version: "3.1.1",
    errorStatusMap,
    base: {
      info: {
        title: "REWY API",
        version: "1.0.0",
        description:
          "Typed API for repository management and AI code review workflows.",
      },
      servers: [{ url: "/api/v1" }],
      security: [{ sessionCookie: [] }],
      components: {
        securitySchemes: {
          sessionCookie: {
            type: "apiKey",
            in: "cookie",
            name: "better-auth.session_token",
          },
          workerBearer: {
            type: "http",
            scheme: "bearer",
            bearerFormat: "worker token",
          },
        },
      },
    },
  });
}

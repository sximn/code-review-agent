import "server-only";

import { z } from "zod";

const envSchema = z.object({
  NODE_ENV: z.literal(["development", "production"]),

  DATABASE_URL: z.url(),
  REDIS_URL: z.url(),
  BETTER_AUTH_URL: z.url(),

  GOOGLE_CLIENT_ID: z.string(),
  GOOGLE_CLIENT_SECRET: z.string(),
  GITHUB_CLIENT_ID: z.string(),
  GITHUB_CLIENT_SECRET: z.string(),

  JOB_STREAM: z.string(),
  REVIEW_JOB_NAME: z.string(),
  WORKER_API_TOKEN: z.string().min(32),
});

export const env = envSchema.parse(process.env);

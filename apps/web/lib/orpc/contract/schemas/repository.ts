import { GIT_OBJECT_ID_PATTERN } from "@/lib/repository-pull-request-utils";
import { z } from "zod";

export const repositoryNameSchema = z
  .string()
  .trim()
  .regex(/^[^/\s]+\/[^/\s]+$/, "Use owner/repository format");

export const publicRepositorySchema = z
  .object({
    fullName: repositoryNameSchema,
  })
  .strict()
  .meta({ id: "PublicRepository" });

export const connectedRepositorySchema = z
  .object({
    id: z.uuid(),
    fullName: repositoryNameSchema,
  })
  .strict()
  .meta({ id: "ConnectedRepository" });

export const pullRequestSchema = z
  .object({
    number: z.int().positive(),
    headSha: z.string().regex(new RegExp(GIT_OBJECT_ID_PATTERN)),
    url: z.url(),
    title: z.string(),
    description: z.string(),
    updatedAt: z.date(),
  })
  .strict()
  .meta({ id: "PullRequest" });

export type PullRequest = z.infer<typeof pullRequestSchema>;

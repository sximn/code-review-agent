CREATE TABLE "pull_request" (
	"id" text PRIMARY KEY,
	"repository_id" text NOT NULL,
	"number" integer NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "pull_request_number_positive" CHECK ("number" > 0)
);
--> statement-breakpoint
CREATE TABLE "pull_request_version" (
	"id" text PRIMARY KEY,
	"pull_request_id" text NOT NULL,
	"head_sha" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "pull_request_version_head_sha_valid" CHECK ("head_sha" is null or "head_sha" ~ '^[0-9a-f]{40}$')
);
--> statement-breakpoint
-- Historical reviews never stored a SHA. Preserve them under one unknown version
-- per PR rather than assigning the current GitHub head to old results.
INSERT INTO "pull_request" ("id", "repository_id", "number", "created_at")
SELECT gen_random_uuid()::text, "repository_id", "pull_request_number", min("created_at")
FROM "review" GROUP BY "repository_id", "pull_request_number";
--> statement-breakpoint
INSERT INTO "pull_request_version" ("id", "pull_request_id", "head_sha", "created_at")
SELECT gen_random_uuid()::text, "id", NULL, "created_at" FROM "pull_request";
--> statement-breakpoint
ALTER TABLE "review" ADD COLUMN "pull_request_version_id" text;
--> statement-breakpoint
UPDATE "review" AS r SET "pull_request_version_id" = v."id"
FROM "pull_request" AS pr JOIN "pull_request_version" AS v ON v."pull_request_id" = pr."id"
WHERE pr."repository_id" = r."repository_id" AND pr."number" = r."pull_request_number";
--> statement-breakpoint
ALTER TABLE "review" ALTER COLUMN "pull_request_version_id" SET NOT NULL;
--> statement-breakpoint
ALTER TABLE "review" DROP CONSTRAINT "review_repository_id_repository_id_fkey";
--> statement-breakpoint
DROP INDEX "review_repository_id_idx";
--> statement-breakpoint
ALTER TABLE "review" DROP COLUMN "repository_id";
--> statement-breakpoint
ALTER TABLE "review" DROP COLUMN "pull_request_number";
--> statement-breakpoint
CREATE UNIQUE INDEX "pull_request_repository_number_idx" ON "pull_request" ("repository_id","number");--> statement-breakpoint
CREATE UNIQUE INDEX "pull_request_version_pr_sha_idx" ON "pull_request_version" ("pull_request_id","head_sha");--> statement-breakpoint
CREATE UNIQUE INDEX "pull_request_version_unknown_sha_idx" ON "pull_request_version" ("pull_request_id") WHERE "head_sha" is null;--> statement-breakpoint
CREATE INDEX "review_pull_request_version_id_idx" ON "review" ("pull_request_version_id");--> statement-breakpoint
ALTER TABLE "pull_request" ADD CONSTRAINT "pull_request_repository_id_repository_id_fkey" FOREIGN KEY ("repository_id") REFERENCES "repository"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "pull_request_version" ADD CONSTRAINT "pull_request_version_pull_request_id_pull_request_id_fkey" FOREIGN KEY ("pull_request_id") REFERENCES "pull_request"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "review" ADD CONSTRAINT "review_pull_request_version_id_pull_request_version_id_fkey" FOREIGN KEY ("pull_request_version_id") REFERENCES "pull_request_version"("id") ON DELETE CASCADE;
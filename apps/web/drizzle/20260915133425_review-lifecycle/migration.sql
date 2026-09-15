CREATE TYPE "review_status" AS ENUM('scheduled', 'running', 'failed', 'finished');--> statement-breakpoint
CREATE TABLE "review" (
	"id" text PRIMARY KEY,
	"repository_id" text NOT NULL,
	"pull_request_number" integer NOT NULL,
	"status" "review_status" DEFAULT 'scheduled'::"review_status" NOT NULL,
	"result" jsonb,
	"error" text,
	"started_at" timestamp,
	"finished_at" timestamp,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "review_repository_id_idx" ON "review" ("repository_id");--> statement-breakpoint
ALTER TABLE "review" ADD CONSTRAINT "review_repository_id_repository_id_fkey" FOREIGN KEY ("repository_id") REFERENCES "repository"("id") ON DELETE CASCADE;
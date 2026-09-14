CREATE TABLE "repository" (
	"id" text PRIMARY KEY,
	"full_name" text NOT NULL,
	"is_private" boolean DEFAULT false NOT NULL,
	"user_id" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "repository_user_id_idx" ON "repository" ("user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "repository_user_full_name_idx" ON "repository" ("user_id","full_name");--> statement-breakpoint
ALTER TABLE "repository" ADD CONSTRAINT "repository_user_id_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE CASCADE;
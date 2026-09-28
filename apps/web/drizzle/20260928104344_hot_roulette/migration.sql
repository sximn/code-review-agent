CREATE TABLE "review_usage" (
	"id" text PRIMARY KEY,
	"review_id" text NOT NULL,
	"request_count" integer NOT NULL,
	"responses_with_usage" integer NOT NULL,
	"input_tokens" integer NOT NULL,
	"cached_input_tokens" integer NOT NULL,
	"cache_write_tokens" integer NOT NULL,
	"output_tokens" integer NOT NULL,
	"reasoning_tokens" integer NOT NULL,
	"total_tokens" integer NOT NULL,
	"esitmated_cost_usd" numeric NOT NULL
);
--> statement-breakpoint
ALTER TABLE "review_usage" ADD CONSTRAINT "review_usage_review_id_review_id_fkey" FOREIGN KEY ("review_id") REFERENCES "review"("id") ON DELETE CASCADE;
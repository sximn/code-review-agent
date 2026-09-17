import { getRedis } from "./redis";
import env from "@/lib/environment";

export type ReviewJobPayload = {
  repository: string;
  pull_request: number;
};

export async function enqueueReviewJob(
  jobId: string,
  payload: ReviewJobPayload,
) {
  const redis = await getRedis();

  const streamId = await redis.xAdd(
    env.JOB_STREAM,
    "*", // `*` to automatically generate ID internally by redis
    {
      job_id: jobId,
      type: env.REVIEW_JOB_NAME,
      payload: JSON.stringify(payload),
      created_at: new Date().toISOString(),
    },
  );

  return {
    jobId,
    streamId,
  };
}

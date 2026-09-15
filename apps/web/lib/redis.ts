import { createClient } from "redis";

let redis: ReturnType<typeof createClient> | undefined;

export async function getRedis() {
  if (!redis) {
    const url = process.env.REDIS_URL;
    if (!url) {
      throw new Error("REDIS_URL is required at runtime");
    }

    redis = createClient({ url });
    redis.on("error", (error) => console.error("Redis error", error));
  }

  if (!redis.isOpen) {
    await redis.connect();
  }

  return redis;
}

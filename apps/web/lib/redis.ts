import { createClient } from "redis";
import env from '@/lib/environment';

let redis: ReturnType<typeof createClient> | undefined;

export async function getRedis() {
  if (!redis) {
    redis = createClient({ url: env.REDIS_URL });
    redis.on("error", (error) => console.error("Redis error", error));
  }

  if (!redis.isOpen) {
    await redis.connect();
  }

  return redis;
}

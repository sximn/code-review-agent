import { timingSafeEqual } from "node:crypto";

import { env } from "@/lib/env/environment";

export function hasValidWorkerToken(headers: Headers): boolean {
  const received = headers.get("authorization") ?? "";
  const expected = `Bearer ${env.WORKER_API_TOKEN}`;
  const receivedBuffer = Buffer.from(received);
  const expectedBuffer = Buffer.from(expected);

  return (
    receivedBuffer.length === expectedBuffer.length &&
    timingSafeEqual(receivedBuffer, expectedBuffer)
  );
}

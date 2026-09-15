import { db } from "@/db/drizzle";
import { getRedis } from "@/lib/redis";

export async function GET() {
  try {

    await db.execute('select 1');

    await (await getRedis()).ping();

    return Response.json(
      { status: 'healthy', timestamp: new Date().toISOString() }
    );
  } catch (err) {
    return Response.json(
      { status: 'unhealthy', error: String(err) },
      { status: 503 }
    );
  }
}

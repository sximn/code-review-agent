import { db } from "@/db/drizzle";

export async function GET() {
  try {
    await db.execute('select 1');
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

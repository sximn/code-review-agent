
import { drizzle } from 'drizzle-orm/postgres-js';
import { relations } from './relations';
import postgres from 'postgres';
import env from '@/lib/environment';

const connectionString = env.DATABASE_URL;
const client = postgres(connectionString, { prepare: false });


export const db = drizzle({
  client, 
  relations,
});


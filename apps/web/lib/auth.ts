import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { db } from "@/db/drizzle";
import * as schema from "@/db/schema";
import { nextCookies } from "better-auth/next-js";

export const auth = betterAuth({
    database: drizzleAdapter(db, {
        provider: "pg",
        schema,
    }),
    emailAndPassword: { 
        enabled: true, 
    },
    plugins: [
        nextCookies(), // make sure this is the last plugin in the array
    ],
    user: {
        deleteUser: {
            enabled: true,
        },
    },
});

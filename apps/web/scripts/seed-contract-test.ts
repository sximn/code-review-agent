import postgres from "postgres";

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  throw new Error("DATABASE_URL is required");
}

const sql = postgres(databaseUrl, { prepare: false });

try {
  await sql.begin(async (transaction) => {
    await transaction`
      insert into "user" (id, name, email, email_verified)
      values ('contract-test-user', 'Contract Test', 'contract-test@example.com', true)
      on conflict (id) do nothing
    `;
    await transaction`
      insert into repository (id, full_name, is_private, user_id)
      values (
        '11111111-1111-4111-8111-111111111111',
        'example/contract-test',
        false,
        'contract-test-user'
      )
      on conflict (id) do nothing
    `;
    await transaction`
      insert into review (
        id,
        repository_id,
        pull_request_number,
        status,
        result,
        error,
        started_at,
        finished_at,
        updated_at
      )
      values (
        '22222222-2222-4222-8222-222222222222',
        '11111111-1111-4111-8111-111111111111',
        1,
        'scheduled',
        null,
        null,
        null,
        null,
        now()
      )
      on conflict (id) do update set
        status = 'scheduled',
        result = null,
        error = null,
        started_at = null,
        finished_at = null,
        updated_at = now()
    `;
  });
} finally {
  await sql.end();
}

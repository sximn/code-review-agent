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
    const [pr] = await transaction`
      insert into pull_request (id, repository_id, number)
      values ('33333333-3333-4333-8333-333333333333', '11111111-1111-4111-8111-111111111111', 1)
      on conflict (repository_id, number) do update set number = excluded.number
      returning id
    `;
    const [version] = await transaction`
      insert into pull_request_version (id, pull_request_id, head_sha)
      values ('44444444-4444-4444-8444-444444444444', ${pr.id}, repeat('a', 40))
      on conflict (pull_request_id, head_sha) do update set head_sha = excluded.head_sha
      returning id
    `;
    await transaction`
      insert into review (
        id,
        pull_request_version_id,
        status,
        result,
        error,
        started_at,
        finished_at,
        updated_at
      )
      values (
        '22222222-2222-4222-8222-222222222222',
        ${version.id},
        'scheduled',
        null,
        null,
        null,
        null,
        now()
      )
      on conflict (id) do update set
        pull_request_version_id = excluded.pull_request_version_id,
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

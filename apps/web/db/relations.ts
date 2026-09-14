import { defineRelations } from 'drizzle-orm';
import * as schema from './schema';

export const relations = defineRelations(
  schema,
  (r) => ({
    user: {
      sessions: r.many.session(),
      accounts: r.many.account(),
      repositories: r.many.repository(),
    },

    session: {
      user: r.one.user({
        from: r.session.userId,
        to: r.user.id,
      }),
    },

    account: {
      user: r.one.user({
        from: r.account.userId,
        to: r.user.id,
      }),
    },

    repository: {
      user: r.one.user({
        from: r.repository.userId,
        to: r.user.id,
      }),
    },
  }),
);

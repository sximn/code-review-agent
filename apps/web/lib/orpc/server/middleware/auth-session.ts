import { auth } from "@/lib/auth";
import { appImplementer } from "../contract-implementer";

export const requireSession = appImplementer.middleware(
  async ({ context, next, errors }) => {
    const session = await auth.api.getSession({ headers: context.headers });
    if (!session) {
      throw errors.UNAUTHORIZED();
    }

    return next({ context: { session } });
  },
);

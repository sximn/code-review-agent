import { oc } from "@orpc/contract";

export const authenticated = oc.errors({
  UNAUTHORIZED: { message: "Unauthorized." },
});

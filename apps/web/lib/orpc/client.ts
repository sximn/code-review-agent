import { createORPCClient } from "@orpc/client";
import { RPCLink } from "@orpc/client/fetch";
import type { RouterContractClient } from "@orpc/contract";
import { createTanstackQueryUtils } from "@orpc/tanstack-query";

import type { appContract } from "@/lib/orpc/contracts";

const link = new RPCLink({
  url: "/rpc",
});

export const client: RouterContractClient<typeof appContract> =
  createORPCClient(link);

export const orpc = createTanstackQueryUtils(client);

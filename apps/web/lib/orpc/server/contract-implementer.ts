import { implement } from "@orpc/server";
import { appContract, internalContract } from "../contract";
import { RequestContext } from "./context";

export const appImplementer = implement(appContract).$context<RequestContext>();

export const internalImplementer =
  implement(internalContract).$context<RequestContext>();

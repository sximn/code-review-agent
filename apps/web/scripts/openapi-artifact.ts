import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

import { generateOpenAPISpec } from "@/lib/orpc/openapi";

export async function renderOpenAPIArtifact(): Promise<string> {
  const spec = await generateOpenAPISpec();
  return `${JSON.stringify(spec, null, 2)}\n`;
}

export function resolveOutputPath(outputPath: string): string {
  return resolve(process.cwd(), outputPath);
}

export async function writeOpenAPIArtifact(outputPath: string): Promise<void> {
  const resolvedPath = resolveOutputPath(outputPath);
  await mkdir(dirname(resolvedPath), { recursive: true });
  await writeFile(resolvedPath, await renderOpenAPIArtifact(), "utf8");
}

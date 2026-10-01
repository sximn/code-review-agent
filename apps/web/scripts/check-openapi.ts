import { checkOpenAPIArtifact } from "./openapi-artifact";

const outputPath = process.argv[2];

if (!outputPath) {
  throw new Error("Usage: tsx scripts/check-openapi.ts <output-path>");
}

await checkOpenAPIArtifact(outputPath);

import { writeOpenAPIArtifact } from "./openapi-artifact";

const outputPath = process.argv[2];

if (!outputPath) {
  throw new Error("Usage: tsx scripts/export-openapi.ts <output-path>");
}

await writeOpenAPIArtifact(outputPath);

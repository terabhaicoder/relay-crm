// Generate TypeScript contracts from the actual FastAPI OpenAPI document.
// Unsupported composition keywords fail closed instead of silently inventing types.
import { readFile, writeFile } from "node:fs/promises";
const document = JSON.parse(await readFile(new URL("../openapi.json", import.meta.url), "utf8"));
const schemas = document.components?.schemas ?? {};
const identifier = name => name.replace(/[^A-Za-z0-9_]/g, "_");
function typeOf(schema = {}) {
  for (const key of ["not", "prefixItems", "unevaluatedProperties"]) {
    if (key in schema) throw new Error(`Unsupported OpenAPI keyword: ${key}`);
  }
  if (schema.$ref) {
    const name = schema.$ref.replace("#/components/schemas/", "");
    if (!(name in schemas)) throw new Error(`Unknown reference ${schema.$ref}`);
    return identifier(name);
  }
  if (schema.anyOf || schema.oneOf) return `(${(schema.anyOf ?? schema.oneOf).map(typeOf).join(" | ")})`;
  if (schema.allOf) return `(${schema.allOf.map(typeOf).join(" & ")})`;
  if (schema.enum) return schema.enum.map(value => JSON.stringify(value)).join(" | ");
  if ("const" in schema) return JSON.stringify(schema.const);
  if (Array.isArray(schema.type)) return schema.type.map(type => typeOf({ ...schema, type })).join(" | ");
  if (schema.type === "string") return "string";
  if (schema.type === "boolean") return "boolean";
  if (schema.type === "number" || schema.type === "integer") return "number";
  if (schema.type === "null") return "null";
  if (schema.type === "array") return `Array<${typeOf(schema.items)}>`;
  if (schema.type === "object" || schema.properties) {
    const properties = Object.entries(schema.properties ?? {}).map(([name, value]) => `${JSON.stringify(name)}${schema.required?.includes(name) ? "" : "?"}: ${typeOf(value)};`);
    const extra = schema.additionalProperties;
    if (!properties.length) return `Record<string, ${extra && typeof extra === "object" ? typeOf(extra) : "unknown"}>`;
    if (extra === true || (extra && typeof extra === "object")) properties.push(`[key: string]: ${extra === true ? "unknown" : typeOf(extra)};`);
    return `{ ${properties.join(" ")} }`;
  }
  if (!schema.type) return "unknown";
  throw new Error(`Unsupported OpenAPI type ${schema.type}`);
}
const aliases = Object.keys(schemas).map(identifier);
if (new Set(aliases).size !== aliases.length) throw new Error("Schema type names collide");
const lines = ["// Generated from frontend/openapi.json. Do not edit."];
for (const [name, value] of Object.entries(schemas)) lines.push(`export type ${identifier(name)} = ${typeOf(value)};`);
const operations = [];
for (const [path, pathItem] of Object.entries(document.paths)) {
  for (const [method, operation] of Object.entries(pathItem)) {
    if (!["get", "post", "put", "patch", "delete", "head", "options"].includes(method)) continue;
    const request = operation.requestBody?.content?.["application/json"]?.schema;
    const responses = Object.entries(operation.responses ?? {}).filter(([status]) => status.startsWith("2")).map(([, response]) => {
      const body = response.content?.["application/json"]?.schema;
      return body ? typeOf(body) : "void";
    });
    operations.push(`${JSON.stringify(`${method.toUpperCase()} ${path}`)}: { request: ${request ? typeOf(request) : "never"}; response: ${responses.join(" | ") || "unknown"}; };`);
    if (path === "/api/v1/health/live") lines.push(`export type LivenessResponse = ${responses[0]};`);
    if (path === "/api/v1/health/ready") lines.push(`export type ReadinessResponse = ${responses[0]};`);
  }
}
lines.push(`export type ApiOperations = {\n${operations.join("\n")}\n};`);
const output = `${lines.join("\n\n")}\n`;
const destination = new URL("../src/lib/api/schema.ts", import.meta.url);
if (process.argv.includes("--check")) {
  if (await readFile(destination, "utf8") !== output) throw new Error("API contracts changed. Run npm run generate:api.");
} else await writeFile(destination, output);

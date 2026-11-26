// Gera apps/web/src/lib/api/schema.ts a partir de packages/contracts/openapi.json.
// Sem dependências: o openapi-typescript exige TypeScript 5 e este pacote usa o 7.
// Uso: node scripts/generate-api-types.mjs [--check]
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const contractPath = fileURLToPath(new URL('../../../packages/contracts/openapi.json', import.meta.url));
const outputPath = fileURLToPath(new URL('../src/lib/api/schema.ts', import.meta.url));

const spec = JSON.parse(readFileSync(contractPath, 'utf8'));

// Nomes do Pydantic como Page[AccountOut] viram Page_AccountOut_ no OpenAPI; usamos um nome TS legível.
const typeName = (name) => name.replace(/^Page_(\w+)_$/, 'Page$1');
const refName = (ref) => typeName(ref.split('/').pop());

function tsType(schema) {
  if (!schema) return 'unknown';
  if (schema.$ref) return refName(schema.$ref);
  if (schema.enum) return schema.enum.map((v) => JSON.stringify(v)).join(' | ');
  if (schema.anyOf) return [...new Set(schema.anyOf.map(tsType))].join(' | ');
  switch (schema.type) {
    case 'string': return 'string';
    // Inteiros do contrato (centavos inclusive) chegam como number JSON; ver ADR-0009.
    case 'integer':
    case 'number': return 'number';
    case 'boolean': return 'boolean';
    case 'null': return 'null';
    case 'array': return `${tsType(schema.items)}[]`;
    case 'object': return objectType(schema, '');
    default: return 'unknown';
  }
}

function objectType(schema, indent) {
  const props = schema.properties ?? {};
  const required = new Set(schema.required ?? []);
  const keys = Object.keys(props);
  if (keys.length === 0) return schema.additionalProperties ? 'Record<string, unknown>' : 'Record<string, never>';
  const lines = keys.map((key) => {
    const optional = required.has(key) ? '' : '?';
    const fmt = props[key].format ? `/** ${props[key].format} */ ` : '';
    return `${indent}  ${fmt}${key}${optional}: ${tsType(props[key])};`;
  });
  return `{\n${lines.join('\n')}\n${indent}}`;
}

const pascal = (id) => id.split('_').map((p) => p[0].toUpperCase() + p.slice(1)).join('');

let out = '// Código gerado por apps/web/scripts/generate-api-types.mjs a partir de\n';
out += '// packages/contracts/openapi.json. Não edite: rode `npm run gen:api`.\n\n';

for (const [name, schema] of Object.entries(spec.components?.schemas ?? {})) {
  if (schema.description) out += `/** ${schema.description.replace(/\*\//g, '*\\/')} */\n`;
  out += `export type ${typeName(name)} = ${schema.type === 'object' || schema.properties ? objectType(schema, '') : tsType(schema)};\n\n`;
}

const operations = [];
for (const [path, methods] of Object.entries(spec.paths)) {
  for (const [method, op] of Object.entries(methods)) {
    operations.push({ path, method: method.toUpperCase(), id: op.operationId });
    const query = (op.parameters ?? []).filter((p) => p.in === 'query');
    if (query.length) {
      const schema = { type: 'object', properties: Object.fromEntries(query.map((p) => [p.name, p.schema])), required: query.filter((p) => p.required).map((p) => p.name) };
      out += `export type ${pascal(op.operationId)}Query = ${objectType(schema, '')};\n\n`;
    }
  }
}

out += 'export const OPERATIONS = {\n';
for (const op of operations) out += `  ${op.id}: { method: '${op.method}', path: '${op.path}' },\n`;
out += '} as const;\n';

if (process.argv.includes('--check')) {
  let current = '';
  try { current = readFileSync(outputPath, 'utf8'); } catch { /* ausente conta como desatualizado */ }
  if (current !== out) {
    console.error('src/lib/api/schema.ts está desatualizado. Rode `npm run gen:api`.');
    process.exit(1);
  }
  console.log('Tipos da API em dia com o OpenAPI.');
} else {
  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, out);
  console.log(`Gerado ${outputPath}`);
}

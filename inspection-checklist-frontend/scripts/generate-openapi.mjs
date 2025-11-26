#!/usr/bin/env node
import { spawnSync } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

const DEFAULT_BASE_URL = 'http://localhost:8000'
const repoRoot = path.resolve(process.cwd(), '..')
const outputPath = 'src/api/gen/schema.ts'
const npxCommand = process.platform === 'win32' ? 'npx.cmd' : 'npx'

async function downloadSchema(url) {
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Unexpected status ${response.status}`)
    }
    const schemaText = await response.text()
    return writeTempSchema(schemaText)
  } catch (error) {
    console.warn(`[generate:api] Unable to download schema from ${url}: ${error.message}`)
    return null
  }
}

function writeTempSchema(contents = '') {
  const tempDir = mkdtempSync(path.join(tmpdir(), 'openapi-schema-'))
  const filePath = path.join(tempDir, 'schema.json')
  writeFileSync(filePath, contents)
  return filePath
}

function generateSchemaLocally() {
  const pythonScript = `
import json
import sys
from pathlib import Path

from fastapi.openapi.utils import get_openapi
from app.main import app

schema = get_openapi(
    title=app.title,
    version=app.version,
    description=app.description,
    routes=app.routes,
)
Path(sys.argv[1]).write_text(json.dumps(schema, indent=2))
`
  const schemaPath = writeTempSchema()
  const pythonCommand = process.env.PYTHON ?? 'python'
  const env = { ...process.env }
  env.PYTHONPATH = env.PYTHONPATH ? `${repoRoot}${path.delimiter}${env.PYTHONPATH}` : repoRoot
  const pythonResult = spawnSync(pythonCommand, ['-c', pythonScript, schemaPath], {
    cwd: repoRoot,
    env,
    stdio: 'inherit',
  })

  if (pythonResult.error) {
    console.error('[generate:api] Failed to execute python for local schema:', pythonResult.error)
    process.exit(1)
  }
  if (pythonResult.status !== 0) {
    process.exit(pythonResult.status ?? 1)
  }
  return schemaPath
}

function runTypeGenerator(schemaSource) {
  const result = spawnSync(npxCommand, ['openapi-typescript', schemaSource, '-o', outputPath], {
    stdio: 'inherit',
  })
  if (result.error) {
    console.error('[generate:api] Failed to run openapi-typescript:', result.error)
    process.exit(1)
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

async function main() {
  const rawBaseUrl = (process.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL).trim()
  if (!process.env.VITE_API_BASE_URL) {
    console.warn(`[generate:api] VITE_API_BASE_URL is not set. Defaulting to ${DEFAULT_BASE_URL}`)
  }
  const normalizedBaseUrl = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl
  const openapiUrl = `${normalizedBaseUrl}/openapi.json`

  let schemaSource = null
  if (!process.env.GENERATE_API_LOCAL_ONLY) {
    schemaSource = await downloadSchema(openapiUrl)
  }
  if (!schemaSource) {
    console.warn('[generate:api] Falling back to generating schema from local FastAPI app')
    schemaSource = generateSchemaLocally()
  } else {
    console.log(`[generate:api] Using schema downloaded from ${openapiUrl}`)
  }
  runTypeGenerator(schemaSource)
}

main().catch((error) => {
  console.error('[generate:api] Unhandled error:', error)
  process.exit(1)
})

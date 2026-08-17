// Post-build obfuscation step for the production bundle.
// Obfuscates ONLY app chunks (page/index code) and leaves vendor chunks
// (react, lightweight-charts, framer-motion, etc.) untouched so they stay
// readable and de-duplicatable. Conservative options: no control-flow
// flattening, no dead-code injection, no debug traps — those break apps and
// cost runtime performance for little extra deterrence.

import { readdir, readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import JavaScriptObfuscator from 'javascript-obfuscator'

const ASSETS_DIR = join(import.meta.dirname, '..', 'dist', 'assets')
const VENDOR_PREFIXES = ['charts-', 'motion-', 'react-vendor-', 'vendor-']

const OPTIONS = {
  compact: true,
  identifierNamesGenerator: 'hexadecimal',
  renameGlobals: false,
  stringArray: true,
  stringArrayEncoding: ['base64'],
  stringArrayThreshold: 0.5,
  controlFlowFlattening: false,
  deadCodeInjection: false,
  debugProtection: false,
  selfDefending: false,
  disableConsoleOutput: false,
  sourceMap: false,
  target: 'browser',
}

const files = (await readdir(ASSETS_DIR)).filter((f) => f.endsWith('.js'))
const appChunks = files.filter(
  (f) => !VENDOR_PREFIXES.some((p) => f.startsWith(p)) && !f.includes('index.css'),
)

let totalIn = 0
let totalOut = 0
for (const file of appChunks) {
  const path = join(ASSETS_DIR, file)
  const source = await readFile(path, 'utf-8')
  const before = Buffer.byteLength(source, 'utf-8')
  let result
  try {
    result = JavaScriptObfuscator.obfuscate(source, OPTIONS).getObfuscatedCode()
  } catch (err) {
    console.error(`[obfuscate] FAILED on ${file}:`, err.message)
    process.exit(1)
  }
  await writeFile(path, result, 'utf-8')
  const after = Buffer.byteLength(result, 'utf-8')
  totalIn += before
  totalOut += after
  const pct = before ? (((after - before) / before) * 100).toFixed(0) : '0'
  console.log(`[obfuscate] ${file}: ${(before / 1024).toFixed(1)}KB -> ${(after / 1024).toFixed(1)}KB (${pct}%)`)
}
console.log(
  `[obfuscate] done: ${appChunks.length} app chunks obfuscated, ` +
    `${files.length - appChunks.length} vendor chunks skipped ` +
    `(${(totalOut / 1024).toFixed(0)}KB vs ${(totalIn / 1024).toFixed(0)}KB)`,
)

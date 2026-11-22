#!/usr/bin/env node
// Validate a PPTD v2 project structurally and semantically without exporting.
import path from 'node:path';
import { parseArgs as parseNodeArgs } from 'node:util';

import { projectSummary, validateProject } from './lib/deck/project.mjs';

export function parseArgs(argv) {
  const { values, positionals } = parseNodeArgs({
    args: argv,
    allowPositionals: true,
    options: {
      'check-fonts': { type: 'boolean', default: false },
      'font-dir': { type: 'string', multiple: true },
      offline: { type: 'boolean', default: false },
      help: { type: 'boolean', short: 'h', default: false },
    },
  });
  if (positionals.length > 1) throw new Error(`unexpected positional argument: ${positionals[1]}`);
  const fontDirs = values['font-dir'] ?? [];
  if (fontDirs.length && !values['check-fonts']) {
    throw new Error('--font-dir requires --check-fonts');
  }
  return {
    input: positionals[0] ?? null,
    checkFonts: values['check-fonts'],
    fontDirs,
    offline: values.offline,
    help: values.help,
  };
}

function usage() {
  return [
    'Usage: node validate.mjs <manifest.pptd|project directory> [options]',
    '',
    'Options:',
    '  --check-fonts      Resolve fonts and report substitution/style/embedding/coverage warnings',
    '  --font-dir PATH    Additional local TTF/TTC/OTF/EOT font directory (repeatable; requires --check-fonts)',
    '  --offline          Forbid uncached Google Fonts requests during --check-fonts',
    '  -h, --help         Show this help message',
  ].join('\n');
}

export async function runCli(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.help) {
    console.log(usage());
    return 0;
  }
  if (!args.input) {
    throw new Error('input .pptd manifest or project directory is required');
  }
  const project = await validateProject(args.input, {
    checkFonts: args.checkFonts,
    fontDirs: args.fontDirs,
    offline: args.offline,
  });
  for (const warning of project.warnings) {
    process.stderr.write(`[pptd] warning: ${warning}\n`);
  }
  console.log(JSON.stringify(projectSummary(project), null, 2));
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === import.meta.filename) {
  runCli().then(
    (code) => { process.exitCode = code; },
    (error) => {
      console.error(`pptd validation failed: ${error.message}`);
      process.exitCode = 1;
    },
  );
}

#!/usr/bin/env node
// Validate a PPTD v2 project structurally without exporting.
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { projectSummary, readProject } from './lib/deck/project.mjs';

export function runCli(argv = process.argv.slice(2)) {
  if (argv.includes('--help') || argv.includes('-h')) {
    console.log('Usage: node validate.mjs <manifest.pptd|project directory>');
    return 0;
  }
  if (argv.length !== 1 || argv[0].startsWith('-')) {
    throw new Error('usage: node validate.mjs <manifest.pptd|project directory>');
  }
  const project = readProject(argv[0]);
  for (const warning of project.warnings) {
    process.stderr.write(`[pptd] warning: ${warning}\n`);
  }
  console.log(JSON.stringify(projectSummary(project), null, 2));
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try {
    process.exitCode = runCli();
  } catch (error) {
    console.error(`pptd validation failed: ${error.message}`);
    process.exitCode = 1;
  }
}

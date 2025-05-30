// leveranciers-portal-nextjs/app/api/sync-ultimo/route.ts
import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function GET(request: Request) {
  console.log('API endpoint /api/sync-ultimo called.');

  // Path to the syncUltimo.ts script.
  // process.cwd() should give the root of the Next.js project.
  // The script is in ./scripts/syncUltimo.ts relative to the 'leveranciers-portal-nextjs' directory.
  // For Next.js server-side code, process.cwd() is typically the project root.
  const projectRoot = process.cwd(); 
  const scriptPath = path.join(projectRoot, 'scripts', 'syncUltimo.ts');
  const tsNodePath = path.join(projectRoot, 'node_modules', '.bin', 'ts-node'); // More reliable path to ts-node

  console.log(`Attempting to run script: ${tsNodePath} ${scriptPath}`);

  // Use a Promise to handle the asynchronous nature of the script execution
  return new Promise((resolve) => {
    const syncProcess = spawn(tsNodePath, [scriptPath], {
      stdio: 'pipe', // Use 'pipe' to capture stdout/stderr
      cwd: projectRoot, // Set current working directory for the script
      env: { ...process.env }, // Pass environment variables
    });

    let scriptOutput = '';
    let scriptError = '';

    syncProcess.stdout.on('data', (data) => {
      const output = data.toString();
      console.log('Sync script stdout:', output);
      scriptOutput += output;
    });

    syncProcess.stderr.on('data', (data) => {
      const errorOutput = data.toString();
      console.error('Sync script stderr:', errorOutput);
      scriptError += errorOutput;
    });

    syncProcess.on('close', (code) => {
      console.log(`Sync script process exited with code ${code}`);
      if (code === 0) {
        resolve(NextResponse.json({ 
          message: 'Synchronization process completed successfully.',
          output: scriptOutput 
        }));
      } else {
        resolve(NextResponse.json({ 
          message: 'Synchronization process failed.',
          error: scriptError || `Exited with code ${code}`,
          output: scriptOutput
        }, { status: 500 }));
      }
    });

    syncProcess.on('error', (err) => {
      console.error('Failed to start sync script process:', err);
      scriptError += `Failed to start process: ${err.message}\n`;
      // Resolve immediately if the process itself couldn't start
      resolve(NextResponse.json({ 
        message: 'Failed to start synchronization process.', 
        error: scriptError,
        output: scriptOutput 
      }, { status: 500 }));
    });
  });
}

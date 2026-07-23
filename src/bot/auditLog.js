import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const AUDIT_FILE = path.join(__dirname, '../../data/audit.jsonl');

export async function logAudit(entry) {
  try {
    const dir = path.dirname(AUDIT_FILE);
    await fs.mkdir(dir, { recursive: true });
    const line =
      JSON.stringify({
        timestamp: new Date().toISOString(),
        ...entry,
      }) + '\n';
    await fs.appendFile(AUDIT_FILE, line, 'utf-8');
  } catch {
    // non-fatal
  }
}

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

class SessionLogger {
  constructor() {
    this.sessionId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    this.sessionDir = null;
    this.logFile = null;
    this.buffer = [];
    this.flushInterval = null;
  }

  async initialize() {
    const sessionsBase = path.expand('~/.config/opencode/sessions');
    const today = new Date().toISOString().split('T')[0];
    this.sessionDir = path.join(sessionsBase, today);

    await fs.mkdir(this.sessionDir, { recursive: true });
    this.logFile = path.join(this.sessionDir, `${this.sessionId}.jsonl`);

    // Start periodic flush
    this.flushInterval = setInterval(() => this.flush(), 5000);

    this.log({
      type: 'session.start',
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
    });
  }

  log(entry) {
    this.buffer.push({
      ...entry,
      timestamp: entry.timestamp || new Date().toISOString(),
    });
  }

  async flush() {
    if (this.buffer.length === 0) return;

    try {
      const lines = this.buffer
        .map(entry => JSON.stringify(entry))
        .join('\n') + '\n';

      await fs.appendFile(this.logFile, lines, 'utf8');
      this.buffer = [];
    } catch (err) {
      console.error('Session logger flush error:', err);
    }
  }

  async shutdown() {
    if (this.flushInterval) clearInterval(this.flushInterval);
    await this.flush();

    this.log({
      type: 'session.end',
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
    });

    await this.flush();
  }

  async getResume() {
    // Read last session for recovery context
    try {
      const files = await fs.readdir(this.sessionDir);
      if (files.length === 0) return null;

      const latestFile = files.sort().pop();
      const content = await fs.readFile(
        path.join(this.sessionDir, latestFile),
        'utf8'
      );

      const lines = content.trim().split('\n');
      const lastEntry = JSON.parse(lines[lines.length - 1]);

      return {
        lastMode: lastEntry.mode,
        lastTask: lastEntry.lastTask,
        context: lastEntry.context,
      };
    } catch (err) {
      return null;
    }
  }
}

const logger = new SessionLogger();

export default {
  hooks: {
    'session.start': async () => {
      await logger.initialize();
    },

    'chat.message': (message) => {
      logger.log({
        type: 'chat.message',
        role: message.role,
        mode: message.mode,
        content: message.content.substring(0, 200), // Truncate for size
        tokens: message.tokens || 0,
      });
    },

    'tool.execute.before': (execution) => {
      logger.log({
        type: 'tool.execute',
        tool: execution.tool,
        params: JSON.stringify(execution.params).substring(0, 100),
      });
    },

    'experimental.session.compacting': (context) => {
      logger.log({
        type: 'session.context',
        mode: context.mode,
        scriptName: context.script,
        projectName: context.project,
        timestamp: new Date().toISOString(),
      });
    },

    'session.end': async () => {
      await logger.shutdown();
    },
  },
};

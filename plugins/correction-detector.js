import fs from 'fs/promises';
import path from 'path';

const CORRECTION_PATTERNS = [
  /^(?:actually|wait|hold on|never mind|scratch that)/i,
  /^(?:instead|better|actually)\s/i,
  /^(?:no|cancel|disregard)\s/i,
  /^let me (?:try|fix|correct|rephrase)/i,
  /^i (?:meant|should have|was wrong)/i,
];

export default {
  hooks: {
    'message.updated': async (oldMessage, newMessage) => {
      const hasCorrection = CORRECTION_PATTERNS.some(pattern =>
        pattern.test(newMessage.content)
      );

      if (!hasCorrection) return;

      const reflection = {
        timestamp: new Date().toISOString(),
        type: 'self-correction',
        original: oldMessage.content.substring(0, 100),
        corrected: newMessage.content.substring(0, 100),
        pattern: CORRECTION_PATTERNS
          .find(p => p.test(newMessage.content))
          ?.toString() || 'unknown',
      };

      try {
        const reflectionsDir = path.expand('~/.config/opencode/reflections');
        await fs.mkdir(reflectionsDir, { recursive: true });

        const today = new Date().toISOString().split('T')[0];
        const reflectionFile = path.join(reflectionsDir, `${today}.jsonl`);

        await fs.appendFile(
          reflectionFile,
          JSON.stringify(reflection) + '\n',
          'utf8'
        );
      } catch (err) {
        console.error('Correction detector error:', err);
      }
    },
  },
};

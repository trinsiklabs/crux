const THINK_MODES = ['debug', 'plan', 'infra-architect', 'review', 'legal', 'strategist', 'psych'];
const NO_THINK_MODES = ['build-py', 'build-ex', 'writer', 'analyst', 'mac', 'docker', 'explain'];
const NEUTRAL_MODES = ['ai-infra'];

export default {
  hooks: {
    'chat.message': (message) => {
      const currentMode = message.mode || 'default';

      // Skip if already has think directive
      if (message.content.startsWith('/think') || message.content.startsWith('/no_think')) {
        return;
      }

      let directive = '';

      if (THINK_MODES.includes(currentMode)) {
        directive = '/think ';
      } else if (NO_THINK_MODES.includes(currentMode)) {
        directive = '/no_think ';
      }
      // NEUTRAL_MODES don't get automatic directive

      if (directive) {
        message.content = directive + message.content;
      }

      return message;
    },
  },
};

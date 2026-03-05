const TIGHT_BUDGET = ['plan', 'review', 'strategist', 'legal', 'psych'];
const GENEROUS_BUDGET = ['build-py', 'build-ex', 'debug', 'docker'];
const READ_ONLY_MODES = ['plan', 'review', 'explain'];

const BUDGETS = {
  tight: 2000,
  standard: 4000,
  generous: 8000,
};

export default {
  hooks: {
    'tool.execute.before': async (execution, context) => {
      // TODO: Implement token budget enforcement
      // - Check mode against budget levels
      // - Track tokens used in session
      // - Warn if approaching limit
      // - Block write/edit tools in read-only modes
      // - Return enforcement decision

      const mode = context.mode || 'default';
      const isReadOnly = READ_ONLY_MODES.includes(mode);

      // Block write tools in read-only modes
      if (isReadOnly && ['edit', 'write', 'bash'].includes(execution.tool)) {
        throw new Error(`${execution.tool} not allowed in ${mode} mode`);
      }

      return true;
    },
  },
};

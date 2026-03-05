import { z } from 'zod';

const ProjectContextSchema = z.object({
  include: z.array(z.string()).optional().describe('Sections to include'),
});

export const tool = {
  name: 'project_context',
  description: 'Read and return PROJECT.md context',
  schema: ProjectContextSchema,
  async execute(params) {
    // TODO: Implement project context retrieval
    // - Find PROJECT.md in current or parent directories
    // - Parse metadata
    // - Filter sections if requested
    // - Return structured project context
    // - Handle missing PROJECT.md gracefully
    throw new Error('Not yet implemented');
  },
};

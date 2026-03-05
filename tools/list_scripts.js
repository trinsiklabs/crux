import { z } from 'zod';

const ListScriptsSchema = z.object({
  filter: z.enum(['active', 'library', 'archive']).optional().describe('Filter by location'),
  riskLevel: z.enum(['low', 'medium', 'high']).optional().describe('Filter by risk level'),
});

export const tool = {
  name: 'list_scripts',
  description: 'List all available scripts with metadata',
  schema: ListScriptsSchema,
  async execute(params) {
    // TODO: Implement script listing
    // - Scan .opencode/scripts/ directories
    // - Parse script headers
    // - Filter by location and risk level
    // - Return formatted list with descriptions
    // - Include last execution date
    // - Show script paths
    throw new Error('Not yet implemented');
  },
};

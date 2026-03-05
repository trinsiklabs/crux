# Command: configure-api

Setup commercial API keys for optional integrations.

## Usage
```
opencode /configure-api <provider>
```

## Supported Providers
- `claude` - Anthropic Claude API
- `openai` - OpenAI GPT models
- `groq` - Groq API for fast inference
- `together` - Together AI
- `huggingface` - Hugging Face endpoints

## Setup Process
1. Verify provider account exists
2. Generate or retrieve API key
3. Securely store in `~/.config/opencode/secrets/`
4. Test connection
5. Configure provider in opencode.json

## Secure Storage
- Keys stored encrypted in `~/.config/opencode/secrets/`
- File permissions: 0600 (owner read/write only)
- Never committed to git
- Automatically loaded when needed

## Examples
```
opencode /configure-api claude
opencode /configure-api openai
```

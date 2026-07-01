/**
 * EAKSO SDK quickstart content — rendered as markdown in SdkDocsPage.
 * Keep API key references to the EAKSO_API_KEY env var only; never embed literals.
 */

export const QUICKSTART_MD = `# EAKSO SDK — Quickstart

## Installation

Download the SDK artifact from the button above, then install it locally:

\`\`\`bash
pip install ./eakso_sdk-latest.tar.gz
\`\`\`

Or, once published to a private index:

\`\`\`bash
pip install eakso-sdk
\`\`\`

## Authentication

The SDK reads your API key from the \`EAKSO_API_KEY\` environment variable.

\`\`\`bash
export EAKSO_API_KEY="<your-api-key>"
\`\`\`

**Never hard-code a key in source code.** Use \`.env\` files (excluded from version
control) or a secrets manager in production.

## Create a client and apply a skill

\`\`\`python
import os
from eakso import Client, Skill

client = Client(api_key=os.environ["EAKSO_API_KEY"])

skill = Skill(client=client, skill_id="<skill-id>")
result = skill.apply({"input": "Hello, EAKSO!"})
print(result)
\`\`\`

## API Reference

### \`Client\`

| Parameter | Type | Description |
|-----------|------|-------------|
| \`api_key\` | \`str\` | Your EAKSO API key (read from \`EAKSO_API_KEY\`). |
| \`base_url\` | \`str\` | Override the API base URL (optional). |
| \`timeout\` | \`int\` | Request timeout in seconds (default: 30). |

### \`Skill\`

| Parameter | Type | Description |
|-----------|------|-------------|
| \`client\` | \`Client\` | Authenticated client instance. |
| \`skill_id\` | \`str\` | The marketplace listing ID for the skill to apply. |

**Methods:**

- \`skill.apply(payload: dict) -> dict\` — Run the skill against the given payload.
- \`skill.info() -> dict\` — Fetch skill metadata (title, version, runtime).
`;

export const API_DOWNLOAD_URL = "/api/v1/sdk/download";

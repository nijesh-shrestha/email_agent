# Triage Label Vocabulary

This repository uses the **default canonical triage labels**. These five labels represent the canonical roles in the triage workflow.

## Label Mapping

| Canonical Role | Label String | Description |
|----------------|--------------|-------------|
| Needs Triage | `needs-triage` | New issues that haven't been reviewed yet |
| Needs Info | `needs-info` | Issues blocked waiting for more information |
| Ready for Agent | `ready-for-agent` | Issues with enough context for an agent to start work |
| Ready for Human | `ready-for-human` | Issues requiring human decision or review |
| Won't Fix | `wontfix` | Issues that won't be addressed |

## Conventions

- Labels are applied exactly as written above (lowercase, hyphenated)
- The `triage` skill uses these exact strings when labeling issues
- If you change these labels in GitHub, update this file to match

## Usage by Skills

- `triage`: Reads this file to know which labels to apply/remove during triage operations
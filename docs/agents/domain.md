# Domain Docs Configuration

This repository uses the **single-context** domain docs layout.

## Layout

```
repo-root/
├── CONTEXT.md          # Single domain context file
├── docs/
│   └── adr/            # Architecture Decision Records
│       ├── 0001-example.md
│       └── ...
└── docs/agents/        # Agent skills configuration (this directory)
    ├── issue-tracker.md
    ├── triage-labels.md
    └── domain.md       # This file
```

## Files

### CONTEXT.md
- **Location**: Repo root (`/CONTEXT.md`)
- **Purpose**: The single source of truth for domain knowledge, architecture overview, and project context
- **Consumers**: All agents and skills read this file for domain understanding

### ADRs (Architecture Decision Records)
- **Location**: `docs/adr/`
- **Naming**: `NNNN-short-title.md` (4-digit sequence number)
- **Purpose**: Record significant architectural decisions
- **Consumers**: Agents read ADRs when working on related code areas

## Consumer Rules

### For Agents Reading Context
1. **Always read `CONTEXT.md` first** when starting work in this repository
2. **Read relevant ADRs** when working on code they document
3. **Do not assume** context from other files — use `CONTEXT.md` as the canonical source

### For Agents Writing Context
1. **Update `CONTEXT.md`** when domain knowledge changes significantly
2. **Create ADRs** for architectural decisions (new patterns, tech choices, structural changes)
3. **Keep ADRs immutable** — don't edit old ones, supersede with new ADRs

## Usage by Skills

- `to-spec`: Reads `CONTEXT.md` and relevant ADRs to ground specifications in domain reality
- `triage`: Reads `CONTEXT.md` to understand issue context
- All skills: Use this layout to locate domain documentation
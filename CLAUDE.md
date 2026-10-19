# Cartograph

Ask questions about a JavaScript/TypeScript codebase in plain English and get exact file + line answers, while watching an AI agent search an interactive map of the code. Python engine (tree-sitter, Postgres + pgvector, LLM agent, FastAPI), TypeScript + React map (Sigma.js). Full plan: `docs/PROJECT_GUIDE.md`. Research: `reports/`.

## Commit rules
- Commit as Bhavyam Misra <misrabhavyam@gmail.com> with short, normal messages.
- Never add `Co-Authored-By: Claude ...` or `Claude-Session: ...` lines.
- Never add "Generated with Claude Code" footers to PR descriptions.

## Sync rule
Local folder and GitHub must always match: fetch and pull remote changes first, then commit and push, then confirm `git status` is clean and up to date.

## Working rules
- After every build phase, explain in plain words what was built and which technologies were used, and add it to `docs/LEARNING_LOG.md`.
- Never put unmeasured numbers in the README or resume.
- No em dashes in docs or site copy.

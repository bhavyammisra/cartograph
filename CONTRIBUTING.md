# Contributing

Thanks for helping. Issues and pull requests are welcome.

## Setup

```bash
docker compose up -d db                 # Postgres + pgvector
cd engine && uv sync                    # Python 3.12 via uv
cd ../web && npm install
```

## Before opening a pull request

```bash
cd engine
uv run ruff check .                     # lint
uv run mypy                             # types
uv run pytest -q                        # tests (database tests skip if Postgres is down)
cd ../web
npm run lint && npm test && npm run build
```

CI runs the same checks, then indexes Express at a pinned commit and fails if the BM25 or ordering benchmark scores drop.

## Ground rules

- **Measure, don't claim.** A change that affects search, the call graph or the agent should come with before and after numbers from `cartograph eval`, `order-eval` or `impact-eval`. Never add an unmeasured number to the docs.
- **Never run the analyzed code.** Cartograph reads code only.
- **Precision over recall in the call graph.** A wrong link misleads more than a missing one; label new resolution rules.
- **Keep the map's design rules** (`DESIGN.md`): yellow is reserved for the route, line colours never mark controls.
- Small, focused commits with plain messages.

## Adding eval questions

Add JSON lines to `eval/<repo>/handwritten.jsonl` or `order.jsonl` with a gold answer and a one-line reason, and set `"reviewed": false` until someone else has checked it.

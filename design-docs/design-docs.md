# FaaSr Blocks — design patterns

Concise conventions for the block builder and related tooling. These are **patterns**, not step-by-step implementation guides.

## Explicit configuration

- Treat integration settings (API credentials, endpoints, model names, canonical paths) as **required** at the application boundary. Avoid silent defaults that hide misconfiguration.
- **Fail fast** when something required is missing: report which inputs or environment variables are absent so operators can fix setup immediately.
- Load configuration **once** at the entry point (CLI, job runner) and pass values into lower layers. Lower layers should not read the environment except for truly optional behavior (e.g. debug flags).

## LLM and I/O clients

- Constructors for external clients should take **fully resolved** settings from the caller. Optional tuning knobs (e.g. timeouts) may keep safe defaults.
- The **caller** owns policy: which provider, which model, which base URL. The client only performs the request.

## Dependency injection

- **Orchestrators** (pipelines that sequence generate / validate / test steps) should not construct their own collaborators when those collaborators are swappable or heavy to test.
- The **caller** constructs generators, validators, runners, and similar services and passes them in. The orchestrator calls a small, consistent surface (e.g. `generate`, `validate`, `run_tests`).
- Benefits: clearer wiring, easier unit tests with fakes, and a single place to change how a stage is implemented.

## Repository layout as convention

- Assume a **fixed** tree for the blocks repo (e.g. blocks under a known root, schema in a known location). Infer roots from that layout instead of threading redundant path arguments through every layer.
- The **block directory** is the unit of work: it already contains `contract.json` and expected subfolders. Workloads read and write **inside** that directory; they do not recreate the contract file from an in-memory object unless that is an explicit product requirement.

## Generators and validators

- **Generators** produce artifacts on disk (or streams) from a contract and context; name methods consistently (e.g. `generate`).
- **Validators** return structured pass/fail results with messages; name methods consistently (e.g. `validate`).
- Keep schema validation **unconditional** when a schema path is part of the product: no optional schema or runtime branching between “validated” and “skipped.”

## Iteration and TDD loops

- When a loop mixes several steps (lint/static check, test run, regenerate), extract **one iteration** into a dedicated helper or method. The loop body should read as: “run one iteration; decide whether to stop or continue.”
- Helpers make failures easier to reason about and keep the outer flow readable.

## Testing and small functions

- Prefer **pure helpers** and short functions for logic that is repeated inside loops or that you want to exercise in isolation (e.g. parsing hints from logs, formatting prompts).
- Align with **TDD**: behavior that is easy to call from tests should live in named functions, not only in nested inline blocks.

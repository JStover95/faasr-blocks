# FaaSr Blocks

An experimental framework for creating reusable, validated functions for the FaaSr serverless workflow platform using natural language input.

## Overview

FaaSr Blocks enables users to generate and manage a library of reusable workflow components (called "blocks") through an interactive agent interface. Each block consists of three key components:

1. **Contract**: Formal specification of inputs, outputs, preconditions, postconditions, and behavior
2. **Tests**: Comprehensive pytest-based validation ensuring the block fulfills its contract
3. **Source Code**: Implementation that satisfies the contract requirements

## Repository Structure

```plaintext
faasr-blocks/
├── blocks/                      # Library of validated blocks
│   └── <BlockName>/
│       ├── contract.json        # Block contract specification
│       ├── src/                 # Implementation
│       │   └── <function>.py
│       └── tests/               # Validation tests
│           ├── test_<function>.py
│           └── fixtures/        # Test data
├── faasr_blocks/                # Core framework code
│   ├── builder/                 # Block generation pipeline
│   ├── discovery/               # Embedding & search (Phase 3)
│   ├── models/                  # Contract data models
│   ├── testing/                 # Test harness and mocks
│   └── validation/              # Contract and block validators
├── docs/                        # Phase-specific documentation
├── examples/                    # Usage examples
├── reference/                   # Embedded FaaSr documentation (git subtrees)
│   ├── faasr-docs/              # Official documentation
│   └── faasr-functions/         # Example workflows
├── schema/                      # JSON schemas
│   └── contract_schema.json
└── tests/                       # Framework tests
```

## Key Features

### Pure, Reusable Blocks

Blocks are designed to be:

- **Pure**: Given the same preconditions, produce the same outputs
- **Idempotent**: Safe to re-run without side effects
- **Workflow-agnostic**: Can be used in any compatible workflow
- **Fully tested**: Complete pytest coverage with isolated tests

### Contract-First Design

Before any code is written:

1. The contract specifies exactly what the block does
2. Tests validate the contract is fulfilled
3. Implementation is treated as a black box

### Block Discovery & Reuse

Once validated and committed, blocks can be:

- Discovered through semantic search
- Reused as-is in new workflows
- Adapted to create similar blocks

## Reference Materials

The `reference/` directory contains embedded documentation from the FaaSr framework:

- **`reference/faasr-docs/`**: Official documentation (subtree from <https://github.com/FaaSr/faasr.github.io>)
  - API references for `faasr_get_file()`, `faasr_put_file()`, `faasr_log()`, `faasr_secret()`, etc.
  - Tutorial and programming model guides
  - Conditional branching and secrets management

- **`reference/faasr-functions/`**: Real-world example workflows (subtree from <https://github.com/FaaSr/FaaSr-Functions>)
  - Tutorial examples with Python and R implementations
  - Weather data processing pipelines
  - API integration patterns

**Note:** These are git subtrees (read-only in this repo). See `reference/README.md` for update instructions.

## Getting Started

### Prerequisites

- Python 3.11+
- FaaSr framework understanding (see [FaaSr Tutorial](https://faasr.io/FaaSr-Docs/tutorial/))

### Installation

```bash
# Clone the repository
git clone <your-fork-url>
cd faasr-blocks

# Install dependencies
pip install -e .
```

### Using the Framework

## Development Status

This is a proof-of-concept implementation focused on:

- **Phase 1 (Complete)**: Foundation - contracts, test harness, validation
- **Phase 2 (Complete)**: Block builder - LLM-backed test and source generation, static checks, pytest loop
- **Phase 3 (Complete)**: Embedding & discovery - semantic search for block reuse
- **Phase 4 (Planned)**: Main agent & CLI - natural language interface

### Phase 2: Building a block from a contract

Requires these environment variables (OpenAI-compatible Chat Completions): `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`.

```bash
cd faasr-blocks
uv pip install -e .
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-4o-mini
faasr-blocks-build blocks/GetWeatherData
# or: python -m faasr_blocks.builder.cli blocks/GetWeatherData
```

The block directory must already exist and contain `contract.json`. The builder validates it against the schema, generates `tests/` then `src/`, validates tests against the contract (LLM), runs static validation and `pytest`, and retries implementation up to three times on failures.

**Manual check:** With valid API settings, run the command above on a copy of a block directory (or after moving aside `src/` and `tests/`) to confirm end-to-end generation.

### Phase 3: Embedding and discovery

Requires these environment variables (OpenAI-compatible API + S3 storage):

- LLM: `OPENAI_API_KEY`, `OPENAI_BASE_URL`
- S3: `FAASR_S3_ENDPOINT`, `FAASR_S3_ACCESS_KEY`, `FAASR_S3_SECRET_KEY`, `FAASR_S3_BUCKET`

#### Generate and upload embeddings

```bash
# Generate embeddings for all blocks and upload to S3
faasr-blocks-discover embed --all

# Generate embedding for a single block
faasr-blocks-discover embed --block GetWeatherData
```

Embeddings are stored in S3 at: `<bucket>/faasr-blocks/embeddings/<BlockName>.json`

#### Search for similar blocks

```bash
# Search using natural language
faasr-blocks-discover search "fetch weather data from an API"

# Return more results
faasr-blocks-discover search "process time-series data" --top-n 10
```

The search engine:

1. Downloads all embeddings from S3
2. Loads them into an in-memory sqlite-vec database
3. Embeds the query text
4. Returns top-N most similar blocks with similarity scores

**Manual check:** After generating embeddings with `--all`, run search queries to verify relevant blocks are returned with high similarity scores.

## Testing

Run the test suite:

```bash
pytest
```

Run tests for a specific block:

```bash
pytest blocks/GetWeatherData/tests/
```

## License

MIT License - see LICENSE file for details

## Related Projects

- [FaaSr Backend](https://github.com/FaaSr/FaaSr-Backend) - Core orchestration engine
- [FaaSr Workflow Builder](https://faasr.io/FaaSr-workflow-builder/) - Visual workflow editor
- [FaaSr Workflow](https://github.com/FaaSr/FaaSr-workflow) - Workflow management
- [FaaSr Docker](https://github.com/FaaSr/FaaSr-Docker) - Container images

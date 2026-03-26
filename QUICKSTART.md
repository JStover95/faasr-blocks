# FaaSr Blocks Quick Start

Fast setup and usage guide for FaaSr Blocks framework.

## Installation

```bash
cd faasr-blocks
uv pip install -e .
```

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
# Edit .env with your API keys and S3 credentials
source .env
```

**Minimum required:**

- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` (for block building and embeddings)
- `FAASR_S3_ENDPOINT`, `FAASR_S3_ACCESS_KEY`, `FAASR_S3_SECRET_KEY`, `FAASR_S3_BUCKET` (for discovery)

## Basic Workflow

### 1. Create a Block Directory

```bash
mkdir -p blocks/MyBlock
```

Create `blocks/MyBlock/contract.json` with your contract specification (see `blocks/GetWeatherData/contract.json` for an example).

### 2. Build the Block

Generate tests and implementation:

```bash
faasr-blocks-build blocks/MyBlock
```

This creates:

- `blocks/MyBlock/tests/test_my_function.py`
- `blocks/MyBlock/src/my_function.py`

### 3. Generate Embedding

Create a searchable embedding for discovery:

```bash
faasr-blocks-discover embed --block MyBlock
```

### 4. Search for Similar Blocks

Later, find blocks by functionality:

```bash
faasr-blocks-discover search "what you want to do"
```

## Complete Example

```bash
# One-time setup
cd faasr-blocks
uv pip install -e .
cp .env.example .env
# Edit .env with your credentials
source .env

# Create and build a block (assuming contract exists)
faasr-blocks-build blocks/GetWeatherData

# Generate embeddings for all blocks
faasr-blocks-discover embed --all

# Search for relevant blocks
faasr-blocks-discover search "fetch weather data from an API"

# Run tests
pytest tests/ -v

# Run full example
uv run python examples/discovery_example.py
```

## CLI Commands

### faasr-blocks-build

Build a block from its contract:

```bash
faasr-blocks-build blocks/BlockName [--max-source-iterations 3]
```

### faasr-blocks-agent (Phase 4)

Interactive orchestrator: contracts from NL, optional Q&A, **approve** to discover + build + summary.

```bash
faasr-blocks-agent
```

Requires LLM and S3 env vars (same as build + discover). Options: `--debug`, `--multiline`, `--history-file PATH`, `--stub` (no keys; stub handler only).

### faasr-blocks-discover

Manage embeddings and search:

```bash
# Generate embeddings
faasr-blocks-discover embed --all
faasr-blocks-discover embed --block BlockName

# Search
faasr-blocks-discover search "query text" [--top-n 5]
```

## File Structure

```plaintext
faasr-blocks/
├── blocks/                  # Your block library
│   └── BlockName/
│       ├── contract.json
│       ├── src/
│       │   └── function_name.py
│       └── tests/
│           └── test_function_name.py
├── .env                     # Your credentials (not committed)
├── examples/                # Usage examples
└── docs/                    # Detailed documentation
```

## Troubleshooting

**Import errors:**

```bash
uv pip install -e .
```

**Missing environment variables:**

```bash
source .env
echo $OPENAI_API_KEY  # Should not be empty
```

**sqlite-vec not loading:**

```bash
uv pip install sqlite-vec
```

**S3 access denied:**

- Check credentials in `.env`
- Verify bucket permissions (PutObject, GetObject, ListBucket)

## Documentation

- **Phase 2 (Block Builder)**: See README.md
- **Phase 3 (Discovery)**: See `docs/phase3-discovery.md`
- **Manual Testing**: See `docs/phase3-manual-testing.md`
- **Design Patterns**: See `design-docs/design-docs.md`

## Testing

```bash
# All tests
pytest -v

# Specific module
pytest tests/test_discovery.py -v

# With coverage
pytest --cov=faasr_blocks --cov-report=html
```

## Getting Help

- Check documentation in `docs/`
- Review example blocks in `blocks/`
- Run example script: `python examples/discovery_example.py`
- Check design patterns: `design-docs/design-docs.md`

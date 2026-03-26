# Discovery Module

Semantic search and embedding infrastructure for FaaSr block discovery.

## Module Structure

```plaintext
faasr_blocks/discovery/
├── __init__.py          # Public API exports
├── cli.py               # Command-line interface
├── embedding.py         # Embedding generation from contracts
├── search.py            # Vector search engine (sqlite-vec)
└── storage.py           # S3 and local embedding persistence
```

## Key Classes

### Embedding Generation

**`BlockEmbedding`**: Immutable embedding representation

- Vector (list[float])
- Metadata hash (SHA-256)
- Searchable text
- JSON serialization

**`EmbeddingClient` (Protocol)**: Interface for embedding APIs

- Enables dependency injection
- Mock implementations for testing

**`OpenAIEmbeddingClient`**: OpenAI-compatible embeddings API

- Calls `/embeddings` endpoint
- Default: `text-embedding-3-small` (1536d)

**`EmbeddingGenerator`**: Contract → embedding converter

- Extracts metadata into searchable text
- Computes integrity hash
- Delegates vector generation to client

### Storage

**`EmbeddingStore` (Protocol)**: Persistence interface

- `upload()`, `download()`, `list_all()`, `download_all()`
- Protocol enables S3 and local implementations

**`S3EmbeddingStore`**: S3-backed persistence

- Path: `<bucket>/faasr-blocks/embeddings/<BlockName>.json`
- Uses boto3 client
- Graceful handling of missing keys

**`LocalEmbeddingStore`**: Filesystem-backed storage

- For development/testing without S3
- Same API as S3 implementation

### Search

**`SearchResult`**: Query result with metadata

- Block identity (name, version)
- Similarity score
- Embedded text
- Metadata hash

**`BlockSearchEngine` (Protocol)**: Search interface

- Context manager: `__enter__` / `__exit__` for automatic cleanup of backing resources
- `search(query_text, top_n)` → results
- `get_embedding(block_name)` → stored embedding

**`SqliteVecSearchEngine`**: In-memory vector database

- Uses sqlite-vec's `vec0` virtual table
- Cosine similarity search
- Builds index on initialization
- Prefer ``with SqliteVecSearchEngine(...) as engine:``; ``close()`` remains available and is idempotent

## Usage Patterns

### Generate Embedding

```python
from faasr_blocks.discovery import EmbeddingGenerator
from faasr_blocks.discovery.embedding import OpenAIEmbeddingClient
from faasr_blocks.models.contract import Contract

client = OpenAIEmbeddingClient(api_key="...", base_url="...")
generator = EmbeddingGenerator(client)

contract = Contract.from_json_path("blocks/MyBlock/contract.json")
embedding = generator.generate(contract)
```

### Store in S3

```python
from faasr_blocks.discovery import EmbeddingStore
from faasr_blocks.discovery.storage import S3EmbeddingStore

store = S3EmbeddingStore(
    endpoint="https://s3.amazonaws.com",
    access_key="...",
    secret_key="...",
    bucket="faasr-blocks"
)

store.upload(embedding)
all_embeddings = store.download_all()
```

### Search Embeddings

```python
from faasr_blocks.discovery import BlockSearchEngine
from faasr_blocks.discovery.search import SqliteVecSearchEngine

with SqliteVecSearchEngine(all_embeddings, embedding_client) as engine:
    results = engine.search("fetch weather data", top_n=5)
    for result in results:
        print(f"{result.block_name}: {result.similarity:.4f}")
```

## Design Principles

### Protocol-Based Design

All major components define protocols for:

- **Testing**: Easy to create mocks
- **Flexibility**: Swap implementations (S3 ↔ Local, OpenAI ↔ other)
- **Type safety**: Runtime checkable with `@runtime_checkable`

### Fail-Fast Configuration

Configuration loaded at entry point (CLI), not lazily:

- Clear error messages
- No hidden defaults
- Caller owns policy decisions

### Separation of Concerns

- **`embedding.py`**: Contract → vector transformation
- **`storage.py`**: Vector persistence (S3/local)
- **`search.py`**: Vector → similarity queries
- **`cli.py`**: User interface and orchestration

Each module has single responsibility and minimal coupling.

### Repository Convention

Infers paths from fixed layout:

- Blocks: `repo_root/blocks/<BlockName>/`
- Embeddings: `<bucket>/faasr-blocks/embeddings/<BlockName>.json`
- Contracts: `blocks/<BlockName>/contract.json`

Reduces path-threading through layers.

## Testing

Run discovery tests:

```bash
pytest tests/test_discovery.py -v
```

11 tests covering:

- Embedding generation and hashing
- Local/S3 storage operations
- Vector search queries
- JSON serialization

All use mock clients (no real API calls in unit tests).

## Integration with Other Phases

### From Phase 1 (Foundation)

- Uses `Contract` model from `faasr_blocks.models.contract`
- Follows repository layout conventions
- Validates contracts before embedding

### From Phase 2 (Block Builder)

- After successful build, generate embedding
- Upload to S3 for future discovery
- Enables reuse in future workflows

### For Phase 4 (Main Agent)

- Agent queries search engine on startup
- Finds reusable blocks before generating new ones
- Presents candidates to user for approval
- Auto-embeds newly created blocks

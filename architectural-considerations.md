# Architectural Considerations

- **S3 mocking strategy**: Tests need to mock `faasr_get_file()`, `faasr_put_file()`, etc. Should there be a standard test harness?
- **Secrets in tests**: How do you test blocks that use `faasr_secret()`?
- **Test data fixtures**: Where are test input files stored? In the repo or referenced externally?
- **Integration vs unit tests**: Do you only unit test blocks, or also test block combinations?
- **Test execution environment**: Do tests run locally, in CI/CD, or in actual FaaSr containers?

**Responses:**

**Mocking strategy:** The simplest solution would be to mock each API stub with a mock factory. Here's a outline of how this can be implemented for `faasr_secret`. A similar pattern can be used for all API stubs.

**`mocks.py`:**

```python
ffrom unittest.mock import patch
from abc import ABC, abstractmethod


class MockFactoryContext(ABC):
    def __init__(self, import_path: str):
        self._import_path = import_path

    @abstractmethod
    def __call__(self):
        ...

    def __enter__(self):
        self._patch = patch(self._import_path)
        mock = self._patch.start()
        mock.side_effect = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is not None:
                raise exc_value
            self.clear()
            return True
        finally:
            self._patch.stop()

    @abstractmethod
    def clear(self):
        ...


class MockFaaSrSecret(MockFactoryContext):
    def __init__(self, import_path: str):
        super().__init__(import_path)
        self._secret_store = dict[str, str]()

    def __call__(self, key: str):
        try:
            return self._secret_store[key]
        except KeyError:
            raise Exception(f"Attempted to access non-existent secret {key}")

    def with_secret(self, key: str, val: str):
        self._secret_store[key] = val

    def clear(self):
        self._secret_store = dict[str, str]()
```

**`function.py`:**

```python
from FaaSr_py.client.py_client_stubs import faasr_secret


def some_function() -> str:
    secret_value = faasr_secret("SOME_SECRET_KEY")
    # Remaining function code
```

**`test_function.py`:**

```python
import pytest
from mocks import MockFaaSrSecret
from function import some_function


@pytest.fixture(scope="module", autouse=True)
def mock_faasr_secret():
    with MockFaaSrSecret("function.faasr_secret") as mock_secret:
        mock_secret.with_secret("SOME_SECRET_KEY", "test_value")
        yield

def test_some_function():
    some_function()
```

**Test execution and environment:** Tests should be completely standalone and not have any external dependencies. Any test data should be included with tests and injected into tests using the aforementioned mock factory pattern. Tests are run on single blocks only. Tests can be run locally or in CI/CD, but without any dependency on using a FaaSr container or other specialized runtime environment.

## 5. **Block Discovery & Reuse**

This is critical for the agent's ability to find relevant blocks:

- **Metadata taxonomy**: Tags, categories, domains (weather, data processing, ML, etc.)
- **Semantic search**: How does the agent match user intent to existing blocks? Embeddings? Keywords?
- **Similarity scoring**: When multiple blocks could work, how does the agent rank them?
- **Composition patterns**: Can the agent recognize common multi-block patterns (fetch→process→visualize)?

**Responses:**

**Metadata taxonomy**: To start, let's use these metadata:

- Role (e.g., fetch data, process data, plot data, etc.)
- Data type (e.g., weather, geological, ecological, etc.)
- Methodology (e.g., data transformation, ML, LLM agent, etc.)
- Tags (free-form tags for miscellaneous categorization)

**Semantic search**: GitHub released a semantic search for Issues that is currently in public preview. Currently, there is no API for this feature, but would be a great GitHub-native solution if one becomes available.

The solution for this use case:

- Use S3 as the embedding data store. This integrates nicely with FaaSr's native support on S3 storage.
- When the agent starts, it downloads existing embeddings from S3 and loads them into an in-memory sqlite database for vector search.
- Before a block is committed to the repo, a final step is to embed the function's metadata and upload the embedding to S3.
- Each embedding is stored along a hash that can be used to validate the embedding against the metadata committed to the database. For PoC, this check should be implemented, but special handling is out-of-scope for now.

**Similarity scoring**: The agent should first reason about the top N results. If it deems any suitable for the user's request, then it can retrieve the block's contract to determine whether any can be used as-is or adapted. If no suitable blocks are found, this it will proceed to generate a new block that matches the user's requirements.

**Composition patterns**: This is out of scope for PoC.

## 6. **Contract Validation Strategy**

- **Static validation**: Can you validate that implementation matches contract before running tests?
- **Runtime enforcement**: Should blocks auto-validate inputs/outputs against the contract at execution time?
- **Test-contract alignment**: How do you ensure tests actually cover all contract requirements?

**Responses:**

Runtime enforcement is out-of-scope for PoC. As a final step in writing tests, a subagent can be assigned to independently validate test-contract alignment. Similarly, before running tests on source code, a subagent can be assigned to independently run static validation.

## 7. **Error Handling Standardization**

The contract specifies error states, but consider:

- **Error taxonomy**: Network failures, validation errors, missing data, timeouts, etc.
- **Retry semantics**: Should some errors trigger retries? How is this declared?
- **Partial failures**: What if a block processes 100 files and 3 fail? Fail completely or partial success?
- **Error propagation**: How do errors propagate through workflows? Immediate failure vs graceful degradation?

**Responses:**

For PoC, let's simplify things as much as possible: assume the happy path. Let's exclude error states from the contract for PoC.

## 8. **Conditional Logic Complexity**

You mention True/False returns, but FaaSr supports richer patterns:

- **Multiple branches**: More than just binary True/False (e.g., "success", "retry", "failed")
- **Ranked actions**: Some blocks might launch parallel instances - does this need contract support?
- **Dynamic branching**: Can blocks dynamically decide which successors to invoke?

**Responses:**

For PoC, let's only consider True/False paths for branching. Blocks that return True or False (via `faasr_return`) must necessarily be used at a branch point in a workflow, and blocks that do not use the `faasr_return` API cannot be used at a branch point in a workflow. Blocks are also pure. Given that the preconditions for a block's contract are met, it should produce the same result across workflows, and therefore should not include logic for "stateful" dynamic branching. Workflows may be dynamically branched by an orchestrator agent, which is out of scope for this project. Similarly, because blocks are pure, they should produce the same result in ranked or non-ranked invocations given the necessary preconditions are met.

## 9. **Block Adaptation vs Cloning**

When the agent finds a "similar" block:

- **Adaptation strategy**: Does it create a new block with modifications, or suggest the user modify the original?
- **Parameterization**: Should blocks support configuration parameters to reduce need for adaptation?
- **Template blocks**: Should there be "template blocks" that are designed to be adapted?

**Responses:**

- **Adaptation strategy**: The user will be using FaaSr-Blocks via a codeless chat interface. If a block's contract can be used according to the user's request without modifications, then it should be used as-is. If the block can be re-used with minor modifications, the the agent must create a new block from scratch, using the existing block as a reference point.

- **Parameterization**: Blocks should support parameterization when possible, but without unnecessary abstraction. A good use case for parameterization would be calculating a sliding window average of arbitrary time series data, where the function could receive arguments for the window size and variable name. Unnecessary abstraction would be supporting multiple data formats for the same calculation. Supporting CSV, HDF5, etc. in one block would result in significant complexity and bloat, whereas a block dedicated to CSV data would be more reliable and easier to test. The factor to consider here is the burden of proof required to show that a given block fulfills its contract. Complex implementations require complex proofs.

- **Template blocks**: This is a good idea, but out of scope for PoC.

## 10. **Data Contract Specifications**

Beyond file names, consider:

- **File format contracts**: CSV with specific columns? JSON with schema? Binary formats?
- **Data validation**: Should blocks validate data structure/content, not just file existence?
- **Size constraints**: Maximum file sizes, row counts, memory requirements?

**Responses:**

Similar to my previous comment about parameterization, a balance must be struck between what can be easily parameterized and what would result in unnecessary abstraction. File and data format should be clearly defined (e.g., CSV, epoch timestamps, etc.), but factors like column names (e.g., temperature_c, TEMP, etc.) can be easily parameterized. When generating the contract, the agent must determine the correct balance between what must be codified in the contract vs. what can be parameterized without adding unnecessary complexity.

Similar to my earlier comment with error handling/validation, for PoC let's simplify as much as possible and always assume the happy path. Assume valid data.

## 11. **Context Propagation**

FaaSr workflows pass context between actions:

- **Implicit inputs**: Does the contract need to declare arguments passed from predecessor blocks?
- **Workflow-level state**: `InvocationID`, logging configs, etc. - are these implicit or explicit in contracts?
- **Side-channel communication**: Beyond S3, blocks can log - is this part of the contract?

**Responses:**

Blocks are pure and must be agnostic to workflow-level state and configuration. Which arguments must be passed to a block are defined by the contract, but the actual values of the arguments are defined by the workflow. Similarly, `InvocationID`, logging configs, etc. should not affect a block's output given the same preconditions.

## 12. **Repository Structure**

The organizational aspect:

- **Directory layout**: How are blocks organized? Flat structure? Categorized folders? Namespaces?
- **Naming conventions**: How are blocks named? Kebab-case? Categories/prefixes?
- **Monolithic vs modular**: One repo for all blocks, or blocks can reference each other across repos?

**Responses:**

- **Directory layout**: For PoC, a simple `blocks/<block-name>/` structure.
- **Naming conventions**: PascalCase.
- **Monolithic vs modular**: One repo for all blocks.

## 13. **Agent Workflow Generation**

Since you're building to a text output:

- **Output format**: What does the agent's output look like? Workflow JSON? Markdown summary? Both?
- **Block selection explanation**: Does the agent explain why it chose specific blocks?
- **Gap identification**: If no perfect block exists, does the agent identify what needs to be created?

**Responses:**

- **Output format**: Simple human-readable markdown summary.
- **Block selection explanation**: Yes, it should provide reasoning.
- **Gap identification**: Yes, when a gap is identified, the agent should create a new block from scratch to fulfill the contract.

## 14. **Natural Language to Contract Translation**

The agent takes NL input, so:

- **Ambiguity resolution**: How does the agent handle vague requirements?
- **Interactive refinement**: Can the user iterate on the contract before generating tests/code?
- **Requirement extraction**: How does the agent extract all contract components from NL?

**Responses:**

A good approach would be to have an iterative approach, similar to the planning stage of agentic IDEs. If the agent identifies ambiguities that it cannot resolve through common-sense reasoning, it can ask follow-up questions to the user. Ideally, this will finish after a single round but a second round may be done if absolutely necessary.

After receiving sufficient requirements, the agent can generate a set of contracts for the workflow. For example, for a simple workflow it may generate three contracts: 1. Get Data, 2. Process Data, and 3. Visualize Data.

Contracts should be presented to the user in codeless natural language. If the user approves the contracts, then the agent will begin generating tests and code. Otherwise, the user can ask for revisions before implementation.

## 15. **Performance Characteristics**

Not in the contract, but might be useful:

- **Expected runtime**: Helps users estimate workflow duration
- **Resource requirements**: Memory, CPU intensity
- **Cost estimates**: For cloud platforms that charge per execution

**Responses:**

All good ideas, but out of scope for PoC.

## Potential Missing Pieces

### **Pre-conditions & Post-conditions**

Beyond error states, consider formal invariants:

- What must be true before the block executes?
- What is guaranteed after successful execution?
- What data transformations occur?

**Responses:**

Following previous comments, contractual preconditions include any input definitions that cannot be specified (e.g., there must be a CSV with epoch timestamps and celsius temperature data). Postconditions only include any S3 outputs generated by the function (e.g., a CSV with 1-week average temperature values). Data transformations must be codified a given methodology must be followed (e.g., 7-day forecasting with linear regression vs. a more complex ML model).

### **Observability**

- **Logging requirements**: What should blocks log? Standard format?
- **Metrics**: Should blocks emit metrics (execution time, records processed)?
- **Tracing**: Support for distributed tracing across workflow?

**Responses:**

Observability should not be codified in contracts. Standardized observability should be a future addition, but for PoC, the agent should simply make a good-effort implementation of basic observability (e.g., on successful completion or failure).

### **Security Considerations**

- **Secret contracts**: If a block needs secrets, how is this declared?
- **Data sensitivity**: Does the contract specify if data is PII, PHI, etc.?
- **Access control**: Who can use/modify blocks?

**Responses:**

Required secrets must be included in contracts as a necessary preconditions for execution. Data sensitivity and access controls are out-of-scope for PoC.

### **Block Composition Semantics**

- **Piping conventions**: How do output paths from Block A map to input paths for Block B?
- **Fan-out/fan-in**: Blocks that produce multiple outputs or consume from multiple predecessors
- **Idempotency**: Can blocks be safely re-run? Should this be in the contract?

**Response:**

Blocks are pure and idempotent. They are agnostic to the workflow's logic and must produce the same outputs given the same preconditions.

---

Overall, the core concept is solid! The main areas to think through are:

1. **How contracts are formally specified** (the format/language)
2. **How the agent discovers and matches blocks** (the intelligence layer)
3. **How blocks declare dependencies** (both on packages and other blocks)
4. **How testing infrastructure mocks FaaSr APIs** (the test harness)
5. **How blocks are versioned and adapted** (the lifecycle management)

Would you like to dive deeper into any of these areas?

## Additional Comments

In my comments I mentioned an orchestrator agent that will be used for generating workflows that is out-of-scope. The FaaSr-Block agent will partially play this role. Although, its role is not to generate a workflow but rather to create contracts according to the user's specifications. Once the contracts are finalized by the user, a subagent should be assigned to each contract for generating tests and code. This way, the FaaSr-Block agent is concerned with the fulfilling the user's request with new or existing contracts, and individual subagents are responsible for fulfilling their given contract with tests and code. For PoC, the final output is a simple markdown summary of the blocks that were created or re-used. Actual workflow orchestration and invocation is out-of-scope for PoC.

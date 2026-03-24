# FaaSr Reference Documentation

This directory contains embedded reference materials from the FaaSr framework to guide the block-building agent when generating contracts, tests, and source code.

## Contents

### faasr-docs/
Official FaaSr documentation from the website (https://faasr.io)

**Source:** https://github.com/FaaSr/faasr.github.io (git subtree)

#### Key Documentation Files

**Core Concepts:**
- `docs/index.md` - FaaSr overview and introduction
- `docs/tutorial.md` - Complete tutorial for building workflows
- `docs/prog_model.md` - Programming model and execution flow
- `docs/workflows.md` - Workflow structure and configuration

**Function Development:**
- `docs/functions.md` - How to create FaaSr functions
- `docs/functionexamples.md` - Function examples and patterns
- `docs/py_api.md` - Python API reference (faasr_get_file, faasr_put_file, etc.)
- `docs/dependences.md` - Managing Python/R package dependencies

**Advanced Features:**
- `docs/conditional.md` - Conditional branching with True/False returns
- `docs/rank.md` - Ranked (parallel) action execution
- `docs/s3.md` - S3 data store configuration
- `docs/credentials.md` - Secrets and credentials management
- `docs/logs.md` - Logging configuration

### faasr-functions/
Real-world example workflows demonstrating FaaSr patterns

**Source:** https://github.com/FaaSr/FaaSr-Functions (git subtree)

#### Key Example Workflows

**Basic Tutorial:**
- `tutorial/` - Simple arithmetic operations (sum, multiply, divide)
  - `compute_sum.py` - Python example with faasr_get_file/put_file
  - `compute_sum.R` - R example with same pattern
  - `tutorial.json` - Workflow configuration
  - Great starting point for understanding function structure

**Weather Data Processing:**
- `WeatherVisualization/` - Fetch, process, and plot weather data
  - Shows sequential data pipeline pattern
  - Demonstrates visualization with matplotlib
  - Good example of S3 file passing between actions

**Geographic Data:**
- `WeatherGeographicPlot/` - Weather data with geographic visualization
  - Shows working with coordinate data
  - Demonstrates geographic plotting patterns

**Advanced Patterns:**
- `idigbio_media_download/` - API integration and media handling
- `nullstart/` - Minimal starter example

## Agent Usage Guide

### When Writing Contracts

Reference these to understand:
- What FaaSr APIs are available (`docs/py_api.md`)
- How arguments are passed between actions (`docs/prog_model.md`)
- What conditional blocks return (`docs/conditional.md`)
- How secrets are accessed (`docs/credentials.md`)

### When Generating Tests

Reference these for patterns:
- Simple function structure: `tutorial/compute_sum.py`
- API usage patterns: any example in `faasr-functions/`
- Input/output conventions: `docs/functions.md`

### When Writing Source Code

Reference these for implementation patterns:
- Basic S3 operations: `tutorial/compute_sum.py`
- Data processing pipeline: `WeatherVisualization/python/`
- API integration with secrets: check if WeatherAPISecrets exists or similar patterns
- Error handling: `docs/prog_model.md`

### Common Function Patterns

#### Pattern 1: Data Transformation
```python
from FaaSr_py.client.py_client_stubs import faasr_get_file, faasr_put_file, faasr_log

def transform_data(folder_name, input_file, output_file):
    # Get input from S3
    faasr_get_file(remote_folder=folder_name, remote_file=input_file, local_file=input_file)
    
    # Process data
    result = process(input_file)
    
    # Put output to S3
    faasr_put_file(local_file=output_file, remote_folder=folder_name, remote_file=output_file)
    
    faasr_log(f"Processed {input_file} -> {output_file}")
```

#### Pattern 2: External API with Secrets
```python
from FaaSr_py.client.py_client_stubs import faasr_secret, faasr_put_file, faasr_log
import requests

def fetch_api_data(output_file):
    # Get API key from secrets
    api_key = faasr_secret("MY_API_KEY")
    
    # Make API request
    response = requests.get(f"https://api.example.com/data?key={api_key}")
    data = response.json()
    
    # Save to S3
    with open(output_file, 'w') as f:
        json.dump(data, f)
    faasr_put_file(local_file=output_file, remote_file=output_file)
```

#### Pattern 3: Conditional Block
```python
from FaaSr_py.client.py_client_stubs import faasr_get_file, faasr_return, faasr_log

def check_threshold(folder_name, input_file, threshold):
    # Get input
    faasr_get_file(remote_folder=folder_name, remote_file=input_file, local_file=input_file)
    
    # Check condition
    with open(input_file) as f:
        value = float(f.read())
    
    result = value > threshold
    faasr_log(f"Threshold check: {value} > {threshold} = {result}")
    
    # Return True/False for conditional branching
    faasr_return(result)
```

## Updating Subtrees

To pull the latest changes from upstream repositories:

```bash
# Update documentation
git subtree pull --prefix=reference/faasr-docs https://github.com/FaaSr/faasr.github.io.git main --squash

# Update examples
git subtree pull --prefix=reference/faasr-functions https://github.com/FaaSr/FaaSr-Functions main --squash
```

**Note:** These subtrees are read-only in this repository. Changes should be made in the upstream repositories.

## Integration with Block Builder

The Phase 2 block builder subagent will:
1. Parse the contract to understand requirements (APIs needed, conditional logic, secrets, etc.)
2. Reference relevant documentation files from `faasr-docs/`
3. Use similar examples from `faasr-functions/` as templates
4. Generate tests and source code following observed patterns
5. Ensure generated code uses only documented FaaSr APIs

The agent should prioritize reading documentation relevant to the specific contract requirements rather than loading all reference materials into context.

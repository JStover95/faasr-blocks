# Default values

The following values are set by default in the Web UI and take effect unless overridden by the user:

## Compute server names

- `GH`: GitHub Actions
- `AWS`: AWS Lambda
- `GCP`: Google Cloud
- `OW`: OpenWhisk
- `SLURM`: Slurm

## Compute server configurations

### GitHubActions 

- `FaaSr-workflow`: workflow repository name
- `main`: workflow repository branch

### AWS Lambda

- `us-east-1`: region

### OpenWhisk

- `False`: allow self-signed certificates

## Data store configurations

- 'S3': default data store name
- `True`: by default, an S3 store is set to writable

## Secrets

- `GH_PAT`: GitHub personal access token
- `AWS_AccessKey`: AWS Lambda access key
- `AWS_SecretKey`: AWS Lambda secret key
- `GCP_SecretKey`: GCP secret key
- `OW_APIkey`: OpenWhisk API key
- `SLURM_Token`: SLURM JWT token

## Log folder (in S3)

- `FaaSrLog`: top-level log folder name; see [log] documentation for full path information

## Containers

Note: the latest stable release is tagged as `:latest` in all containers; specific release versions are tagged with the version number, e.g. `:2.0.0` for version 2.0.0

### Python
- `ghcr.io/faasr/github-actions-python:latest`: GitHub Actions (in GHRC)
- `145342739029.dkr.ecr.us-east-1.amazonaws.com/aws-lambda-python:latest`: AWS Lambda east-1 (in ECR)
- `faasr/gcp-python:latest`: GCP (in DockerHub)
- `faasr/openwhisk-python:latest`: OpenWhisk (in DockerHub)
- `faasr/slurm-python:latest`: Slurm (in DockerHub)

### R

- `ghcr.io/faasr/github-actions-r:latest`: GitHub Actions (in GHRC)
- `145342739029.dkr.ecr.us-east-1.amazonaws.com/aws-lambda-r:latest`: AWS Lambda east-1 (in ECR)
- `faasr/gcp-r:latest`: GCP (in DockerHub)
- `faasr/openwhisk-r:latest`: OpenWhisk (in DockerHub)
- `faasr/slurm-r:latest`: Slurm (in DockerHub)

[log]:logs.md

# Your FaaSr-workflow repo

Your FaaSr-workflow GitHub repository is the default management/launching pad environment for all your workflows; it is the primary location where you will store credentials/secrets, and register and launch workflows. As described in the [workflow model] document, before you start using FaaSr to run workflows, you need to setup your **FaaSr-workflow** GitHub repository to hold the following information:

- JSON configuration files for each of your workflows
- GitHub secrets for your compute and data cloud servers
- GitHub actions that allow you to [register] and [invoke] workflows

The simplest way to configure this repository is to fork from the FaaSr organization's FaaSr-workflow repository

## Forking the base repository

- In your browser, [navigate to the FaaSr-workflow base repository](https://github.com/FaaSr/FaaSr-workflow)
- Click on the down arrow next to _Fork_ for a pull-down menu; select _Create a new fork_
- Choose your account name as the _Owner_ of the fork
- While you can choose a different name for your fork, here we assume you leave the default _FaaSr-workflow_
- Leave the default _Copy the main branch only_ checkbox checked
- Click on the green _Create fork_ button

### Keeping your repository in sync

When the [FaaSr-workflow base repository](https://github.com/FaaSr/FaaSr-workflow) is updated with new features and bug fixes, you will notice that in your own FaaSr-workflow fork there will be a message that `This branch is XX commits behind of` the upstream `FaaSr/FaaSr-workflow:main` repo. To incorporate these updates to your fork, use the `Sync fork` drop-down menu.

## Enabling FaaSr actions

In order to use register and invoke workflows, you also need to perform a one-time configuration to enable running the pre-defined FaaSr register and invoke workflow actions. To do this:

- Click on the _Actions_ tab (top of the GitHub page, next to _Code_ and _Pull requests_)
- Click on the green button _I understand my workflows, please go ahead and enable them_

## Configuring secrets

Before you can register and invoke workflows, you need to create secrets storing credentials for the cloud providers you will use. The following assumes that you already have obtained [cloud credentials] for those.

- In the _FaaSr-workflow_ repo you just forked, click on the _Settings_ tab (top of the page, to the right)
- Scroll down; on the left pane, click on the pull-down _Secrets and variables_ and select _Actions_
- Click on the green _New repository secret_ to enter a new secret
- Enter the proper _Name_ for your secret (see below) and paste the secret itself in the _Secret_ text box
- Click on _Add secret_

## Naming convention for secrets

### S3 data store servers

- When creating a workflow with the [FaaSr Workflow Builder Web UI], you are asked to enter a name for your S3 data server(s)
- The default compute server name for an S3 server is `S3`
- Assume the name of a data server you are setting the secrets for is `S3`, you need two secrets, named exactly as follows (replace `S3` with the name of the server you configured)
- `S3_AccessKey`
- `S3_SecretKey`
- The secrets you store under these names are the access and secret keys you obtained from your S3 provider

### GitHub Actions

- The default compute server name for GitHub Actions is `GH`
- You should **not** modify this name unless you plan to use FaaSr with custom [advanced] actions
- You need one secret, named `GH_PAT`
- The secret you store under this name is a GitHub Personal Access Token

### AWS Lambda

- The default compute server name for AWS Lambda is `AWS`
- You should **not** modify this name unless you plan to use FaaSr with custom [advanced] actions
- You need two secrets, named: `AWS_AccessKey` and `AWS_SecretKey`
- The secrets you store under these names are the access and secret keys you obtained from AWS Lambda

### Google Cloud

- The default compute server name for AWS Lambda is `GCP`
- You should **not** modify this name unless you plan to use FaaSr with custom [advanced] actions
- You need one secret named: `GCP_SecretKey` 
- The secret you store under this name is the secret key you obtained from Google Cloud

### OpenWhisk

- The default compute server name for AWS Lambda is `OW`
- You should **not** modify this name unless you plan to use FaaSr with custom [advanced] actions
- You need one secret named: `OW_APIKey` 
- The secret you store under this name is the API key you obtained from your OpenWhisk provider

### Slurm

- The default compute server name for AWS Lambda is `SLURM`
- You should **not** modify this name unless you plan to use FaaSr with custom [advanced] actions
- You need one secret named: `SLURM_Token` 
- The secret you store under this name is the JWT token you obtained from your Slurm provider

## What next?
It's recommended you start by first running the simple [FaaSr tutorial]. The secrets you will need are: *GH_PAT* (your GitHub token), *S3_AccessKey* and *S3_SecretKey* (the test Minio Play S3 bucket credentials).

Once you are comfortable with the FaaSr tutorial, you may want to check additional [FaaSr function examples] as helpful workflow templates (JSON files) and functions (R and Python) for you to follow as you develop your own workflows. 

[workflow model]: prog_model.md
[register]: register_workflow.md
[invoke]: invoke_workflow.md
[FaaSr tutorial]: tutorial.md
[cloud credentials]: credentials.md
[FaaSr Workflow Builder Web UI]: workflows.md
[advanced]: advanced.md
[FaaSr function examples]: functionexamples.md

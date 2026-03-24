# Tutorial

This document guides you through a simple tutorial that uses GitHub Actions and a free S3 data store (Minio Play).

## Prerequisites

For this tutorial, all you need is a GitHub account. It is also recommended that your refer to the [Setting up the FaaSr-workflow repo](./workflow_repo.md) documentation for details about the FaaSr-workflow repository.

## Configure your FaaSr-workflow repository

This is a one-time step you go through to set up your [workflow repository] to host all your workflows, including the tutorial.

- Navigate to the [FaaSr organization workflow repo](https://github.com/FaaSr/FaaSr-workflow)
- Fork the repository to your own GitHub account, keeping the FaaSr-workflow name
- In your forked repository, click on _Actions_ and click on _I understand my workflows, go ahead and enable them_ to allow FaaSr register/invoke actions to execute

## Configure your GitHub PAT

You need a personal access token in your repository secrets to run this tutorial.

Follow the steps outlined in the [GitHub Actions credentials] documentation to obtain your PAT. Copy this PAT so you can paste it as a secret in the next step

## Configure your repository secrets

Before you can register and invoke workflows, you need to create secrets storing credentials for the cloud providers you will use.

!!! note "Guest S3 Credentials"
    Note that for this tutorial we are using guest credentials for a free S3 data store offered by MinIO. In practice, you will use your own credentials (see the [credentials](./credentials.md) documentation for more information).

- In the _FaaSr-workflow_ repo you just forked, click on the _Settings_ tab (top of the page, to the right)
- Scroll down; on the left pane, click on the pull-down _Secrets and variables_ and select _Actions_
- Click on the green _New repository secret_ to enter a new secret
- Enter the proper _Name_ for each of the three secrets below (one for GitHub actions, two for Minio Play) and past the secret itself in the _Secret_ text box:
- Click on _Add secret_ and add a secret named `GH_PAT`, pasting your GitHub PAT created in the previous step
- Click on _Add secret_ and add a secret named `S3_AccessKey`, pasting the following text: `Q3AM3UQ867SPQQA43P2F`
- Click on _Add secret_ and add a secret named `S3_SecretKey`, pasting the following text: `zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG`

## Edit the tutorial JSON file

The tutorial.json file is available in the FaaSr-Functions repository; you will need to import it, configure it with your GitHub account name, and upload to your FaaSr-workflow repository

### Step 1: Import and edit tutorial.json in the Web UI

- Open the [FaaSr Workflow Builder Web UI] in a separate browser window/tab
- Click on Upload (top left)
- To import the tutorial file from GitHub, enter in text box: `https://github.com/FaaSr/FaaSr-Functions/blob/main/tutorial/tutorial.json`
- Click on _Import from GitHub URL_
- Click on _Edit Compute Servers_ (top bar), click on _GH_ (top left), then replace _YOUR_USERNAME_ with your GitHub account name

### Step 2: Download to your computer and upload to FaaSr-workflow

- Click on _Download_ to download tutorial.json to your computer
- Upload tutorial.json to your FaaSr-workflow repository, using your preferred method (e.g. clicking on the _+_ button, selecting Upload file, and dragging tutorial.json)

## Register the workflow

- You first need to [register the workflow] before it can be invoked
- Click on _Actions_
- Click on `(FAASR REGISTER)` (left)
- Click on the `Run workflow` drop-down; enter `tutorial.json` and click on `Run workflow`
- This will take a few seconds to complete; wait until the action completes before proceeding
- Note: if successful, `(FAASR REGISTER)` will create two additional GitHub actions for your repository: `tutorial-start` and `tutorial-sum`. These are generated automatically for this workflow, which is named `tutorial` and has two nodes in the graph (`start` and `sum`)

## Invoke the workflow

!!! question "What code am I running?"
    For this tutorial, function code is sourced from the [FaaSr-Functions](https://github.com/FaaSr/FaaSr-Functions) repository. See [Creating Functions](./functions.md) for more information on how FaaSr runs function code.

!!! warning
    Run only [workflows and code that you trust](./security.md#only-reuse-workflowsfunctions-that-you-trust) with FaaSr. Always check that you trust the provenance of the workflow or code that you are running.

- After register, you can [invoke the workflow]
- Click on _Actions_
- Click on `(FAASR INVOKE)` (left)
- Click on the `Run workflow` drop-down; enter `tutorial.json` and click on `Run workflow`
- You will notice three actions will run: `(FAASR INVOKE)` is used to "kick-start" your workflow; `tutorial-start` and `tutorial-sum` are the two actions generated automatically for this workflow in the previous step
- Wait until these actions complete before proceeding

## Check outputs

The workflow outputs are stored in the Minio Play S3 bucket. There are different ways you can access it, with different S3 clients (e.g. Minio client); we will use the Minio Play console in this tutorial:

- Browse to [minio play web UI](https://play.min.io:9443/login)
- For user name, enter `Q3AM3UQ867SPQQA43P2F`
- For password, enter `zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG`
- On the search textbox (top left) enter `faasr`. Select the faasr bucket, then the tutorial folder to see the output files

## Another example

The tutorial.json workflow is based on two R functions (start, compute_sum). Another example is found in tutorialRpy.json that uses an R function (start) followed by a Python function (compute_sum). If you'd like to test this out, repeat the process of:

- importing `https://github.com/FaaSr/FaaSr-Functions/blob/main/tutorial/tutorialRpy.json` into the WebUI
- edit your username
- download tutorialRpy.json to your computer
- upload tutorilRpy.json to your FaaSr-workflow repo
- `(FAASR REGISTER)` tutorialRpy.json
- `(FAASR INVOKE)` tutorialRpy.json

[workflow repository]: workflow_repo.md
[GitHub Actions credentials]: credentials.md#github-actions
[FaaSr Workflow Builder Web UI]: https://faasr.io/FaaSr-workflow-builder/
[register the workflow]: register_workflow.md
[invoke the workflow]: invoke_workflow.md

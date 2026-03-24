# Registering workflows

The process of registering workflows is required to go from a workflow _description_ (i.e. a FaaSr-compliant JSON configuration file) to a workflow that can be _invoked_. This is implemented by the GitHub Action `FAASR REGISTER` available in your [FaaSr-workflow repo] once you fork it.

## Requirements

To register a workflow, you need:

- Your forked [FaaSr-workflow repo]
- A JSON workflow configuration file, downloaded from the [workflow Web UI] and uploaded to your [FaaSr-workflow repo]
- Proper [cloud credentials] for any cloud compute servers and data stores you use, stored as GitHub Secrets

## Running FAASR REGISTER

- The workflow registration action `FAASR REGISTER` is available under the `Actions` tab in your [FaaSr-workflow repo] (it is named such that it appears at the top of the action list). to execute, select this action from the list, then click on the drop-down `Run workflow` menu to the right, and enter the name of the JSON workflow configuration file.
- If your workflow uses [custom containers], you are required to tick the checkbox `Allow custom containers`; please review the [security best practices] document.
- If any errors occur during registration, a red `X` icon will appear after the action completes. Click on the action name and then on the `deploy` box to review logs for errors.
- If registration is successful, each action in your workflow results in the creation (or update) of a corresponding action in the cloud provider you use: these could be GitHub actions (for GH compute servers), AWS Lambdas (for AWS), Google Cloud Run jobs (for GCP), OpenWhisk actions (for OW), or Slurm jobs.
- The naming scheme used for the actions created by `FAASR REGISTER` is as follows: `WorkflowName-ActionName` where `WorkflowName` is the workflow name defined in your configuration file (under `Workflow settings` in the [workflow Web UI]), and `ActionName` is the name of the action (each node of the graph in the [workflow Web UI]). For example, for the FaaSr tutorial, the workflow name is `tutorial` and there are two actions in the graph (`start` and `sum`); correspondingly, two GitHub Actions are created, named `tutorial-start` and `tutorial-sum`.

[FaaSr-workflow repo]: workflow_repo.md
[workflow Web UI]: workflows.md
[cloud credentials]: credentials.md
[security best practices]: security.md
[custom containers]: advanced.md

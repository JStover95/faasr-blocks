# Invoking workflows

After successfully [registering a workflow], the workflow is ready to be _invoked_. This is implemented by the GitHub Action `FAASR INVOKE`, also available in your [FaaSr-workflow repo] once you fork it. In short, `FAASR INVOKE` "kick-starts" your workflow by invoking its entry point action; subsequent actions are then executed according to the order implied by your workflow DAG as per the [programming model].

## Requirements

To invoke a workflow, you need:

- Your forked [FaaSr-workflow repo]
- A JSON workflow configuration file, downloaded from the [workflow Web UI] and uploaded to your [FaaSr-workflow repo], successfully registered with `FAASR REGISTER`
- Proper [cloud credentials] for any cloud compute servers and data stores you use, stored as GitHub Secrets. These secrets must also be copied and available in cloud platforms that have native secret stores, AWS and GCP

## Running FAASR INVOKE

- The workflow invocation action `FAASR INVOKE` is available under the `Actions` tab in your [FaaSr-workflow repo] (it is named such that it appears near the top of the action list).
- To execute, select this action from the list, then click on the drop-down `Run workflow` menu to the right, and enter the name of the JSON workflow configuration file.
- If invocation is successful, each action in your workflow results in the execution of a a corresponding action in the cloud provider you use: these could be GitHub actions (for GH compute servers), AWS Lambdas (for AWS), Google Cloud Run jobs (for GCP), OpenWhisk actions (for OW), or Slurm jobs.
- The naming scheme used for the actions invoked throughout the workflow by `FAASR INVOKE` is as follows: `WorkflowName-ActionName` where `WorkflowName` is the workflow name defined in your configuration file (under `Workflow settings` in the [workflow Web UI]), and `ActionName` is the name of the action (each node of the graph in the [workflow Web UI]).
- For example, for the FaaSr tutorial, the workflow name is `tutorial` and there are two actions in the graph (`start` and `sum`); correspondingly, two GitHub Actions are executed, _in sequence_, namely: `tutorial-start` followed by `tutorial-sum`.
- If any errors occur during invocation, a red `X` icon will appear after the action completes. Click on the action name and then on the `deploy` box to review logs for errors.
- Errors that may happen during the workflow execution will appear with the same red `X` icon, if you use GH as your cloud compute platform. If you invoke workflows in other platforms (AWS, GCP, OW, SLURM), error logs will be available on that cloud platform rather than on GitHub Actions.

[workflow Web UI]: workflows.md
[cloud credentials]: credentials.md
[registering a workflow]: register_workflow.md
[FaaSr-workflow repo]: workflow_repo.md
[programming model]: prog_model.md

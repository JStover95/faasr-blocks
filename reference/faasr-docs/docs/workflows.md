# Creating and Editing Workflows

In a new browser tab or window, open the [Workflow Builder Web UI](https://faasr.io/FaaSr-workflow-builder/). This Web-based user interface is used for composing and editing workflows to create FaaSr-compliant workflow JSONs. You can create one from scratch, or upload an existing FaaSr workflow JSON and edit it.

## Uploading and Downloading Workflows

To upload an existing workflow, either upload a JSON file stored locally, or enter the URL of a workflow JSON stored in Github (e.g. `https://github.com/FaaSr/FaaSr-Functions/blob/main/tutorial/tutorial.json`).

To download your workflow, navigate to the Download tab, and click 'Download *my-workflow*.json'. The web UI will verify that the JSON is compliant, and report any errors that need to be fixed, such as missing fields that are required. 

## Download and save frequently!

It is good practice to download checkpoints of your workflow as you make changes to it in order to prevent loss from a browser crash or unintentional window/tab closing. If the workflow is incomplete, the web UI will notify you of it but still allows you to download.

### Working with Layout Files

Layout files contain information about the position of the action nodes in the web UI. It does not affect the behavior of the workflow. To save the workflow layout, navigate to the Download tab, and click 'Download *my-workflow*-layout.json'. To restore a workflow layout, first navigate to the Upload tab and upload your workflow JSON. Then, click 'Load layout file' and upload your layout file to restore the layout of your workflow.

## Secrets

The workflow builder web UI is not used to insert secrets into the workflow. Rather, secrets for your data stores and compute servers will be entered as Github Actions Secrets in your FaaSr-workflows repository. See Configuring Secrets in the [workflow repo] documentation.
## Data Stores

Data Stores are S3 buckets (cloud storage locations), for example AWS S3 or MinIO. In order to run FaaSr workflows, you must specify at least one Data Store. To create a data store, click `Create Data Store` and specify a name for your data store. This name will be used to reference the data store when using the FaaSr S3 APIs.

**Endpoint**
A web URL specifying the location of the S3 server. For example, `https://play.min.io` for MinIO's Play sandbox, or an [Amazon S3 endpoint](https://docs.aws.amazon.com/general/latest/gr/s3.html#s3_region).

**Bucket**
A unique name identifying the S3 bucket. 

**Region**
For AWS S3, you're required to specify the region of your S3 bucket. For example, `us-east-1`.

## Compute Servers

Each action you define in your workflow must have an associated compute server to run on. When you create a new compute server, it will get a default name based on the platform chosen. You should **not** modify this name unless you plan to use FaaSr with custom [advanced] actions. You must then fill out any required fields for that platform.

## Actions

To create a new action in your workflow, navigate to the 'Edit Actions/Functions' tab, and enter a name for the action in the dropdown box. This action name is the unique identifier for a node in the workflow DAG. Then, create a [function] and link it to this action by supplying the Function Name and Function's Git Repo/Path. It's also required to specify the Function Type (i.e. language, Python and R are supported) and the Compute Server on which the action will be invoked. 

#### Adding/Removing an Action from the Layout

You may remove an existing action from the layout to exclude it from your workflow without deleting it permanently. If you export a workflow with an action removed from the layout, that action and any incoming or outgoing invocations will be stripped from your workflow. To add an action back to the layout, select that action in the dropdown box, and click 'Add Action to Layout'.

### Next Actions To Invoke

Choose which subsequent actions will be invoked when your action finishes executing. Descendant actions will run when all of their predecessors have finished executing.

#### Rank

If you specify a rank *n* for a descendant action, that action will be invoked *n* times. You can set the rank of descendant action by entering the rank in the input next to the descendant's name. **Ranked actions may not have more than one predecessor**.

#### Conditional Invocations ####

You may also create conditional invocations, which enable branching in your workflow based on the return value of your action. Invocations designated True only activate if the return value of the invoking action is True; likewise, Invocations designated False only activate if the return value of the invoking action is False.

### Action Containers

Each action must be associated with a container that it will run inside of. A FaaSr Container will be automatically selected as a default based on the compute server/function type pair. Advanced users may develop and specify custom containers.

### Packages

You may specify package for each action; these packages will be included in your container and available for use by your function. PyPI and CRAN packages can be added by name to your functions. GitHub repositories can be added by adding their URL as a GitHub package.

## Workflow Settings

In the 'Workflow Settings' tab, you must specify the following settings:

**Workflow Name**
**Entry Point**
- The first action in the workflow. The action must not have predecessors.
**Default Data Store**
- This data store will be used if you use the FaaSr S3 APIs without specifying a specific data store.

You can also change the following optional settings:
**Log File Name**
- Logs created in the S3 Bucket will have this name
**InvocationID**
- Determines the unique location for a workflow invocation's logs - see [Invocation IDs]
**Data Store for Logs**
- Specify a separate S3 server for logs 

[workflow repo]: workflow_repo.md
[advanced]: advanced.md
[function]: functions.md
[Invocation IDs]: invocationid.md


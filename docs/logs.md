# Logs

## FaaSr logs

Logs produced by FaaSr functions using the `faasr_log()` API are stored in an S3 server. This document overviews how to select an S3 server to store these logs, and the folder naming structure to help you locate a particular log

## Selecting an S3 bucket for logs

- In the typical scenario, a single S3 server/bucket can be used for both workflow files and logs, but you may also use separate buckets
- The S3 server used for logs is configured as the **Default server to store logs** under **Workflow settings** in the [FaaSr Workflow Builder Web UI] 

## Log folder naming convention

- Using the [FaaSr Workflow Builder Web UI] you must name your workflow uniquely; we'll use `WorkflowName` in this example
- Using the [FaaSr Workflow Builder Web UI] you can also provide a name for the top-level log folder; if you do not provide one, by default the name is is set to `FaaSrLog`
- Then, the path where you can find logs for a particular _Action_ function execution is:

`FaaSrLog/WorkflowName/InvocationTimestamp/InvocationID/ActionName.txt`

Where:
- `ActionName` is the name of the action (i.e. the name of a node in your DAG)
- `InvocationID` is a _specific invocation_ of your _Action_. Refer to the [invocationID] documentation for the different types of invocation IDs supported (UUID, user-provided, and timestamp-derived)
- `InvocationTimestamp` is a string-formatted invocation timestamp recorded at the time your workflow's entry action starts execution. It is recorded as an ISO 8601-like timestamp with filename-safe separators

## Examples

- Suppose you run the [FaaSr tutorial] as an example
- In this workflow configuration, the log folder is the default `FaaSrLog` and the workflow name is `FaaSrTutorial`
- Suppose you also leave the `InvocationID` as default, which generates a unique [UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier) automatically at the _start_ entry point. In this example, let's assume the UUID generated is: `f81d4fae-7dec-11d0-a765-00a0c91e6bf6`
- Suppose when you invoke the workflow, the current time seen by the _start_ action was timestamped as `2025-08-29T23-17-01`

You will then be able to retrieve logs for the *compute_sum* action from the (unique) path: 

`FaaSrLog/FaaSrTutorial/2025-08-29T23-17-01/f81d4fae-7dec-11d0-a765-00a0c91e6bf6/compute_sum.txt`

If you invoke the workflow again, a new timestamp and UUID will be generated

## Cloud logs

- In addition to FaaSr-specific logs (i.e. where you use the `faasr_log()` API), you will find provider-specific action logs in your cloud provider of choice
- Please refer to their documentation:
- [GitHub Action logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)
- [AWS Lambda logs](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs-view.html)
- [Google cloud logs](https://cloud.google.com/run/docs/logging)

[FaaSr Workflow Builder Web UI]: workflows.md
[invocationID]: invocationid.md
[FaaSr tutorial]: tutorial.md
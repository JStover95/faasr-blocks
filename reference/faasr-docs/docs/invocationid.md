# Invocation IDs

Each FaaSr workflow can be tagged with a unique ID. This is useful for two key reasons:

* It determines where [logs] are stored
* It allows you to derive unique names from your FaaSr functions, e.g. to create unique file names

FaaSr allows you to specify a method for your unique invocation ID in one of three choices:

* Randomly-generated UUID (default)
* Timestamp-derived ID
* User-provided ID

The invocation ID can be retrieved in your user functions using the [R API] or [Python API], respectively.

## Default: randomly-generated UUID

This is the default method in the WebUI, and the behavior is as follows:

* A [UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier) is generated randomly in the _entry action of your workflow_, e.g. `550e8400-e29b-41d4-a716-446655440000`
* The UUID generated in the entry action is automatically _propagated to all actions in your workflow_

## Timestamp-derived ID

This method can be selected in the WebUI under _Workflow Settings_ in the drop-down menu for _InvocationID_. If selected, you need to also determine the _Timestamp format_ to be used to derive the Invocation ID. The behavior is as follows:

* A timestamp string is generated in the _entry action of your workflow_ based on the UTC local time of the invocation of the action
* The format of the timestamp is defined as a string that follows the [strftime format from the Python datetime class](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior) specifies which fields of the data/time are used. This depends on your particular use case - e.g. for a timestamp that is unique daily you can use `%Y%m%d`; unique hourly: `%Y%m%d%H`; unique per minute: `%Y%m%d%H%M`
* Example: Suppose the entry action is dispatched on October 21, 2025 at 11:03pm (or 23:03). A timestamp format for daily, i.e. `%Y%m%d` generates an invocation ID that looks like `20251021`. A timestamp format for hourly, i.e. `%Y%m%d%H`, generates an invocation ID `2025102123`. A timestamp format for per-minute, i.e. `%Y_%m_%d_%H_%M`, generates an invocation ID `2025_10_21_23_03`

## User-provided ID

Finally, in the user-provided ID, the invocation ID is provided by the user in the JSON configuration.


[logs]: logs.md
[R API]: r_api.md
[Python API]: py_api.md
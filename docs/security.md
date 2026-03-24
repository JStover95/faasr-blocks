# Security best-practices

FaaSr faciliattes the process of executing workflows in cloud platforms for you. It is important for you to be aware of best-practices to safeguard from running unintended code as part of these workflows.

## Use the default container images whenever possible

FaaSr deploys containers for each action of your workflow. The default container images built and published to container registries maintained by FaaSr developers build on Ubuntu Linux, Python, and a minimal set of dependences to minimize the risk of vulnerabilities. For your information, the list of dependences used in FaaSr containers are available in the [FaaSr Docker](https://github.com/FaaSr/FaaSr-Docker) repository.

If you need to use a custom container, it is strongly recommended that you build the container yourself, or that you trust the user/registry where the container resides. The [FAASR REGISTER] GitHub action requires you to explicitly check that you acknowledge the use of custom containers if they are detected in your workflow JSON configuration to prevent you from unintentionally using a custom container.

## Only reuse workflows/functions that you trust

If you plan to reuse workflows (JSON configuration files) and functions (Python or R) created by other users, make sure you trust their provenance. Similarly to when you download and run code from the Internet into your computer, it is crucial that you trust code that runs in your cloud accounts to prevent misuse.


[FAASR REGISTER]: register_workflow.md
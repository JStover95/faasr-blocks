# Using package dependences

## Overview

If a function has package dependences, it is possible to declare them when you create your workflow using the [FaaSr Workflow Builder Web UI].  Dependences are downloaded and installed dynamically before your function is executed

## R dependences

When you create/edit an Action in the Web UI, scrolling the left pane to the bottom there are entries for:

- *GitHub Packages for the Function*: this can be used to install a package hosted in a GitHub repository. Provide the name of the GitHub repository to install from, for example
- *CRAN Packages for the Function*: this can be used to install a package hosted in CRAN. Provide the name of the package in the text box, for example *ridigbio*

Import the dependence in your function, e.g. *library('ridigbio')*

## Python dependences


[FaaSr R APIs]: r_api.md
[FaaSr Python APIs]: py_api.md
[FaaSr Workflow Builder Web UI]: workflows.md
[FaaSr tutorial]: tutorial.md
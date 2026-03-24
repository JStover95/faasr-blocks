# Process for development on workflow builder gui

## Workflow-Builder repository
In order to start development on the workflow builder, you must first fork it's repository at [github.com/FaaSr/FaaSr-workflow-builder](https://github.com/FaaSr/FaaSr-workflow-builder).

* **Note**: Uncheck `Copy the main branch only` during forking to ensure the gh-pages branch is populated with the most recent build.

## Local dev environment

### Dependencies
Once you forked this repository, install all necessary dependencies: 

* Run `npm ci`

### Testing Locally
* Run `npm start` to launch the development server
* The application will be accessible at [localhost:3000/](http://localhost:3000/)

### Hosting on GitHub Pages
To host your fork on GitHub Pages for external access:

* Run `npm run deploy` to build and populate the gh-pages branch
* Navigate to Settings → Pages in your forked repository
* Select the `gh-pages` branch with `/root` as the source
* After deployment completes, your site will be available at [https://YOUR_GITHUB_USERNAME.github.io/FaaSr-workflow-builder/](https://YOUR_GITHUB_USERNAME.github.io/FaaSr-workflow-builder/)
* To deploy updates: run `npm run deploy` and changes will be live within minutes

## Applying changes to main repository
You simply need to issue a pull request. When the pull request is completed, the page will automaticaly start a GH Action to build what is in the main src branch to the gh-pages branch and then deploy that build at [faasr.io/FaaSr-workflow-builder/](https://faasr.io/FaaSr-workflow-builder/).


## Internal Development Tools

### Enabling debug mode
To access development-only debugging features during local testing:

- Set the `debug` constant in `WorkflowContext.js` to `true`
- If you add new debug features, make them depend on this variable as well
- Remember to set it back to `false` before submitting a pull request

### Available debugging utilities

- *Toggle Workflow*: Displays a panel showing the current workflow object
- *Toggle Layout*: Displays a panel showing the current nodes and edges objects
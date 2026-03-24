# Process for building Docker containers

## FaaSr-Docker repository

The FaaSr/FaaSr-Docker repository contains the Dockerfiles and entry points needed to build containers for the different supported platforms. If you want to build your own custom containers, you can fork this repository and configure it to build containers with your own environment and publish them in your own container registry account(s)

## Secrets needed

When you fork this repository, you need to set up the following GitHub Actions repository secrets:

* `DOCKERHUB_USERNAME`: user name of account to publish images to DockerHub
* `DOCKERHUB_TOKEN`: token to publish images to DockerHub
* `AWS_ACCESS_KEY_ID`: access key to publish images to Amazon ECR
* `AWS_SECRET_ACCESS_KEY`: secret key to publish images to Amazon ECR

## Building base containers

Before building any platform-specific containers (e.g. for GH, AWS, GCP), you need to build the base container. The platform-specific containers all build from this base container.

### Building Python base container

* In `Actions`, select `py-base->DockerHub`
* Click on `Run workflow`
* In `username:tag` to build from, typically you will leave the default (e.g. `python:3.13`)
* In `name to be used for this base FaaSr image` you also typically leave the default, `base-python`
* In `FaaSr version tag`, enter the tag of the `FaaSr-Backend` repository to build from. Typically, this will be the current release of FaaSr, e.g. `2.1.0`
* Run the workflow; once completed, it will publish the image to your DockerHub account, e.g. `yourname/base-python:2.1.0`

### Building R/Rocker base container

* In `Actions`, select `rocker-base->DockerHub`
* Click on `Run workflow`
* In `username:tag` to build from, typically you will leave the default (e.g. `rocker/tidyverse:4.4`)
* In `name to be used for this base FaaSr image` you also typically leave the default, `base-r`
* In `FaaSr version tag`, enter the tag of the `FaaSr-Backend` repository to build from. Typically, this will be the current release of FaaSr, e.g. `2.1.0`
* Run the workflow; once completed, it will publish the image to your DockerHub account, e.g. `yourname/base-r:2.1.0`

## Building platform-specific containers

Once you have successfully built the base containers for Python and/or R, you will be able to build the following platform-specific containers

### GitHub Actions

* Select Action `github-actions->GHCR`
* Click `Run workflow`
* In `user/name:tag of the base FaaSr image`, enter the DockerHub name of one of the image you created above, e.g. `yourname/base-python:2.1.0` or `yourname/base-r:2.1.0`
* In `name of the FaaS-specific image to build`, enter the name of the image. This _does not_ include your account name or tag - e.g. for python the default names we use are: `github-actions-python` and for r `github-actions-r`
* In `FaaSr-py version` enter the same release number of the FaaSr-Backend used when building the base image, e.g. `2.1.0`
* In `GitHub repo to install FaaSr-py from` enter the repo to build the Backend from. Typically this is the main `faasr/FaaSr-Backend` repo, but you can build from your own repo as well (e.g. if have forked FaaSr-Backend to develop and test a new feature)
* In `GitHub Container Repository (GHCR) to push image to` enter the name of your github account to publish the image to
* Run the workflow; once completed, it will publish the image to your GHCR account, e.g. `ghcr.io/yourusername/github-actions-python:2.1.0`

### OpenWhisk

* Select Action `openwhisk->DockerHub`
* Click `Run workflow`
* In `user/name:tag of the base FaaSr image`, enter the DockerHub name of one of the image you created above, e.g. `yourname/base-python:2.1.0` or `yourname/base-r:2.1.0`
* In `name of the FaaS-specific image to build`, enter the name of the image. This _does not_ include your account name or tag - e.g. for python the default names we use are: `openwhisk-python` and for r `openwhisk-r`
* In `FaaSr-py version` enter the same release number of the FaaSr-Backend used when building the base image, e.g. `2.1.0`
* In `GitHub repo to install FaaSr-py from` enter the repo to build the Backend from. Typically this is the main `faasr/FaaSr-Backend` repo, but you can build from your own repo as well (e.g. if have forked FaaSr-Backend to develop and test a new feature)
* Run the workflow; once completed, it will publish the image to your DockerHub account, e.g. `yourusername/github-actions-python:2.1.0`

There is also an arm64 build process available for OpenWhisk - simply follow similar steps to build the base and OpenWhisk images as above, but use `py-base-arm->DockerHub` and `openwhisk-arm->DockerHub` instead

### AWS Lambda

* Select Action `aws-lambda->ECR`
* Click `Run workflow`
* In `user/name:tag of the base FaaSr image`, enter the DockerHub name of one of the image you created above, e.g. `yourname/base-python:2.1.0` or `yourname/base-r:2.1.0`
* In `name of the FaaS-specific image to build`, enter the name of the image. This _does not_ include your account name or tag - e.g. for python the default names we use are: `aws-lambda-python` and for r `aws-lambda-r`
* In `FaaSr-py version` enter the same release number of the FaaSr-Backend used when building the base image, e.g. `2.1.0`
* In `GitHub repo to install FaaSr-py from` enter the repo to build the Backend from. Typically this is the main `faasr/FaaSr-Backend` repo, but you can build from your own repo as well (e.g. if have forked FaaSr-Backend to develop and test a new feature)
* In `AWS ECR region to push image to` enter the region of ECR to publish to
* Run the workflow; once completed, it will publish the image to your DockerHub account, e.g. `yourECR/aws-lambda-python:2.1.0`

### Google Cloud

* Select Action `gcp->DockerHub`
* Click `Run workflow`
* In `user/name:tag of the base FaaSr image`, enter the DockerHub name of one of the image you created above, e.g. `yourname/base-python:2.1.0` or `yourname/base-r:2.1.0`
* In `name of the FaaS-specific image to build`, enter the name of the image. This _does not_ include your account name or tag - e.g. for python the default names we use are: `gcp-python` and for r `gcp-r`
* In `FaaSr-py version` enter the same release number of the FaaSr-Backend used when building the base image, e.g. `2.1.0`
* In `GitHub repo to install FaaSr-py from` enter the repo to build the Backend from. Typically this is the main `faasr/FaaSr-Backend` repo, but you can build from your own repo as well (e.g. if have forked FaaSr-Backend to develop and test a new feature)
* Run the workflow; once completed, it will publish the image to your DockerHub account, e.g. `yourusername/gcp-python:2.1.0`

### Slurm

* Select Action `slurm->DockerHub`
* Click `Run workflow`
* In `user/name:tag of the base FaaSr image`, enter the DockerHub name of one of the image you created above, e.g. `yourname/base-python:2.1.0` or `yourname/base-r:2.1.0`
* In `name of the FaaS-specific image to build`, enter the name of the image. This _does not_ include your account name or tag - e.g. for python the default names we use are: `slurm-python` and for r `slurm-r`
* In `FaaSr-py version` enter the same release number of the FaaSr-Backend used when building the base image, e.g. `2.1.0`
* In `GitHub repo to install FaaSr-py from` enter the repo to build the Backend from. Typically this is the main `faasr/FaaSr-Backend` repo, but you can build from your own repo as well (e.g. if have forked FaaSr-Backend to develop and test a new feature)
* Run the workflow; once completed, it will publish the image to your DockerHub account, e.g. `yourusername/slurm-python:2.1.0`

## Customizing Dockerfiles

If you need to customize your Dockerfiles with particular dependences, these can be found in the `faas_specific` folder. Edit as needed to add your dependences; you must not change the `WORKDIR`, `ARG`, `RUN`, `COPY`, `FROM` and `CMD` statements - you can only add dependences.



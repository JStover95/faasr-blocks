# Creating cloud credentials

## S3 data server

- In general, the credentials you need from your S3 account are the `AccessKey` and the `SecretKey`. These are akin to user names and passwords.
- How you obtain these credentials will depend on your provider (e.g. AWS S3, MINIO, OSN see the [S3] document for additional information)
- Paste the access key and the secret key as _Repository secrets_ in your _FaaSr-workflow_ as per the instructions in the [workflow repo] documentation

## GitHub Actions

If you don't already have one, you need to generate a GitHub Personal Access Token (PAT) to configure FaaSr.
[Details on how to create a PAT are available here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic)

In summary:

- In the upper-right corner of any page, click your profile photo, then click Settings.
- In the left sidebar, click Developer settings.
- In the left sidebar, click Personal access tokens.
- Click Generate new token.
- In the "Note" field, give your token a descriptive name.
- In scopes, select “workflow” and “read:org” (under admin:org)
- Copy the token; you may save it in your local computer's password manager as well
- Paste the token under the name `GH_PAT` as a _Repository secret_ in your _FaaSr-workflow_ as per the instructions in the [workflow repo] documentation

## AWS Lambda

- You need an access key, secret key, and ARN to use Lambda in FaaSr.
- You can access your access and secret keys, and your ARN from your [Amazon AWS console](https://console.aws.amazon.com/console/home).
- Paste the access key and the secret key under the names `AWS_AccessKey` and `AWS_SecretKey`, respectively, as _Repository secrets_ in your _FaaSr-workflow_ as per the instructions in the [workflow repo] documentation
- Paste your ARN as `AWS_ARN` as _Repository secrets_ in your _FaaSr-workflow_

## OpenWhisk

- You need an API key from your provider to configure for use in FaaSr
- How you obtain this will depend on your cloud provider.
- Paste the API key under the name `OW_APIkey` as a _Repository secret_ in your _FaaSr-workflow_ as per the instructions in the [workflow repo] documentation

## Google Cloud Platform

- You need a private secret key to use Google Cloud Platform (GCP) with FaaSr
- You can access your key from the [Google Cloud console](https://console.cloud.google.com)
- TBD

## Slurm

TBD


[workflow repo]: workflow_repo.md
[S3]: s3.md

<!--
SPDX-FileCopyrightText: 2025 Dominik Wombacher <dominik@wombacher.cc>

SPDX-License-Identifier: Apache-2.0
-->

# Infrastructure: Automation

Infrastructure-as-Code (IaC) for 'Automation' Account / Project

<!-- markdownlint-disable MD013 -->
[![REUSE status](https://api.reuse.software/badge/github.com/wombelix/infra-automation)](https://api.reuse.software/info/github.com/wombelix/infra-automation)
[![Mirror](https://github.com/wombelix/infra-automation/actions/workflows/mirror.yml/badge.svg)](https://github.com/wombelix/infra-automation/actions/workflows/mirror.yml)
<!-- markdownlint-enable MD013 -->

## Table of Contents

* [Usage](#usage)
* [Source](#source)
* [Contribute](#contribute)
* [License](#license)

## Usage

### Prerequisites

* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/)
* [Rain](https://github.com/aws-cloudformation/rain)
* [Task](https://taskfile.dev/)

### IAM Roles

The IAM roles for CloudFormation are managed in `cfn/iam-cfn-roles.yaml`.
Two roles exist:

* `CustomerServiceRoleForCloudformationInfraAutomation` -
  Used by CloudFormation to manage IaC resources (KMS, S3, DynamoDB, IAM)
* `CustomerServiceRoleForCloudformationInfraAutomationGitSync` -
  Used by CodeConnections for Git sync

Deploy the roles:

```bash
task iam-cfn-roles:deploy
```

Run `task` to list all available tasks.

### Git Sync Stacks

Create CloudFormation stacks with Sync from Git through the AWS console.
Use the Role ARN from `task iam-cfn-roles:deploy` output as IAM execution role.
Point to the repo mirror on GitHub and each `stack-deployment-*.yaml` file.
Create one stack per entry point file.

Deploy `*-replica` stacks in the secondary region (eu-west-1),
all others in the primary region (eu-central-1).

### Stack Deployment Order

Due to cross-stack and cross-region dependencies, deploy stacks in this order:

1. **IAM roles** (eu-central-1): `task iam-cfn-roles:deploy`
1. **KMS Primary** (eu-central-1): `stack-deployment-kms.yaml`
1. **KMS Replica** (eu-west-1): `stack-deployment-kms-replica.yaml`
   * **Note:** Update `KMSKeyBackendEncryptionPrimaryArn` parameter with the
     ARN exported from the primary KMS stack before deployment
1. **IaC Replica** (eu-west-1): `stack-deployment-iac-replica.yaml`
1. **IaC Primary** (eu-central-1): `stack-deployment-iac.yaml`

The IaC Replica must be deployed before IaC Primary because the primary S3
bucket replication config references the replication IAM role
created in the replica stack.

## Source

The primary location is:
[github.com/wombelix/infra-automation](https://github.com/wombelix/infra-automation)

Mirrors are available on
[Codeberg](https://codeberg.org/wombelix/infra-automation) and
[Gitlab](https://gitlab.com/wombelix/infra-automation).

## Contribute

Pick the platform you prefer and are most comfortable with.

Provide feedback, open an issue or create a pull / merge request.

## License

Unless otherwise stated: `Apache 2.0`

All files contain license information either as a
`header comment` or a `corresponding .license` file.

[REUSE](https://reuse.software) from the [FSFE](https://fsfe.org/)
is implemented to verify license and copyright compliance.

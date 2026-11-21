#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Dominik Wombacher <dominik@wombacher.cc>
#
# SPDX-License-Identifier: Apache-2.0

# Deploys a CloudFormation stack through a change set, like rain deploy
# Usage: cfn-deploy.sh <deploy|preview> <stack> <template> <region>
# The same file is in infra-aws-org, keep both copies in sync
set -euo pipefail

mode="$1"
stack="$2"
template="$3"
region="$4"
change_set="task-$(date +%Y%m%d%H%M%S)"

cfn() {
  aws cloudformation "$@" --region "$region" --no-cli-pager
}

delete_change_set() {
  cfn delete-change-set --stack-name "$stack" --change-set-name "$change_set"
}

# A missing stack is the only describe error that is expected
if output=$(cfn describe-stacks --stack-name "$stack" --query 'Stacks[0].StackStatus' --output text 2>&1); then
  status="$output"
elif [[ "$output" == *"does not exist"* ]]; then
  status="NONE"
else
  echo "$output" >&2
  exit 1
fi

case "$status" in
  NONE | REVIEW_IN_PROGRESS)
    change_set_type="CREATE"
    # A failed first create deletes the stack instead of leaving ROLLBACK_COMPLETE
    extra_args=(--on-stack-failure DELETE)
    ;;
  ROLLBACK_COMPLETE)
    echo "Stack $stack is in ROLLBACK_COMPLETE and cannot be updated. Delete it first." >&2
    exit 1
    ;;
  *_IN_PROGRESS)
    echo "Stack $stack is busy: $status" >&2
    exit 1
    ;;
  *)
    change_set_type="UPDATE"
    extra_args=()
    ;;
esac

# No --tags, so the stack keeps its tags. No --parameters, so the template defaults apply
cfn create-change-set \
  --stack-name "$stack" \
  --change-set-name "$change_set" \
  --change-set-type "$change_set_type" \
  --template-body "file://$template" \
  --capabilities CAPABILITY_NAMED_IAM \
  "${extra_args[@]}" > /dev/null

# The waiter also fails when the change set has no changes, the status below decides and reports errors
cfn wait change-set-create-complete --stack-name "$stack" --change-set-name "$change_set" 2> /dev/null || true

change_set_status=$(cfn describe-change-set --stack-name "$stack" --change-set-name "$change_set" --query Status --output text)
change_set_reason=$(cfn describe-change-set --stack-name "$stack" --change-set-name "$change_set" --query StatusReason --output text)

if [[ "$change_set_status" == "FAILED" ]]; then
  delete_change_set
  if [[ "$change_set_reason" == *"didn't contain changes"* || "$change_set_reason" == *"No updates are to be performed"* ]]; then
    echo "No changes for stack $stack"
    exit 0
  fi
  echo "Change set failed: $change_set_reason" >&2
  exit 1
fi

cfn describe-change-set --stack-name "$stack" --change-set-name "$change_set" \
  --query 'Changes[].ResourceChange.[Action,LogicalResourceId,ResourceType,Replacement]' \
  --output table

if [[ "$mode" == "preview" ]]; then
  delete_change_set
  exit 0
fi

read -r -p "Execute these changes on stack $stack? [y/N] " answer
if [[ "$answer" != "y" ]]; then
  delete_change_set
  echo "Aborted, nothing changed"
  exit 0
fi

cfn execute-change-set --stack-name "$stack" --change-set-name "$change_set"

if [[ "$change_set_type" == "CREATE" ]]; then
  wait_command="stack-create-complete"
else
  wait_command="stack-update-complete"
fi
if ! cfn wait "$wait_command" --stack-name "$stack"; then
  echo "Deploy of stack $stack failed, check its events" >&2
  exit 1
fi

cfn describe-stacks --stack-name "$stack" --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' --output table

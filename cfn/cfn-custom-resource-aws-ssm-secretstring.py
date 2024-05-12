# SPDX-FileCopyrightText: 2024 Dominik Wombacher <dominik@wombacher.cc>
#
# SPDX-License-Identifier: MIT

# Bootstrapped with 'Custom generic CloudFormation resource example'
# https://github.com/stelligent/cloudformation-custom-resources
# Inspired by 'Creating Secure String in AWS System Manager Parameter Store via AWS CloudFormation'
# https://rnanthan.medium.com/creating-secure-string-in-aws-system-manager-parameter-store-via-aws-cloudformation-f3ab62d9d4c3

import boto3
import json
import logging
from urllib.request import build_opener, HTTPHandler, Request

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    try:
        LOGGER.info('REQUEST RECEIVED:\n %s', event)
        LOGGER.info('REQUEST RECEIVED:\n %s', context)

        parameter_name = event['ResourceProperties']['Name']
        parameter_value = event['ResourceProperties']['Value']
        LOGGER.debug('Parameter Name:\n %s', parameter_name)
        LOGGER.debug('Parameter Value:\n %s', parameter_value)

        if 'Description' in event['ResourceProperties']:
            parameter_description = event['ResourceProperties']['Description']
            LOGGER.debug('Parameter Description:\n %s', parameter_description)
        else:
            parameter_description = ""
        
        if 'KmsKeyId' in event['ResourceProperties']:
            kms_key_id = event['ResourceProperties']['KmsKeyId']
            LOGGER.debug('AWS KMS Key ID:\n %s', kms_key_id)
        else:
            kms_key_id = None

        if 'Tags' in event['ResourceProperties']:
            parameter_tags = event['ResourceProperties']['Tags']
            LOGGER.debug('Parameter Tags:\n %s', parameter_tags)
        else:
            parameter_tags = []

        client = boto3.client('ssm')

        if event['RequestType'] == 'Create':
            LOGGER.info('CREATE!')
            try:
                if kms_key_id is not None:
                    client.put_parameter(
                            Name = parameter_name,
                            Value = parameter_value,
                            Description = parameter_description,
                            Type = 'SecureString',
                            KeyId = kms_key_id,
                            Tier = 'Standard',
                            Overwrite = False,
                            Tags = parameter_tags
                        )
                else:
                    client.put_parameter(
                            Name = parameter_name,
                            Value = parameter_value,
                            Description = parameter_description,
                            Type = 'SecureString',
                            Tier = 'Standard',
                            Overwrite = False,
                            Tags = parameter_tags
                        )
                send_response(event, context, "SUCCESS",
                            {"Message": "Resource creation successful!"})
            except client.exceptions.ParameterAlreadyExists:
                LOGGER.error("Parameter already exists")
                send_response(event, context, "FAILED",
                        {"Message": "Parameter already exists!"})
            except Exception as e:
                LOGGER.error("Exception occurred", exc_info=True)
                send_response(event, context, "FAILED",
                        {"Message": f"Exception occurred - {type(e).__name__} - Resource creation failed!"})

        elif event['RequestType'] == 'Update':
            LOGGER.info('UPDATE!')
            try:
                if kms_key_id is not None:
                    client.put_parameter(
                            Name = parameter_name,
                            Value = parameter_value,
                            Description = parameter_description,
                            Type = 'SecureString',
                            KeyId = kms_key_id,
                            Tier = 'Standard',
                            Overwrite = True
                        )
                else:
                    client.put_parameter(
                            Name = parameter_name,
                            Value = parameter_value,
                            Description = parameter_description,
                            Type = 'SecureString',
                            Tier = 'Standard',
                            Overwrite = True
                        )
                client.add_tags_to_resource(
                        ResourceType = "Parameter",
                        ResourceId = parameter_name,
                        Tags = parameter_tags
                    )

                send_response(event, context, "SUCCESS",
                            {"Message": "Resource updated successful!"})
            except Exception as e:
                LOGGER.error("Exception occurred", exc_info=True)
                send_response(event, context, "FAILED",
                        {"Message": f"Exception occurred - {type(e).__name__} - Resource update failed!"})

        elif event['RequestType'] == 'Delete':
            LOGGER.info('DELETE!')
            try:
                client.delete_parameter(Name = parameter_name)
                send_response(event, context, "SUCCESS",
                        {"Message": "Resource deletion successful!"}
                )
            except client.exceptions.ParameterNotFound:
                LOGGER.warn("Parameter not found.")
                send_response(event, context, "SUCCESS",
                        {"Message": "Resource doesn't exist, not deletion necessary!"}
                )
            except Exception as e:
                LOGGER.error("Exception occurred", exc_info=True)
                send_response(event, context, "FAILED",
                        {"Message": f"Exception occurred - {type(e).__name__} - Resource update failed!"})

        else:
            LOGGER.error('FAILED! Unexpected event received from CloudFormation.')
            send_response(event, context, "FAILED",
                          {"Message": "Unexpected event received from CloudFormation"})

    except Exception as e:
        LOGGER.error('FAILED! Exception during processing.', exc_info=True)
        send_response(event, context, "FAILED", {
            "Message": f"Exception during processing - {type(e).__name__}"})


def send_response(event, context, response_status, response_data):
    '''Send a resource manipulation status response to CloudFormation'''
    response_body = json.dumps({
        "Status": response_status,
        "Reason": "See the details in CloudWatch Log Stream: " + context.log_stream_name,
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event['StackId'],
        "RequestId": event['RequestId'],
        "LogicalResourceId": event['LogicalResourceId'],
        "Data": response_data
    })

    LOGGER.info('ResponseURL: %s', event['ResponseURL'])
    LOGGER.info('ResponseBody: %s', response_body)

    opener = build_opener(HTTPHandler)
    request = Request(event['ResponseURL'], data=response_body)
    request.add_header('Content-Type', '')
    request.add_header('Content-Length', len(response_body))
    request.get_method = lambda: 'PUT'
    response = opener.open(request)
    LOGGER.info("Status code: %s", response.getcode())
    LOGGER.info("Status message: %s", response.msg)

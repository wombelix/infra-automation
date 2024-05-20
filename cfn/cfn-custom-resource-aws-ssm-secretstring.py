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
import urllib3

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()


def lambda_handler(event, context):
    response = {
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Status': 'SUCCESS',
        'Data': {}
    }
    try:
        LOGGER.info('REQUEST RECEIVED:\n %s', event)
        LOGGER.info('REQUEST RECEIVED:\n %s', context)

        parameter_name = event['ResourceProperties']['Name']
        parameter_value = event['ResourceProperties']['Value']
        LOGGER.debug('Parameter Name:\n %s', parameter_name)
        LOGGER.debug('Parameter Value (truncated, first five characters):\n %s', parameter_value[0:5])

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
                send(event, context, SUCCESS, response, "CustomResourcePhysicalID")
            except client.exceptions.ParameterAlreadyExists:
                LOGGER.error("Parameter already exists")
                response['Status'] = 'FAILED'
                response['Reason'] = 'Parameter already exists'
                send(event, context, FAILED, response, "CustomResourcePhysicalID")
            except Exception as e:
                LOGGER.error("Exception occurred", exc_info=True)
                response['Status'] = 'FAILED'
                response['Reason'] = f"Exception occurred - {type(e).__name__} - Resource creation failed!"
                send(event, context, FAILED, response, "CustomResourcePhysicalID")

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

                send(event, context, SUCCESS, response, "CustomResourcePhysicalID")
            except Exception as e:
                LOGGER.error("Exception occurred", exc_info=True)
                response['Status'] = 'FAILED'
                response['Reason'] = f"Exception occurred - {type(e).__name__} - Resource update failed!"
                send(event, context, FAILED, response, "CustomResourcePhysicalID")

        elif event['RequestType'] == 'Delete':
            LOGGER.info('DELETE!')
            try:
                client.delete_parameter(Name = parameter_name)
                send(event, context, SUCCESS, response, "CustomResourcePhysicalID")
            except client.exceptions.ParameterNotFound:
                LOGGER.warn("Parameter not found.")
                send(event, context, SUCCESS, response, "CustomResourcePhysicalID")
            except Exception as e:
                LOGGER.error("Exception occurred", exc_info=True)
                response['Status'] = 'FAILED'
                response['Reason'] = f"Exception occurred - {type(e).__name__} - Resource deletion failed!"
                send(event, context, FAILED, response, "CustomResourcePhysicalID")

        else:
            LOGGER.error('FAILED! Unexpected event received from CloudFormation.')
            response['Status'] = 'FAILED'
            response['Reason'] = 'Unexpected event received from CloudFormation'
            send(event, context, FAILED, response, "CustomResourcePhysicalID")

    except Exception as e:
        LOGGER.error('FAILED! Exception during processing.', exc_info=True)
        response['Status'] = 'FAILED'
        response['Reason'] = f"Exception during processing - {type(e).__name__}"
        send(event, context, FAILED, response, "CustomResourcePhysicalID")


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    responseUrl = event['ResponseURL']

    LOGGER.info(responseUrl)

    responseBody = {
        'Status' : responseStatus,
        'Reason' : reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
        'PhysicalResourceId' : physicalResourceId or context.log_stream_name,
        'StackId' : event['StackId'],
        'RequestId' : event['RequestId'],
        'LogicalResourceId' : event['LogicalResourceId'],
        'NoEcho' : noEcho,
        'Data' : responseData
    }

    json_responseBody = json.dumps(responseBody)

    LOGGER.info("Response body:")
    LOGGER.info(json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
        LOGGER.info(f"Status code: {response.status}")

    except Exception as e:
        LOGGER.error('FAILED! Exception while executing http.request.', exc_info=True)

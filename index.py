import logging
import boto3
import json
import os
from helper.ms_teams import post_message_in_chat
from helper.aws_error_getter import get_pipeline_execution

logger = logging.getLogger()
logger.setLevel(logging.INFO)

email_sender = boto3.client('ses')


def get_secret():
    secret_name = os.getenv("REFRESH_TOKEN_ID")
    region_name = os.getenv("REGION")

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )

    secret = json.loads(get_secret_value_response['SecretString'])
    return secret


def get_color_attribute(state):
    if state == 'SUCCEEDED':
        return 'green'
    if state == 'STARTED':
        return 'blue'
    if state == 'FAILED':
        return 'red'


def prepare_message(notification):
    environment = os.getenv("ENVIRONMENT")
    pipeline_name = notification['detail']['pipeline']
    pipeline_state = notification['detail']['state']
    pipeline_region = notification['region']
    pipeline_link = f'https://{pipeline_region}.console.aws.amazon.com/codesuite/codepipeline/' + \
                    f'pipelines/{pipeline_name}/view?region={pipeline_region}'

    if pipeline_state != "FAILED":
        message = f'''<b>{pipeline_name}</b> state was changed. <br>
                Current state: <span style="color:{get_color_attribute(pipeline_state)};"><b>{pipeline_state}</b></span>
                <br>
                Environment: <b>{environment}</b> <br>
                <a href="{pipeline_link}">Go to pipeline</a><br>
                '''
        return message
    else:
        execution_id = notification['detail']['execution-id']
        errors_list = get_pipeline_execution(pipeline_name, execution_id)
        error_string = ''
        for error in errors_list:
            error_string += f'''Failed stage: <b>"{error["stage-name"]}"</b><br>
                            Failed action: <b>"{error["action-name"]}"</b><br>
                            Error:<br><pre>{error["error_message"]}</pre><br>
                            <a href="{error["link"]}">Go to logs</a><br>
                            ------------<br>'''

        message = f'''<b>{pipeline_name}</b> state was changed. <br>
                        Current state: <span style="color:{get_color_attribute(pipeline_state)};">
                        <b>{pipeline_state}</b></span><br>
                        Environment: <b>{environment}</b> <br>
                        <a href="{pipeline_link}">Go to pipeline</a><br>
                        Details: <br>
                        {error_string}
                    '''
        return message


def handler(event: str, _):
    notification = json.loads(event['Records'][0]['Sns']['Message'])
    chat_id = os.getenv("CHANNEL_ID")
    message = prepare_message(notification)

    try:  # Send notification to Teams
        post_message_in_chat(chat_id, message, get_secret()['refresh_token'])
    except Exception as error:  # Send email notification with lambda error
        # Emails should be verified manually in AWS SES settings
        emails_to = [item.strip() for item in os.getenv("EMAIL_TO").split(",")]
        environment = os.getenv("ENVIRONMENT")
        email_sender.send_email(
            Source=os.getenv("EMAIL_FROM"),
            Destination={
                'ToAddresses': emails_to
            },
            Message={
                'Subject': {
                    'Data': f"""{environment}: Lambda for Pipeline Teams notifications failed""",
                    'Charset': "UTF-8"
                },
                'Body': {
                    'Html': {
                        'Data': f"""
                                <b>
                                    This email notifies you that lambda execution for Teams notification regarding
                                    pipeline status failed. <br>
                                    Please check logs.<br>
                                    Error details:
                                </b>
                                <hr />
                                <pre>{error}</pre>
                            """
                    }
                }
            }
        )
        raise error

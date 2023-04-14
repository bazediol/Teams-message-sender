import boto3


def get_pipeline_execution(pipeline_name, execution_id):
    pipeline_client = boto3.client('codepipeline')
    actions = pipeline_client.list_action_executions(
        pipelineName=pipeline_name,
        filter={
            "pipelineExecutionId": execution_id
        }
    )

    for action in actions['actionExecutionDetails']:
        if action['status'] == "Failed":
            failed_action_id = action['output']['executionResult']['externalExecutionId']

            if 'build-batch/' in failed_action_id:
                error_detail = get_failed_batch_errors(
                    failed_action_id.replace('build-batch/', '')
                )
                return error_detail  # in this case list is returned
            else:
                stage_name = action['stageName']
                action_name = action['actionName']
                error_detail = get_build_error(stage_name, failed_action_id, action_name)
                return [error_detail]  # as get_build_error returns dict, it should be returned in list for consistency


def get_failed_batch_errors(batch_id):
    failed_builds = []
    error_list = []
    codebuild_client = boto3.client('codebuild')
    batches = codebuild_client.batch_get_build_batches(
        ids=[
            batch_id
        ]
    )

    for build_group in batches['buildBatches'][0]['buildGroups']:
        if build_group['currentBuildSummary']['buildStatus'] == "FAILED":
            failed_build = {
                "stage-name": build_group['identifier'],
                "id": build_group['currentBuildSummary']['arn'].split('/')[1]
            }
            failed_builds.append(failed_build)

    for build in failed_builds:
        error_list.append(get_build_error(build['stage-name'], build['id']))

    return error_list


def get_build_error(stage_name, failed_build, action_name):
    codebuild_client = boto3.client('codebuild')
    failed_build = codebuild_client.batch_get_builds(
        ids=[failed_build]
    )

    for build in failed_build['builds']:
        error = {
            'stage-name': stage_name,
            'action-name': action_name
        }
        region = build['arn'].split(':')[3]
        account = build['arn'].split(':')[4]
        build_id = build['id']
        project = build['projectName']
        link = f'https://{region}.console.aws.amazon.com/codesuite/codebuild/{account}/projects/{project}/' + \
            f'build/{build_id}/?region={region}'
        for phase in build['phases']:
            if phase['phaseStatus'] == 'FAILED':
                error['error_message'] = phase['contexts'][0]['message']
                error['link'] = link
                return error

from gitlab_ import GitLab
from requests import post
from json import dumps

import argparse


def collect_statistic_for_pipeline(gitlab: GitLab,
                                   save_endpoint: str,
                                   project_name: str,
                                   pipeline_id: int) -> None:
    data = gitlab.get_statistics(gitlab.get_pipeline_by_id(pipeline_id))
    if data:
        data['project'] = project_name
        data['pipeline_id'] = pipeline_id
        response = post(save_endpoint,
                        data=dumps(data),
                        headers={'content-type': 'application/json'})
        print(pipeline_id, response)


def collect_statistics(gitlab: GitLab,
                       save_endpoint: str,
                       project_name: str,
                       per_page: int, page: int) -> None:
    pipelines = gitlab.get_pipelines(status='success', per_page=per_page, page=page)

    for pipeline in pipelines:
        collect_statistic_for_pipeline(gitlab, save_endpoint, project_name, pipeline.id)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Trigger a GitLab Pipeline and wait for its completion')

    ap.add_argument('-s', '--save-endpoint', nargs='?', type=str, help='Endpoint to save metrics')
    ap.add_argument('-p', '--pipeline-id', nargs='?', type=int, help='Numerical Pipeline ID')
    ap.add_argument('-r', '--project-id', type=int, help='Numerical Project ID')
    ap.add_argument('-n', '--project-name', nargs='?', type=str, help='Project Name')
    ap.add_argument('-t', '--private-token',
                    help='An private or personal token authorised to query pipeline status. '
                         'See https://docs.gitlab.com/ee/api/README.html#private-tokens. '
                         'By default, this value is initialized with PRIVATE_TOKEN environment variable.')

    ap.add_argument('--per-page', nargs='?', type=int, default=5)
    ap.add_argument('--page',  nargs='?', type=int, default=1)

    ap.add_argument('--stage-build', nargs='?', type=str, default='build',
                    help='Name of stage, where e2e image builds. Default: build')
    ap.add_argument('--jobs-build', nargs='*', default=['build-e2e'],
                    help='Name of jobs where e2e image builds. Default: build-e2e. '
                         'Can be multiple!')
    
    ap.add_argument('--stage-e2e', nargs='?', type=str, default='test',
                    help='Name of stage, where e2e tests run. Default: test')
    ap.add_argument('--jobs-e2e-blacklist', nargs='*', default=['coverage', 'e2e-lint', 'e2e:lint', 'unit'],
                    help='Name of jobs in stage to be excluded from statistics '
                         '(for example jobs with unit tests with linter). '
                         'Default: coverage e2e-lint e2e:lint unit. '
                         'Can be multiple!')

    ap.add_argument('--job-steps-names', nargs='*', default=['up', 'e2e'],
                    help='Step names in job to track.'
                         'Default: up e2e.'
                         'Supported steps: pull up e2e.'
                         'Save steps in running order!')

    ap.add_argument('--optimistic', action='store_true',
                    help='Not fail metrics collecting if some of jobs don\'t have any')

    args = ap.parse_args()
    args_dict = dict()
    for key in vars(args):
        value = getattr(args, key)
        args_dict[key] = value

    save_endpoint = args_dict['save_endpoint']

    project_id = args_dict['project_id']
    private_token = args_dict['private_token']
    project_name = args_dict['project_name']

    stage_build = args_dict['stage_build']
    jobs_build = args_dict['jobs_build']

    stage_e2e = args_dict['stage_e2e']
    jobs_e2e_blacklist = args_dict['jobs_e2e_blacklist']

    job_steps = args_dict['job_steps_names']

    gitlab = GitLab(project_id, private_token,
                    stage_build, jobs_build,
                    stage_e2e, jobs_e2e_blacklist,
                    job_steps,
                    is_optimistic=args_dict['optimistic'])

    if args_dict['pipeline_id']:
        collect_statistic_for_pipeline(gitlab,
                                       save_endpoint=save_endpoint,
                                       project_name=project_name,
                                       pipeline_id=args_dict['pipeline_id'])
    else:
        collect_statistics(gitlab,
                           save_endpoint=save_endpoint,
                           project_name=project_name,
                           per_page=args_dict['per_page'],
                           page=args_dict['page'])

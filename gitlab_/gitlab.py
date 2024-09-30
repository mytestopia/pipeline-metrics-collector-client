from datetime import datetime
from typing import List, Dict
import gitlab
from gitlab_ import get_job_stats_by_trace
from gitlab.v4.objects import ProjectPipelineJob, ProjectJob


class ErrorLogger:

    def __init__(self, is_optimistic: bool):
        self.is_optimistic = is_optimistic

    def report_exception(self, error: Exception):
        if self.is_optimistic:
            print(error)
        else:
            raise error


class GitLab:
    _SERVER_URL = 'https://gitlab.2gis.ru'

    def __init__(self, project_id: int,
                 private_token: str,
                 stage_build: str,
                 jobs_build: List[str],
                 stage_e2e: str,
                 jobs_e2e_blacklist: List[str],
                 job_steps: List[str],
                 is_optimistic: bool):
        self.server = gitlab.Gitlab(url=self._SERVER_URL, private_token=private_token)
        self.project = self.server.projects.get(id=project_id)

        self.STAGE_BUILD = stage_build
        self.JOBS_BUILD = jobs_build

        self.STAGE_E2E = stage_e2e
        self.JOBS_E2E_BLACKLIST = jobs_e2e_blacklist

        self.JOBS_STEPS = job_steps

        self.error_logger = ErrorLogger(is_optimistic)

    def get_pipelines(self, **kwargs):
        return self.project.pipelines.list(**kwargs)

    def get_pipeline_by_id(self, pipeline_id):
        return self.project.pipelines.get(pipeline_id)

    def filter_e2e_jobs(self, jobs: List[ProjectPipelineJob]) -> List[ProjectPipelineJob]:
        e2e_jobs = list()
        for job in jobs:
            if job.attributes['stage'] == self.STAGE_E2E \
                    and job.attributes['name'] not in self.JOBS_E2E_BLACKLIST:
                e2e_jobs.append(job)
        return e2e_jobs

    def filter_e2e_build_job(self, jobs: List[ProjectPipelineJob]) -> List[ProjectPipelineJob]:
        build_jobs = []
        for job in jobs:
            if job.attributes['stage'] == self.STAGE_BUILD and job.attributes['name'] in self.JOBS_BUILD:
                build_jobs.append(job)
        return build_jobs

    def get_e2e_job_statistics(self, e2e_jobs: List[ProjectPipelineJob], is_passed=True) -> List[Dict]:
        stats = list()

        for pipeline_job in e2e_jobs:
            job = self.get_job(pipeline_job.id)
            duration = pipeline_job.attributes['duration']
            if duration is None:
                print("Error: duration is None")
                print(pipeline_job)
                continue
            job_stat = {
                'name': pipeline_job.attributes['name'],
                'started_at': pipeline_job.attributes['started_at'],
                'finished_at': pipeline_job.attributes['finished_at'],
                'duration': int(duration),
            }
            if is_passed:
                try:
                    job_stat.update(**get_job_stats_by_trace(job.trace(), self.JOBS_STEPS))
                except AttributeError as error:
                    self.error_logger.report_exception(
                        type(error)(f'job {pipeline_job.attributes["name"]}: {str(error)}'))
                except Exception as error:
                    self.error_logger.report_exception(
                        type(error)(f'job {pipeline_job.attributes["name"]}: failed to get time from trace'))
            stats += [job_stat]
        return stats

    @staticmethod
    def get_job_duration(job: ProjectPipelineJob) -> int:
        return int(job.attributes['duration'])

    def get_pipeline_duration(self, pipeline) -> int:
        return pipeline.attributes['duration']

    def get_pipeline_created_time(self, pipeline) -> str:
        return pipeline.attributes['created_at']

    def get_pipeline_ref(self, pipeline):
        return pipeline.attributes['ref']

    def get_jobs(self, pipeline) -> List[ProjectPipelineJob]:
        return pipeline.jobs.list(all=True)

    def get_retried_jobs(self, pipeline) -> List[ProjectPipelineJob]:
        return pipeline.jobs.list(scope=['failed'], include_retried=True)

    def get_job(self, job_id: str) -> ProjectJob:
        return self.project.jobs.get(job_id, lazy=True)

    def get_statistics_failed(self, pipeline) -> List[Dict]:
        failed_jobs = self.get_retried_jobs(pipeline)
        e2e_failed_jobs = self.filter_e2e_jobs(failed_jobs)

        return self.get_e2e_job_statistics(e2e_failed_jobs, is_passed=False)

    def get_statistics(self, pipeline) -> Dict or None:
        stats = dict()

        jobs = self.get_jobs(pipeline)

        e2e_jobs = self.filter_e2e_jobs(jobs)
        stats['jobs'] = self.get_e2e_job_statistics(e2e_jobs)

        # if there is no e2e job in pipeline (like in perf pipelines)
        if not stats['jobs']:
            return None

        e2e_build_jobs = self.filter_e2e_build_job(jobs)
        stats['builds'] = [
            {job.attributes['name']: self.get_job_duration(job)}
            for job in e2e_build_jobs
        ]
        stats['build'] = sum([sum(job.values()) for job in stats['builds']])
        stats['created_at'] = self.get_pipeline_created_time(pipeline)
        stats['ref'] = self.get_pipeline_ref(pipeline)

        # time between pipeline creation and last e2e job
        strptime_pattern = '%Y-%m-%dT%H:%M:%S.%f%z'
        times_finished = list(datetime.strptime(job['finished_at'], strptime_pattern) for job in stats['jobs'])
        last_job_finished = max(times_finished)
        stats['duration'] = int(
            (last_job_finished - datetime.strptime(stats['created_at'], strptime_pattern)).total_seconds())

        # time of e2e execution (total)
        times_started = list(datetime.strptime(job['started_at'], strptime_pattern) for job in stats['jobs'])
        first_job_started = min(times_started)
        stats['duration_e2e'] = int((last_job_finished - first_job_started).total_seconds())

        failed_stats = self.get_statistics_failed(pipeline)
        stats['jobs_failed'] = failed_stats
        stats['has_restarts'] = True if failed_stats else False

        return stats

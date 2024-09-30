from pytimeparse.timeparse import timeparse
from typing import Dict, List
import re


def get_job_stats_by_trace(trace: bytes,
                           steps: List[str]) -> Dict[str, int]:
    """
    From the trace jobs we extract the time, measured using time:
    look for the string "real 3m25.087s" and parse in seconds

    There are 2 possible situations:

    1) there are 2 time calculations in the job:
    - make up time (make up includes docker-compose pull and docker-compose up)
    - time make e2e-run
    -> send {'up': 42, 'e2e': 10}

    2) there are 3 time calculations in the job:
    - make pull time (docker-compose pull)
    - make up time (docker-compose up)
    - time make e2e-run
    -> send {'pull': 25, 'up': 35, 'e2e': 6, 'up_without_pull': 10}
    """
    stats = dict()

    try:
        trace = trace.decode('utf-8')
    except UnicodeDecodeError:
        for step in steps:
            stats[step] = 0

    if steps != ['pull', 'up', 'e2e'] and steps != ['up', 'e2e']:
        raise ValueError(f'Steps are not supported. Allowed only "pull up e2e", "up e2e"')

    matches = re.findall('real\t([0-9]+m[0-9]+.[0-9]+s)\n', trace)

    if len(steps) != len(matches):
        raise AttributeError(
            f'Count of steps in job and timings don\'t match! '
            f'{len(steps)} steps {steps} are given, but found {len(matches)} time-markers.')

    for step, match in zip(steps, matches):
        stats[step] = int(timeparse(match))

    if 'pull' in steps:
        stats['up_without_pull'] = stats['up']
        stats['up'] = stats['up'] + stats['pull']

    return stats

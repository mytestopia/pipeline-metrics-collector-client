# pipeline-metrics-collector-client

Python-based worker collects data from gitlab API about pepine duration and e2e jobs data and send request to 
[pipeline-metrics-collector](https://github.com/mytestopia/pipeline-metrics-collector) API

To separate the time of running tests in a job from the time of setting the environment ("up" from "e2e), 
its trace is parsed by time (commands for running tests and raising are wrapped in time)

Total duration (time) in statistics = time elapsed from the moment the pipeline started until the 
the statistics were collected. That is, if one of the jobs failed and it was not immediately blocked, 
the total time may skyrocket 🚀

## How to use

0. Run [pipeline-metrics-collector](https://github.com/mytestopia/pipeline-metrics-collector) server
1. Build image for client-worker
   ```shell
     docker image build -t metrics-collector-client .; 
    ```
2. Run worker

    For specified pipeline use parameter `--pipeline-id`, for multipal pipelines use `--per-page` and `--page` parameters
    ```shell
     docker run metrics-collector-client \
     --save-endpoint http://web:5000/save_metrics \
     --private-token <PRIVATE-TOKEN> \
     --project-id 123 \
     --project-name test/project \
     --stage-build build --jobs-build build-e2e \
     --stage-e2e test \
     --jobs-e2e-blacklist test:e2e:lint coverage lint \
     --pipeline-id 1  # for specified pipeline
     # --per-page 10 --page 1
    ```
   For local debug (server and client running on same machine) use `--network host` parameter for run
   ```shell
     docker run --network pipeline-metrics-collector_default metrics-collector-client ...
    ```

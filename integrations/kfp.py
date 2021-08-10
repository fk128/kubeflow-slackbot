import os
import kfp
from eks_token import get_token


class kfpClient(kfp.Client):

    def _load_config(self, *args, **kwargs):
        config = super()._load_config(*args, **kwargs)
        config.api_key['authorization'] = get_token(cluster_name=os.environ['CLUSTER_NAME'])['status']['token']
        config.api_key_prefix['authorization'] = 'Bearer'
        print(config.__dict__)
        return config


def submit_to_kfp(
        arg_dict=None,
        pipeline_name: str = None,
        run_name: str = None,
        experiment_name: str = 'Default'
):
    """submit a KFP run"""

    client = kfpClient()

    pipeline_id = client.get_pipeline_id(name=pipeline_name)

    version = client.get_pipeline(pipeline_id).default_version.id

    if run_name is None:
        run_name = f'Run of {pipeline_name}/{version}'
    package_file = None

    experiment = client.create_experiment(experiment_name)
    run = client.run_pipeline(experiment.id, run_name, package_file, arg_dict, pipeline_id=None,
                              version_id=version)
    return run.id

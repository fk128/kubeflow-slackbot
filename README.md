# Kubeflow Slackbot on AWS lambda


Template for creating modals to trigger kubeflow pipelines. To create a modal you simply need to define the blocks in yaml `modals/my_modal.yaml`; see `modals/` for examples. You'd also have to create the corresponding slash command in your slack bot settings.

An example of a modal that attaches to a `/kfp-predict` slash command and triggers a kubeflow pipeline called `predict`.

```yaml
# models/predict-modal.yaml
name: predict
title: Predict
slash_command: /kfp-predict
validate_args_func: validate_predict_args
kfp:
  pipeline_name: predict
  experiment_name: Evaluation
blocks:
  - name: model_version
    type: str
  - name: dataset-id
    display_name: Dataset ID
    type: int
```

You can optionally write a validation function in `validation.py` for checking the input arguments for errors and refer to the name of the function in `validate_args_func:`.


Install [serverless](https://www.serverless.com/) and edit `serverless.yaml`. The main things you need to edit are:

```yaml
    SLACK_BOT_TOKEN: ${file(config.${opt:stage, 'dev'}.json):SLACK_BOT_TOKEN}
    SLACK_SIGNING_SECRET: ${file(config.${opt:stage, 'dev'}.json):SLACK_SIGNING_SECRET}
    KUBECONFIG: /tmp/kubeconfig
    CLUSTER_NAME: my-k8s-cluster
    REGION: eu-west-2
    BASE_URL: "https://kfp.mydomain.com/"
```

see [serverless variables](https://www.serverless.com/framework/docs/providers/aws/guide/variables/) for more information about defining environment variables.

```bash
# apply roles to cluster
kubectl apply -f roles.yaml

# install plugin
serverless plugin install -n serverless-python-requirements

# deploy
serverless deploy
```

Copy the url generated and use it as a webhook for your slash command.

## Serverless Usage

### Deployment

In order to deploy the example, you need to run the following command:

```
$ serverless deploy
```

After running deploy, you should see output similar to:

```bash
Serverless: Packaging service...
Serverless: Excluding development dependencies...
Serverless: Creating Stack...
Serverless: Checking Stack create progress...
........
Serverless: Stack create finished...
Serverless: Uploading CloudFormation file to S3...
Serverless: Uploading artifacts...
Serverless: Uploading service aws-python.zip file to S3 (711.23 KB)...
Serverless: Validating template...
Serverless: Updating Stack...
Serverless: Checking Stack update progress...
.................................
Serverless: Stack update finished...
Service Information
service: aws-python
stage: dev
region: us-east-1
stack: aws-python-dev
resources: 6
functions:
  api: aws-python-dev-hello
layers:
  None
```

### Invocation

After successful deployment, you can invoke the deployed function by using the following command:

```bash
serverless invoke --function hello
```

Which should result in response similar to the following:

```json
{
    "statusCode": 200,
    "body": "{\"message\": \"Go Serverless v2.0! Your function executed successfully!\", \"input\": {}}"
}
```

### Local development

You can invoke your function locally by using the following command:

```bash
serverless invoke local --function hello
```

Which should result in response similar to the following:

```
{
    "statusCode": 200,
    "body": "{\"message\": \"Go Serverless v2.0! Your function executed successfully!\", \"input\": {}}"
}
```

### Bundling dependencies

In case you would like to include third-party dependencies, you will need to use a plugin called `serverless-python-requirements`. You can set it up by running the following command:

```bash
serverless plugin install -n serverless-python-requirements
```

Running the above will automatically add `serverless-python-requirements` to `plugins` section in your `serverless.yml` file and add it as a `devDependency` to `package.json` file. The `package.json` file will be automatically created if it doesn't exist beforehand. Now you will be able to add your dependencies to `requirements.txt` file (`Pipfile` and `pyproject.toml` is also supported but requires additional configuration) and they will be automatically injected to Lambda package during build process. For more details about the plugin's configuration, please refer to [official documentation](https://github.com/UnitedIncome/serverless-python-requirements).


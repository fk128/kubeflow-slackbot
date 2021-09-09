import logging
import os
from pathlib import Path

import boto3
import yaml
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

import validation


def submit_job(experiment_name, pipeline_name, run_name, arg_dict, client, channel, values, user=None):
    try:
        create_kubeconfig()
        from integrations import kfp
        base_url = os.environ['BASE_URL']
        run_id = kfp.submit_to_kfp(experiment_name=experiment_name,
                                   run_name=run_name,
                                   arg_dict=arg_dict,
                                   pipeline_name=pipeline_name)

        url = os.path.join(base_url, f'#/runs/details/{run_id}')
        msg = f"Your submission was successful"
        submission_info = {'Run id': f'<{url}|{run_id}>',
                           'Run name': run_name,
                           'Experiment': experiment_name,
                           'Pipeline name': pipeline_name}
        if user is not None:
            submission_info['Submitter'] = user['name']
        client.chat_postMessage(channel=channel,
                                text='',
                                blocks=[
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": msg
                                        },
                                        "accessory": {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "View pipeline",
                                                "emoji": True
                                            },
                                            "value": "click_me",
                                            "url": url,
                                            "action_id": "button-action"
                                        }
                                    },
                                    build_text_fields(submission_info),
                                    {
                                        "type": "divider"
                                    },
                                    build_text_fields(values)
                                ])
    except Exception as e:
        # Handle error
        msg = "There was an error with your submission" + str(e)
        client.chat_postMessage(channel=channel,
                                text=msg)


def build_static_select(item):
    name = str(item['name'])
    display_name = str(item['display_name']) if 'display_name' in item else name
    options = [
        {
            "text": {
                "type": "plain_text",
                "text": str(choice),
                "emoji": True
            },
            "value": str(choice)
        }
        for choice in item['choices']
    ]

    element = {
        "type": "input",
        "block_id": name,
        "element": {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": "Select an item",
                "emoji": True
            },
            "options": options,
            "action_id": f"{name}-action"
        },
        "label": {
            "type": "plain_text",
            "text": display_name.capitalize().replace('_', ' '),
            "emoji": True
        }
    }

    return element


def build_text_input(item):
    name = str(item['name'])
    display_name = str(item['display_name']) if 'display_name' in item else name
    element = {
        "type": "input",
        "block_id": name,
        "element": {
            "type": "plain_text_input",
            "action_id": f"{name}-action"
        },
        "label": {
            "type": "plain_text",
            "text": display_name.capitalize().replace('_', ' '),
            "emoji": True
        }
    }
    if 'hint' in item:
        element['element']['placeholder'] = {
            "type": "plain_text",
            "text": str(item['hint']),
            "emoji": True
        }
    if 'value' in item:
        element['element']['initial_value'] = str(item['value'])
    if 'optional' in item:
        element['optional'] = item['optional']
    return element


def load_yaml(path):
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return data


def parse_submission(view, path):
    data = load_yaml(path)

    values = {}
    if isinstance(data['kfp']['pipeline_name'], list):
        name = 'kfp_pipeline_name'
        values[name] = {'value': view["state"]["values"][name][f"{name}-action"]['selected_option']['value']}
    for item in data['blocks']:
        name = item['name']
        if 'choices' in item and item['choices'] is not None:
            item['value'] = view["state"]["values"][name][f"{name}-action"]['selected_option']['value']
        else:
            item['value'] = view["state"]["values"][name][f"{name}-action"]['value']
        values[name] = item
    return values


def build_modal_view_from_yaml(path):
    data = load_yaml(path)
    blocks = []
    if isinstance(data['kfp']['pipeline_name'], list):
        item = {'name': 'kfp_pipeline_name', 'choices': data['kfp']['pipeline_name']}
        block = build_static_select(item)
        blocks.append(block)

    for item in data['blocks']:
        if 'choices' in item and item['choices'] is not None:
            block = build_static_select(item)
        else:
            block = build_text_input(item)
        blocks.append(block)

    return {"type": "modal",
            "callback_id": f"{data['name']}_callback",
            "title": {
                "type": "plain_text",
                "text": data['title'],
                "emoji": True
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit",
                "emoji": True
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel",
                "emoji": True
            },
            "blocks": blocks
            }


def build_text_fields(items):
    fields = [{
        "type": "mrkdwn",
        "text": f"*{k}*: {v['value'] if isinstance(v, dict) else v}"
    } for k, v in items.items()]
    return {
        "type": "section",
        "fields": fields
    }


def create_kubeconfig():
    if not os.path.exists(os.environ['KUBECONFIG']):
        eks_api = boto3.client('eks', region_name=os.environ['REGION'])
        cluster_info = eks_api.describe_cluster(name=os.environ['CLUSTER_NAME'])
        certificate = cluster_info['cluster']['certificateAuthority']['data']
        endpoint = cluster_info['cluster']['endpoint']

        kube_content = dict()

        kube_content['apiVersion'] = 'v1'
        kube_content['clusters'] = [
            {
                'cluster':
                    {
                        'server': endpoint,
                        'certificate-authority-data': certificate
                    },
                'name': 'kubernetes'

            }]

        kube_content['contexts'] = [
            {
                'context':
                    {
                        'cluster': 'kubernetes',
                        'user': 'aws'
                    },
                'name': 'aws'
            }]

        kube_content['current-context'] = 'aws'
        kube_content['Kind'] = 'config'
        kube_content['users'] = [
            {
                'name': 'aws',
                'user': {'name': 'lambda'}
            }
        ]

        with open(os.environ['KUBECONFIG'], 'w') as outfile:
            yaml.dump(kube_content, outfile, default_flow_style=False)


app = App(process_before_response=True)


def update_view(client, body, text=None):
    text = text or "Sometimes this takes more than 3 seconds, so you might get a timeout error because of a limitation " \
                   "in slack. You should however receive a message from the slackbot within 20 seconds. " \
                   "If you do not, then something has gone wrong."
    client.views_update(
        # Pass the view_id
        view_id=body["view"]["id"],
        hash=body["view"]["hash"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "view_1",
            "title": {"type": "plain_text", "text": "Working on it"},
            "blocks": [{
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": text,
                    "emoji": True
                }
            }]}
    )


@app.event("app_mention")
def handle_app_mentions(body, say, logger):
    logger.info(body)
    say("What's up?")


def build_functions(modal_path, kfp_data, validate_args_func=None, channel=None):
    def open_modal(ack, body, client):
        # Acknowledge the command request
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=build_modal_view_from_yaml(modal_path)
        )

    def handle_submission(ack, body, client, view, logger):
        ack()
        update_view(client, body, text=None)
        pipeline_name = kfp_data['pipeline_name']
        experiment_name = kfp_data.get('experiment_name', 'Default')

        values = parse_submission(view, modal_path)

        if isinstance(pipeline_name, list):
            pipeline_name = values.pop('kfp_pipeline_name')['value']

        if validate_args_func:
            arg_dict, errors = validate_args_func(values)
        else:
            arg_dict = {}
            errors = {}
            for k, v in values.items():
                arg_dict[k] = v['value']

        if len(errors) > 0:
            ack(response_action="errors", errors=errors)
            return

        nonlocal channel
        if channel is None:
            channel = body["user"]["id"]

        submit_job(experiment_name=experiment_name, pipeline_name=pipeline_name,
                   run_name=None, arg_dict=arg_dict,
                   client=client, channel=channel, values=values, user=body["user"])

    return open_modal, handle_submission


# build commands and callbacks
for modal_path in Path('modals').glob('*.yaml'):
    data = load_yaml(modal_path)
    if data.get('manual', False):
        continue
    channel = data.get('channel', None)
    validate_args_func = getattr(validation, data["validate_args_func"]) if 'validate_args_func' in data else None
    open_modal_func, handle_sub_func = build_functions(modal_path, data['kfp'], validate_args_func=validate_args_func,
                                                       channel=channel)
    app.command(data['slash_command'])(open_modal_func)
    app.view(f"{data['name']}_callback")(handle_sub_func)

SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


def handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)

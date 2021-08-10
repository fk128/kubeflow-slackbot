def validate_train_args(values):
    errors = {}

    values['dataset-id']['value'] = int(values['dataset-id']['value'])

    if values['dataset-id']['value'] not in {1, 2, 3}:
        errors['dataset-id'] = "The value must be 1,2, or 3"

    arg_dict = {}
    for k, v in values.items():
        arg_dict[k] = v['value']
    return arg_dict, errors


def validate_predict_args(values):
    arg_dict = {}
    errors = {}
    return arg_dict, errors

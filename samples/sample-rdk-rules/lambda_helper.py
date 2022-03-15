import argparse
import json
import os
import shutil
import uuid
import sys
import logging
import boto3
from s3 import S3
from pathlib import Path


deployment_account_region = os.environ.get("AWS_REGION")
project_root = os.path.dirname(__file__)
s3_rdk_assets_prefix = "rdk_assets"
config_rules_dir = "config-rules"
templates_dir = "templates"
config_rules_root = os.path.join(project_root, "config-rules")
templates_root = os.path.join(project_root, templates_dir)

def load_json_file(file: str) -> dict:
    try:
        with open(f"{file}") as file:
            return json.load(file)
    except FileNotFoundError:
        logging.exception(f"File {file} not found.")
        sys.exit(1)
        
def replace_rule_name_and_load(file: str, rule_name:str, rule_name_stripped:str) -> dict:
    try:
        with open(file, 'r') as f:
            content = f.read().replace("RuleNameStripped", rule_name_stripped)
            content = content.replace("RuleName", rule_name)
            return json.loads(content)
    except FileNotFoundError:
        logging.exception(f"File {file} not found.")
        sys.exit(1)

def clean_up_template(file: str):
    if os.path.exists(file):
        os.remove(file)
   

def get_tempalte_skeleton(shared_modules_bucket: str) -> dict:
    #get skeleton
    parameters = load_json_file(Path(templates_root).joinpath("parameters.json"))
    parameters["SourceBucketFolder"]["Default"] = s3_rdk_assets_prefix
    parameters["SourceBucket"]["Default"] = shared_modules_bucket
    
    #get parameters
    skeleton = load_json_file(Path(templates_root).joinpath("skeleton.json"))
    
    skeleton["Parameters"] = parameters
    
    return skeleton

def add_lambda_to_template_by_rule(template:dict, config_rule_dir: str, rule_name:str, s3_asset_key:str) -> dict:
    parameter_file = Path(config_rule_dir).joinpath("parameters.json")
    parameter_content = load_json_file(parameter_file)
    rule_name_stripped = rule_name.replace("_", "")
    runtime = parameter_content.get('Parameters').get('SourceRuntime')
    
    #get lambda-role
    #RuleNameLambdaRole
    lambda_role = replace_rule_name_and_load(Path(templates_root).joinpath("lambda-role.json"), rule_name, rule_name_stripped)
    template["Resources"][f"{rule_name_stripped}LambdaRole"] = lambda_role
    
    #get lambda-function
    #"RuleNameLambdaFunction": 
    lambda_function = replace_rule_name_and_load(Path(templates_root).joinpath("lambda-function.json"), rule_name, rule_name_stripped)
    lambda_function["Properties"]["Code"]["S3Key"] = s3_asset_key
    lambda_function["Properties"]["Runtime"] = runtime
    template["Resources"][f"{rule_name_stripped}LambdaFunction"] = lambda_function
    
    #get lambda-permission
    lambda_permission = replace_rule_name_and_load(Path(templates_root).joinpath("lambda-permission.json"), rule_name, rule_name_stripped)
    template["Resources"][f"{rule_name_stripped}LambdaPermissions"] = lambda_permission
    
    return template
    
def write_template(template:dict, file_name:str):
    with open(file_name, "a") as file:
        json.dump(template, file, indent=4)


def main(shared_modules_bucket: str):
    s3 = S3(deployment_account_region, shared_modules_bucket)
    clean_up_template(template_name)
    template = get_tempalte_skeleton(shared_modules_bucket)
    
    config_rules_dirs = [x for x in  Path(config_rules_root).iterdir() if x.is_dir()]
    for config_rule_dir in config_rules_dirs:
        rule_name = config_rule_dir.name.replace("-", "_")
    
        logging.info(f'Zipping rule {config_rule_dir.name}')
    
        file_asset_path = shutil.make_archive(
            Path(config_rule_dir).joinpath(config_rule_dir.name),
            "zip",
            config_rule_dir
        )
        unique_id = uuid.uuid4()
        if asset_folder:
            s3_asset_key =f'{asset_folder}/{rule_name}/{rule_name}-{unique_id}.zip'
    
        logging.info(f'Uploading rule {config_rule_dir.name}')
        uploaded_asset_path = s3.put_object(
            s3_asset_key,
            file_asset_path,
            style="s3-url",
            pre_check=True,
        )
        print(f"uploaded to {uploaded_asset_path}")
        clean_up_template(file_asset_path)
        print(f"Creating tempalte for {rule_name}")
        template = add_lambda_to_template_by_rule(template, config_rule_dir, rule_name, s3_asset_key)
    
    write_template(template, template_name)
       
  

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset-folder', required=False, help='[optional] Asset folder in the ADF bucket')
    parser.add_argument('--template-name', required=True, help='Name for the generated template name')
    parser.add_argument(
        "-r",
        "--region",
    )
    args = parser.parse_args()
   
    target_region = args.region if args.region else deployment_account_region
    parameter_store = boto3.client('ssm')
    
    template_name = args.template_name 
    
    bucket_path_ssm =  f"/cross_region/s3_regional_bucket/{target_region}"
    res = parameter_store.get_parameter(Name=bucket_path_ssm)

    shared_modules_bucket = res['Parameter']['Value']
    asset_folder = args.asset_folder if args.asset_folder else s3_rdk_assets_prefix
    # If remove trailing slash if exists to be 
    if asset_folder and asset_folder.endswith('/'):
        asset_folder = asset_folder[:-1]

    main(shared_modules_bucket)

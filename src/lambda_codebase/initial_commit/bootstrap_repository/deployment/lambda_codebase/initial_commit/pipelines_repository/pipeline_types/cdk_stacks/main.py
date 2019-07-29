from aws_cdk import core
from cdk_constructs import adf_codepipeline

class PipelineMainStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        pipeline = adf_codepipeline.Pipeline(self, id, params)

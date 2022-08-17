"""
Standardised class for pushing CloudWatch metric data to a service within the ADF Namespace
"""

import boto3


class ADFMetrics:
    def __init__(self, client: boto3.client, service, namespace="ADF") -> None:
        """
        Client: Any Boto3 Cloudwatch client
        Service: The name of the Service e.g PipelineManagement/Repository or AccountManagement/EnableSupport
        namespace: Defaults to ADF
        """
        self.cw = client
        self.namespace = f"{namespace}/{service}"

    def put_metric_data(self, metric_data):
        if not isinstance(metric_data, list):
            metric_data = [metric_data]
        self.cw.put_metric_data(Namespace=self.namespace, MetricData=metric_data)

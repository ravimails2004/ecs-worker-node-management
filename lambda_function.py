from metric_reader import GetMetricTerminateEc2
import boto3

def lambda_handler(event, context):
    print("Start Execution")
    GetMetricTerminateEc2().get_metric()

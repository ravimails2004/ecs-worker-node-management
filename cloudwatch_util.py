import boto3
import json
import logging
from utils import get_aws_region
from botocore.exceptions import ClientError

logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class CloudWatchUtil:
    def __init__(self):
        self.cw = boto3.client(service_name="cloudwatch", region_name=get_aws_region())

    def put_metric_data(self, ns, metric_data):
        try:
            logger.debug("Entered put_metric_data")
            print(metric_data)
            resp = self.cw.put_metric_data(Namespace=ns, MetricData=metric_data)
            logger.info("Response of put_metric_data: {}".format(json.dumps(resp)))

        except KeyError as e:
            logger.error("Recieved KeyError:".format(e), exc_info=True)
            logger.error("Dict looks like the following: {}".format(json.dumps(resp)))
            raise e

    def list_metrics(self, Namespace, MetricName, Dimensions):
        try:
            return self.cw.list_metrics(Namespace=Namespace, MetricName=MetricName, Dimensions=Dimensions)
        except ClientError as e:
            logger.error("client connection is failing {}".format(e))
            return None

    def get_metric_statistics(self, Namespace, MetricName, Dimensions, Period, StartTime, EndTime, Statistics):
        try:
            return self.cw.get_metric_statistics(Namespace=Namespace, MetricName=MetricName, Dimensions=Dimensions, Period=Period, StartTime=StartTime, EndTime=EndTime, Statistics=Statistics)
        except ClientError as e:
            logger.error("client connection is failing: {}".format(e))
            return None

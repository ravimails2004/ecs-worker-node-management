import boto3
import json
import logging
from utils import get_aws_region

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class EcsUtil():
    def __init__(self):
        self.service = 'ecs'
        self.client = boto3.client(service_name=self.service, region_name=get_aws_region())
        self.service2 = 'ec2'
        self.client2 = boto3.client(service_name=self.service2, region_name=get_aws_region())
        

    def describe_container_instances(self, cluster, container_instances):
        results = []
        try:
            for i in range(0, len(container_instances), 100):
                response = self.client.describe_container_instances(cluster=cluster,
                                                                    containerInstances=container_instances[i:i + 100])
                results.extend(response["containerInstances"])
            return results
        except KeyError as e:
            logger.error("Recieved KeyError: {}".format(e), exc_info=True)
            logger.error("Dict looks like the following:{}".format(json.dumps(response)))
            raise e

    def list_ecs_cluster_arns(self):
        return self.__get_complete_list(self.client.list_clusters, 'clusterArns')

    def list_container_instance_arns(self, cluster):
        return self.__get_complete_list(self.client.list_container_instances, 'containerInstanceArns', cluster=cluster)
        
    def update_container_instances_state(self, cluster, containerInstances, status):
        return self.client.update_container_instances_state(cluster=cluster, containerInstances=containerInstances, status=status)
    
    def deregister_container_instance(self, cluster, containerInstance, force=True):
        logger.info("====deregister_container_instance====")
        logger.info(cluster, containerInstance)
        logger.info("=================")
        return self.client.deregister_container_instance(cluster=cluster, containerInstance=containerInstance, force=force)
        
    def terminate_instances(self, InstanceIds, DryRun=False):
        return self.client2.terminate_instances(InstanceIds=InstanceIds, DryRun=DryRun)
        
    
    def __get_complete_list(self, function, key, **kwargs):
        try:
            results = []
            next_token = ""
            response = function(nextToken=next_token, **kwargs)
            results.extend(response[key])
            if "nextToken" not in response:
                next_token = ""
            else:
                next_token = response["nextToken"]

            while next_token != "":
                response = function(next_token=next_token, **kwargs)
                results.extend(response[key])
                if "nextToken" not in response:
                    next_token = ""
                else:
                    next_token = response["nextToken"]
            return results
        except KeyError as e:
            logger.error("Received KeyError: {}".format(e), exc_info=True)
            logger.error("Dict looks like the following: {}".format(json.dumps(response)))
            raise e

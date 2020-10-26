import boto3
import json
import datetime
from botocore.exceptions import ClientError
from cloudwatch_util import CloudWatchUtil
from ecs_util import EcsUtil
from ecs_lambda_config import get_cw_ns
import logging
import time
from datetime import datetime, timedelta

logger=logging.getLogger()
logger.setLevel(logging.INFO)


class GetMetricTerminateEc2:
    def __init__(self):
        self.ecs_util = EcsUtil()
        self.cw_util = CloudWatchUtil()
        self.ns = get_cw_ns()

    def get_metric(self):
        try:
            NOW=datetime.now()
            response=self.cw_util.list_metrics(Namespace=self.ns, MetricName='AgentConnected', Dimensions=[])
            logger.info("List Metrics Response: %s" % response)
            self.validate_data_point(response)
        except ClientError as e:
            logger.error("Received error: %s", e, exc_info=True)
            raise e
            
    def validate_data_point(self, response):
        for i in response['Metrics']:
            NOW=datetime.now()
            try:
                response2=self.cw_util.get_metric_statistics(
                    Namespace=self.ns,
                    MetricName='AgentConnected',
                    Dimensions=i['Dimensions'],
                    Period=300,
                    StartTime=NOW - timedelta(minutes=5),
                    EndTime=NOW,
                    Statistics=['Average'])
                if not response2['Datapoints']:
                    tid=i['Dimensions'][0]['Value']
                    logger.info("Looks like this is an instance which is already terminated: %s" % tid)
                elif response2['Datapoints'][0]['Average'] == 0.0:
                    instance_id=i['Dimensions'][0]['Value']
                    containerInstanceArn=i['Dimensions'][1]['Value']
                    cluster_name=i['Dimensions'][2]['Value']
                    cluster_name=cluster_name.split("/")
                    cluster_name=cluster_name[1]
                    message=[instance_id, containerInstanceArn, cluster_name]
                    logger.info("proceeding with draining, deregistration and instance termination: {}".format(' '.join(map(str, message))))
                    self.drain_and_terminate_instances(instance_id, cluster_name, containerInstanceArn)
                else:
                    instance_id=i['Dimensions'][0]['Value']
                    containerInstanceArn=i['Dimensions'][1]['Value']
                    cluster_name=i['Dimensions'][2]['Value']
                    cluster_name=cluster_name.split("/")
                    cluster_name=cluster_name[1]
                    message=[instance_id, cluster_name, containerInstanceArn]
                    logger.info("Draining not required for: {}".format(' '.join(map(str, message))))
            except ClientError as e:
                logger.error("Received error: %s", e, exc_info=True)
                raise e
                
    def get_instance_attribute(self, instance_id):
        try:
            client2 = boto3.resource('ec2')
            ec2instance = client2.Instance(instance_id)
            for tags in ec2instance.tags:
                if tags["Key"] == 'aws:autoscaling:groupName':
                   asg_name = tags["Value"]
                   logger.info("AutoScaling Group Name: %s" % asg_name)
                   return asg_name
        except ClientError as e:
            logger.error("Received error: %s", e, exc_info=True)
            raise e        
    
    def modify_autoscaling_sg(self, asg_name, action):
        try:
           client = boto3.client('autoscaling')
           #response = asg_name['LaunchConfigurationName']
           asgs = client.describe_auto_scaling_groups()['AutoScalingGroups']
           for asg in asgs:
               if asg['AutoScalingGroupName'] == asg_name:
                   LCNAME=asg['LaunchConfigurationName']
                   logger.info("Launch Configuration Name: %s" % LCNAME)
                   data=client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
                   logger.info("AutoScaling Group Data: %s" % data)
                   while 'NextToken' in data:
                       data = client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name], NextToken=data['NextToken'])
                       logger.info("AutoScaling Group Data: %s" % data)
                   Cluster_Minsize=data['AutoScalingGroups'][0]['MinSize']
                   Cluster_Maxsize=data['AutoScalingGroups'][0]['MaxSize']
                   Cluster_DesiredCapacity=data['AutoScalingGroups'][0]['DesiredCapacity']
                   message=[Cluster_Minsize, Cluster_Maxsize, Cluster_DesiredCapacity]
                   logger.info("Cluster_Minsize, Cluster_Maxsize, Cluster_DesiredCapacity: {}".format(' '.join(map(str, message))))
                   if action == "up":
                       logger.info("updating the autoscaling setting Min Max and Desired by +1")
                       response = client.update_auto_scaling_group(AutoScalingGroupName=asg_name, LaunchConfigurationName=LCNAME, MinSize=Cluster_Minsize + 1, MaxSize=Cluster_Maxsize + 1, DesiredCapacity=Cluster_DesiredCapacity + 1)
                   elif action == "down":
                       logger.info("Resetting the autoscaling setting Min Max and Desired by -1")
                       response = client.update_auto_scaling_group(AutoScalingGroupName=asg_name, LaunchConfigurationName=LCNAME, MinSize=Cluster_Minsize - 1, MaxSize=Cluster_Maxsize - 1, DesiredCapacity=Cluster_DesiredCapacity - 1)
        except ClientError as e:
            logger.error("Received error: %s", e, exc_info=True)
            raise e 
    
    def drain_and_terminate_instances(self, instance_id, cluster_name, containerInstanceArn):
        asg_name=self.get_instance_attribute(instance_id)
        self.modify_autoscaling_sg(asg_name, action='up')
        containerInstances = []
        containerInstances.append(containerInstanceArn)
        drain=self.ecs_util.update_container_instances_state(cluster=cluster_name, containerInstances=containerInstances, status='DRAINING')
        if drain['containerInstances'][0]['status'] == 'DRAINING':
            logger.info("Successfully set container instance status to DRAINING, Proceeding with instance termination in one minute")
            time.sleep(20)
            try:
                print("============drain=============")
                print(instance_id, cluster_name, containerInstanceArn)
                print("=========================")
                self.ecs_util.deregister_container_instance(cluster=cluster_name, containerInstance=containerInstanceArn, force=True)
                logger.info("Instance deregistration completed successfully")
            except Exception as e:
                logger.error('Error at %s', e,   exc_info=True )
            try:
                time.sleep(20)
                self.ecs_util.terminate_instances(InstanceIds=[instance_id, ], DryRun=False)
                logger.info("Instance termination completed successfully")
                self.modify_autoscaling_sg(asg_name, action='down')
            except Exception as e:
                logger.error('Error at %s', e, exc_info=True)
        else:
            logger.error("Something went wrong.")

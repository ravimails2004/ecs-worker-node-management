import os
import sys
from datetime import datetime as dt, timezone


def get_aws_region():
	runtime_region = os.environ['AWS_REGION']
	return runtime_region


def get_aws_region2():
	return "us-east-1"

def get_epoch_as_datetime():
	now =  dt.now()
	return now.replace(tzinfo=timezone.utc).timestamp()

def get_epoch_in_ms_as_int():
	return int(get_epoch_as_datetime() * 1000)

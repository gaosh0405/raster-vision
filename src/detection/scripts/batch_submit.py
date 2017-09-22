#!/usr/bin/env python

from os import environ

import click
import boto3

s3_bucket = environ.get('S3_BUCKET')


@click.command()
@click.argument('branch_name', help='Branch with code to run on Batch')
@click.argument('command', help='Command in quotes to run on Batch')
@click.option('--attempts', default=3, help='Number of times to retry job')
@click.option('--cpu', is_flag=True, help='Use CPU EC2 instances')
def batch_submit(branch_name, command_args, attempts=3, cpu=False):
    """
        Submit a git branch and command to run on the GPU Docker container
        using AWS Batch.
    """
    command = ['run_script.sh', branch_name]
    command.extend(command_args)

    client = boto3.client('batch')
    job_queue = 'raster-vision-cpu' if cpu else \
        'raster-vision-gpu'
    job_definition = 'raster-vision-cpu' if cpu else \
        'raster-vision-gpu'

    job_name = '-'.join(command_args) \
                  .replace('/', '-').replace('.', '-')
    job_name = 'batch_submit'

    job_id = client.submit_job(
        jobName=job_name,
        jobQueue=job_queue,
        jobDefinition=job_definition,
        containerOverrides={
            'command': command
        },
        retryStrategy={
            'attempts': attempts
        })['jobId']

    click.echo(
        'Submitted job with jobName={} and jobId={}'.format(job_name, job_id))


if __name__ == '__main__':
    batch_submit()

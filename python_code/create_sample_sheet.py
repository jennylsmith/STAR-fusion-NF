#!/usr/bin/env python3

#Jenny Smith
#Sept 23, 2020 
#Purpose: create a sample sheet of files hosted on AWS S3. 


#import modules 
import argparse
import os
import re
import itertools
import boto3
import logging
from botocore.exceptions import ClientError
import numpy as np
import pandas as pd


def create_sample_sheet(bucket_name,prefix_name,filetype="fastq",samples=None,filename="sample_sheet.txt", write=True):

    """
    A function to query an S3 bucket, list its objects, and filter the files by sample IDs. 
    The bucket_name is a string. Example: "fh-pi-my-bucket"
    The prefix_name is a string. Need trailing slash. Example: "SR/myfiles/"
    """

    #function to parse the object summary from Boto3 for fastqs
    def sample_name(s3_object_summary):
        sample = s3_object_summary.key.split("/")[2]
        sample = re.sub(r"[._][Rr][12].+$","", sample)
        return(sample)
    
    #Connection to S3 Bucket 
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    delim = "/"    

    #query S3 bucket to list the fastq files 
    fqs = bucket.objects.filter(Delimiter=delim,
                                Prefix=prefix_name)

    #iterate over the fastqs 
    fqs_PE = dict()
    for obj in fqs:
        samp = sample_name(obj)
#         print(samp)
        if re.search(r"[._-][Rr][12].(fastq|fq)", obj.key):
            read = '{0}//{1}/{2}'.format("s3:", obj.bucket_name, obj.key)

            #print(samp + ":" + read)
            if samp not in fqs_PE.keys():
                fqs_PE[samp] = [read]
            else:
                fqs_PE[samp] = fqs_PE[samp] + [read]
                #final sort to ensure order
                fqs_PE[samp].sort()


    print("There are " + str(len(fqs_PE)) + " Fastq files.")

    #Create a pandas dataframe 
    #split the samples for filtering by space or comma
    #if no sample IDs are provided, the regex will include all files in the S3 bucket/prefix. 
    if samples is None:
        samples = ""

    regex = re.compile('|'.join(re.split(',| ',samples)))
    filtered = [{"Sample":sample,"R1":fastqs[0],"R2":fastqs[1]} for sample, fastqs in fqs_PE.items() if re.search(regex, sample)]
    sample_sheet = pd.DataFrame(filtered) 
    
    
    #Save the dataframe to file or return the dataframe
    if write: 
        sample_sheet.to_csv(path_or_buf=filename,
                    sep="\t", header=True,
                    index=False,quoting=None)
    
        print("Finished writing " + str(len(sample_sheet.index)) + " records to file: " + filename)
    else: 
        return(sample_sheet)
    
    

#Taken directly form https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html 
def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response
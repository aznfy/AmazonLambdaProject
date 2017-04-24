from flask import Flask, request, render_template, redirect, url_for, flash, g, send_file
import boto3
import os
from app import webapp
import urllib2
import urllib
import StringIO
from io import BytesIO
from io import FileIO
import zipfile
from boto3.dynamodb.conditions import Key
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

@webapp.route('/thumbnails/list/<username>', methods=['GET'])
def thumb_list(username):
    s3 = boto3.client('s3')
    table = dynamodb.Table('Images')
    response = table.query(
        KeyConditionExpression=Key('username').eq(username)
    )
    print(response)
    urls = []
    for i in response['Items']:
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': 'ece1779project',
                'Key': i['imagename']
            }
        )
        urls.append(url)
        #print (urls)
    return render_template('/thumbnails/list.html', urls=urls, username=username)

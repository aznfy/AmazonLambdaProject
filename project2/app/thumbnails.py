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

@webapp.route('/download/<username>',methods=['GET'])
def download(username):
    s3 = boto3.client('s3')
    table = dynamodb.Table('Images')
    response = table.query(
        KeyConditionExpression=Key('username').eq(username)
    )
    print(response)
    urls = []
    # memory_file = FileIO()
    # zf = zipfile.ZipFile(memory_file, mode='a')
    for i in response['Items']:
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': 'ece1779project',
                'Key': i['imagename']
            }
        )
        req = urllib2.Request(url)
        img = StringIO.StringIO(urllib2.urlopen(req).read())
        # zf.write(img, arcname=i['imagename'])
    # memory_file.seek(0)
    return send_file(img, attachment_filename='test.jpg', as_attachment=True)
    return redirect(url_for('thumb_list', username=username))

    # memory_file = BytesIO()
    # with zipfile.ZipFile(memory_file, 'w') as zf:
    #     files = result['files']
    #     for individualFile in files:
    #         data = zipfile.ZipInfo(individualFile['fileName'])
    #         data.date_time = time.localtime(time.time())[:6]
    #         data.compress_type = zipfile.ZIP_DEFLATED
    #         zf.writestr(data, individualFile['fileData'])
    # memory_file.seek(0)
    # return send_file(memory_file, attachment_filename='capsule.zip', as_attachment=True)

#
# print 'creating archive'
# zf = zipfile.ZipFile('zipfile_append.zip', mode='w')
# try:
#     zf.write('README.txt')
# finally:
#     zf.close()
#
# print
# print_info('zipfile_append.zip')
#
# print 'appending to the archive'
# zf = zipfile.ZipFile('zipfile_append.zip', mode='a')
# try:
#     zf.write('README.txt', arcname='README2.txt')
# finally:
#     zf.close()
#
# print
# print_info('zipfile_append.zip')
from flask import Flask, request, render_template, redirect, url_for, flash, g, session

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, EqualTo
from instaLooter import InstaLooter
from six.moves.urllib.parse import urlparse
import icrawler
from icrawler.builtin import GoogleImageCrawler
from icrawler.builtin import GreedyImageCrawler
from boto3.dynamodb.conditions import Key

import tempfile
import os
import boto3
from urllib2 import urlopen
import io

from app import webapp


dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

file_names = []

'''

We Override the function in icrawler

'''

def new_get_filename(self, task, default_ext):
    """Set the path where the image will be saved.

    The default strategy is to use an increasing 6-digit number as
    the filename. You can override this method if you want to set custom
    naming rules. The file extension is kept if it can be obtained from
    the url, otherwise ``default_ext`` is used as extension.

    Args:
        task (dict): The task dict got from ``task_queue``.

    Output:
        Filename with extension.
    """
    url_path = urlparse(task['file_url'])[2]
    new_url_path = ""
    extension = url_path.split('.')[-1] if '.' in url_path else default_ext
    for ch in url_path:
        if ch == '/':
            ch = '_'
        new_url_path += ch
    return new_url_path

icrawler.Downloader.get_filename = new_get_filename

def new_download(self, task, default_ext, timeout=5, max_retry=3, **kwargs):
    """Download the image and save it to the corresponding path.

    Args:
        task (dict): The task dict got from ``task_queue``.
        timeout (int): Timeout of making requests for downloading images.
        max_retry (int): the max retry times if the request fails.
        **kwargs: reserved arguments for overriding.
    """

    file_url = task['file_url']

    retry = max_retry
    while retry > 0 and not self.signal.get('reach_max_num'):
        try:
            response = self.session.get(file_url, timeout=timeout)
        except Exception as e:
            self.logger.error('Exception caught when downloading file %s, '
                              'error: %s, remaining retry times: %d',
                              file_url, e, retry - 1)
        else:
            if self.reach_max_num():
                self.signal.set(reach_max_num=True)
                break
            elif response.status_code != 200:
                self.logger.error('Response status code %d, file %s',
                                  response.status_code, file_url)
                break
            elif not self.keep_file(response, **kwargs):
                break
            with self.lock:
                self.fetched_num += 1
                filename = self.get_filename(task, default_ext)
            self.logger.info('image #%s\t%s', self.fetched_num, file_url)
            # self.storage.write(filename, response.content)
            s3 = boto3.client('s3')
            fp = io.BytesIO(urlopen(file_url).read())

            s3.upload_fileobj(fp, 'ece1779project', filename)

            file_names.append(filename)
            break
        finally:
            retry -= 1

icrawler.Downloader.download = new_download

'''

Class Definitions

'''

class RegisterForm(FlaskForm):
    username = StringField(u'Username', validators=[
                DataRequired(message= u'Username can not be empty.'), Length(4, 16)])
    password = PasswordField('New Password', validators=[
        DataRequired(message= u'Password can not be empty.'),
        EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    submit = SubmitField(u'Register')

class LoginForm(FlaskForm):
    username = StringField(u'Username', validators=[
               DataRequired(message=u'Username can not be empty.'), Length(4, 16)])
    password = PasswordField(u'Password',
                             validators=[DataRequired(message=u'Password can not be empty.')])
    submit = SubmitField(u'Login')

'''

Routers for Login

'''

@webapp.route('/login', methods=['GET', 'POST'])
# Display an empty HTML form that allows users to login
# check the database for existing username and password
# if not right, return to this page again
def login():
    form = LoginForm()
    username = request.form.get('username')
    password = request.form.get('password')
    if form.validate_on_submit():
        table = dynamodb.Table('Users')
        response = table.query(
            KeyConditionExpression=Key('username').eq(username)
        )
        if response['Count'] == 0:
            flash(u"Username doesn't exist!",'warning')
            return render_template("/login/login.html",form=form)
        else:
            for i in response['Items']:
                pass_word = i['password']
            if(password==pass_word):
                session['logged_in']=True
                session['username']=username
                print (session)
                flash(u"Login Success!", 'success')
                return redirect(url_for('thumb_list', username=username))
            else:
                flash(u"Password is wrong!", 'warning')
                return render_template("/login/login.html", form=form)
    return render_template("/login/login.html", form=form)

'''

Routers for Register

'''
@webapp.route('/register', methods=['GET', 'POST'])
# Display an empty HTML form that allows users to register a new account
# If everything in the form are right, save them in the dataabse to create a new account for the new user
def register():
    form = RegisterForm()
    username = request.form.get('username')
    password = request.form.get('password')
    if form.validate_on_submit():
        table = dynamodb.Table('Users')
        response = table.query(
            KeyConditionExpression=Key('username').eq(username)
        )
        print(response)
        if response['Count']!=0:
            flash(u"That username is already taken.", 'warning')
            return render_template("/register/register.html", form=form)
        else:
            response = table.put_item(
                Item={
                    'username': username,
                    'password': password,
                }
            )
            flash(u"Register Success!", 'success')
            return render_template("main.html")
    return render_template("/register/register.html", form=form)

'''

Routers for Crawling Images

'''

@webapp.route('/imagecrawler/form',methods=['GET'])
#Return file upload form
def image_form():
    return render_template("/imagecrawler/form.html")

@webapp.route('/imagecrawler',methods=['POST'])
#Upload a new image and tranform it
def image_crawler():
    table = dynamodb.Table('Images')
    target = request.form.get('target')
    num = request.form.get('num')
    num = int(num)
    radio = request.form.get('gridRadios')

    if radio == 'Greedy':
        url = target
        url=str(url)
        greedy_crawler = GreedyImageCrawler(storage={'root_dir': 'downloaded_pictures'})
        greedy_crawler.crawl(domains=url, max_num=num,
                             min_size=(200, 200), max_size=None)
        print(file_names)
        for file_name in file_names:
            response = table.put_item(
                Item={
                    'username': session['username'],
                    'imagename': file_name,
                }
            )

    if radio == 'Instagram':
        looter = InstaLooter(directory="./downloaded_pictures", profile=target)
        looter.download_pictures(media_count=num)
        counter = 0
        for media in looter.medias():
            # print(media)
            if (counter < num):
                if media['is_video']:
                    url = looter.get_post_info(media['code'])['video_url']
                else:
                    counter = counter + 1
                    url = media['display_src']
                    s3 = boto3.client('s3')
                    fp = io.BytesIO(urlopen(url).read())
                    s3.upload_fileobj(fp, 'ece1779project', media['id'] + '.jpg')
                    response = table.put_item(
                        Item={
                            'username': session['username'],
                            'imagename': media['id'] + '.jpg',
                        }
                    )
            else:
                break

    if radio == 'Google':
        google_crawler = GoogleImageCrawler(parser_threads=2, downloader_threads=4,
                                            storage={'root_dir': 'downloaded_pictures'})
        google_crawler.crawl(keyword=target, max_num=num,
                             date_min=None, date_max=None,
                             min_size=(200, 200), max_size=None)
        for file_name in file_names:
            response = table.put_item(
                Item={
                    'username': session['username'],
                    'imagename': file_name,
                }
            )

    return render_template("/imagecrawler/form.html")

from flask import Flask, request, render_template, redirect, url_for, flash, g, session

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, EqualTo
from instaLooter import InstaLooter
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
    print (radio)

    if radio == '500px':
        url = 'https://500px.com/search?submit=Submit&q={}&type=photos'.format(target)
        greedy_crawler = GreedyImageCrawler(storage={'root_dir': 'downloaded_pictures'})
        greedy_crawler.crawl(domains=url, max_num=num,
                             min_size=None, max_size=None)

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

    return render_template("/imagecrawler/form.html")

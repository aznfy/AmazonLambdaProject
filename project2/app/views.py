from app import webapp
from flask import render_template
import boto3
import urllib

@webapp.route('/',methods=['GET'])
#Return html to the homepage
def main():
    return render_template("main.html")

@webapp.route('/test',methods=['GET'])
def test():
    # Get the service client
    s3 = boto3.client('s3')
    # Download object at bucket-name with key-name to tmp.txt
    # s3.download_file("ece1779project", "1042788575503003245.jpg", "1042788575503003245.jpg")
    print "downloading with urllib"
    testfile = urllib.URLopener()
    testfile.retrieve("https://s3.amazonaws.com/ece1779project/000001.jpg", "test.jpg")
    return render_template("main.html")
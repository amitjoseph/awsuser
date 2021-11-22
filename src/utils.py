import random
import string
import boto3
import re
import pyotp
import time
import datetime
from curtsies.fmtfuncs import red, bold, green, on_blue, yellow

def get_random_password(password_length=20):
    allowed_symbols = "@#$!*^%"
    random_source = string.ascii_letters + string.digits + allowed_symbols #string.punctuation
    
    password = random.choice(string.ascii_lowercase) # select 1 lowercase
    password += random.choice(string.ascii_uppercase) # select 1 uppercase
    password += random.choice(string.digits) # select 1 digit
    password += random.choice(allowed_symbols) ## select 1 special symbol - string.punctuation

    # fill other characters
    for i in range(password_length-4):
        password += random.choice(random_source)

    password_list = list(password)
    random.SystemRandom().shuffle(password_list) # shuffle all characters
    password = ''.join(password_list)
    return password


def get_account_alias():
    try:
        return boto3.client('iam').list_account_aliases()['AccountAliases'][0]
    except IndexError:
        return boto3.client('sts').get_caller_identity().get('Account')
    except:
        return ""


def list_users():
    client = boto3.client('iam')
    response = client.list_users()
    usernames =[u['UserName'] for u in response['Users']]
    return usernames


def filter_username(search_string):
    usernames = list_users()
    filtered_list=[]
    for u in usernames:
        if re.search("^"+search_string, u, re.IGNORECASE):
            filtered_list.append(u)
    return filtered_list

def get_mfa_tokens(mfa_secret):
    totp = pyotp.TOTP(mfa_secret)
    values = []
    values.append(totp.now())
    for i in range(30):
        time.sleep(1)
        tt = totp.now()
        if tt != values[0]:
            break
        print(" >> Please Wait %3d s" % (30-i),end ="\r")

    values.append(tt)
    print("MFA tokens Generated \t\t\t")
    return values

def check_recent_use(check_date):
    if not check_date:
        return ""
    today = datetime.datetime.now()
    delta = today - check_date.replace(tzinfo=None)
    if delta.days < 7:
        return red(bold(":: been used recently"))

def list_groups():
    client = boto3.client('iam')
    response = client.list_groups()
    usernames =[u['GroupName'] for u in response['Groups']]
    return usernames

def filter_groups(search_string):
    usernames = list_groups()
    filtered_list=[]
    for u in usernames:
        if re.search("^"+search_string, u, re.IGNORECASE):
            filtered_list.append(u)
    return filtered_list
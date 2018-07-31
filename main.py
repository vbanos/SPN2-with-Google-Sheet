import re
import requests
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPN_URL = 'https://web-beta.archive.org/save/'
LOGIN_URL = 'https://archive.org/account/login.php'
AVAILABILITY_API_URL = 'https://archive.org/wayback/available'
USERNAME = 'Username'
PASSWORD = 'Password'
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
HEADERS = {
    'User-Agent': 'Wayback_Machine_SPN2_Google_App_Script',
    'Accept' : 'application/json'
}

def is_valid_url(url):
    match = re.match(r'(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?', url)
    return match is not None

def request_capture(url, session):
    response = session.get(url=SPN_URL + url, headers=HEADERS)

    try:
        data = response.json()
        return data['job_id']
    except:
        return None

def request_capture_status(job_id, session):
    time.sleep(20)
    response = session.get(url=SPN_URL + '_status/' + job_id, headers=HEADERS)

    try:
        data = response.json()
        if data['status'] == 'pending':
            return request_capture_status(job_id, session)
        else:
            if 'timestamp' in data and 'original_url' in data:
                return (data['status'], 'http://web.archive.org/web/' + data['timestamp'] + '/' + data['original_url'])
            else:
                return (data['status'], '')
    except:
        return('Error: JSON parse', '')

def check_availability(url, session):
    response = session.get(url=AVAILABILITY_API_URL + '?url=' + url, headers=HEADERS)

    if get_wayback_url_from_response(response.json()):
        return True

    return False

def get_wayback_url_from_response(json):
    ret = None

    if (json and
        json['archived_snapshots'] and
        json['archived_snapshots']['closest'] and
        json['archived_snapshots']['closest']['available'] and
        json['archived_snapshots']['closest']['available'] == True and
        json['archived_snapshots']['closest']['status'] == '200' and
        is_valid_url(json['archived_snapshots']['closest']['url'])):

        ret = make_https(json['archived_snapshots']['closest']['url'])

    return ret

def make_https(url):
    return url.replace('http:', 'https:')

def run():
    session = requests.session()
    session.get(LOGIN_URL)
    session.post(url=LOGIN_URL, data={'username': USERNAME, 'password': PASSWORD, 'action': 'login'})

    creds = ServiceAccountCredentials.from_json_keyfile_name('SPN2 with Google Sheet-6669bdd49f71.json', SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open("The Brink").sheet1
    urls = sheet.col_values(1)

    for index, url in enumerate(urls):
        if not is_valid_url(url):
            continue

        availability = check_availability(url, session)
        job_id = request_capture(url, session)

        if not job_id:
            continue

        (status, captured_url) = request_capture_status(job_id, session)

        sheet.update_cell(index + 1, 2, availability)
        sheet.update_cell(index + 1, 3, status)
        sheet.update_cell(index + 1, 4, captured_url)
        sheet.update_cell(index + 1, 5, job_id)

run()


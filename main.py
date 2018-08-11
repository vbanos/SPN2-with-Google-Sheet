import argparse
import logging
import re
import requests
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials


parser = argparse.ArgumentParser(description='SPN2 Options.')
parser.add_argument('--spn-url', dest='spn_url',
                    default='https://web-beta.archive.org/save/')
parser.add_argument('--availability-api-url', dest='availability_api_url',
                    default='https://archive.org/wayback/available')
# get these keys at https://archive.org/account/s3.php
parser.add_argument('--ias3key', dest='ias3key', required=True)
parser.add_argument('--ias3secret', dest='ias3secret', required=True)

args = parser.parse_args()

SCOPE = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
HEADERS = {
    'User-Agent': 'Wayback_Machine_SPN2_Google_App_Script',
    'Accept': 'application/json',
    'authorization': 'LOW %s:%s' % (args.ias3key, args.ias3secret)
}

session = requests.Session()

def is_valid_url(url):
    match = re.match(r'(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?', url)
    return match is not None

def request_capture(url):
    response = session.get(url=args.spn_url + url, headers=HEADERS)
    try:
        data = response.json()
        return data['job_id']
    except Exception as exc:
        logging.error(exc)
        return None

def request_capture_status(job_id):
    time.sleep(10)
    status_url = '%sstatus/%s?_t=%s' % (args.spn_url, job_id, str(time.time()))
    response = session.get(status_url, headers=HEADERS)

    try:
        data = response.json()
        logging.debug(data)
        if data['status'] == 'pending':
            return request_capture_status(job_id)
        else:
            if 'timestamp' in data and 'original_url' in data:
                return (data['status'], 'http://web.archive.org/web/' + data['timestamp'] + '/' + data['original_url'])
            else:
                return (data['status'], '')
    except Exception as exc:
        logging.error(exc)
        return('Error: JSON parse', '')

def check_availability(url):
    response = session.get(url=args.availability_api_url + '?url=' + url, headers=HEADERS)

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
    creds = ServiceAccountCredentials.from_json_keyfile_name('SPN2 with Google Sheet-6669bdd49f71.json', SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open("The Brink").sheet1
    urls = sheet.col_values(1)
    logging.info("Total URLS", len(urls))
    for index, url in enumerate(urls):
        logging.info(index, url)
        if not is_valid_url(url):
            continue

        availability = check_availability(url)
        job_id = request_capture(url)
        if not job_id:
            continue

        (status, captured_url) = request_capture_status(job_id)
        logging.info(status, captured_url)
        sheet.update_cell(index + 1, 2, availability)
        sheet.update_cell(index + 1, 3, status)
        sheet.update_cell(index + 1, 4, captured_url)
        sheet.update_cell(index + 1, 5, job_id)

run()

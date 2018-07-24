import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('SPN2 with Google Sheet-6669bdd49f71.json', scope)
client = gspread.authorize(creds)
sheet = client.open("ISKME Press Mention URLs ").sheet1

list_of_hashes = sheet.get_all_records() 
print(list_of_hashes)
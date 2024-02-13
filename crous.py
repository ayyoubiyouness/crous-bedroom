import requests
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
pd.set_option('display.max_columns', None)


def mysql_connect():
    return mysql.connector.connect(
        host="srv1230.hstgr.io",  
        user="u203255105_crous",
        password="CrousHayatech2023",
        database="u203255105_crous"
    )


def insert_into_database(df, connection) :
    cursor = connection.cursor()

    
    for _, row in df.iterrows():
        sql = """INSERT INTO crousdata (Title, Adresse, Price, Size)
                 VALUES (%s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE
                 Adresse = VALUES(Adresse), Price = VALUES(Price), Size = VALUES(Size)"""
        val = (row['Title'], row['Adresse'], row['Price'], row['Size'])
        cursor.execute(sql, val)

    connection.commit()
    cursor.close()

def scrape_website() : 
    url = 'https://trouverunlogement.lescrous.fr/tools/32/search'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')

    titles = []
    addresses = []
    prices = []
    sizes = []
    details = []

    content = soup.find_all('div', class_='fr-card')

    for card in content : 
    # print("hello world")
        title_tag = card.find('h3', class_='fr-card__title')
        titles.append(title_tag.get_text(strip=True) if title_tag else 'N/A')

        address_tag = card.find('p', class_='fr-card__desc')
        addresses.append(address_tag.get_text(strip=True) if address_tag else 'N/A')

        price_tag = card.find('p', class_='fr-badge')
        prices.append(price_tag.get_text(strip=True) if price_tag else 'N/A')

        size_tag = card.find('p', class_='fr-card__detail')
        sizes.append(size_tag.get_text(strip=True) if size_tag else 'N/A')

    data = {
            'Title' : titles,
            'Adresse' : addresses,
            'Price' : prices,
            'Size' : sizes
        }

    df = pd.DataFrame(data)

    return df



def update_df(existing_df) : 
    new_data = scrape_website()
    new_df = pd.DataFrame(new_data)
    combined_df = pd.concat([existing_df, new_df]).drop_duplicates(keep='first')
    return combined_df

def check_marseille_and_notify(df):
    # Check for 'Toulon' in the 'Adresse' column
    perpignan_df = df[df['Adresse'].str.contains('PERPIGNAN', case=False, na=False)]
    brive_df = df[df['Adresse'].str.contains('BRIVE', case=False, na=False)]


    frames = [perpignan_df, brive_df]
    result = pd.concat(frames)
    if not result.empty :
        send_email(result)


def send_email(dataframe):
    msg = MIMEMultipart()
    msg['From'] = 'younessayyoubi@gmail.com'
    msg['To'] = 'younessayy22@gmail.com'
    msg['Subject'] = 'New Listing in Toulon'

    body = "New listings found in Toulon:\n\n" + dataframe.to_string()
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)  # Use SMTP_SSL for secure connection
        server.login('younessayyoubi@gmail.com', 'neydhgsehwyndquc')  # Your app-specific password
        server.sendmail('younessayyoubi@gmail.com', 'younessayy22@gmail.com', msg.as_string())
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")


df = pd.DataFrame(scrape_website())
print(df)

def get_dataframe():
    global df
    return df



while True :
    print("Checking for updates...")
    db_connection = mysql_connect()
    df = update_df(df)
    check_marseille_and_notify(df) 
    insert_into_database(df, db_connection)
    db_connection.close()
    time.sleep(15)


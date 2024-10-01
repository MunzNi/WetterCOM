import random
import time
import re
import os

from bs4 import BeautifulSoup
from selenium import webdriver
import paho.mqtt.client as mqtt

mqtt_broker = os.getenv("MQTT_BROKER")
mqtt_port = os.getenv("MQTT_PORT")
mqtt_topic = os.getenv("MQTT_TOPIC")
mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")
website_url = os.getenv("WETTERCOM_URL")

#Chromedriver aufsetzen
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]
user_agent = random.choice(user_agents)

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument(f"--user-agent={user_agent}")
driver = webdriver.Chrome(options=chrome_options)


def scrape_website() -> dict:
    driver.get(website_url)
    time.sleep(2)
    html = driver.page_source

    soup = BeautifulSoup(html, 'lxml')
    
    all_days_data = {}
    
    # Schleife für 3 Tage (Tag 1, 2 und 3)
    for day in range(1, 4):
        element = soup.select_one(f'[data-label="VHSZeitraum_zumTag{day}"]')
        
        if element:
            day_data = extract_day(element)
            all_days_data[f"day{day}"] = day_data
        else:
            print(f"Element für Tag {day} nicht gefunden.")
    
    driver.quit()
    
    return all_days_data

def extract_day(soup: BeautifulSoup) -> dict:
    
    data = {}
    
    #temperatur
    temp = soup.find('div', class_='swg-col-temperature swg-row')
    temp_max_raw = temp.find('span', class_='swg-text-large').text
    temp_min_raw = temp.find('span', class_='swg-text-small').text
    max_temp = re.sub(r'[^\d\-]', '', temp_max_raw)
    min_temp = re.sub(r'[^\d\-]', '', temp_min_raw)
    data['max_temp'] = max_temp
    data['min_temp'] = min_temp
    
    #regenwahrscheinlichkeit
    regen_wahrscheinlichkeit_raw = soup.find('div', class_='swg-col-wv1 swg-row').text
    regen_wahrscheinlichkeit = re.sub(r'[^\d]', '', regen_wahrscheinlichkeit_raw)
    data['regen_wahrscheinlichkeit'] = regen_wahrscheinlichkeit
    
    #regenmenge
    regen_menge_raw = soup.find('div', class_='swg-col-wv2 swg-row').text
    regen_menge = re.sub(r'[^\d,\.]', '', regen_menge_raw)
    regen_menge = regen_menge.replace(',', '.')
    data['regen_menge'] = regen_menge
    
    #Wind
    Wind_raw = soup.find('div', class_='swg-col-wv3 swg-row').text
    Wind = re.sub(r'[^\d]', '', Wind_raw)
    data['Wind'] = Wind
    
    return data

def send_to_mqtt(weather_data: dict):

    # MQTT-Client initialisieren
    client = mqtt.Client()

    # Authentifizierung mit Benutzername und Passwort
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)
    
    port = int(mqtt_port)
    client.connect(mqtt_broker, port)

    for day, values in weather_data.items():
        for key, value in values.items():
            # Daten an spezifische Topics senden
            topic = f"{mqtt_topic}/{day}/{key}"
            client.publish(topic, value)

    # Verbindung trennen
    client.disconnect()

if __name__ == "__main__":
    all_days_data = scrape_website()
    send_to_mqtt(all_days_data)

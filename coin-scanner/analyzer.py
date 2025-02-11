import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import json


class DexScreenerData:
    def __init__(self):
        self.data_url = "https://api.dexscreener.com/token-profiles/latest/v1"

    def format(self, listdict, chain='solana'):
        data = {}

        for coin in listdict:
            if coin.get("chainId") == chain:
                dex_url = coin.get("url")
                chain_id = coin.get("chainId")
                token_address = coin.get("tokenAddress")
                icon = coin.get("icon")
                header = coin.get("header")
                open_graph = coin.get("openGraph")
                description = coin.get("description")
                links = coin.get("links", [])

                # Adding all the values to the dictionary for each token address
                data[token_address] = {
                    "dex_url": dex_url,
                    "chain_id": chain_id,
                    "icon": icon,
                    "header": header,
                    "open_graph": open_graph,
                    "description": description,
                    "links": links
                }
        return data
    
    def analyze_token_security(self, tokens: list):
        organic_scores = {}
        
        options = Options() # set up chrome options
        options.add_argument("--disable-gpu")  # disable gpu hardware acceleration (required for headless mode)
        options.add_argument("--no-sandbox")   # disable the sandbox (useful for some environments)
        options.add_argument("--headless") #not visible
        options.add_argument("--log-level=3")  # error level logs only
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("""Object.defineProperty(navigator, 'webdriver', { get: () => false });""")

        for token_address in tokens:
            check_url = f"https://jup.ag/tokens/{token_address}"

            try:
                driver.get(check_url) #load url
                html_content = driver.page_source
                organic_score = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex.items-center.rounded-r.px-2.text-sm.font-medium.text-black"))
                ).text #jup organic score

                organic_scores[token_address] = organic_score
    
            except requests.RequestException as e:
                print(f"An error occurred while fetching data: {e}")
                return None
            
        driver.quit()   

        return organic_scores

    def scan(self):
        coins = requests.get(self.data_url).json()
        data = self.format(coins)
        return self.analyze_token_security(data.keys())

print(DexScreenerData().scan())
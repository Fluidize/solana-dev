import os
import time
import json

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tabulate import tabulate

from textual.app import App
from textual.widgets import Header, Footer, Button
from textual.reactive import Reactive
from textual.containers import Container

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    DEFAULT = '\033[39m'

class CoinData:
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

        token_count = len(tokens)

        for token_address in tokens:
            print(bcolors.OKBLUE + f"{token_count} left to scan." + bcolors.DEFAULT, end = '\r')
            
            check_url = f"https://jup.ag/tokens/{token_address}"
            try:
                driver.get(check_url) #load url
                
                html_content = driver.page_source
                organic_score = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex.items-center.rounded-r.px-2.text-sm.font-medium.text-black"))
                ).text #jup organic score
                token_name = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex.items-center.gap-1\\.5.text-xl.font-semibold"))
                ).text #token name

                organic_scores[token_address] = (token_name,organic_score)

                token_count -= 1

            except requests.RequestException as e:
                print(f"An error occurred while fetching data: {e}")
                return None
        
        os.system('cls')
        driver.quit()
        return organic_scores

    def scan(self):
        coins = requests.get(self.data_url).json()
        data = self.format(coins)
        organic_scores = self.analyze_token_security(data.keys()) #addr + score

        #make it chart-readable
        #columns --- token addr + token name + organic score + rugcheck link
        table_data = []
        for coin in organic_scores:
            float_score = float(organic_scores[coin][1])
            if float_score >= 80.00:
                colored_score = bcolors.OKGREEN + organic_scores[coin][1] + bcolors.DEFAULT
            elif float_score > 0.00:
                colored_score = bcolors.WARNING + organic_scores[coin][1] + bcolors.DEFAULT
            else:
                colored_score = bcolors.FAIL + organic_scores[coin][1] + bcolors.DEFAULT

            table_data.append((coin, organic_scores[coin][0], colored_score, "https://rugcheck.xyz/tokens/"+coin))

        return table_data
    
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import sys

# Initialize the console for output
Console = Console()

class CommandUI:
    def __init__(self):
        self.CoinData = CoinData()
        self.commands = {
            "help": self.show_help,
            "add": self.add_numbers,
            "scan": self.scan,
            "exit": self.exit_app
        }

    def show_help(self):
        help_text = Text("Available Commands:", style="bold green")
        help_text.append("\n  - help: Show this help message")
        help_text.append("\n  - scan: Scan on Dexscreener.")
        help_text.append("\n  - add <num1> <num2>: Add two numbers")
        help_text.append("\n  - exit: Exit the app")
        # Create a panel with the help text (no soft_wrap here)
        Console.print(Panel(help_text))

    def add_numbers(self):
        num1 = Prompt.ask("Enter first number", default=10)
        num2 = Prompt.ask("Enter second number", default=20)
        result = int(num1) + int(num2)
        Console.print(f"The result of adding {num1} and {num2} is {result}", style="bold yellow")

    def scan(self):
        self.CoinData.scan()

    def exit_app(self):
        Console.print("Exiting the app...", style="bold red")
        sys.exit()

    def run(self):
        while True:
            # Show the prompt
            command = Prompt.ask("\nEnter a command", default="help")
            if command in self.commands:
                # Run the command if valid
                self.commands[command]()
            else:
                # Handle invalid command
                Console.print(f"[bold red]Invalid command:[/bold red] {command}. Type [bold green]help[/bold green] for available commands.")

if __name__ == "__main__":
    # Initialize the UI
    ui = CommandUI()
    # Run the UI
    ui.run()

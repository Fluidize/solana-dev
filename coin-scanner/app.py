import os
import time
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import SQUARE
import sys

rich_console = Console()

class CoinData:
    def __init__(self):
        self.data_url = "https://api.dexscreener.com/token-profiles/latest/v1"

        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")  # run in background
        options.add_argument("--log-level=3")  # suppress unnecessary logs
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # initialize WebDriver once for the class
        rich_console.print("[bold green]Initializing selenium webscraper...[/bold green]", end="")
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")

    def close_driver(self):
        self.driver.quit()

    def format(self, listdict, chain='solana'):
        """Filter and format coin data for a specific blockchain (default: Solana)."""
        data = {}
        for coin in listdict:
            if coin.get("chainId") == chain:
                token_address = coin.get("tokenAddress")
                data[token_address] = {
                    "dex_url": coin.get("url"),
                    "chain_id": coin.get("chainId"),
                    "icon": coin.get("icon"),
                    "header": coin.get("header"),
                    "open_graph": coin.get("openGraph"),
                    "description": coin.get("description"),
                    "links": coin.get("links", [])
                }
        return data
    
    def analyze_token_security(self, tokens):
        organic_scores = {}

        if isinstance(tokens, str):  # if scanning a single token
            return self._scan_single_token_jup(tokens)
        else:  # multiple tokens
            for token_address in tokens:
                rich_console.print(f"[cyan]Scanning {token_address}...[/cyan]", end="\r")
                result = self._scan_single_token_jup(token_address)
                if result: #check if empty
                    organic_scores[token_address] = result
        return organic_scores

    def _scan_single_token_jup(self, token_address): #data from jup
        check_url = f"https://jup.ag/tokens/{token_address}"
        try:
            self.driver.get(check_url)  # Load URL
            
            # Wait for elements to load
            token_name = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex.items-center.gap-1\\.5.text-xl.font-semibold"))
            ).text

            organic_score = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex.items-center.rounded-r.px-2.text-sm.font-medium.text-black"))
            ).text

            price = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex.items-center.text-lg.font-semibold"))
            ).text.replace("\n", "").replace("\t", "").replace("    ", "") #subscript does newline for some reason

            elements = self.driver.find_elements(By.CSS_SELECTOR, ".flex.items-center.text-sm.font-semibold") #mkt cap , liquidity, 24h vol, holders
            elements = [element.text for element in elements if element.text]
            if elements[3] == "Instant": #liquidity box is gone
                elements[3] = elements[2] #shift
                elements[2] = elements[1]
                elements[1] = "[bold red]None[/bold red]"

            #token name, address, score, price, mkt cap , liquidity, 24h vol, holders
            return (token_name, token_address, organic_score, price, elements[0], elements[1], elements[2], elements[3]) #[link=] for hypertext

        except Exception as e:
            rich_console.print(f"[bold red]Error scanning {token_address}[/bold red]")
            print(e)
            return None

    def _scan_single_token_gmgn(self, token_address):
        pass

    def scan(self):
        coins = requests.get(self.data_url).json()
        data = self.format(coins)
        jup_data = self.analyze_token_security(data.keys())  # get token data from jupiter

        # Format data for display - flatten
        table_data = [
            (data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7])
            for key, data in jup_data.items()
        ]
        return table_data



class CommandUI:
    def __init__(self):
        self.CoinData = CoinData()
        self.commands = {
            "help": self.show_help,

            "scan": self.scan, #alias
            "sc": self.scan,

            "scan-auto": self.scan_auto,
            "sca": self.scan_auto,

            "rugcheck": self.rugcheck,
            "rc": self.rugcheck,

            "exit": self.exit_app
        }

    def show_help(self):
        help_text = Text("Available Commands:", style="bold green")
        help_text.append("\n  - help - Show this help message")
        help_text.append("\n  - scan-auto - Scan coins from Dexscreener. | sca ")
        help_text.append("\n  - scan <token> - Scan a specific token address. | sc")
        help_text.append("\n  - rugcheck <token> - Generate a link to rugcheck.xyz. | rc")
        help_text.append("\n  - exit - Exit the app")
        rich_console.print(Panel(help_text))
    
    def scan_auto(self):
        table = Table(title="[bold cyan]Jupiter Organic Scores[/bold cyan]", header_style="bold white", box=SQUARE)
        table.add_column("Name", justify="center", style="bold white")
        table.add_column("Token + Rugcheck.xyz URL", justify="center")
        table.add_column("Score", justify="center")
        table.add_column("Price", justify="center")
        table.add_column("Mkt Cap", justify="center")
        table.add_column("Liquidity", justify="center")
        table.add_column("24h Volume", justify="center")
        table.add_column("Holders", justify="center")
        table.add_column("GMGN.ai", justify="center")

        table_data = self.CoinData.scan()

        for data in table_data:
            score_style = self._get_score_style(data[2])
            table.add_row(data[0], f"[underline bright_blue][link=https://rugcheck.xyz/tokens/{data[1]}]{data[1]}[/underline bright_blue]", f"[{score_style}]{str(data[2])}[/{score_style}]",data[3],data[4], data[5], data[6], data[7], f"[underline bright_green][link=https://gmgn.ai/sol/token/{data[1]}]{data[0]}[/underline bright_green]")

        rich_console.print(table)

    def scan(self,token):
        # token = Prompt.ask("Enter token address")
        data = self.CoinData.analyze_token_security(token)

        if not data:
            rich_console.print("[bold red]Failed to retrieve token data.[/bold red]")
            return

        table = Table(title="[bold cyan]Jupiter Organic Scores[/bold cyan]", header_style="bold white", box=SQUARE)
        table.add_column("Name", justify="center", style="bold white")
        table.add_column("Token + Rugcheck.xyz URL", justify="center")
        table.add_column("Score", justify="center")
        table.add_column("Price", justify="center")
        table.add_column("Mkt Cap", justify="center")
        table.add_column("Liquidity", justify="center")
        table.add_column("24h Volume", justify="center")
        table.add_column("Holders", justify="center")
        table.add_column("GMGN.ai", justify="center")

        score_style = self._get_score_style(data[2])
        table.add_row(data[0], f"[underline bright_blue][link=https://rugcheck.xyz/tokens/{data[1]}]{data[1]}[/underline bright_blue]", f"[{score_style}]{str(data[2])}[/{score_style}]",data[3],data[4], data[5], data[6], data[7], f"[underline bright_green][link=https://gmgn.ai/sol/token/{data[1]}]{data[0]}[/underline bright_green]")

        rich_console.print(table)

    def rugcheck(self, token):
        rich_console.print(f"[underline bright_blue]https://rugcheck.xyz/tokens/{token}[/underline bright_blue]")

    def _get_score_style(self, score):
        score = float(score)
        if score >= 80.00:
            return "bold bright_green"
        elif score > 0.00:
            return "bold bright_yellow"
        else:
            return "bold bright_red"

    def exit_app(self):
        self.CoinData.close()  # Ensure WebDriver is properly closed
        rich_console.print("Exiting the app...", style="bold red")
        sys.exit()

    def run(self):
        while True:
            command_input = Prompt.ask("\nEnter a command", default="help")
            command_parts = command_input.split(" ")

            command_name = command_parts[0]
            command_args = command_parts[1:]

            if command_name in self.commands:
                try:
                    self.commands[command_name](*command_args)
                except TypeError as e:
                    rich_console.print(f"[bold red]Error: Incorrect parameters ({e})[/bold red]")
            else:
                rich_console.print(f"[bold red]Invalid command:[/bold red] {command_name}. Type [bold green]help[/bold green] for available commands.")

if __name__ == "__main__":
    ui = CommandUI()
    ui.run()
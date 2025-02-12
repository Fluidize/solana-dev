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

# Initialize Rich Console
rich_console = Console()

class CoinData:
    def __init__(self):
        """Initialize WebDriver for Selenium in headless mode."""
        self.data_url = "https://api.dexscreener.com/token-profiles/latest/v1"

        # Set up Chrome options
        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")  # Run in background
        options.add_argument("--log-level=3")  # Suppress unnecessary logs
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # Initialize WebDriver once for the class
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

        if isinstance(tokens, str):  # If scanning a single token
            return self._scan_single_token(tokens)
        else:  # If scanning multiple tokens
            for token_address in tokens:
                rich_console.print(f"[cyan]Scanning {token_address}...[/cyan]", end="\r")
                result = self._scan_single_token(token_address)
                if result:
                    organic_scores[token_address] = result
        return organic_scores

    def _scan_single_token(self, token_address):
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

            return (token_name, token_address, float(organic_score), f"https://rugcheck.xyz/tokens/{token_address}")

        except Exception as e:
            rich_console.print(f"[bold red]Error scanning {token_address}: {e}[/bold red]")
            return None

    def scan(self):
        coins = requests.get(self.data_url).json()
        data = self.format(coins)
        organic_scores = self.analyze_token_security(data.keys())  # Get addresses and scores

        # Format data for display
        table_data = [
            (score[0], addr, score[2], score[3])  # Token name, address, score, rugcheck link
            for addr, score in organic_scores.items()
        ]
        return table_data

class CommandUI:
    def __init__(self):
        self.CoinData = CoinData()
        self.commands = {
            "help": self.show_help,
            "scan": self.scan,
            "scan-auto": self.scan_auto,
            "exit": self.exit_app
        }

    def show_help(self):
        help_text = Text("Available Commands:", style="bold green")
        help_text.append("\n  - help: Show this help message")
        help_text.append("\n  - scan-auto: Scan coins from Dexscreener.")
        help_text.append("\n  - scan: Scan a specific token address.")
        help_text.append("\n  - exit: Exit the app")
        rich_console.print(Panel(help_text))

    def scan_auto(self):
        table = Table(title="[bold cyan]Jupiter Organic Scores[/bold cyan]", header_style="bold white", box=SQUARE)
        table.add_column("Name", justify="center", style="bold white")
        table.add_column("Token", justify="center")
        table.add_column("Score", justify="center")
        table.add_column("Rugcheck.xyz", justify="center", style="underline bright_blue")

        table_data = self.CoinData.scan()

        for data in table_data:
            score_style = self._get_score_style(data[2])
            table.add_row(data[0], data[1], f"[{score_style}]{str(data[2])}[/{score_style}]", data[3])

        rich_console.print(table)

    def scan(self):
        token = Prompt.ask("Enter token address")
        table_data = self.CoinData.analyze_token_security(token)

        if not table_data:
            rich_console.print("[bold red]Failed to retrieve token data.[/bold red]")
            return

        table = Table(title="[bold cyan]Jupiter Organic Scores[/bold cyan]", header_style="bold white", box=SQUARE)
        table.add_column("Name", justify="center", style="bold white")
        table.add_column("Token", justify="center")
        table.add_column("Score", justify="center")
        table.add_column("Rugcheck.xyz", justify="center", style="underline bright_blue")

        score_style = self._get_score_style(table_data[2])
        table.add_row(table_data[0], table_data[1], f"[{score_style}]{str(table_data[2])}[/{score_style}]", table_data[3])

        rich_console.print(table)

    def _get_score_style(self, score):
        """Assigns colors based on the score range."""
        if score >= 80.00:
            return "bold bright_green"
        elif score > 0.00:
            return "bold bright_yellow"
        else:
            return "bold bright_red"

    def exit_app(self):
        """Closes Selenium WebDriver and exits the app."""
        self.CoinData.close()  # Ensure WebDriver is properly closed
        rich_console.print("Exiting the app...", style="bold red")
        sys.exit()

    def run(self):
        while True:
            command = Prompt.ask("\nEnter a command", default="help")
            if command in self.commands:
                self.commands[command]()
            else:
                rich_console.print(f"[bold red]Invalid command:[/bold red] {command}. Type [bold green]help[/bold green] for available commands.")

if __name__ == "__main__":
    ui = CommandUI()
    ui.run()
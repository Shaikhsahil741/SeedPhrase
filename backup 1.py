import tkinter as tk
from tkinter import messagebox, font as tkFont
from bip_utils import Bip39MnemonicGenerator, Bip39MnemonicValidator, Bip39WordsNum, Bip39Languages, Bip39SeedGenerator, Bip44, Bip44Coins
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


class SeedPhraseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Seed Phrase Generator with Wallet Balance")
        self.root.geometry("600x500")
        self.root.configure(bg="#f5f5f5")

        # Create a header frame
        header_frame = tk.Frame(root, bg="#4CAF50", pady=10)
        header_frame.pack(fill=tk.X)

        # Title label
        title_font = tkFont.Font(family="Helvetica", size=16, weight="bold")
        title_label = tk.Label(header_frame, text="Project Aziz",
                               font=title_font, fg="white", bg="#4CAF50")
        title_label.pack()

        # Main content frame
        self.content_frame = tk.Frame(root, bg="#f5f5f5")
        self.content_frame.pack(pady=10)

        # Label for seed phrase and balances
        self.label = tk.Label(
            self.content_frame, text="Generated Seed Phrase and Balances:", bg="#f5f5f5", font=("Helvetica", 12))
        self.label.pack(pady=5)

        # Text area for displaying phrases
        self.phrase_display = tk.Text(self.content_frame, height=15, width=70,
                                      wrap=tk.WORD, bg="#ffffff", fg="#333333", font=("Courier New", 10))
        self.phrase_display.pack(pady=5)
        self.phrase_display.config(state=tk.DISABLED)

        # Buttons frame
        buttons_frame = tk.Frame(root, bg="#f5f5f5")
        buttons_frame.pack(pady=10)

        # Copy button
        self.copy_button = tk.Button(buttons_frame, text="Copy Selected Phrase", command=self.copy_phrase,
                                     bg="#4CAF50", fg="white", font=("Helvetica", 10), borderwidth=0)
        self.copy_button.pack(side=tk.LEFT, padx=5)

        # Pause button
        self.pause_button = tk.Button(buttons_frame, text="Pause Scrolling", command=self.toggle_pause,
                                      bg="#4CAF50", fg="white", font=("Helvetica", 10), borderwidth=0)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.paused = False
        self.running = True

        # Define the coins to monitor
        self.coins = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'LTC': 'litecoin',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'SOL': 'solana',
            'DOGE': 'dogecoin'
        }

        self.prices = {}
        self.update_prices()  # Fetch current prices on startup
        self.log_file_path = "seed_phrase_log.txt"
        self.generate_seed()

    def update_prices(self):
        try:
            for symbol, id in self.coins.items():
                response = requests.get(
                    f"https://api.coingecko.com/api/v3/simple/price?ids={id}&vs_currencies=usd")
                if response.status_code == 200:
                    self.prices[symbol] = response.json()[id]["usd"]
                else:
                    self.prices[symbol] = 0.0
        except requests.RequestException as e:
            print(f"Error fetching cryptocurrency prices: {e}")

    def generate_seed(self):
        mnemonic_generator = Bip39MnemonicGenerator()
        validator = Bip39MnemonicValidator(Bip39Languages.ENGLISH)

        def update_phrases():
            while self.running:
                if not self.paused:
                    seed_phrase = mnemonic_generator.FromWordsNumber(
                        Bip39WordsNum.WORDS_NUM_12)

                    if validator.IsValid(seed_phrase):
                        seed_bytes = Bip39SeedGenerator(seed_phrase).Generate()

                        # Fetch wallet balances in parallel
                        with ThreadPoolExecutor() as executor:
                            futures = {executor.submit(
                                self.check_wallet_balance, seed_bytes, symbol): symbol for symbol in self.coins}

                            balances = {}
                            for future in as_completed(futures):
                                symbol = futures[future]
                                try:
                                    balance = future.result()
                                    balances[symbol] = balance
                                except Exception as e:
                                    print(
                                        f"Error fetching {symbol} balance: {e}")
                                    balances[symbol] = 0

                        balance_display = ", ".join(
                            f"{symbol} ${balance * self.prices[symbol]:.8f}" for symbol, balance in balances.items())

                        self.phrase_display.config(state=tk.NORMAL)
                        self.phrase_display.insert(
                            tk.END, f"Phrase: {seed_phrase}\n")
                        self.phrase_display.insert(
                            tk.END, f"Wallet Balances: {balance_display}\n")
                        self.phrase_display.insert(tk.END, "-" * 60 + "\n")
                        self.phrase_display.config(state=tk.DISABLED)
                        self.phrase_display.see(tk.END)

                        # Log non-zero balances
                        for symbol, balance in balances.items():
                            total_value = balance * self.prices[symbol]
                            if total_value > 0:
                                self.log_seed_phrase(seed_phrase, balances)
                                messagebox.showinfo(
                                    "Balance Alert", f"Non-zero balance detected for seed phrase:\n{seed_phrase}\n{balance_display}")

                self.root.update_idletasks()
                time.sleep(0.1)  # Shortened delay for faster generation

        # Run the phrase generation in a separate thread
        thread = threading.Thread(target=update_phrases)
        thread.daemon = True
        thread.start()

    def check_wallet_balance(self, seed_bytes, coin):
        if coin == 'BTC':
            bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
        elif coin == 'ETH':
            bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
        elif coin == 'LTC':
            bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.LITECOIN)
        elif coin == 'XRP':
            bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.RIPPLE)
        elif coin == 'ADA':
            bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.CARDANO_BYRON_ICARUS)
        elif coin == 'SOL':
            bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
        elif coin == 'DOGE':
            bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.DOGECOIN)
        else:
            return 0

        wallet_address = bip44.PublicKey().ToAddress()

        try:
            # API calls to get balances for each coin
            if coin == 'BTC':
                response = requests.get(
                    f"https://api.blockcypher.com/v1/btc/main/addrs/{wallet_address}/balance")
                if response.status_code == 200:
                    return response.json().get('final_balance', 0)
            elif coin == 'ETH':
                response = requests.get(
                    f"https://api.blockcypher.com/v1/eth/main/addrs/{wallet_address}/balance")
                if response.status_code == 200:
                    return response.json().get('final_balance', 0)
            elif coin == 'LTC':
                response = requests.get(
                    f"https://api.blockcypher.com/v1/ltc/main/addrs/{wallet_address}/balance")
                if response.status_code == 200:
                    return response.json().get('final_balance', 0)
            elif coin == 'XRP':
                response = requests.get(
                    f"https://data.ripple.com/v2/accounts/{wallet_address}/balances")
                if response.status_code == 200:
                    for balance in response.json()['balances']:
                        if balance['currency'] == 'XRP':
                            return float(balance['value'])
            elif coin == 'ADA':
                response = requests.get(
                    f"https://cardano-mainnet.blockfrost.io/api/v0/addresses/{wallet_address}/statistics",
                    headers={"project_id": "<YOUR_BLOCKFROST_PROJECT_ID>"})
                if response.status_code == 200:
                    return float(response.json().get('total_received', 0))
            elif coin == 'SOL':
                response = requests.post(
                    "https://api.mainnet-beta.solana.com",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getBalance",
                        "params": [wallet_address]
                    }
                )
                if response.status_code == 200:
                    return response.json().get('result', {}).get('value', 0)
            elif coin == 'DOGE':
                response = requests.get(
                    f"https://api.blockcypher.com/v1/doge/main/addrs/{wallet_address}/balance")
                if response.status_code == 200:
                    return response.json().get('final_balance', 0)
        except requests.RequestException:
            return 0

        return 0

    def log_seed_phrase(self, seed_phrase, balances):
        with open(self.log_file_path, 'a') as f:
            f.write(f"Seed Phrase: {seed_phrase}\n")
            for symbol, balance in balances.items():
                f.write(f"{symbol} Balance: {balance}\n")
            f.write("-" * 60 + "\n")

    def copy_phrase(self):
        selected_text = self.phrase_display.get(tk.SEL_FIRST, tk.SEL_LAST)
        if selected_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            messagebox.showinfo("Copy", "Selected text copied to clipboard")

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_button.config(text="Resume Scrolling")
        else:
            self.pause_button.config(text="Pause Scrolling")


if __name__ == "__main__":
    root = tk.Tk()
    app = SeedPhraseApp(root)
    root.mainloop()

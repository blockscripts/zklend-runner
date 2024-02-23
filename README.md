# ZK Lend Transaction Script 🌉

This Python script automates transactions on the Starknet network within ZKlend environment. The script utilizes the `ccxt` library for OKX exchange interactions and the `starknet_py` library for Starknet operations.

## Requirements 💼

Make sure you have the required Python libraries installed. You can install them using:

```bash
pip install -r requirements.txt
```

- `ccxt`: Cryptocurrency trading library
- `starknet_py`: Starknet Python SDK
- `asyncio`: Asynchronous I/O library
- `loguru`: Logging library
- `web3`: Ethereum interaction library
- `aiohttp`: Asynchronous HTTP library

## Configuration ⚙️

IMPORTANT: Addresses in Starknet must be added to the **trusted address book** in OKX (see step 5).

1. In `src/okx/config/secrets.py`, add the keys for the OKX account (IMPORTANT: all 3 functions - `Read`, `Withdraw`, `Trade` - are required, with the last one for transferring between subaccounts).

2. In `src/accounts/okx_addresses.txt`, add the addresses of OKX subaccounts to which Ethereum will be returned.

3. In `src/accounts/starknet_privkeys.txt`, add the private keys of Argent wallets.

4. If needed, configure parameters:
   - `src/okx/config/settings.py` for OKX
   - `src/zklend/config/settings.py` for zkLend

5. In the terminal:
   - `pip install -r requirements.txt` - install libraries
   - `cd src`
   - `python get_addresses.py` - get addresses for OKX address book
   - `python main.py` - run the script


<h2>Script Workflow 👨🏻‍💻</h2>

1. Random delay in seconds from the `SEND_WAIT` range (`src/okx/config/settings.py`).

2. Collect Ethereum from all subaccounts to the main account for withdrawal. If there is not enough Ethereum for withdrawal, random delay in seconds from the `RETRY_WAIT` range (`src/settings.py`) and repeat from step 1 for the same wallet.

3. Withdraw to the next Starknet account in the list with a percentage from the `SEND_PERCENTAGE` range (`src/okx/config/settings.py`).

4. If the account is not activated: Random delay in seconds from the `INIT_WAIT` range (`src/zklend/config/settings.py`).

5. If the account is not activated: Activate the account.

6. Random delay in seconds from the `DEPOSIT_WAIT` range (`src/zklend/config/settings.py`).

7. Deposit Ethereum into the zkLend pool with a percentage from the `DEPOSIT_PERCENTAGE` range (`src/zklend/config/settings.py`).

8. Random delay in seconds from the `WITHDRAW_WAIT` range (`src/zklend/config/settings.py`).

9. Withdraw Ethereum from the zkLend pool.

10. Random delay in seconds from the `TRANSFER_WAIT` range (`src/zklend/config/settings.py`).

11. Transfer Ethereum to the next OKX subaccount, leaving an amount in the account within the `LEFT_AMOUNT` range (`src/okx/config/settings.py`).

12. Repeat from step 1.

There are also variables:

- `MAX_GAS` (`src/zklend/config/settings.py`) - maximum amount of gas per transaction.

- `RETRY_COUNT` (`src/zklend/config/settings.py`) - number of attempts to retry the transaction in case of an error.

- `RETRY_WAIT` (`src/zklend/config/settings.py`) - delay in seconds between retry attempts.

IMPORTANT: The Ethereum amount is always specified in wei, where 1 ETH = 10^18 wei https://eth-converter.com/

IMPORTANT: When the balance in the account becomes less than `LEFT_AMOUNT` (`src/okx/config/settings.py`), the script stops.

## Usage 🐍

Run the `main.py` script to initiate transactions. Make sure to fill in the necessary OKX addresses and Starknet private keys in the respective files.

```bash
python main.py
```
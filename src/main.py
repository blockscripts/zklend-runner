import ccxt
from okx.methods import get_balance, get_sub_list, transfer_to_main, withdraw
from okx.config.secrets import OKX_API_KEY
from okx.config.settings import SEND_WAIT, SEND_PERCENTAGE
from settings import RETRY_WAIT
from zklend.utils import print
from zklend.methods import get_address, main as zklend_main
from random import randrange
from time import sleep
import asyncio


with open("accounts/okx_addresses.txt", "r") as f:
    OKX_ADDRESSES = [int(address.strip(), 16) for address in f.readlines()]


with open("accounts/starknet_privkeys.txt", "r") as f:
    STARKNET_PRIVKEYS = [int(privkey.strip(), 16) for privkey in f.readlines()]


def main():
    if len(OKX_ADDRESSES) != len(STARKNET_PRIVKEYS):
        raise Exception("Number of OKX addresses and Starknet private keys must be the same")

    print("INITIATING\n")

    print("OKX ADDRESSES")
    for address in OKX_ADDRESSES:
        print(hex(address))
    print("=====================================\n")

    print("STARKNET PRIVKEYS")
    for privkey in STARKNET_PRIVKEYS:
        print(hex(privkey))
    print("=====================================\n")

    print("STARTING\n")

    okx_instance = ccxt.okex({
        'apiKey': OKX_API_KEY["API_KEY"],
        'secret': OKX_API_KEY["API_SECRET"],
        'password': OKX_API_KEY["PASSWORD"],
        'enableRateLimit': True,
    })
    for i in range(len(OKX_ADDRESSES)):
        while True:
            print(f"Wallet pair {i + 1}/{len(OKX_ADDRESSES)}")
            sleep_send = randrange(*SEND_WAIT)
            print(f'sleeping send for {sleep_send}s')
            sleep(sleep_send)
            okx_instance.load_markets()
            for sub_id in get_sub_list(okx_instance):
                transfer_to_main(okx_instance, sub_id, currency='ETH')
                sleep(1)
            balance = get_balance(okx_instance)
            print(f"current balance: {balance} ETH")
            if balance < 0.001:
                raise Exception(f"Not enough funds in main account: {balance} ETH")

            send_percent = randrange(*SEND_PERCENTAGE)
            print(f'sending {send_percent}% of balance')

            send_address = get_address(private_key=STARKNET_PRIVKEYS[i])
            print("to", hex(send_address))

            success = withdraw(okx_instance, hex(send_address), amount=balance*(send_percent / 100), fee_included=True)
            if not success:
                sleep_retry = randrange(*RETRY_WAIT)
                print(f"Amount less than MIN_SEND, retrying after {sleep_retry}s")
                sleep(sleep_retry)
                continue
            print("sleeping for 3 mins")
            sleep(3*60)  # wait until funds are sent to wallet
            asyncio.run(zklend_main(STARKNET_PRIVKEYS[i], OKX_ADDRESSES[i]))
            print("SUCCESS on Starknet wallet", hex(send_address))
            print("proceeding to next wallet")
            break
    print("SUCCESS for all wallets")


if __name__ == '__main__':
    main()

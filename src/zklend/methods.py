from starknet_py.contract import Contract
from starknet_py.hash.address import compute_address
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.account.account import Account
from starknet_py.net.client_models import Call
from starknet_py.net.client_errors import ClientError
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.models import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair
from .config.settings import (
    CAIRO_VERSION,
    STARKNET_RPC,
    STARKNET_ETH_ADDRESS,
    ZKLEND_ROUTER,
    ZKLEND_ETH_CONTRACT_ADDRESS,
    ARGENTX_PROXY_CLASS_HASH,
    ARGENTX_IMPLEMENTATION_CLASS_HASH_V0,
    ARGENTX_IMPLEMENTATION_CLASS_HASH,
    MAX_GAS,
    INIT_WAIT,
    ETH_THRESHOLD,
    DEPOSIT_WAIT,
    DEPOSIT_PERCENTAGE,
    WITHDRAW_WAIT,
    TRANSFER_WAIT,
    LEFT_AMOUNT,
)
import requests
from .utils import check_gas, retry, make_amount, print
from random import randrange
from json import load
from time import sleep
import aiohttp


if __name__ == "__main__":
    with open("config/erc20_abi.json", "r") as f:
        ERC20_ABI = load(f)
else:
    with open("zklend/config/erc20_abi.json", "r") as f:
        ERC20_ABI = load(f)


def get_class_hash():
    return ARGENTX_PROXY_CLASS_HASH if CAIRO_VERSION == 0 else ARGENTX_IMPLEMENTATION_CLASS_HASH


def get_address(key_pair=None, private_key=None):
    if not key_pair:
        key_pair = KeyPair.from_private_key(private_key)
    res = requests.get(
        f'https://recovery.braavos.app/pubkey-to-address/?network=mainnet-alpha&pubkey={hex(key_pair.public_key)}'
    )
    if res.status_code == 200:
        addresses = res.json()['address']
        if len(addresses) > 0:
            return int(addresses[0], 16)
    return compute_address(
        class_hash=ARGENTX_PROXY_CLASS_HASH,
        constructor_calldata=[
            ARGENTX_IMPLEMENTATION_CLASS_HASH_V0,
            get_selector_from_name("initialize"),
            2,
            key_pair.public_key,
            0
        ],
        salt=key_pair.public_key,
    ) if CAIRO_VERSION == 0 else compute_address(
        class_hash=ARGENTX_IMPLEMENTATION_CLASS_HASH,
        constructor_calldata=[key_pair.public_key, 0],
        salt=key_pair.public_key,
    )


def get_account(key_pair=None, private_key=None, session=None):
    if not key_pair:
        key_pair = KeyPair.from_private_key(private_key)
    return Account(
        address=get_address(key_pair=key_pair, private_key=private_key),
        client=FullNodeClient(
            STARKNET_RPC,
            session=session
        ),
        key_pair=key_pair,
        chain=StarknetChainId.MAINNET,
    )


async def get_balance(starknet_account):
    return (await Contract(
        address=STARKNET_ETH_ADDRESS,
        abi=ERC20_ABI,
        provider=starknet_account
    ).functions["balanceOf"].call(starknet_account.address)).balance


async def is_deployed(starknet_account):
    try:
        await starknet_account.get_nonce()
        return True
    except ClientError:
        return False


@retry
@check_gas
async def deploy(starknet_account, key_pair):
    account_deployment_result = await starknet_account.deploy_account(
        address=starknet_account.address,
        class_hash=get_class_hash(),
        salt=key_pair.public_key,
        key_pair=key_pair,
        client=starknet_account.client,
        chain=StarknetChainId.MAINNET,
        constructor_calldata=[key_pair.public_key, 0],
        auto_estimate=True,
    )
    await account_deployment_result.wait_for_acceptance()

    return account_deployment_result.account


@retry
@check_gas
async def deposit(starknet_account, amount):
    amount = make_amount(amount)

    await starknet_account.client.wait_for_tx(
        (await starknet_account.client.send_transaction(await starknet_account.sign_invoke_transaction(
            calls=[
                Contract(
                    address=STARKNET_ETH_ADDRESS,
                    abi=ERC20_ABI,
                    provider=starknet_account
                ).functions["approve"].prepare(
                    ZKLEND_ROUTER,
                    amount
                ),
                Call(
                    to_addr=ZKLEND_ROUTER,
                    selector=get_selector_from_name("deposit"),
                    calldata=[STARKNET_ETH_ADDRESS, amount],
                )
            ],
            auto_estimate=True,
            nonce=(await starknet_account.get_nonce())
        ))).transaction_hash,
        check_interval=10
    )


@retry
@check_gas
async def withdraw(starknet_account):
    if (await Contract(
        address=ZKLEND_ETH_CONTRACT_ADDRESS,
        abi=ERC20_ABI,
        provider=starknet_account
    ).functions["balanceOf"].call(starknet_account.address)).balance > 0:

        await starknet_account.client.wait_for_tx(
            (await starknet_account.client.send_transaction(await starknet_account.sign_invoke_transaction(
                    calls=[
                        Call(
                            to_addr=ZKLEND_ROUTER,
                            selector=get_selector_from_name("withdraw_all"),
                            calldata=[STARKNET_ETH_ADDRESS],
                        )
                    ],
                    auto_estimate=True,
                    nonce=(await starknet_account.get_nonce())
                )
            )).transaction_hash,
            check_interval=10
        )


@retry
@check_gas
async def transfer(starknet_account, to_address, amount):
    amount = make_amount(amount)

    transfer_data = Contract(
        address=STARKNET_ETH_ADDRESS,
        abi=ERC20_ABI,
        provider=starknet_account
    ).functions["transfer"].prepare(to_address, amount)

    await starknet_account.client.wait_for_tx(
        (await starknet_account.client.send_transaction(await starknet_account.sign_invoke_transaction(
            calls=[
                Call(
                    to_addr=STARKNET_ETH_ADDRESS,
                    selector=transfer_data.selector,
                    calldata=transfer_data.calldata
                )
            ],
            auto_estimate=True,
            nonce=(await starknet_account.get_nonce())
        ))).transaction_hash,
        check_interval=10
    )


async def main(private_key, transfer_address):
    aio_session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False)
    )
    starknet_account = get_account(private_key=private_key, session=aio_session)

    if not (await is_deployed(starknet_account)):
        print('not deployed')
        sleep_deploy = randrange(*INIT_WAIT)
        print(f'sleeping deployment for {sleep_deploy}s')
        sleep(sleep_deploy)
        starknet_account = (await deploy(starknet_account, KeyPair.from_private_key(private_key)))
    else:
        print('deployed')

    balance = await get_balance(starknet_account)
    print(f'received {balance / 10**18} ETH')

    reps = 1 + (balance < ETH_THRESHOLD)
    for _ in range(reps):

        sleep_deposit = randrange(*DEPOSIT_WAIT)
        print(f'sleeping deposit for {sleep_deposit}s')
        sleep(sleep_deposit)
        deposit_percent = randrange(*DEPOSIT_PERCENTAGE)
        print(f'depositing {deposit_percent}%')
        amount = deposit_percent * balance // 100
        await deposit(starknet_account, amount - (3 * reps) * MAX_GAS)  # ensure we have enough to withdraw and transfer

        sleep_withdraw = randrange(*WITHDRAW_WAIT)
        print(f'sleeping withdraw for {sleep_withdraw}s')
        sleep(sleep_withdraw)
        await withdraw(starknet_account)

    sleep_transfer = randrange(*TRANSFER_WAIT)
    print(f'sleeping transfer for {sleep_transfer}s')
    sleep(sleep_transfer)
    balance = await get_balance(starknet_account)
    if min(*LEFT_AMOUNT) > balance - MAX_GAS:
        return  # nothing to transfer
    if max(*LEFT_AMOUNT) > balance:
        # transfer almost all
        transfer_amount = randrange(min(*LEFT_AMOUNT), balance - MAX_GAS)
    else:
        transfer_amount = balance - randrange(*LEFT_AMOUNT)
        while transfer_amount - MAX_GAS < 0:
            transfer_amount = balance - randrange(*LEFT_AMOUNT)
    print(f'transferring back {transfer_amount / 10**18} ETH to', hex(transfer_address))
    await transfer(starknet_account, transfer_address, transfer_amount - MAX_GAS)
    await aio_session.close()

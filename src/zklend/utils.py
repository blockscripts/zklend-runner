from loguru import logger
from starknet_py.net.gateway_client import GatewayClient
from web3 import Web3
from .config.settings import MAX_GAS, GAS_WAIT, RETRY_COUNT, RETRY_WAIT
import random
import asyncio
from datetime import datetime
import builtins
import aiohttp
# from time import sleep


def retry(func):
    async def wrapper(*args, **kwargs):
        retries = 0
        while retries < RETRY_COUNT:
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Error | {e}")
                await asyncio.sleep(random.randrange(*RETRY_WAIT))
                retries += 1

    return wrapper


async def sleep(sleep_from: int, sleep_to: int):
    delay = random.randint(sleep_from, sleep_to)

    logger.info(f"💤 Sleep {delay} s.")
    await asyncio.sleep(delay)


async def wait_gas():
    logger.info("Get GWEI")

    aio_session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False)
    )

    client = GatewayClient("mainnet", aio_session)

    while True:
        block_data = await client.get_block("latest")
        gas = Web3.from_wei(block_data.gas_price, "wei")

        if gas > MAX_GAS:
            logger.info(f'Current GWEI: {gas} > {MAX_GAS}')
            await sleep(*GAS_WAIT)
        else:
            logger.success(f"GWEI is normal | current: {gas} < {MAX_GAS}")
            break

    await aio_session.close()


def check_gas(func):
    async def _wrapper(*args, **kwargs):
        await wait_gas()
        return await func(*args, **kwargs)
    return _wrapper


def make_amount(amount):
    # check if amount in ETH
    if amount < 10**12:
        # convert to wei
        amount *= 10**18
    return int(amount)


def print(*args, **kwargs):
    builtins.print(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], end=" | "
    )
    builtins.print(*args, **kwargs)

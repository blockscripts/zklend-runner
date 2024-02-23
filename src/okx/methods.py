from .config.settings import MIN_SEND

def get_sub_list(okx_instance):
    return [account['label'] for account in okx_instance.private_get_users_subaccount_list()['data']]


def get_sub_balance(okx_instance, sub_id, currency='ETH'):
    for _currency in okx_instance.private_get_asset_subaccount_balances({
        'subAcct': sub_id
    })['data']:
        if _currency['ccy'].lower() == currency.lower():
            return float(_currency['availBal'])
    return 0.0


def transfer_to_main(okx_instance, sub_id, amount=None, currency='ETH'):
    if amount is None:
        amount = get_sub_balance(okx_instance, sub_id, currency)
    if amount >= 0.001:
        okx_instance.private_post_asset_transfer({
            'ccy': currency.upper(),
            'amt': str(amount),
            'type': '2', 
            'from': '6',
            'to': '6',
            'subAcct': sub_id,
        })


def get_balance(okx_instance, currency='ETH'):
    for balance in okx_instance.private_get_asset_balances()['data']:
        if balance['ccy'].lower() == currency.lower():
            return float(balance['availBal'])


def get_withdrawal_fee(okx_instance, currency='ETH', network='Starknet'):
    return float(okx_instance.fetch_deposit_withdraw_fees([currency])[currency]['networks'][network]['withdraw']['fee'])


def withdraw(okx_instance, address, amount=None, currency='ETH', network='Starknet', fee_included=False):
    # if fee is already included, subtract it from the amount
    if not amount:
        amount = get_balance(okx_instance, currency)
        fee_included = True
    fee = get_withdrawal_fee(okx_instance)
    if fee_included:
        amount -= fee
    if amount >= MIN_SEND:
        okx_instance.withdraw(currency.upper(), amount, address,
            params={
                "toAddress": address,
                "chainName": network,
                "dest": 4,
                "fee": fee,
                "pwd": '-',
                "amt": amount,
                "network": network
            }
        )
        return True
    return False

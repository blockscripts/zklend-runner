from zklend.methods import get_address


with open("accounts/starknet_privkeys.txt", "r") as f:
    for privkey in [int(privkey.strip(), 16) for privkey in f.readlines()]:
        print(hex(get_address(private_key=privkey)))

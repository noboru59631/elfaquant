from mantle_executor import get_balances, w3, wmnt, account
mnt, usdt = get_balances()
wmnt_raw = wmnt.functions.balanceOf(account.address).call()
native = w3.eth.get_balance(account.address)
print(f"native MNT: {float(w3.from_wei(native, 'ether')):.6f}")
print(f"WMNT:       {float(w3.from_wei(wmnt_raw, 'ether')):.6f}")
print(f"USDT:       {usdt:.4f}")

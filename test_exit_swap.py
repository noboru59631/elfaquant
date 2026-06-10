from mantle_executor import execute_swap_wmnt_to_usdt, get_balances
mnt, usdt = get_balances()
print(f"before: MNT={mnt:.4f} USDT={usdt:.4f}")
tx = execute_swap_wmnt_to_usdt(0.000993)
print(f"tx: {tx}")
mnt2, usdt2 = get_balances()
print(f"after:  MNT={mnt2:.4f} USDT={usdt2:.4f}")

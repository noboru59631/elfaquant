"""fix_amount_and_restart.py - amount を 0.002 に更新して全策略をアクティブに戻す"""
import sqlite3

c = sqlite3.connect('registry.db')

# amount を 0.002 に更新（min_notional $100 以上を確保）
c.execute("UPDATE strategies SET amount = 0.002 WHERE amount < 0.002")
print(f"Updated {c.rowcount} rows: amount → 0.002")

# fired を active に戻す
c.execute("UPDATE strategies SET status = 'active' WHERE status = 'fired'")
print(f"Reset {c.rowcount} fired → active")

c.commit()

print("\n=== Final DB ===")
for row in c.execute("SELECT title, amount, status FROM strategies ORDER BY title"):
    print(f"  {row[0]:<30} amount={row[1]}  status={row[2]}")

c.close()
print("\nOK - ready to restart bot")

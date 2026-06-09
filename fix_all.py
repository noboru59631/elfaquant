import sqlite3
from datetime import datetime

c = sqlite3.connect('registry.db')

# fired -> active リセット
c.execute("UPDATE strategies SET status='active' WHERE status='fired'")
print('fired reset:', c.execute('SELECT changes()').fetchone()[0])

# RSI_BELOW_60 重複削除（RSI_BELOW_65だけ残す）
c.execute("DELETE FROM strategies WHERE title='RSI_BELOW_60'")
print('RSI_BELOW_60 deleted:', c.execute('SELECT changes()').fetchone()[0])

c.commit()
print('')
print('=== Final DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()

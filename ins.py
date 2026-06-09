import sqlite3
from datetime import datetime

c = sqlite3.connect('registry.db')
c.execute("UPDATE strategies SET status='active' WHERE status='fired'")
print('fired reset:', c.execute('SELECT changes()').fetchone()[0])

now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
row = ('91292be5-e977-40ba-a531-6e1c7ef7de11','RSI_BELOW_35','BTC 1H RSI below 35','{}','BTC_USDT_Perp','sell',0.02,'market',None,2,'GTC',0,500.0,3.5,1.0,'prod','active',now,now)
c.execute("INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
c.commit()
print('inserted RSI_BELOW_35')

for r in c.execute('SELECT title, status FROM strategies'):
    print(r)
c.close()

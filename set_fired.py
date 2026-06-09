import sqlite3
conn = sqlite3.connect('registry.db')
conn.execute("UPDATE strategies SET status='fired' WHERE query_id IN ('df9d80bd-f25d-40af-a743-a75de27e088b','55331a30-47a7-44b5-9682-2daaaa1f6f49')")
conn.commit()
print('OK - SHORT_NOW_1H and SHORT_SETUP_15m set to fired')
for r in conn.execute('SELECT title, status FROM strategies'):
    print(r)
conn.close()

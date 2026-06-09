import sqlite3
c = sqlite3.connect('registry.db')
c.execute("UPDATE strategies SET status='active' WHERE status='fired'")
c.commit()
print('OK - all fired → active')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()

import sqlite3
c = sqlite3.connect('registry.db')
c.execute("DELETE FROM strategies WHERE query_id='97404ca1-66ec-4f71-b286-d90c0d518459'")
c.execute("DELETE FROM strategies WHERE query_id='e7aad711-c2fb-4439-bb88-dddb61f5d0cd'")
c.commit()
print('deleted triggered queries')
for row in c.execute('SELECT query_id, title, status FROM strategies'):
    print(row)
c.close()

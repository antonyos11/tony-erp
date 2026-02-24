import sqlite3

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# حذف جميع القروض
cursor.execute("DELETE FROM accounting_loan")
conn.commit()

print(f"تم حذف {cursor.rowcount} قرض")

conn.close()

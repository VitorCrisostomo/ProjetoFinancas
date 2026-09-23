import sqlite3

# Conecta ao banco de dados
conn = sqlite3.connect('instance/mydatabase.db')
cursor = conn.cursor()

# Busca as informações da tabela 'user'
cursor.execute("PRAGMA table_info(user)")
colunas = cursor.fetchall()

print("As colunas da sua tabela 'user' são:")
for col in colunas:
    print(f"- {col[1]}")

conn.close()
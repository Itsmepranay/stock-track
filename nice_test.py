import snowflake.connector

conn = snowflake.connector.connect(
    account="rwuepbs-qg82440",
    user="PRANAYECOEDU",
    password="Windowsxp0080#",
)

print("Connected!")
conn.close()
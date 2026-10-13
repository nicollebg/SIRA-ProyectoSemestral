from database import engine

try:

    with engine.connect() as connection:

        resultado = connection.exec_driver_sql(
            "SELECT DATABASE(), VERSION()"
        )

        fila = resultado.fetchone()

        print("================================")
        print("CONEXIÓN EXITOSA")
        print("Base de datos:", fila[0])
        print("MySQL:", fila[1])
        print("================================")

except Exception as e:

    print("================================")
    print("ERROR DE CONEXIÓN")
    print(e)
    print("================================")
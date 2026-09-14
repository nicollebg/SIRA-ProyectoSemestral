from database import engine


try:
    with engine.connect() as connection:
        print("Conexion exitosa a MySQL")
except Exception as e:
    print("Error de conexion:")
    print(e)
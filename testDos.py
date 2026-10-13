from database import SessionLocal

try:

    with SessionLocal() as session:

        resultado = session.execute(
            __import__("sqlalchemy").text(
                "SELECT 1"
            )
        )

        print(resultado.scalar())

except Exception as e:

    print("ERROR:")
    print(e)
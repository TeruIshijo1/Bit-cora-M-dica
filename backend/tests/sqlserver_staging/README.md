# SQL Server STAGING/TEST

Este directorio queda reservado para pruebas de integración futuras contra una
instancia sintética de SQL Server. Su `conftest.py` exige `APP_ENV=test`, una
base cuyo nombre termine en `_test` y rechaza explícitamente `KH_HE`.

No hay conexión ni prueba automática contra SQL Server en FASE 3A.0. Los tests
unitarios continúan usando mocks.


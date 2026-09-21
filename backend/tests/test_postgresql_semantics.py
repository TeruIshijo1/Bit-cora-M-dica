from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

import database
import models


pytestmark = pytest.mark.postgresql


def test_suite_is_using_real_postgresql() -> None:
    assert database.engine.dialect.name == "postgresql"


def test_unique_index_is_enforced() -> None:
    with database.SessionLocal() as session:
        session.add(models.Usuario(username="duplicado", password_hash="x", rol="admin"))
        session.commit()
        session.add(models.Usuario(username="duplicado", password_hash="y", rol="rh"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_username_unique_index_exists_in_migrated_schema() -> None:
    indexes = inspect(database.engine).get_indexes("usuarios")
    username_index = next(index for index in indexes if index["name"] == "ix_usuarios_username")
    assert username_index["unique"] is True
    assert username_index["column_names"] == ["username"]


def test_foreign_key_is_enforced() -> None:
    with database.SessionLocal() as session:
        session.add(
            models.Paciente(
                nombre_completo="PACIENTE SINTETICO FK",
                num_habitacion="TEST-1",
                creado_por_id=999_999,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_not_null_constraint_is_enforced() -> None:
    with database.engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO documentos_verificacion_qr DEFAULT VALUES"))
        transaction.rollback()


def test_rollback_discards_writes() -> None:
    with database.SessionLocal() as session:
        session.add(models.Usuario(username="rollback", password_hash="x", rol="admin"))
        session.flush()
        session.rollback()

    with database.SessionLocal() as verification:
        assert verification.scalar(
            select(models.Usuario.id).where(models.Usuario.username == "rollback")
        ) is None


def test_uncommitted_data_is_hidden_from_another_connection() -> None:
    with database.engine.connect() as first, database.engine.connect() as second:
        first_tx = first.begin()
        first.execute(
            text(
                "INSERT INTO usuarios (username, password_hash, rol, activo) "
                "VALUES ('aislamiento', 'x', 'admin', true)"
            )
        )
        assert second.scalar(
            text("SELECT count(*) FROM usuarios WHERE username = 'aislamiento'")
        ) == 0
        first_tx.commit()
        assert second.scalar(
            text("SELECT count(*) FROM usuarios WHERE username = 'aislamiento'")
        ) == 1


def test_row_lock_blocks_a_second_writer() -> None:
    with database.engine.begin() as setup:
        setup.execute(
            text(
                "INSERT INTO usuarios (username, password_hash, rol, activo) "
                "VALUES ('bloqueado', 'x', 'admin', true)"
            )
        )

    with database.engine.connect() as locker, database.engine.connect() as contender:
        locker_tx = locker.begin()
        locker.execute(text("SELECT id FROM usuarios WHERE username = 'bloqueado' FOR UPDATE"))
        contender_tx = contender.begin()
        contender.execute(text("SET LOCAL lock_timeout = '250ms'"))
        with pytest.raises(DBAPIError):
            contender.execute(
                text("UPDATE usuarios SET rol = 'rh' WHERE username = 'bloqueado'")
            )
        contender_tx.rollback()
        locker_tx.rollback()


def test_simultaneous_transactions_preserve_uniqueness() -> None:
    barrier = Barrier(2)

    def insert_same_username() -> str:
        with database.SessionLocal() as session:
            session.add(
                models.Usuario(
                    username="carrera-unica",
                    password_hash="x",
                    rol="admin",
                    activo=True,
                )
            )
            barrier.wait(timeout=5)
            try:
                session.commit()
                return "committed"
            except IntegrityError:
                session.rollback()
                return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(lambda _: insert_same_username(), range(2)))

    assert outcomes == ["committed", "rejected"]
    with database.SessionLocal() as verification:
        assert verification.scalar(
            select(text("count(*)")).select_from(models.Usuario).where(
                models.Usuario.username == "carrera-unica"
            )
        ) == 1

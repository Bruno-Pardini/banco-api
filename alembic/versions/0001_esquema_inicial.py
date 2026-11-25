"""Esquema inicial del Banco (Paso 8): cliente, cuenta, codigo_rechazo, transaccion, movimiento.

Revision ID: 0001
Revises:
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MOTIVOS = [
    ("R01", "Cuenta origen inexistente o inactiva"),
    ("R02", "Cuenta destino inexistente, inactiva o, en una transferencia, igual a la origen"),
    ("R03", "Fondos insuficientes en la cuenta origen"),
    ("R04", "El titular no coincide con el registrado en la cuenta origen"),
    ("R05", "Error técnico al aplicar la operación; se revirtió sin afectar saldos"),
    ("R06", "Solicitud incompleta o con importe menor o igual a $0.00"),
]


def upgrade() -> None:
    op.create_table(
        "cliente",
        sa.Column("id_cliente", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("tipo_cliente", sa.String(9), nullable=False),
        sa.Column("rfc", sa.String(13), nullable=True),
        sa.Column("correo", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id_cliente", name="pk_cliente"),
        sa.UniqueConstraint("rfc", name="uq_cliente_rfc"),
        sa.CheckConstraint(
            "tipo_cliente IN ('HUESPED','EMPRESA','HOTEL','PROVEEDOR')", name="ck_cliente_tipo_cliente"
        ),
    )

    op.create_table(
        "cuenta",
        sa.Column("numero_cuenta", sa.CHAR(10), nullable=False),
        sa.Column("id_cliente", sa.Integer(), nullable=False),
        sa.Column("saldo", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("estatus", sa.String(8), server_default="ACTIVA", nullable=False),
        sa.Column("fecha_apertura", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.PrimaryKeyConstraint("numero_cuenta", name="pk_cuenta"),
        sa.ForeignKeyConstraint(
            ["id_cliente"], ["cliente.id_cliente"], name="fk_cuenta_id_cliente_cliente", ondelete="RESTRICT"
        ),
        sa.CheckConstraint("numero_cuenta ~ '^[0-9]{10}$'", name="ck_cuenta_numero_cuenta_10_digitos"),
        sa.CheckConstraint("saldo >= 0", name="ck_cuenta_saldo_no_negativo"),
        sa.CheckConstraint("estatus IN ('ACTIVA','INACTIVA')", name="ck_cuenta_estatus"),
    )
    op.create_index("ix_cuenta_id_cliente", "cuenta", ["id_cliente"])

    codigo = op.create_table(
        "codigo_rechazo",
        sa.Column("codigo", sa.CHAR(3), nullable=False),
        sa.Column("motivo", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("codigo", name="pk_codigo_rechazo"),
    )
    op.bulk_insert(codigo, [{"codigo": c, "motivo": m} for c, m in MOTIVOS])

    op.execute(sa.schema.CreateSequence(
        sa.Sequence("transaccion_folio_seq", start=1, minvalue=1, maxvalue=999999, cycle=False)
    ))

    op.create_table(
        "transaccion",
        sa.Column("folio_operacion", sa.CHAR(14), nullable=False),
        sa.Column("folio_solicitud", sa.String(20), nullable=True),
        sa.Column("sistema_solicitante", sa.CHAR(3), nullable=True),
        sa.Column("tipo_operacion", sa.String(13), nullable=True),
        sa.Column("cuenta_origen", sa.CHAR(10), nullable=True),
        sa.Column("cuenta_destino", sa.CHAR(10), nullable=True),
        sa.Column("importe", sa.Numeric(12, 2), nullable=True),
        sa.Column("concepto", sa.String(100), nullable=True),
        sa.Column("estatus", sa.String(9), nullable=False),
        sa.Column("codigo_rechazo", sa.CHAR(3), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(timezone=False), nullable=False),
        sa.Column("fecha_hora_solicitud", sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint("folio_operacion", name="pk_transaccion"),
        sa.UniqueConstraint("folio_solicitud", name="uq_transaccion_folio_solicitud"),
        sa.ForeignKeyConstraint(
            ["codigo_rechazo"], ["codigo_rechazo.codigo"],
            name="fk_transaccion_codigo_rechazo_codigo_rechazo", ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "sistema_solicitante IN ('RES','VST','VGS','SRE','SPA','GEE','GJA','CIO')",
            name="ck_transaccion_sistema_solicitante",
        ),
        sa.CheckConstraint(
            "tipo_operacion IN ('DEPOSITO','RETIRO','TRANSFERENCIA')", name="ck_transaccion_tipo_operacion"
        ),
        sa.CheckConstraint("estatus IN ('APROBADA','RECHAZADA')", name="ck_transaccion_estatus"),
        sa.CheckConstraint(
            "(estatus = 'APROBADA' AND codigo_rechazo IS NULL) OR "
            "(estatus = 'RECHAZADA' AND codigo_rechazo IS NOT NULL)",
            name="ck_transaccion_estatus_codigo",
        ),
        sa.CheckConstraint(
            "folio_operacion ~ '^OP-[0-9]{4}-[0-9]{6}$'", name="ck_transaccion_folio_operacion_formato"
        ),
    )
    op.create_index("ix_transaccion_fecha_hora", "transaccion", ["fecha_hora"])
    op.create_index("ix_transaccion_sistema_estatus", "transaccion", ["sistema_solicitante", "estatus"])
    op.create_index("ix_transaccion_cuenta_origen", "transaccion", ["cuenta_origen"])
    op.create_index("ix_transaccion_cuenta_destino", "transaccion", ["cuenta_destino"])

    op.create_table(
        "movimiento",
        sa.Column("folio_operacion", sa.CHAR(14), nullable=False),
        sa.Column("tipo_movimiento", sa.String(8), nullable=False),
        sa.Column("numero_cuenta", sa.CHAR(10), nullable=False),
        sa.Column("importe", sa.Numeric(12, 2), nullable=False),
        sa.Column("saldo_resultante", sa.Numeric(12, 2), nullable=False),
        sa.PrimaryKeyConstraint("folio_operacion", "tipo_movimiento", name="pk_movimiento"),
        sa.ForeignKeyConstraint(
            ["folio_operacion"], ["transaccion.folio_operacion"],
            name="fk_movimiento_folio_operacion_transaccion", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["numero_cuenta"], ["cuenta.numero_cuenta"],
            name="fk_movimiento_numero_cuenta_cuenta", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("tipo_movimiento IN ('RETIRO','DEPOSITO')", name="ck_movimiento_tipo_movimiento"),
        sa.CheckConstraint("importe > 0", name="ck_movimiento_importe_positivo"),
        sa.CheckConstraint("saldo_resultante >= 0", name="ck_movimiento_saldo_resultante_no_negativo"),
    )
    op.create_index("ix_movimiento_numero_cuenta", "movimiento", ["numero_cuenta"])


def downgrade() -> None:
    op.drop_table("movimiento")
    op.drop_table("transaccion")
    op.execute(sa.schema.DropSequence(sa.Sequence("transaccion_folio_seq")))
    op.drop_table("codigo_rechazo")
    op.drop_table("cuenta")
    op.drop_table("cliente")

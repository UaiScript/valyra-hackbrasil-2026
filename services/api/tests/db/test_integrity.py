from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, StatementError

from valyra.finance.models import Account, Category, ImportBatch, ImportRejection

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 11, 7, 18, tzinfo=UTC)


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("user", "name", None),
        ("account", "balance_cents", None),
        ("account", "user_id", uuid4()),
        ("batch", "file_name", None),
        ("batch", "account_id", uuid4()),
        ("batch", "status", "ready"),
        ("category", "slug", None),
        ("category", "kind", "other"),
    ],
)
def test_required_values_and_references(db_session, reference_rows, target, field, value):
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            setattr(reference_rows[target], field, value)
            db_session.flush()


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount_cents": 0},
        {"amount_cents": None},
        {"description": None},
        {"category_source": "unknown"},
        {"category_id": uuid4()},
        {"predicted_category_id": uuid4()},
        {"updated_at": NOW - timedelta(days=1), "created_at": NOW},
    ],
)
def test_invalid_transaction(db_session, insert_transaction, overrides):
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            insert_transaction(**overrides)


def test_database_stores_exact_bigint(db_session, insert_transaction):
    transaction = insert_transaction(amount_cents=9007199254740993)
    db_session.expire(transaction)
    assert transaction.amount_cents == 9007199254740993


def test_bulk_money_insert_rejects_float(db_session, reference_rows):
    from sqlalchemy.dialects.postgresql import insert

    with pytest.raises(StatementError, match="inteiro em centavos"):
        with db_session.begin_nested():
            db_session.execute(
                insert(Account).values(
                    user_id=reference_rows["user"].id,
                    name="Inválida",
                    balance_cents=10.5,
                    balance_as_of=date(2026, 11, 1),
                )
            )


def test_duplicate_hash_same_account_is_rejected(db_session, insert_transaction):
    insert_transaction(row_hash="same")
    with pytest.raises(IntegrityError) as caught:
        with db_session.begin_nested():
            insert_transaction(row_hash="same")
    assert caught.value.orig.diag.constraint_name == "uq_transactions_account_id_row_hash"


def test_same_hash_in_different_accounts(db_session, reference_rows, insert_transaction):
    insert_transaction(row_hash="same")
    account = Account(
        user_id=reference_rows["user"].id,
        name="Outra",
        balance_cents=0,
        balance_as_of=date(2026, 11, 1),
    )
    db_session.add(account)
    db_session.flush()
    batch = ImportBatch(account_id=account.id, file_name="outro.csv")
    db_session.add(batch)
    db_session.flush()
    second = insert_transaction(account_id=account.id, import_batch_id=batch.id, row_hash="same")
    assert second.account_id == account.id
    with pytest.raises(IntegrityError) as caught:
        with db_session.begin_nested():
            insert_transaction(account_id=account.id)
    assert (
        caught.value.orig.diag.constraint_name == "fk_transactions_import_batch_id_import_batches"
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"rows_total": -1},
        {"rows_imported": -1},
        {"rows_duplicated": -1},
        {"rows_rejected": -1},
        {"rows_total": 1, "rows_imported": 2},
        {"status": "completed", "rows_total": 1, "completed_at": NOW},
        {"status": "processing", "completed_at": NOW},
        {"status": "completed"},
        {"status": "failed"},
        {"status": "failed", "completed_at": NOW - timedelta(days=1)},
        {"rows_total": 2147483647, "rows_imported": 2147483647, "rows_duplicated": 2147483647},
    ],
)
def test_batch_counter_and_state_constraints(db_session, reference_rows, overrides):
    batch = ImportBatch(
        **(
            {"account_id": reference_rows["account"].id, "file_name": "x.csv", "created_at": NOW}
            | overrides
        )
    )
    with pytest.raises(IntegrityError) as caught:
        with db_session.begin_nested():
            db_session.add(batch)
            db_session.flush()
    assert caught.value.orig.sqlstate == "23514"  # CHECK, inclusive na soma promovida a BIGINT.


@pytest.mark.parametrize(
    "state,counts,completed",
    [
        ("processing", (3, 1, 0, 1), None),
        ("completed", (3, 1, 1, 1), NOW),
        ("completed", (0, 0, 0, 0), NOW),
        ("failed", (3, 1, 0, 0), NOW),
    ],
)
def test_valid_batch_states(db_session, reference_rows, state, counts, completed):
    total, imported, duplicated, rejected = counts
    batch = ImportBatch(
        account_id=reference_rows["account"].id,
        file_name="x.csv",
        status=state,
        rows_total=total,
        rows_imported=imported,
        rows_duplicated=duplicated,
        rows_rejected=rejected,
        created_at=NOW,
        completed_at=completed,
    )
    db_session.add(batch)
    db_session.flush()
    assert batch.id is not None


@pytest.mark.parametrize("field", ["category_confidence", "anomaly_score"])
@pytest.mark.parametrize("value", [None, Decimal("0"), Decimal("1")])
def test_optional_score_boundaries(insert_transaction, field, value):
    assert getattr(insert_transaction(**{field: value}), field) == value


@pytest.mark.parametrize("field", ["category_confidence", "anomaly_score"])
@pytest.mark.parametrize("value", [Decimal("-0.01"), Decimal("1.01")])
def test_out_of_range_scores(db_session, insert_transaction, field, value):
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            insert_transaction(**{field: value})


def test_timestamps_defaults_and_orm_update(db_session, reference_rows, insert_transaction):
    transaction = insert_transaction()
    assert transaction.created_at == transaction.updated_at
    assert transaction.created_at.utcoffset() == timedelta(0)
    old = datetime(2020, 1, 1, tzinfo=UTC)
    account = reference_rows["account"]
    account.created_at = account.updated_at = old
    db_session.flush()
    account.name = "Nome atualizado"
    db_session.flush()
    assert account.created_at == old and account.updated_at > old
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            account.updated_at = old - timedelta(days=1)
            db_session.flush()


def test_user_correction_keeps_original_prediction(db_session, insert_transaction):
    transaction = insert_transaction()
    original = transaction.predicted_category_id
    other = Category(slug="mercado", name="Mercado", kind="expense")
    db_session.add(other)
    db_session.flush()
    transaction.category_id = other.id
    transaction.category_source = "user"
    db_session.flush()
    assert transaction.predicted_category_id == original


@pytest.mark.parametrize("target", ["user", "account", "batch", "category"])
def test_referenced_rows_cannot_be_deleted(db_session, reference_rows, insert_transaction, target):
    insert_transaction()
    row = reference_rows[target]
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(delete(type(row)).where(type(row).id == row.id))


def test_predicted_category_is_also_restricted(db_session, insert_transaction):
    predicted = Category(slug="prevista", name="Prevista", kind="expense")
    db_session.add(predicted)
    db_session.flush()
    insert_transaction(predicted_category_id=predicted.id)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(delete(Category).where(Category.id == predicted.id))


def test_rejections_cascade_with_unreferenced_batch(db_session, reference_rows):
    rejection = ImportRejection(
        import_batch_id=reference_rows["batch"].id,
        line_number=2,
        reason="invalid_date",
        raw_line="inválida",
    )
    db_session.add(rejection)
    db_session.flush()
    db_session.execute(delete(ImportBatch).where(ImportBatch.id == reference_rows["batch"].id))
    assert db_session.scalar(select(func.count()).select_from(ImportRejection)) == 0


@pytest.mark.parametrize("line_number,reason", [(0, "invalid_date"), (2, None)])
def test_invalid_rejection(db_session, reference_rows, line_number, reason):
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                ImportRejection(
                    import_batch_id=reference_rows["batch"].id,
                    line_number=line_number,
                    reason=reason,
                    raw_line="inválida",
                )
            )
            db_session.flush()


def test_duplicate_rejection_line_is_rejected(db_session, reference_rows):
    values = dict(
        import_batch_id=reference_rows["batch"].id, line_number=2, reason="x", raw_line="x"
    )
    db_session.add(ImportRejection(**values))
    db_session.flush()
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(ImportRejection(**values))
            db_session.flush()

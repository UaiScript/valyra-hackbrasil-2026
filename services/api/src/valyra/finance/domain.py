"""Pure CSV import rules for Finance (Issue #13).

The upload byte limit belongs to the router; this module limits data records.
The header must match the three named columns in their contracted order.
Whitespace-only physical lines are blank; delimiter-only and quoted-empty
records are data. For multiline records, line_number is the first physical
line; raw_line retains internal newlines and removes only the final terminator.
Rejection precedence is column structure, date, description, then amount.

Malformed data records use wrong_column_count, as agreed for Issue #13.
An unterminated quoted record consumes the remaining input: guessing a new
record boundary would risk importing fragments of the rejected description.
The process's csv.field_size_limit is left unchanged (normally 128 KiB per
field). A record exceeding it is rejected as wrong_column_count, even within
the 1 MiB upload limit; this restriction was explicitly accepted for Issue #13.
Logical records are framed before csv.reader validates fields, so a reader
error cannot turn a later physical line inside a quoted field into a transaction.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from hashlib import sha256
from io import StringIO
from uuid import UUID

MAX_FILE_BYTES = 1_048_576
MAX_ROWS = 5000

_HEADER = ["date", "description", "amount"]
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_AMOUNT = re.compile(r"-?\d+(?:\.\d{1,2})?")
_MIN_REAIS = Decimal("-92233720368547758.08")
_MAX_REAIS = Decimal("92233720368547758.07")

CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("mercado", ("supermercado", "mercado", "atacadao", "hortifruti")),
    ("restaurantes", ("restaurante", "ifood", "lanchonete", "padaria")),
    ("transporte", ("uber", "99", "combustivel", "posto", "estacionamento")),
    ("moradia", ("aluguel", "condominio")),
    ("contas-e-servicos", ("energia", "cemig", "agua", "copasa", "internet", "telefone")),
    ("saude", ("farmacia", "drogaria", "hospital", "clinica")),
    ("educacao", ("escola", "faculdade", "curso", "livraria")),
    ("lazer", ("cinema", "show", "ingresso")),
    ("assinaturas", ("netflix", "spotify", "prime", "disney")),
    ("salario", ("salario", "folha")),
]


@dataclass(frozen=True)
class ParsedRow:
    line_number: int
    date: date
    description: str
    amount_cents: int


@dataclass(frozen=True)
class RejectedRow:
    line_number: int
    reason: str
    raw_line: str


@dataclass(frozen=True)
class ParseResult:
    rows: list[ParsedRow]
    rejected: list[RejectedRow]
    total: int


class CsvFormatError(Exception):
    """A file-level error with one of the codes registered in Issue #13."""

    code: str

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _without_terminator(text: str) -> str:
    if text.endswith("\r\n"):
        return text[:-2]
    if text.endswith(("\r", "\n")):
        return text[:-1]
    return text


def _csv_records(text: str) -> Iterator[tuple[int, str]]:
    """Frame records with the default CSV quote/delimiter rules, preserving text.

    Only quoted fields may cross physical lines. Quotes in an unquoted field
    are literal, doubled quotes escape a quote, and a character after a closing
    quote makes the record malformed. csv.reader(strict=True) still performs
    the actual parsing/validation; framing never modifies the field-size limit.
    """
    state = "start"
    first_line = 1
    parts: list[str] = []
    for line_number, line in enumerate(StringIO(text, newline=""), start=1):
        if not parts:
            first_line = line_number
        parts.append(line)
        for char in _without_terminator(line):
            if state == "quoted":
                if char == '"':
                    state = "closed"
            elif state == "closed":
                if char == '"':
                    state = "quoted"
                elif char == ",":
                    state = "start"
                else:
                    state = "malformed"
            elif state == "start":
                if char == '"':
                    state = "quoted"
                elif char != ",":
                    state = "unquoted"
            elif state == "unquoted" and char == ",":
                state = "start"
        if state != "quoted":
            yield first_line, "".join(parts)
            parts = []
            state = "start"
    if parts:
        yield first_line, "".join(parts)


def _parse_record(columns: list[str], line_number: int, raw: str) -> ParsedRow | RejectedRow:
    if len(columns) != 3:
        return RejectedRow(line_number, "wrong_column_count", raw)
    date_text, description, amount_text = columns
    if not _DATE.fullmatch(date_text):
        return RejectedRow(line_number, "invalid_date", raw)
    try:
        business_date = date.fromisoformat(date_text)
    except ValueError:
        return RejectedRow(line_number, "invalid_date", raw)
    if not description.strip():
        return RejectedRow(line_number, "empty_description", raw)
    if not _AMOUNT.fullmatch(amount_text):
        return RejectedRow(line_number, "invalid_amount", raw)
    amount = Decimal(amount_text)
    # Compare before multiplication: oversized coefficients must never be rounded.
    if not _MIN_REAIS <= amount <= _MAX_REAIS:
        return RejectedRow(line_number, "invalid_amount", raw)
    if amount == 0:
        return RejectedRow(line_number, "zero_amount", raw)
    # BIGINT cents need at most 19 significant digits. Do not inherit a caller's
    # reduced precision/exponent range or alter their Decimal context.
    with localcontext() as context:
        context.prec = 21
        context.Emax = 99
        context.Emin = -99
        amount_cents = int(amount * 100)
    return ParsedRow(line_number, business_date, description, amount_cents)


def parse_csv(content: bytes) -> ParseResult:
    """Validate CSV without IO, persistence, deduplication or categorization."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CsvFormatError("CSV_ENCODING") from error

    records = _csv_records(text)
    try:
        _, header_text = next(records)
        header = next(csv.reader(StringIO(header_text, newline=""), strict=True))
    except (StopIteration, csv.Error) as error:
        raise CsvFormatError("CSV_MISSING_COLUMNS") from error
    if [name.strip().lower() for name in header] != _HEADER:
        raise CsvFormatError("CSV_MISSING_COLUMNS")

    rows: list[ParsedRow] = []
    rejected: list[RejectedRow] = []
    total = 0
    for line_number, record in records:
        raw = _without_terminator(record)
        if not raw.strip():
            continue
        total += 1
        if total > MAX_ROWS:
            raise CsvFormatError("CSV_TOO_MANY_ROWS")
        try:
            columns = next(csv.reader(StringIO(record, newline=""), strict=True))
        except csv.Error:
            rejected.append(RejectedRow(line_number, "wrong_column_count", raw))
            continue
        result = _parse_record(columns, line_number, raw)
        if isinstance(result, ParsedRow):
            rows.append(result)
        else:
            rejected.append(result)
    return ParseResult(rows, rejected, total)


def normalize_description(text: str) -> str:
    """Remove diacritics, lowercase and collapse whitespace; keep punctuation."""
    decomposed = unicodedata.normalize("NFKD", text)
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unaccented.lower().split())


def compute_row_hashes(account_id: UUID, rows: list[ParsedRow]) -> list[str]:
    """Hash each row with a per-file occurrence counter, preserving repetitions."""
    occurrences: Counter[tuple[date, int, str]] = Counter()
    hashes: list[str] = []
    for row in rows:
        description = normalize_description(row.description)
        key = (row.date, row.amount_cents, description)
        occurrences[key] += 1
        preimage = (
            f"{account_id}|{row.date.isoformat()}|{row.amount_cents}|"
            f"{description}|{occurrences[key]}"
        )
        hashes.append(sha256(preimage.encode("utf-8")).hexdigest())
    return hashes


def categorize(description: str, amount_cents: int) -> str:
    """Return the first whole-word rule for the sign, or its fallback slug.

    Zero has no transaction sign and is already rejected by the CSV parser;
    a direct caller passing zero gets ValueError, not a new public error code.
    """
    if amount_cents == 0:
        raise ValueError("A transaction amount must not be zero")
    normalized = normalize_description(description)
    for slug, keywords in CATEGORY_RULES:
        if (slug == "salario") != (amount_cents > 0):
            continue
        if any(re.search(rf"\b{re.escape(keyword)}\b", normalized) for keyword in keywords):
            return slug
    return "outros" if amount_cents < 0 else "outras-receitas"

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { centsToInput, formatCents, formatIsoDate, formatMonth, formatScore, formatShortDate, parseReaisToCents, shiftMonth } from '../src/app/money.ts';

test('formatCents usa centavos inteiros sem float', () => {
  assert.equal(formatCents(500000), 'R$ 5.000,00');
  assert.equal(formatCents(-12990), '-R$ 129,90');
  assert.equal(formatCents(5), 'R$ 0,05');
  assert.equal(formatCents(0), 'R$ 0,00');
  assert.equal(formatCents(123456789), 'R$ 1.234.567,89');
  assert.throws(() => formatCents(10.5));
});

test('parseReaisToCents aceita o formato brasileiro', () => {
  assert.equal(parseReaisToCents('1.234,56'), 123456);
  assert.equal(parseReaisToCents('1234,5'), 123450);
  assert.equal(parseReaisToCents('-89,90'), -8990);
  assert.equal(parseReaisToCents('R$ 1500'), 150000);
  assert.equal(parseReaisToCents('0,07'), 7);
});

test('parseReaisToCents recusa entradas ambíguas ou fora da faixa', () => {
  for (const bad of ['', 'abc', '1,234', '12.34', '1.23,00', '99999999999999999999']) {
    assert.equal(parseReaisToCents(bad), null, bad);
  }
});

test('centsToInput e formatIsoDate', () => {
  assert.equal(centsToInput(421050), '4210,50');
  assert.equal(centsToInput(-8990), '-89,90');
  assert.equal(parseReaisToCents(centsToInput(123456789)), 123456789);
  assert.equal(formatIsoDate('2026-11-07'), '07/11/2026');
});

test('formatMonth, shiftMonth e formatShortDate não dependem de Date', () => {
  assert.equal(formatMonth('2026-10'), 'outubro de 2026');
  assert.equal(shiftMonth('2026-01', -1), '2025-12');
  assert.equal(shiftMonth('2026-11', 2), '2027-01');
  assert.equal(formatShortDate('2026-11-09'), '9 nov');
});

test('formatScore trunca em duas casas sem float', () => {
  assert.equal(formatScore('1.0000'), '1,00');
  assert.equal(formatScore('0.8125'), '0,81');
  assert.equal(formatScore('0'), '0,00');
});

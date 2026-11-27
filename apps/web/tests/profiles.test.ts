import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NEUTRAL_PROFILE, PROFILES, TICKER_MODES, byPriority, findProfile, isTickerMode } from '../src/app/profiles.ts';

// Os perfis são dados editáveis: este teste pega erro de digitação antes da demo.
test('cada perfil tem id único, três módulos distintos e um atalho por módulo', () => {
  assert.equal(new Set(PROFILES.map((p) => p.id)).size, PROFILES.length);
  for (const p of [...PROFILES, NEUTRAL_PROFILE]) {
    assert.deepEqual([...p.modules].sort(), ['ai', 'alpha', 'finance'], p.id);
    assert.deepEqual(p.shortcuts.map((s) => s.module).sort(), ['ai', 'alpha', 'finance'], p.id);
    assert.ok(isTickerMode(p.ticker), p.id);
  }
});

test('os perfis da demo mostram os três modos da faixa', () => {
  assert.deepEqual(PROFILES.map((p) => p.ticker).sort(), [...TICKER_MODES].sort());
});

test('perfil salvo que não existe mais volta para a experiência neutra', () => {
  assert.equal(findProfile(PROFILES[1].id), PROFILES[1]);
  assert.equal(findProfile('perfil-removido'), null);
  assert.equal(findProfile(null), null);
  assert.equal(isTickerMode('cripto'), false);
});

test('byPriority sobe os temas do perfil e mantém a ordem dos demais', () => {
  const keys = ['acoes', 'agro', 'alimentos', 'juros', 'renda'];
  assert.deepEqual(byPriority(keys, (k) => k, ['agro', 'juros']), ['agro', 'juros', 'acoes', 'alimentos', 'renda']);
  assert.deepEqual(byPriority(keys, (k) => k, []), keys);
});

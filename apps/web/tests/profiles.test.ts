import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { NEUTRAL_PROFILE, PROFILES, byPriority, findProfile, isTickerMode } from '../src/app/profiles.ts';

// Os perfis são dados editáveis: este teste pega erro de digitação antes da demo.
test('cada perfil tem id único, três módulos distintos e um atalho por módulo', () => {
  assert.equal(new Set(PROFILES.map((p) => p.id)).size, PROFILES.length);
  for (const p of [...PROFILES, NEUTRAL_PROFILE]) {
    assert.deepEqual([...p.modules].sort(), ['ai', 'alpha', 'finance'], p.id);
    assert.deepEqual(p.shortcuts.map((s) => s.module).sort(), ['ai', 'alpha', 'finance'], p.id);
    assert.ok(isTickerMode(p.ticker), p.id);
  }
});

// Perfil sem cliente na API abriria a conta vazia do usuário demo padrão, sem histórico.
test('cada perfil tem um cliente fictício com histórico na API', () => {
  const backend = readFileSync(new URL('../../../services/api/src/valyra/core/demo_profiles.py', import.meta.url), 'utf8');
  const keys = [...backend.matchAll(/^\s+"([a-z-]+)": UUID\(/gm)].map((m) => m[1]).sort();
  assert.deepEqual(PROFILES.map((p) => p.id).sort(), keys);
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

// As previsões de cada perfil moram na API; um id trocado só de um lado cairia no padrão.
test('cada perfil tem previsões próprias na API', () => {
  const backend = readFileSync(new URL('../../../services/api/src/valyra/alpha/forecast.py', import.meta.url), 'utf8');
  const block = backend.slice(backend.indexOf('PROFILE_SPECS'), backend.indexOf('DEFAULT_SPECS'));
  const keys = [...block.matchAll(/^\s+"([a-z-]+)": \(/gm)].map((m) => m[1]).sort();
  assert.deepEqual(PROFILES.map((p) => p.id).sort(), keys);
});

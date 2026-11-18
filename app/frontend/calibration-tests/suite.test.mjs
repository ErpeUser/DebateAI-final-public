import test from 'node:test';
import assert from 'node:assert/strict';
import * as core from '../public/calibration/core.mjs';

const sample = () => ({case_id: 'one', mode: 'hart', context: 'Welche Beobachtung belegt das?', candidates: [
  {id: 'model-one', text: 'Welche Beobachtung belegt das?'}, {id: 'model-two', text: 'Dafuer fehlt noch ein Beleg.'}
]});

test('suite importer exists and accepts the existing single-case format', () => {
  assert.equal(typeof core.validateBlindSuite, 'function');
  assert.equal(core.validateBlindSuite(sample()).length, 1);
});
test('bounded multi-case import supports both modes', () => {
  const a = sample(), b = {...sample(), mode: 'ueberzeugen'};
  assert.equal(core.validateBlindSuite({schema_version: 1, cases: [a,b]}).length, 2);
});
test('duplicate case/mode cannot be accidentally rated twice in one suite', () => {
  assert.throws(() => core.validateBlindSuite({schema_version: 1, cases: [sample(), sample()]}));
});
test('empty, oversized and unknown-schema suites are rejected', () => {
  for (const cases of [[], Array.from({length:101}, (_,i)=>({...sample(),case_id:String(i)}))]) {
    assert.throws(() => core.validateBlindSuite({schema_version:1,cases}));
  }
  assert.throws(() => core.validateBlindSuite({schema_version:2,cases:[sample()]}));
});
test('context is visible separately from candidate identities', () => {
  const trial = core.createBlindTrial(sample(), () => 0);
  assert.equal(trial.context, sample().context);
  assert.equal(trial.cards.some(c => 'id' in c), false);
});
test('mismatched candidate context hashes are rejected', () => {
  const value = sample(); value.context_sha256 = 'a'.repeat(64);
  value.candidates[0].context_sha256 = 'b'.repeat(64);
  assert.throws(() => core.validateBlindCase(value));
});
test('invalid hashes and non-text context are rejected', () => {
  for (const extra of [{context_sha256:'wrong'}, {context:{}}, {context:'x'.repeat(12001)}]) {
    assert.throws(() => core.validateBlindCase({...sample(),...extra}));
  }
});

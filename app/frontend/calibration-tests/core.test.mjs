import test from 'node:test';
import assert from 'node:assert/strict';
import { createBlindTrial, recordVote, validateBlindCase, formatPercent, Recorder } from '../public/calibration/core.mjs';
const fixture = {case_id:'case-1', mode:'hart', context_sha256:'a'.repeat(64), candidates:[{id:'model-1',text:'Welche Quelle belegt das?'},{id:'model-2',text:'Das ist nicht belegt.'}]};
test('blind labels have no identity before vote',()=>{
 const t=createBlindTrial(fixture,()=>1);
 assert.deepEqual(t.cards.map(x=>Object.keys(x).sort()),[['label','text'],['label','text']]);
 assert.equal(t.cards[0].text, fixture.candidates[1].text);
});
test('reverse randomized order maps vote to correct original ID',()=>{
 const t=createBlindTrial(fixture,()=>1);
 const v=recordVote(t,'A',{speakability:4,relevance:5});
 assert.equal(v.winner_id,'model-2');
 assert.equal(v.factual_status,'unverified');
});
test('tie does not invent winner',()=>assert.equal(recordVote(createBlindTrial(fixture,()=>0),'tie',{}).winner_id,null));
test('both bad does not invent winner',()=>assert.equal(recordVote(createBlindTrial(fixture,()=>0),'both_bad',{}).winner_id,null));
test('a trial cannot be rated twice',()=>{
 const t=createBlindTrial(fixture,()=>0);recordVote(t,'B',{});
 assert.throws(()=>recordVote(t,'A',{}));
});
test('invalid/duplicate candidates rejected',()=>{
 assert.throws(()=>validateBlindCase({...fixture,candidates:[{id:'x',text:'a'},{id:'x',text:'b'}]}));
 assert.throws(()=>validateBlindCase({...fixture,candidates:[{id:'x',text:'a'}]}));
});
test('unsafe numeric ratings rejected',()=>assert.throws(()=>recordVote(createBlindTrial(fixture,()=>0),'A',{relevance:NaN})));
test('WER >100% remains visible',()=>assert.equal(formatPercent(1.5),'150.0 %'));
test('undefined metric not displayed as zero',()=>assert.equal(formatPercent(null),'\u2014'));
test('late microphone permission after cancel releases tracks',async()=>{
 let resolve;let stopped=0;
 const media={getUserMedia:()=>new Promise(r=>resolve=r)};
 const recorder=new Recorder({mediaDevices:media, MediaRecorderClass:class {}});
 const start=recorder.start(); recorder.cancel();
 resolve({getTracks:()=>[{stop:()=>stopped++}]});await start;
 assert.equal(stopped,1);assert.equal(recorder.state,'idle');
});

class FakeMediaRecorder {
  static isTypeSupported(){return true;}
  constructor(){this.state='inactive';this.mimeType='audio/webm';}
  start(){this.state='recording';}
  stop(){this.state='inactive';queueMicrotask(()=>this.onstop?.());}
}
function mediaFixture(){return {getUserMedia:async()=>({getTracks:()=>[{stop(){}}]})};}
test('recorder error releases controls before notifying UI',async()=>{
 let stateAtError;
 const r=new Recorder({mediaDevices:mediaFixture(),MediaRecorderClass:FakeMediaRecorder,onError:()=>stateAtError=r.state});
 await r.start();r.recorder.onerror();
 assert.equal(stateAtError,'idle');assert.equal(r.state,'idle');
});
test('oversized recording cancels before notifying UI',async()=>{
 let stateAtError;
 const r=new Recorder({mediaDevices:mediaFixture(),MediaRecorderClass:FakeMediaRecorder,onError:()=>stateAtError=r.state});
 await r.start();r.recorder.ondataavailable({data:{size:16*1024*1024+1}});
 assert.equal(stateAtError,'idle');assert.equal(r.state,'idle');
});
test('empty recording still returns UI to idle',async()=>{
 let idleCalls=0;
 const r=new Recorder({mediaDevices:mediaFixture(),MediaRecorderClass:FakeMediaRecorder,onIdle:()=>idleCalls++});
 await r.start();r.stop();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(r.state,'idle');assert.equal(idleCalls,1);
});

import { Recorder, createBlindTrial, recordVote, validateBlindSuite, validateBlindImport, comparisonSummary, formatPercent } from './core.mjs';
import { createDesktopSession } from './session.mjs';
const desktopSession = createDesktopSession((...args) => fetch(...args));

const $ = id => document.getElementById(id);
const KEY = 'debate-ai.calibration.v1';
const MAX_BYTES = 16 * 1024 * 1024;
const PRESETS = [
  ['negation','Negationen','Ich stimme diesem Vorschlag nicht zu, weil die wichtigste Voraussetzung noch nicht erf\u00fcllt ist.','Achte besonders auf jedes nicht.'],
  ['numbers','Zahlen und Einheiten','Die Datei nennt 3,5 Prozent, nicht 35 Prozent. Das Budget betr\u00e4gt 1.250 Euro.','Ziffern und ausgeschriebene Zahlen k\u00f6nnen trotz gleicher Bedeutung WER erzeugen. Rohtext immer mitlesen.'],
  ['umlaut','Umlaute und Namen','Frau M\u00fcller begr\u00fc\u00dft Herrn J\u00e4ger in \u00d6sterreich und fragt nach den n\u00e4chsten Schritten.','Namen sind Testdaten, keine echten Personenangaben.'],
  ['short','Kurzer Einwand','Nein, das folgt daraus nicht.','Kurze Aussage mit etwas Stille davor und danach aufnehmen.'],
  ['question','Gegenfrage','Welche konkrete Beobachtung w\u00fcrde deine Behauptung widerlegen?','Frageintonation und Satzende vergleichen.'],
  ['correction','Selbstkorrektur','Der Termin ist am Dienstag, nein, ich korrigiere mich, am Donnerstag.','Die Selbstkorrektur darf nicht stillschweigend verschwinden.'],
  ['causality','Kausaler Einwand','Dass zwei Dinge gleichzeitig auftreten, beweist noch nicht, dass das eine das andere verursacht.','Ruhig und dann in einem zweiten Durchgang schneller sprechen.'],
  ['qualification','Einschr\u00e4nkung','In diesem Punkt stimme ich zu. Daraus folgt aber keine allgemeine Regel.','Zustimmung und Einschr\u00e4nkung m\u00fcssen beide erhalten bleiben.'],
  ['units','Einheiten','Wir vergleichen Milligramm mit Gramm und Sekunden mit Minuten, nicht dieselben Gr\u00f6\u00dfen.','Verwechslungen gesondert notieren.'],
  ['repeat','Echte Wiederholung','Das ist wichtig. Das ist wichtig. Bitte l\u00f6sche die Wiederholung nicht.','Wiederholung ist hier beabsichtigt.'],
  ['fast','Schnelle Rede','Wenn wir die Annahmen \u00e4ndern, m\u00fcssen wir auch die Schlussfolgerung neu pr\u00fcfen.','Einmal normal, einmal schnell. Jeweils getrennte Aufnahme, innerhalb eines Vergleichs derselbe Clip.'],
  ['silence','Stille / Halluzinationen','','Stille: 3 bis 5 Sekunden aufnehmen. WER ist hier nicht definiert; ausgegebene W\u00f6rter werden gez\u00e4hlt.'],
  ['custom','Eigener Testsatz','','Eigene Referenz exakt eintragen. Keine sensiblen Daten f\u00fcr einen allgemeinen Test verwenden.'],
];
const NAMES = {'local-whisper-base':'Whisper Base', 'local-parakeet-tdt-0.6b-v3':'Parakeet TDT v3', 'local-whisper-large-v3-turbo':'Whisper Large v3 Turbo'};
let blindCases = [], blindIndex = 0, blindGeneration = 0, importedEvidence = [], activeImport = null;
let clip = null, clipUrl = null, result = null, votes = [], trial = null, generation = 0, request = null, busy = false;
const report = () => ({schema_version:1, created_at:new Date().toISOString(), kind:'local_calibration', source_commit:null,
  audio_included:false, settings_changed:false, asr:result, votes, imported_suites:importedEvidence,
  limitations:['No Windows hardware or streaming proof is implied.', 'Human usefulness ratings are not factual truth labels.',
  'Imported candidate provenance must be checked independently.']});
function status(message, error=false) { $('status').textContent=message; $('status').classList.toggle('error',error); }
function element(tag, text, cls) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; }
function selectedModels() {return [...document.querySelectorAll('#model-options input:checked')].map(e=>e.value);}
function controls() {
  $('run').disabled=!clip || !selectedModels().length || busy || recorder.state!=='idle';
  $('record').disabled=busy || recorder.state!=='idle';
  $('stop').disabled=!['recording','requesting'].includes(recorder.state);
  $('cancel').disabled=!busy;
}
function persist() {
  if (!$('persist').checked) return;
  try { localStorage.setItem(KEY, JSON.stringify(report())); }
  catch { status('Browserspeicher nicht verf\u00fcgbar oder voll. Ergebnisse jetzt als JSON sichern.',true); }
}
function invalidate() {
  ++generation; request?.abort(); request=null; busy=false; result=null;
  $('results').replaceChildren(element('div','Referenz oder Aufnahme ge\u00e4ndert. Neu messen.','empty'));
  controls(); persist();
}
function setClip(blob, name) {
  if (blob.size > MAX_BYTES) {status('Datei ist gr\u00f6\u00dfer als 16 MiB.',true); return;}
  invalidate(); clip=new File([blob],name,{type:blob.type});
  if (clipUrl) URL.revokeObjectURL(clipUrl);
  clipUrl=URL.createObjectURL(blob);$('playback').src=clipUrl;$('clip-name').textContent=name;
  status('Clip bereit. Alle ausgew\u00e4hlten Modelle erhalten genau diese Aufnahme.');controls();
}
const recorder=new Recorder({
  onIdle:()=>controls(),
  onClip:blob=>{const extension=blob.type.includes('ogg')?'ogg':blob.type.includes('mp4')?'m4a':'webm';setClip(blob,`Aufnahme.${extension}`);},
  onError:error=>{status(error.message,true);controls();},
});
for(const [id,name] of PRESETS){const o=element('option',name);o.value=id;$('preset').append(o);}
function preset(){const p=PRESETS.find(p=>p[0]===$('preset').value);$('reference').value=p[2];$('case-note').textContent=p[3];invalidate();}
$('preset').addEventListener('change',preset);$('reference').addEventListener('input',invalidate);preset();

async function api(path, options={}) {
  const response=await desktopSession.fetch(`/api/calibration/${path}`,{credentials:'same-origin',cache:'no-store',...options});
  let payload;try{payload=await response.json();}catch{throw new Error('Backend liefert kein Diagnose-JSON. Anwendung und Paket-Integration pr\u00fcfen.');}
  if(!response.ok)throw new Error(typeof payload.detail==='string'?payload.detail:`Diagnose fehlgeschlagen (HTTP ${response.status}).`);
  return payload;
}
async function catalog(){
  try{
    const data=await api('catalog');$('model-options').replaceChildren();
    for(const model of data.models){
      const label=element('label',undefined,`model-option${model.cached&&data.runtime_available?'':' unavailable'}`);
      const input=document.createElement('input');input.type='checkbox';input.value=model.id;input.checked=!!(model.cached&&data.runtime_available);input.disabled=!model.cached||!data.runtime_available;
      input.addEventListener('change',controls);const text=element('span',NAMES[model.id]||model.id);
      text.append(element('small',model.cached?'Dateien vorhanden; Inferenz noch zu testen':'Nicht im lokalen Cache. Kein automatischer Download.'));
      label.append(input,text);$('model-options').append(label);
    }
    status(data.runtime_available?'Bereit. Lokal testen, bewusst bewerten.':'Lokale ASR-Laufzeit fehlt. Bestehende Anwendungseinrichtung pr\u00fcfen.',!data.runtime_available);
    controls();
  }catch(error){$('model-options').replaceChildren(element('p','Backend nicht verbunden. Blindbewertung und JSON-Export bleiben lokal nutzbar.','warning'));status(error.message,true);}
}
catalog();
$('devices').addEventListener('click',async()=>{
  try{
    if(!navigator.mediaDevices?.enumerateDevices)throw new Error('Ger\u00e4teauswahl nicht unterst\u00fctzt.');
    const devices=await navigator.mediaDevices.enumerateDevices();const selected=$('device').value;
    $('device').replaceChildren(Object.assign(element('option','Windows-/Browser-Standard'),{value:''}));
    for(const [i,device] of devices.filter(d=>d.kind==='audioinput').entries())$('device').append(Object.assign(element('option',device.label||`Mikrofon ${i+1}`),{value:device.deviceId}));
    if([...$('device').options].some(o=>o.value===selected))$('device').value=selected;
    status('Ger\u00e4te aktualisiert. Namen sind eventuell erst nach Mikrofonfreigabe sichtbar.');
  }catch(error){status(error.message,true);}
});
$('record').addEventListener('click',async()=>{
  try{
    const promise=recorder.start($('device').value);controls();
    await promise;controls();
    if(recorder.state==='recording')status('Aufnahme l\u00e4uft. Referenz sprechen und stoppen; automatischer Stopp nach 30 Sekunden.');
  }catch(error){status(error.name==='NotAllowedError'?'Mikrofonzugriff verweigert. Windows-/Browserfreigabe pr\u00fcfen oder Datei ausw\u00e4hlen.':error.message,true);controls();}
});
$('stop').addEventListener('click',()=>{recorder.stop();controls();});
$('audio-file').addEventListener('change',()=>{const f=$('audio-file').files?.[0];if(f){recorder.cancel();setClip(f,f.name);}});

function renderResult(data){
  $('results').replaceChildren();
  $('results').append(element('p',`${data.attempted_trials} Messversuche, ${data.failed_trials} fehlgeschlagen. Fehler bleiben im Nenner. Kleine Stichprobe, keine Rangliste.`,'hint'));
  for(const model of data.models){
    const card=element('article',undefined,'result-card');card.append(element('h3',NAMES[model.model_id]||model.model_id));
    const measured=model.trials.find(t=>t.status==='ok')||model.trials.find(t=>t.metrics)||model.trials[0];
    const m=measured?.metrics;const metrics=element('div',undefined,'metrics');
    const values=[['WER',formatPercent(m?.wer)],['CER',formatPercent(m?.cer)],['Median / Clip',model.latency_p50_seconds!=null?`${model.latency_p50_seconds.toFixed(2)} s`:'\u2014'],['RTF',measured?.real_time_factor!=null?measured.real_time_factor.toFixed(2):'\u2014']];
    for(const [label,value] of values){const v=element('div',undefined,'metric');v.append(element('strong',value),element('small',label));metrics.append(v);}
    card.append(metrics);
    for(const [index,t] of model.trials.entries()){
      card.append(element('p',`Messung ${index+1}: ${t.status==='ok'?'erfolgreich':`fehlgeschlagen (${t.reason||'ohne Ergebnis'})`}`,'hint'));
      if(t.text!==undefined&&t.text!==null)card.append(element('p',t.text||'(kein Text)','transcript'));
      if(t.metrics){const x=t.metrics;card.append(element('p',`Ersetzt: ${x.substitutions}; fehlt: ${x.deletions}; hinzugef\u00fcgt: ${x.insertions}; kritisch gelöscht: ${x.false_deletions ?? 0}.`,'hint'));
        if(x.hallucinated_words!==undefined&&x.hallucinated_words!==null)card.append(element('p',`Stille-Test: ${x.hallucinated_words} ausgegebene W\u00f6rter. WER nicht definiert.`,'warning'));
        if(JSON.stringify(x.critical_reference_tokens)!==JSON.stringify(x.critical_hypothesis_tokens))card.append(element('p',`Zahlen/Negationen abweichend: Referenz [${(x.critical_reference_tokens||[]).join(', ')}], erkannt [${(x.critical_hypothesis_tokens||[]).join(', ')}]. Manuell pr\u00fcfen.`,'warning'));
      }
    }
    $('results').append(card);
  }
}
$('run').addEventListener('click',async()=>{
  if(!clip||busy)return;const current=++generation;request=new AbortController();busy=true;controls();
  const body=new FormData();body.append('file',clip);body.append('reference',$('reference').value);body.append('model_ids',JSON.stringify(selectedModels()));body.append('repeats',$('repeats').value);
  status('Lokaler Vergleich l\u00e4uft. Modelle werden nacheinander gemessen; aktive Einstellungen bleiben unver\u00e4ndert.');
  try{
    const data=await api('asr',{method:'POST',body,signal:request.signal});
    if(current!==generation)return;result=data;renderResult(data);persist();status('Vergleich abgeschlossen. Texte und kritische W\u00f6rter pr\u00fcfen, nicht nur die Geschwindigkeit.');
  }catch(error){if(current===generation&&error.name!=='AbortError')status(error.message,true);}
  finally{if(current===generation){busy=false;request=null;controls();}}
});
$('cancel').addEventListener('click',()=>{
  ++generation;request?.abort();request=null;busy=false;controls();
  status('Anzeige abgebrochen. Native Arbeit kann weiterlaufen; der Server l\u00e4sst keinen \u00fcberlappenden Test zu.');
});

function loadBlind(value,isDemo=false){
  $('speakability').value='';$('relevance').value='';
  trial=createBlindTrial(value);$('blind-context').textContent=trial.context||'Kein Kontext mitgeliefert; Relevanz nur eingeschraenkt beurteilbar.'; $('next-case').disabled=true; $('identity').hidden=true;$('identity').textContent='';
  $('blind-cards').replaceChildren();
  for(const c of trial.cards){const article=element('article');article.append(element('b',`ANTWORT ${c.label}`),element('p',c.text));$('blind-cards').append(article);}
  $('blind-cards').hidden=false;$('rating-panel').hidden=false;
  document.querySelectorAll('[data-vote]').forEach(b=>b.disabled=false);
  $('blind-notice').textContent=isDemo?'DEMO: von Hand geschriebene Beispielantworten, keine Modellausgaben und kein Leistungsnachweis.':`Fall ${trial.caseId} | ${trial.mode==='hart'?'Hart':'\u00dcberzeugen'}. Identit\u00e4ten erst nach der Bewertung. Herkunft und gleichen Kontext separat pr\u00fcfen.`;
}
$('load-demo').addEventListener('click',()=>{$('comparison-summary').textContent='';++blindGeneration;activeImport=null;blindCases=[];blindIndex=0;$('case-progress').textContent='';loadBlind({case_id:'demo-causality',mode:'ueberzeugen',candidates:[
  {id:'demo-rueckfrage',text:'Die Beobachtung ist interessant. Woran erkennen wir, dass wirklich die Ursache und nicht nur ein Zusammenhang dahintersteckt?'},
  {id:'demo-einwand',text:'Gleichzeitigkeit allein belegt noch keine Ursache. Daf\u00fcr brauchen wir einen Vergleich, der andere Erkl\u00e4rungen ausschlie\u00dft.'},
]},true);});
$('blind-file').addEventListener('change',async()=>{
  const file=$('blind-file').files?.[0];if(!file)return;const current=++blindGeneration;
  try{
    if(file.size>524288)throw new Error('Vergleichsdatei darf hoechstens 512 KiB haben.');
    const text=await file.text();const value=JSON.parse(text);
    const cases=await validateBlindImport(value);
    if(current!==blindGeneration)return;
    const summary=comparisonSummary(value);
    const digest=crypto.subtle ? Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('') : null;
    if(current!==blindGeneration)return;
    activeImport=digest;
    const raw=value.provenance||{};
    const provenance={source_commit:typeof raw.source_commit==='string'&&/^[a-f0-9]{40}$/.test(raw.source_commit)?raw.source_commit:null,
      tracked_source_dirty:typeof raw.tracked_source_dirty==='boolean'?raw.tracked_source_dirty:null,
      measurement_path:value.kind==='production_replay_blind_suite'?'headless production replay':'user-supplied'};
    importedEvidence.push({import_sha256:digest,summary,provenance});importedEvidence=importedEvidence.slice(-100);
    blindCases=cases;blindIndex=0;
    if(cases.length){loadBlind(cases[0]);$('case-progress').textContent=`1 / ${cases.length}`;}
    else{trial=null;$('blind-cards').hidden=true;$('rating-panel').hidden=true;$('identity').hidden=true;$('next-case').disabled=true;$('case-progress').textContent='0 / 0';$('blind-context').textContent='';}
    $('comparison-summary').textContent=`${summary.attempted_pairs} Paare versucht; ${summary.votable_pairs} bewertbar; ${summary.failed_pairs} fehlgeschlagen. Fehler bleiben im Nenner.`;
    status(cases.length?'Produktionsvergleich geladen. Quelle, Last und Modellversionen separat pruefen.':'Kein bewertbares Antwortpaar. Fehlgeschlagene Versuche sind im Bericht enthalten.',!cases.length);persist();
  }
  catch(error){if(current===blindGeneration)status(error.message,true);}
});
for(const button of document.querySelectorAll('[data-vote]'))button.addEventListener('click',()=>{
  try{
    if(!trial)throw new Error('Zuerst einen Vergleich laden.');
    const ratings={};for(const key of ['speakability','relevance'])if($(key).value!=='')ratings[key]=Number($(key).value);
    const vote=recordVote(trial,button.dataset.vote,ratings);
    vote.import_sha256=activeImport;votes.push(vote);$('next-case').disabled=blindIndex+1>=blindCases.length;$('vote-count').textContent=`${votes.length} Bewertungen`;
    $('identity').textContent=`A: ${trial.identities[0].id} | B: ${trial.identities[1].id}. Entscheidung: ${vote.choice}. N\u00fctzlichkeitsfeedback, kein Faktenlabel.`;
    $('identity').hidden=false;document.querySelectorAll('[data-vote]').forEach(b=>b.disabled=true);persist();
    status('Bewertung erfasst. Kein Modell, Prompt oder Debattenprofil wurde umgestellt.');
  }catch(error){status(error.message,true);}
});
$('persist').addEventListener('change',()=>{
  if($('persist').checked)persist();
  else{try{localStorage.removeItem(KEY);}catch{}status('Browserspeicherung deaktiviert; nur der Arbeitsspeicher dieses Labors bleibt.');}
});
$('export').addEventListener('click',()=>{
  const blob=new Blob([JSON.stringify(report(),null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=`DebateAI-Kalibrierung-${new Date().toISOString().replace(/[:.]/g,'-')}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$('clear').addEventListener('click',()=>{
  recorder.cancel();invalidate();clip=null;votes=[];trial=null;importedEvidence=[];activeImport=null;$('comparison-summary').textContent='';++blindGeneration;blindCases=[];blindIndex=0;$('next-case').disabled=true;$('case-progress').textContent='';$('blind-context').textContent='';$('persist').checked=false;
  try{localStorage.removeItem(KEY);}catch{}
  if(clipUrl)URL.revokeObjectURL(clipUrl);clipUrl=null;$('playback').removeAttribute('src');$('playback').load();
  $('clip-name').textContent='Noch keine Aufnahme';$('vote-count').textContent='0 Bewertungen';
  $('blind-cards').hidden=true;$('rating-panel').hidden=true;$('identity').hidden=true;controls();
  status('Nur Labordaten zur\u00fcckgesetzt. Anwendungseinstellungen, Sitzungen und Modelle bleiben unver\u00e4ndert.');
});
try{
  const saved=JSON.parse(localStorage.getItem(KEY)||'null');
  if(saved?.schema_version===1&&Array.isArray(saved.votes)){
    importedEvidence=Array.isArray(saved.imported_suites)?saved.imported_suites.slice(-100):[];votes=saved.votes.slice(-1000);result=saved.asr||null;$('persist').checked=true;$('vote-count').textContent=`${votes.length} Bewertungen`;
    if(result?.models)renderResult(result);
  }
}catch{status('Gespeicherte Labordaten sind nicht lesbar. Ohne Wiederherstellung fortgesetzt.',true);}
window.addEventListener('pagehide',()=>{recorder.cancel();request?.abort();if(clipUrl)URL.revokeObjectURL(clipUrl);});

$('next-case').addEventListener('click',()=>{
  if(!trial?.voted || blindIndex+1>=blindCases.length)return;
  loadBlind(blindCases[++blindIndex]);$('case-progress').textContent=`${blindIndex+1} / ${blindCases.length}`;
});
window.addEventListener('message',event=>{
  if(event.origin!==location.origin || event.source!==window.parent || event.data?.type!=='debateai:lab-pause')return;
  recorder.cancel();++generation;request?.abort();request=null;busy=false;controls();
  status('Aufnahme und Anzeige angehalten. Ergebnisse bleiben im Labor; native Arbeit kann noch auslaufen.');
});
if(window.parent!==window){
  for(const link of document.querySelectorAll('a[href="/"]'))link.addEventListener('click',event=>{
    event.preventDefault();window.parent.postMessage({type:'debateai:lab-close'},location.origin==='null'?'*':location.origin);
  });
}

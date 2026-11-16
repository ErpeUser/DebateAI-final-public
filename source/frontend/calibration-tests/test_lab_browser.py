import functools
import http.server
import json
import pathlib
import threading
import unittest
import os
import shutil
from playwright.sync_api import sync_playwright

from browser_fixture import PUBLIC, load_calibration_modules

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(PUBLIC)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None, headless=True,
            args=['--no-sandbox', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'])
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/calibration.html'

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop(); cls.server.shutdown(); cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1440,'height':1000})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.page.set_default_timeout(5000)
        self.errors=[]; self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        # The host's Chromium enterprise policy blocks every navigation and real
        # capture. Do not disable it. Render the exact page in about:blank with
        # explicit fetch/storage/media fixtures. This is NOT a hardware test.
        html=(PUBLIC/'calibration.html').read_text(encoding='utf-8')
        import re
        html=re.sub(r'<link rel="stylesheet"[^>]+>', '', html)
        html=re.sub(r'<script[^>]+></script>', '', html)
        self.page.set_content(html)
        self.page.add_style_tag(path=str(PUBLIC/'calibration/lab.css'))
        self.page.evaluate(r"""() => {
          const store=new Map();
          Object.defineProperty(window,'localStorage',{value:{
            getItem:k=>store.get(k)??null, setItem:(k,v)=>store.set(k,String(v)), removeItem:k=>store.delete(k)
          }, configurable:true});
          window.__asrResponse={status:200,body:{models:[],attempted_trials:0,failed_trials:0}};
          window.__uploads=[];
          window.fetch=async (url, options={})=>{
            if(url==='/api/meta')return new Response('{}', {headers:{'X-DebateAI-Instance':'calibration-fixture'}});
            if(new Headers(options.headers).get('X-DebateAI-Instance')!=='calibration-fixture'){
              throw new Error('Calibration request did not use its bootstrapped desktop session.');
            }
            if(url==='/api/calibration/catalog')return new Response(JSON.stringify({runtime_available:true,local_only:true,models:[
              {id:'local-whisper-base',cached:true},{id:'local-parakeet-tdt-0.6b-v3',cached:true},{id:'local-whisper-large-v3-turbo',cached:false}]}),{status:200});
            if(url==='/api/calibration/status')return new Response(JSON.stringify({busy:false,runtime_busy:false}),{status:200});
            if(url==='/api/calibration/asr'){
              const file=options.body.get('file');
              window.__uploads.push({name:file.name, size:file.size, model_ids:options.body.get('model_ids')});
              return new Response(JSON.stringify(window.__asrResponse.body),{status:window.__asrResponse.status});
            }
            throw new Error('No network is allowed in this fixture.');
          };
          Object.defineProperty(navigator,'mediaDevices',{value:{
            enumerateDevices:async()=>[],
            getUserMedia:async()=>{
              const ctx=new AudioContext();const node=ctx.createOscillator();const dest=ctx.createMediaStreamDestination();
              node.connect(dest);node.start();window.__audioContext=ctx;
              return dest.stream;
            }
          },configurable:true});
        }""")
        load_calibration_modules(self.page)
        self.page.wait_for_selector('#model-options input')

    def clip(self):
        self.page.locator('#audio-file').set_input_files({'name':'fixture.wav','mimeType':'audio/wav','buffer':b'RIFFfixture'})

    def import_cases(self):
        cases=[{'case_id':str(i),'mode':'hart','context':f'Kontext {i}',
                'candidates':[{'id':f'a-{i}','text':f'Antwort a-{i}'},{'id':f'b-{i}','text':f'Antwort b-{i}'}]} for i in range(2)]
        self.page.locator('#blind-file').set_input_files({'name':'suite.json','mimeType':'application/json',
            'buffer':json.dumps({'schema_version':1,'cases':cases}).encode()})
        self.page.wait_for_function("document.querySelector('#case-progress').textContent==='1 / 2'")

    def test_suite_advances_only_after_vote(self):
        self.import_cases(); self.assertTrue(self.page.locator('#next-case').is_disabled())
        self.assertEqual(self.page.inner_text('#blind-context'),'Kontext 0')
        self.page.click('button[data-vote="tie"]'); self.page.click('#next-case')
        self.assertEqual(self.page.inner_text('#case-progress'),'2 / 2')
        self.assertEqual(self.page.inner_text('#blind-context'),'Kontext 1')
        self.assertFalse(self.page.locator('#identity').is_visible())
        self.assertTrue(self.page.locator('#next-case').is_disabled())

    def test_demo_cannot_advance_an_unrelated_imported_suite(self):
        self.import_cases(); self.page.click('#load-demo'); self.page.click('button[data-vote="A"]')
        self.assertTrue(self.page.locator('#next-case').is_disabled())
        self.assertEqual(self.page.inner_text('#case-progress'),'')

    def test_parent_pause_releases_recording_controls(self):
        self.page.click('#record'); self.page.wait_for_function("!document.querySelector('#stop').disabled")
        self.page.evaluate("window.dispatchEvent(new MessageEvent('message',{origin:location.origin,source:window.parent,data:{type:'debateai:lab-pause'}}))")
        self.assertFalse(self.page.locator('#record').is_disabled())
        self.assertTrue(self.page.locator('#stop').is_disabled())

    def test_page_loads_without_javascript_errors(self):
        self.page.wait_for_selector('#model-options input')
        self.assertIn('Kalibrierung', self.page.title())
        self.assertEqual(self.errors,[])

    def test_uncached_model_cannot_be_selected(self):
        self.assertTrue(self.page.locator('input[value="local-whisper-large-v3-turbo"]').is_disabled())

    def test_silence_preset_has_empty_reference(self):
        self.page.select_option('#preset','silence')
        self.assertEqual(self.page.input_value('#reference'),'')
        self.assertIn('Stille',self.page.inner_text('#case-note'))

    def test_blind_identity_hidden_until_vote(self):
        self.page.click('#load-demo')
        self.assertFalse(self.page.locator('#identity').is_visible())
        self.page.click('button[data-vote="A"]')
        self.assertTrue(self.page.locator('#identity').is_visible())
        self.assertIn('demo-',self.page.inner_text('#identity'))
        self.assertTrue(self.page.locator('button[data-vote="B"]').is_disabled())

    def test_both_bad_is_recorded(self):
        self.page.click('#load-demo'); self.page.click('button[data-vote="both_bad"]')
        self.assertIn('1',self.page.inner_text('#vote-count'))
        self.assertEqual(self.page.evaluate('localStorage.getItem("debate-ai.calibration.v1")'),None)

    def test_persistence_requires_opt_in(self):
        self.page.check('#persist'); self.page.click('#load-demo'); self.page.click('button[data-vote="tie"]')
        saved=json.loads(self.page.evaluate('localStorage.getItem("debate-ai.calibration.v1")'))
        self.assertEqual(saved['votes'][0]['winner_id'],None)
        self.assertNotIn('audio', saved)

    def test_export_is_json_and_has_no_audio(self):
        self.page.click('#load-demo');self.page.click('button[data-vote="A"]')
        with self.page.expect_download() as d:self.page.click('#export')
        content=json.loads(pathlib.Path(d.value.path()).read_text())
        self.assertEqual(content['schema_version'],1)
        self.assertFalse(content['audio_included'])
        self.assertEqual(len(content['votes']),1)

    def test_busy_error_is_visible(self):
        self.page.evaluate("window.__asrResponse={status:409,body:{detail:'Aktive Debatte zuerst beenden.'}}")
        self.clip();self.page.click('#run')
        self.page.wait_for_function("document.querySelector('#status').textContent.includes('Aktive Debatte')")

    def test_asr_result_and_same_file_upload(self):
        self.page.evaluate("""window.__asrResponse={status:200,body:{audio_seconds:1,attempted_trials:2,failed_trials:0,audio_sha256:'a'.repeat(64),models:[{
          model_id:'local-whisper-base',latency_p50_seconds:.2,trials:[{status:'ok',seconds:.2,text:'Ich stimme nicht zu.',real_time_factor:.2,
          metrics:{wer:.25,cer:.1,deletions:1,insertions:0,substitutions:0,critical_reference_tokens:['nicht'],critical_hypothesis_tokens:[]}}]}]}}""")
        self.clip();self.page.click('#run')
        self.page.wait_for_selector('#results .result-card')
        self.assertIn('25.0 %',self.page.inner_text('#results'))
        received=self.page.evaluate('window.__uploads')
        self.assertEqual(received[0]['name'],'fixture.wav')
        self.assertIn('local-parakeet-tdt-0.6b-v3',received[0]['model_ids'])

    def test_reference_edit_invalidates_displayed_result(self):
        self.page.evaluate("document.querySelector('#results').textContent='old-result'")
        self.page.fill('#reference','Neue Referenz')
        self.assertNotIn('old-result',self.page.inner_text('#results'))

    def test_malformed_blind_file_is_rejected(self):
        self.page.locator('#blind-file').set_input_files({'name':'wrong.json','mimeType':'application/json','buffer':b'{"candidates":[]}'})
        self.page.wait_for_function("document.querySelector('#status').textContent.includes('Erwartet')")

    def test_mobile_no_horizontal_overflow(self):
        self.page.set_viewport_size({'width':390,'height':844})
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))

    def test_browser_microphone_records_synthetic_device(self):
        self.page.click('#record')
        self.page.wait_for_function("document.querySelector('#stop').disabled === false")
        self.page.wait_for_timeout(750)
        self.page.click('#stop')
        self.page.wait_for_function("document.querySelector('#clip-name').textContent.includes('Aufnahme.')")
        self.assertFalse(self.page.locator('#run').is_disabled())

    def test_denied_microphone_is_visible(self):
        self.page.evaluate("() => { navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Permission denied','NotAllowedError'); }; }")
        self.page.click('#record')
        self.page.wait_for_function("document.querySelector('#status').textContent.includes('Mikrofonzugriff')")

if __name__ == '__main__':unittest.main()

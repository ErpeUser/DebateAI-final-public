"""Real DOM, explicit API/storage fixtures; not audio hardware acceptance."""
import json
import os
import shutil
from pathlib import Path
import re
import unittest
from playwright.sync_api import sync_playwright
from browser_fixture import PUBLIC, load_calibration_modules
class ImportEvidenceBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = cls.enterClassContext(sync_playwright())
        cls.browser = cls.pw.chromium.launch(
            executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,
            headless=True, args=['--no-sandbox'])
        cls.addClassCleanup(cls.browser.close)
    def setUp(self):
        self.context=self.browser.new_context();self.page=self.context.new_page();self.page.set_default_timeout(5000)
        self.addCleanup(self.context.close)
        html=re.sub(r'<link rel="stylesheet"[^>]+>|<script[^>]+></script>','',(PUBLIC/'calibration.html').read_text(encoding='utf-8'))
        self.page.set_content(html)
        self.page.evaluate('''() => {const store=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},configurable:true});window.fetch=async()=>new Response(JSON.stringify({runtime_available:false,models:[]}),{status:200});}''')
        load_calibration_modules(self.page)
    def upload(self,value):self.page.locator('#blind-file').set_input_files({'name':'experiment.json','mimeType':'application/json','buffer':json.dumps(value).encode()})
    def test_failed_experiment_summary_but_no_fake_vote(self):
        self.page.check('#persist');self.upload({'schema_version':1,'kind':'production_replay_blind_suite','cases':[],'failures':[{'case_id':'de-001','mode':'hart','errors':[{'candidate_id':'a','status':'failed'}]}],'summary':{'attempted_pairs':1,'votable_pairs':0,'failed_pairs':1,'attempted_candidates':2,'failed_candidates':1}})
        self.page.wait_for_function("document.querySelector('#comparison-summary').textContent.includes('1 fehlgeschlagen')")
        self.assertFalse(self.page.locator('#rating-panel').is_visible())
        saved=json.loads(self.page.evaluate('localStorage.getItem("debate-ai.calibration.v1")'));self.assertEqual(saved['imported_suites'][0]['summary']['failed_pairs'],1)
    def test_identity_hidden_until_vote(self):
        self.upload({'case_id':'c','mode':'hart','context':'Kontext','candidates':[{'id':'hidden-one','text':'Antwort eins'},{'id':'hidden-two','text':'Antwort zwei'}]})
        self.page.wait_for_selector('#blind-cards article');self.assertFalse(self.page.locator('#identity').is_visible());self.assertNotIn('hidden-one',self.page.locator('#blind-cards').inner_text())
        self.page.click('button[data-vote="tie"]');self.assertTrue(self.page.locator('#identity').is_visible())
    def test_unselected_ratings_not_fabricated(self):
        self.page.check('#persist');self.page.click('#load-demo');self.page.click('button[data-vote="A"]')
        saved=json.loads(self.page.evaluate('localStorage.getItem("debate-ai.calibration.v1")'));self.assertEqual(saved['votes'][0]['ratings'],{})
    def test_wrong_denominator_rejected(self):
        self.upload({'schema_version':1,'kind':'production_replay_blind_suite','cases':[],'failures':[],'summary':{'attempted_pairs':2,'votable_pairs':0,'failed_pairs':0,'attempted_candidates':4,'failed_candidates':0}})
        self.page.wait_for_function("document.querySelector('#status').classList.contains('error')");self.assertFalse(self.page.locator('#rating-panel').is_visible())
if __name__=='__main__':unittest.main()

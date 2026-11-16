"""Browser DOM checks. No real microphone, Windows runtime or model is exercised."""
import pathlib
import unittest
import os
import shutil
from playwright.sync_api import sync_playwright

PUBLIC=pathlib.Path(__file__).resolve().parents[1]/'public'

class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=sync_playwright().start()
        cls.browser=cls.p.chromium.launch(executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,headless=True,args=['--no-sandbox'])
    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.p.stop()
    def setUp(self):
        self.page=self.browser.new_page()
        self.page.set_default_timeout(5000)
        self.page.set_content('<main id="root"><input id="session" value="ongoing-call"></main>')
        self.page.evaluate('window.originalRoot=document.getElementById("root")')
    def tearDown(self): self.page.close()
    def install(self, search=''):
        source=(PUBLIC/'calibration/launcher.mjs').read_text()
        self.page.evaluate('([src,search])=>new Function("location",src)({search,origin:window.location.origin})',[source,search])
    def test_no_frame_or_permission_request_before_click(self):
        self.install(); self.assertEqual(self.page.locator('#debateai-lab-launch').count(),1)
        self.assertEqual(self.page.locator('iframe').count(),0)
    def test_overlay_has_no_launcher_but_main_debate_view_does(self):
        self.install('?desktop=1&view=debate-overlay'); self.assertEqual(self.page.locator('#debateai-lab-launch').count(),0)
        self.install('?desktop=1&view=debate'); self.assertEqual(self.page.locator('#debateai-lab-launch').count(),1)
    def test_main_call_tree_survives_open_and_close(self):
        self.install(); self.page.click('#debateai-lab-launch'); self.page.click('#debateai-lab-dialog button')
        self.assertTrue(self.page.evaluate('originalRoot===document.getElementById("root")'))
        self.assertEqual(self.page.input_value('#session'),'ongoing-call')
        self.assertFalse(self.page.locator('#debateai-lab-dialog').evaluate('(e)=>e.open'))
    def test_iframe_reused_for_existing_results(self):
        self.install(); self.page.click('#debateai-lab-launch')
        self.page.evaluate('window.savedFrame=document.querySelector("iframe")')
        self.page.click('#debateai-lab-dialog button'); self.page.click('#debateai-lab-launch')
        self.assertTrue(self.page.evaluate('savedFrame===document.querySelector("iframe")'))
    def test_forged_message_cannot_close_dialog(self):
        self.install(); self.page.click('#debateai-lab-launch')
        self.page.evaluate('window.dispatchEvent(new MessageEvent("message",{origin:location.origin,source:window,data:{type:"debateai:lab-close"}}))')
        self.assertTrue(self.page.locator('#debateai-lab-dialog').evaluate('(e)=>e.open'))
    def test_only_own_frame_may_close_dialog(self):
        self.install(); self.page.click('#debateai-lab-launch')
        self.page.evaluate('window.dispatchEvent(new MessageEvent("message",{origin:location.origin,source:document.querySelector("iframe").contentWindow,data:{type:"debateai:lab-close"}}))')
        self.assertFalse(self.page.locator('#debateai-lab-dialog').evaluate('(e)=>e.open'))
    def test_duplicate_install_does_not_duplicate_controls(self):
        self.install(); self.install(); self.assertEqual(self.page.locator('#debateai-lab-launch').count(),1)

if __name__=='__main__': unittest.main()

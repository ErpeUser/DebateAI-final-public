// This self-contained entry keeps the React live-call tree mounted.
// No model, network, microphone permission or settings change happens on load.
(() => {
  if ((new URLSearchParams(location.search).get('view') || '').includes('overlay') || document.getElementById('debateai-lab-dialog')) return;
  const launch = document.createElement('button');
  launch.id = 'debateai-lab-launch'; launch.type = 'button';
  launch.textContent = 'Testlabor'; launch.setAttribute('aria-haspopup', 'dialog');
  launch.setAttribute('aria-controls', 'debateai-lab-dialog');
  launch.title = 'DebateAI: Sprache und Antworten vergleichen';
  const dialog = document.createElement('dialog');
  dialog.id = 'debateai-lab-dialog'; dialog.setAttribute('aria-labelledby', 'debateai-lab-title');
  const header = document.createElement('header');
  const title = document.createElement('strong');
  title.id = 'debateai-lab-title'; title.textContent = 'DebateAI | Testlabor';
  const close = document.createElement('button'); close.type = 'button';
  close.textContent = 'Zur Debatte'; close.setAttribute('aria-label', 'Testlabor schliessen und zur Debatte');
  header.append(title, close); dialog.append(header);
  let frame = null;
  const messageOrigin = () => location.origin === 'null' ? '*' : location.origin;
  launch.addEventListener('click', () => {
    if (!frame) {
      frame = document.createElement('iframe');
      frame.title = 'Lokales DebateAI Kalibrierungslabor';
      frame.allow = 'microphone'; frame.src = '/calibration.html';
      dialog.append(frame);
    }
    if (!dialog.open) dialog.showModal();
    close.focus();
  });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    // Keep results in the frame, but release capture and abandon the UI waiter.
    // The backend retains ownership of any still-running native worker.
    frame?.contentWindow?.postMessage({type:'debateai:lab-pause'}, messageOrigin());
    launch.focus();
  });
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== frame?.contentWindow) return;
    if (event.data?.type === 'debateai:lab-close' && dialog.open) dialog.close();
  });
  document.body.append(launch, dialog);
})();

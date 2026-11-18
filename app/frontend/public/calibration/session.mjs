// Same-origin desktop authorization shared by the main window and its lab.
// Keep the token only in memory, never in URLs, storage, or exported reports.
export function createDesktopSession(fetcher, enabled = true) {
  const header = 'X-DebateAI-Instance';
  let token = '', bootstrap = null;
  function responseToken(response) {
    // Fetch combines repeated response headers with commas. Uvicorn and the
    // bootstrap guard may both send the same token; never echo the whole list.
    const values = (response.headers?.get?.(header) || '').split(',').map(value => value.trim());
    if (values.some(value => value !== values[0])) {
      throw new Error('Widerspruechliche Desktop-Sitzung. Anwendung neu starten.');
    }
    return values[0];
  }
  return {
    getToken: () => token,
    async fetch(input, options = {}) {
      if (enabled) {
        if (!bootstrap) {
          bootstrap = fetcher('/api/meta', {cache:'no-store', credentials:'same-origin'})
            .then(response => {
              if (!response.ok) throw new Error('Desktop-Verbindung konnte nicht hergestellt werden.');
              token = responseToken(response);
            }).catch(error => { bootstrap = null; throw error; });
        }
        await bootstrap;
      }
      const headers = new Headers(options.headers);
      if (token) headers.set(header, token);
      const response = await fetcher(input, {...options, headers});
      token = responseToken(response) || token;
      return response;
    },
  };
}

// Same-origin desktop authorization shared by the main window and its lab.
// Keep the token only in memory, never in URLs, storage, or exported reports.
export function createDesktopSession(fetcher, enabled = true) {
  const header = 'X-DebateAI-Instance';
  let token = '', bootstrap = null;
  return {
    getToken: () => token,
    async fetch(input, options = {}) {
      if (enabled) {
        if (!bootstrap) {
          bootstrap = fetcher('/api/meta', {cache:'no-store', credentials:'same-origin'})
            .then(response => {
              if (!response.ok) throw new Error('Desktop-Verbindung konnte nicht hergestellt werden.');
              token = response.headers?.get?.(header) || '';
            }).catch(error => { bootstrap = null; throw error; });
        }
        await bootstrap;
      }
      const headers = new Headers(options.headers);
      if (token) headers.set(header, token);
      const response = await fetcher(input, {...options, headers});
      token = response.headers?.get?.(header) || token;
      return response;
    },
  };
}

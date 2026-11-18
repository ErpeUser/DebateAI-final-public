export type OAuthWindow = {
  opener: unknown;
  location: { replace: (url: string) => void };
  focus: () => void;
  close: () => void;
};

export type OAuthWindowOpener = (
  url: string,
  target: string,
  features: string,
) => OAuthWindow | null;

export function reserveOAuthWindow(
  openWindow: OAuthWindowOpener = (url, target, features) => (
    window.open(url, target, features) as OAuthWindow | null
  ),
): OAuthWindow | null {
  try {
    return openWindow("about:blank", "_blank", "popup,width=760,height=820");
  } catch {
    // CSP, privacy settings, and embedded browsers can throw instead of
    // returning null. The caller still renders the manual authentication link.
    return null;
  }
}

export function navigateOAuthWindow(popup: OAuthWindow | null, url: string): boolean {
  if (!popup) return false;
  popup.opener = null;
  popup.location.replace(url);
  popup.focus();
  return true;
}

export function closeOAuthWindow(popup: OAuthWindow | null): void {
  try {
    popup?.close();
  } catch {
    // A manually closed or browser-blocked placeholder needs no cleanup.
  }
}

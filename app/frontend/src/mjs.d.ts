declare module "*.mjs" {
  export function shouldAcceptDebateOverlaySnapshot(
    current: unknown,
    next: unknown,
  ): boolean;
}

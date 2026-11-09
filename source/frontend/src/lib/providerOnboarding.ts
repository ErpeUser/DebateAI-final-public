// Pure setup-readiness logic behind the first-run provider onboarding
// (welcome checklist step 1 and the contextual API Keys setup card). Kept
// free of service imports so node --test can exercise it directly.

export interface ReadinessTranscription {
  ready: boolean;
  model_id: string;
  provider: string;
  reason: string;
}

// One agent joined to its selected model's registry entry. keyAvailable
// mirrors ModelInfo.key_available with absence treated as available.
export interface ReadinessAgentModel {
  agentName: string;
  enabled: boolean;
  modelId: string;
  provider: string;
  keyAvailable: boolean;
  available: boolean;
  runsLocally: boolean;
}

// Minimal structural slices of AgentConfig and ModelInfo, so callers pass
// their app types while node --test can exercise this module standalone.
export interface ReadinessAgentSource {
  name: string;
  enabled: boolean;
  model_id: string;
}

export interface ReadinessModelSource {
  id: string;
  provider: string;
  key_available?: boolean;
  runs_locally?: boolean;
}

export function toReadinessAgentModels(
  agents: ReadinessAgentSource[],
  models: ReadinessModelSource[]
): ReadinessAgentModel[] {
  return agents.map((a) => {
    const model = models.find((m) => m.id === a.model_id);
    return {
      agentName: a.name,
      enabled: a.enabled,
      modelId: a.model_id,
      provider: model?.provider ?? "",
      keyAvailable: model?.key_available !== false,
      available: Boolean(model),
      runsLocally: model?.runs_locally ?? model?.provider === "Local",
    };
  });
}

export interface SetupReadiness {
  ready: boolean;
  // Plain-language explanation of the first blocking gap; empty when ready.
  reason: string;
}

export function webProviderStartupNeedsAttention(
  providers: { available: boolean; ready: boolean }[]
): boolean {
  return providers.some((provider) => provider.available && !provider.ready);
}

// A workspace is ready only when the currently selected transcription and
// agent configuration can actually run -- not merely when some provider key
// exists.
export function setupReadiness(input: {
  localOnly: boolean;
  transcription: ReadinessTranscription | null;
  agentModels: ReadinessAgentModel[];
}): SetupReadiness {
  const t = input.transcription;
  if (!t) return { ready: false, reason: "Transkription wird geprüft ..." };
  if (!t.ready) {
    const reason =
      t.reason.trim() ||
      `Das ausgewählte Transkriptionsmodell (${t.model_id}) benötigt einen gültigen ` +
        `${t.provider}-API-Schlüssel. Hinterlege ihn unter Verbindungen, wechsle das ` +
        `Transkriptionsmodell oder aktiviere Privacy First für lokale Modelle.`;
    return { ready: false, reason };
  }

  const unselected = input.agentModels.filter((a) => a.enabled && !a.modelId);
  if (unselected.length > 0) {
    return {
      ready: false,
      reason:
        `${agentNames(unselected)} benötigen ein Modell. Wähle eines unter ` +
        "Einstellungen → Assistenten; „Empfohlen“ markiert einen guten Startpunkt.",
    };
  }

  const unavailable = input.agentModels.filter(
    (a) => a.enabled && a.modelId && !a.available
  );
  if (unavailable.length > 0) {
    return {
      ready: false,
      reason:
        `${agentNames(unavailable)} verwenden nicht mehr verfügbare Modelle. ` +
        "Wähle unter Einstellungen → Assistenten Ersatzmodelle aus.",
    };
  }

  const privacyBlocked = input.agentModels.filter(
    (a) => a.enabled && input.localOnly && !a.runsLocally
  );
  if (privacyBlocked.length > 0) {
    return {
      ready: false,
      reason:
        `Privacy First blockiert die ausgewählten Modelle für ${agentNames(privacyBlocked)}. ` +
        "Wähle unter Einstellungen → Assistenten lokale Modelle oder deaktiviere Privacy First.",
    };
  }

  const blocked = input.agentModels.filter(
    (a) => a.enabled && !a.runsLocally && !a.keyAvailable
  );
  if (blocked.length > 0) {
    const names = blocked
      .slice(0, 3)
      .map((a) => `${a.agentName} (${a.provider})`)
      .join(", ");
    const more = blocked.length > 3 ? ` und ${blocked.length - 3} weitere` : "";
    return {
      ready: false,
      reason:
        `Die Transkription ist bereit, aber für die ausgewählten Modelle von ${names}${more} ` +
        `fehlt ein gültiger API-Schlüssel. Hinterlege den Schlüssel des Anbieters oder wähle ` +
        `unter Einstellungen → Assistenten andere Modelle.`,
    };
  }

  return { ready: true, reason: "" };
}

function agentNames(agents: ReadinessAgentModel[]): string {
  const names = agents.slice(0, 3).map((agent) => agent.agentName).join(", ");
  return agents.length > 3 ? `${names} und ${agents.length - 3} weitere` : names;
}

// Which contextual state the onboarding setup card is in. "choose" shows the
// two-path decision, "partial" surfaces the mismatch explanation for a saved
// but insufficient key, "ready" offers the continue action.
export type OnboardingStage = "choose" | "partial" | "ready";

export function onboardingStage(input: {
  anyKeySaved: boolean;
  readiness: SetupReadiness;
}): OnboardingStage {
  if (input.readiness.ready) return "ready";
  return input.anyKeySaved ? "partial" : "choose";
}

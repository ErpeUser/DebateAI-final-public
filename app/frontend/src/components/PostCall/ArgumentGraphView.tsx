import type { ArgumentGraph, ArgumentNode } from "../../types";

interface ArgumentGraphViewProps {
  graph: ArgumentGraph | null;
  loading: boolean;
  error?: string | null;
}

function childrenFor(
  graph: ArgumentGraph,
  claimId: string,
  kind: ArgumentNode["kind"],
) {
  return graph.nodes.filter(
    (node) => node.claim_id === claimId && node.kind === kind,
  );
}

export default function ArgumentGraphView({
  graph,
  loading,
  error,
}: ArgumentGraphViewProps) {
  if (loading)
    return (
      <p
        role="status"
        className="rounded-xl bg-surface p-6 text-sm text-brand-gray"
      >
        Argumentbaum wird geladen …
      </p>
    );
  if (error)
    return (
      <p
        role="alert"
        className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700"
      >
        {error}
      </p>
    );

  const claims = (graph?.nodes ?? [])
    .filter((node) => node.kind === "claim")
    .sort((left, right) => right.revision - left.revision);
  if (!graph || claims.length === 0) {
    return (
      <p className="rounded-xl bg-surface p-6 text-sm text-brand-gray">
        Noch keine Argumente gespeichert.
      </p>
    );
  }

  return (
    <section aria-labelledby="argument-memory-title" className="space-y-3">
      <div>
        <h2
          id="argument-memory-title"
          className="font-display text-lg font-semibold text-brand-dark-gray"
        >
          Argumentgedächtnis
        </h2>
        <p className="mt-1 text-sm text-brand-gray">
          Gespeicherte Claims, Qwen-Antworten und offene Fragen – neueste
          Revision zuerst.
        </p>
      </div>
      {claims.map((claim) => {
        const responses = childrenFor(graph, claim.claim_id, "response");
        const points = childrenFor(graph, claim.claim_id, "point");
        const questions = childrenFor(graph, claim.claim_id, "question");
        const parent = graph.edges.find(
          (edge) =>
            edge.source_id === claim.id && edge.relation === "continues",
        );
        const parentClaim = parent
          ? graph.nodes.find((node) => node.id === parent.target_id)
          : null;
        return (
          <article
            key={claim.id}
            className="rounded-xl border border-brand-light-gray-1 bg-surface p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-wide text-brand-teal">
                Behauptung · Revision {claim.revision}
              </span>
              {claim.speaker_name && (
                <span className="text-xs text-brand-gray">
                  {claim.speaker_name}
                </span>
              )}
            </div>
            <p className="mt-2 font-body font-semibold text-brand-dark-gray">
              {claim.text}
            </p>
            {parentClaim && (
              <p className="mt-1 text-xs text-brand-gray">
                Setzt fort: {parentClaim.text}
              </p>
            )}
            {responses.map((response) => (
              <div
                key={response.id}
                className="mt-3 rounded-lg bg-brand-teal/5 p-3"
              >
                <p className="text-[10px] font-semibold uppercase tracking-wide text-brand-teal">
                  Qwen-Antwort
                </p>
                <p className="mt-1 text-sm text-brand-dark-gray">
                  {response.text}
                </p>
                {response.evidence_urls.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {response.evidence_urls.map((url, index) => (
                      <a
                        key={url}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-semibold text-brand-teal underline"
                      >
                        Quelle {index + 1}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {points.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-brand-gray">
                {points.map((point) => (
                  <li key={point.id}>{point.text}</li>
                ))}
              </ul>
            )}
            {questions.map((question) => (
              <p
                key={question.id}
                className="mt-3 border-l-2 border-brand-amber pl-3 text-sm text-brand-dark-gray"
              >
                <span className="font-semibold">Offene Frage:</span>{" "}
                {question.text}
              </p>
            ))}
          </article>
        );
      })}
    </section>
  );
}

export type LabSide = "A" | "B";
export type Rating = number | null;

export interface QualityRating {
  naturalness: Rating;
  strength: Rating;
  precision: Rating;
  source_honesty: Rating;
  usability: Rating;
  both_unsuitable: boolean;
}

export interface RaterRating extends Partial<QualityRating> {
  both_unsuitable?: boolean;
}

/** Stable blind ordering: the same run can be replayed, while a new seed can swap sides. */
export function blindOrder(runId: string, seed = 0): [LabSide, LabSide] {
  let hash = seed >>> 0;
  for (let index = 0; index < runId.length; index += 1) {
    hash = Math.imul(hash ^ runId.charCodeAt(index), 16777619) >>> 0;
  }
  return (hash & 1) === 0 ? ["A", "B"] : ["B", "A"];
}

export function isRatingComplete(rating: QualityRating): boolean {
  if (rating.both_unsuitable) return true;
  return [rating.naturalness, rating.strength, rating.precision, rating.source_honesty, rating.usability]
    .every((value) => typeof value === "number" && value >= 1 && value <= 5);
}

/** Agreement on a 1–5 scale, normalized to 0…1; ignores missing dimensions. */
export function raterAgreement(ratings: RaterRating[]): number | null {
  if (ratings.length < 2) return ratings.length === 1 ? 1 : null;
  const dimensions: Array<keyof QualityRating> = ["naturalness", "strength", "precision", "source_honesty", "usability"];
  const pairs: number[] = [];
  for (const dimension of dimensions) {
    const values = ratings
      .map((rating) => rating[dimension])
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
    if (values.length < 2) continue;
    const spread = Math.max(...values) - Math.min(...values);
    pairs.push(1 - spread / 4);
  }
  return pairs.length ? Math.max(0, pairs.reduce((sum, value) => sum + value, 0) / pairs.length) : null;
}

export function ratingLabel(value: number | null): string {
  return value == null ? "offen" : `${value}/5`;
}

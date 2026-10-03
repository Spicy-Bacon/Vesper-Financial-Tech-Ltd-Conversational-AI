import type { Question } from "./contracts";
// UI-only placeholders, not an approved workbook release. Namespaced option IDs
// deliberately cannot be confused with authoritative workbook option IDs.
const rows = [
  [
    "Maximum loss",
    "In this fictional example, what maximum loss would you feel able to accept?",
    "A maximum of £300",
    "My stated maximum loss is £300 in this fictional example.",
    "A maximum of £100",
    "My stated maximum loss is £100 in this fictional example.",
  ],
  [
    "Comfort with changes",
    "How would you feel if the value of this fictional investment went down?",
    "Some falls would feel manageable",
    "Some falls in value would feel manageable in this fictional example.",
    "Falls would worry me",
    "Falls in value would worry me in this fictional example.",
  ],
  [
    "Essential spending",
    "Could a loss affect your essential spending in this fictional example?",
    "Essentials would still be covered",
    "A loss would not affect essential spending in this fictional example.",
    "Essentials could be affected",
    "A loss could affect essential spending in this fictional example.",
  ],
  [
    "Accessible savings",
    "Do you have savings separate from this money, accessible within a few days, to cover essentials?",
    "Three months, separate and accessible",
    "In this fictional example, separate savings accessible within a few days cover three months of essentials.",
    "No separate accessible savings",
    "In this fictional example, there are no separate savings accessible within a few days for essential spending.",
  ],
  [
    "Borrowing",
    "How would you describe your borrowing in this fictional example?",
    "No outstanding borrowing",
    "There is no outstanding borrowing in this fictional example.",
    "I need to explain the borrowing",
    "My fictional borrowing circumstances need further explanation.",
  ],
  [
    "First possible withdrawal",
    "When might you first withdraw any of this money in this fictional example?",
    "First withdrawal in five years",
    "The first possible withdrawal of any of this fictional money is in five years.",
    "First withdrawal in two years",
    "The first possible withdrawal of any of this fictional money is in two years.",
  ],
];
export const questions: Question[] = rows.map((r, i) => ({
  question_id: `Q${i + 1}`,
  order: i + 1,
  label: r[0],
  text: r[1],
  safety: i >= 2 && i <= 4,
  options: [
    {
      option_id: `demo_Q${i + 1}_A`,
      label: r[2],
      playback: r[3],
      is_unsure: false,
    },
    {
      option_id: `demo_Q${i + 1}_B`,
      label: r[4],
      playback: r[5],
      is_unsure: false,
    },
    {
      option_id: `demo_Q${i + 1}_U`,
      label: "Not sure",
      playback: `I am unsure about ${r[0].toLowerCase()} in this fictional example.`,
      is_unsure: true,
    },
  ],
}));
export const scenarios = {
  clarification: "Demo scenario: ambiguous reply",
  explanation: "Demo scenario: explanation",
  support: "Demo scenario: offer support",
  refusal: "Demo scenario: refusal",
  fallback: "Demo scenario: model unavailable",
  out_of_scope: "Demo scenario: investment recommendation",
} as const;

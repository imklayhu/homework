import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { RemixTray } from "@/components/RemixTray";
import type { Insight } from "@/lib/types";


const insights: Insight[] = [
  { id: "i1", title: "观点一", explanation: "a", start_ms: 0, end_ms: 20_000, transcript_evidence: "a", visual_evidence: "", evidence_types: ["transcript"], confidence: .9, remix_reason: "a" },
  { id: "i2", title: "观点二", explanation: "b", start_ms: 20_000, end_ms: 50_000, transcript_evidence: "b", visual_evidence: "", evidence_types: ["transcript"], confidence: .8, remix_reason: "b" },
];


test("reorders selected insights and reports total duration", async () => {
  let latest = insights;
  const { rerender } = render(<RemixTray insights={latest} onChange={(next) => { latest = next; }} onGenerate={() => undefined} />);
  expect(screen.getByText("00:50")).toBeInTheDocument();

  await userEvent.click(screen.getByLabelText("上移观点二"));
  rerender(<RemixTray insights={latest} onChange={(next) => { latest = next; }} onGenerate={() => undefined} />);

  expect(screen.getAllByTestId("remix-item")[0]).toHaveTextContent("观点二");
});

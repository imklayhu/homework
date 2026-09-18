import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import Home from "@/app/page";
import ProductPage from "@/app/product/page";

test("opens the product brief and dashboard in new tabs", () => {
  render(<Home />);

  expect(screen.getByRole("link", { name: /产品方案/i })).toHaveAttribute("target", "_blank");
  expect(screen.getByRole("link", { name: /数据看板/i })).toHaveAttribute("target", "_blank");
});

test("presents the product story and roadmap", () => {
  render(<ProductPage />);

  expect(screen.getByRole("heading", { name: "把教育长视频变成可验证、可复用的内容资产" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "三阶段产品路线" })).toBeInTheDocument();
});

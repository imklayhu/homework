import { describe, expect, it } from "vitest";

import nextConfig from "../next.config";

describe("Next.js proxy configuration", () => {
  it("accepts request bodies larger than the 300 MB video upload limit", () => {
    expect(nextConfig.experimental?.proxyClientMaxBodySize).toBe("320mb");
  });
});

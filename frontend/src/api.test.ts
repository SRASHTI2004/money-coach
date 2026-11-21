import { describe, expect, it } from "vitest";
import { dateFmt, inr, inrShort, monthName } from "./api";

describe("Indian number formatting", () => {
  it("groups in lakhs and crores", () => {
    expect(inr(125000)).toBe("₹1,25,000");
    expect(inr(25000000)).toBe("₹2,50,00,000");
    expect(inr(950)).toBe("₹950");
  });
  it("handles sign, rounding and missing values", () => {
    expect(inr(-100000)).toBe("-₹1,00,000");
    expect(inr(2500.6, true)).toBe("+₹2,501");
    expect(inr(null)).toBe("-");
    expect(inr(undefined)).toBe("-");
  });
  it("compacts for charts", () => {
    expect(inrShort(180000)).toBe("₹1.8L");
    expect(inrShort(25000000)).toBe("₹2.5Cr");
    expect(inrShort(54000)).toBe("₹54k");
    expect(inrShort(4500)).toBe("₹4.5k");
    expect(inrShort(-32994)).toBe("-₹33k");
    expect(inrShort(640)).toBe("₹640");
  });
});

describe("date helpers", () => {
  it("formats dates and months for en-IN", () => {
    expect(monthName("2026-11")).toContain("2026");
    expect(dateFmt("2026-11-21")).toContain("2026");
    expect(dateFmt(null)).toBe("-");
  });
});

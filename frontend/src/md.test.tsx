import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Md } from "./parts";

describe("Md renderer", () => {
  it("renders bold, italics and bullet lists", () => {
    const html = renderToStaticMarkup(<Md text={"**Bold** and *soft*\n\n- one\n- two"} />);
    expect(html).toContain("<b>Bold</b>");
    expect(html).toContain("<em>soft</em>");
    expect(html).toContain("<li><span>one</span></li>");
  });
  it("never injects raw HTML", () => {
    const html = renderToStaticMarkup(<Md text={"<img src=x onerror=alert(1)>"} />);
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
  });
});

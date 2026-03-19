---
title: Mermaid and Pagebreak Test
version: 1.0
date: 2026-03-19
---

# Section 1: Mermaid Diagram

This section contains a Mermaid diagram to test the diagram generation feature.

```mermaid {png_width=3000}
graph TD;
    A[Start] --> B{Is it working?};
    B -- Yes --> C[Celebrate];
    B -- No --> D[Debug];
    D --> B;
```

\newpage

# Section 2: After Page Break

This section started after a page break. If the `pagebreak.lua` filter is working correctly, this header should appear on a new page in the generated ODT or PDF.

## Dynamic Content

The version of this document is {{ version }} and it was generated on {{ date }}.

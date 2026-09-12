# Named products and brand accents

Product names normally use the same [house style](style.md) as other components. A product name identifies the implementation; its shape and color identify its role in this diagram.

```python
api = d.node(40, 80, "Application API", "request handling")
store = d.cylinder(328, 72, "PostgreSQL", "relational data", family="green")
d.arrow(api.right, store.left, color="green", label="query", label_offset=12)
```

Use a brand accent when the user requests brand recognition or provides a logo/palette. Verify current identity assets when fidelity matters. Keep supplied assets inline, retain readable text, and leave the rest of the diagram consistent. Avoid inventing a tiny abbreviation badge in place of the product name.

Brand paint can trigger an advisory palette finding. Inspect that deliberate exception alongside the usual geometry and readability checks. Do not reduce labels below the 14/12 scale to fit an icon tile.

For Azure grouping and names, see [product-colors-azure.md](product-colors-azure.md).

# Azure diagrams

Use service names and the common [shape vocabulary](shape-vocabulary.md). A service can be a labeled process box or store; the diagram's meaning should remain readable without a logo.

- Label actual boundaries: subscription, resource group, region, VNet, or subnet. A resource group is not itself a network or trust boundary.
- Distinguish requests, data, identity, and deployment dependencies when those relationships matter.
- Use the user's service names and architecture. Do not infer placement or connectivity from a product category alone.
- If Azure icons are requested, use supplied or current official assets, inline them, and keep the surrounding 14/12 typography and spacing.

Example group, assuming an existing `Diagram`:

```python
d.container(40, 80, 520, 200, "Azure · application resource group")
api = d.node(64, 144, "App Service", "application API", w=176)
data = d.cylinder(336, 136, "Azure SQL", "application data", w=176)
d.arrow(api.right, data.left, color="green", label="query", label_offset=12)
```

The standard palette remains sufficient for cloud diagrams. Follow [brand-accent guidance](product-colors.md) when identity colors are part of the request.

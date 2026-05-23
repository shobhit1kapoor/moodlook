import { Router } from "express";

const router = Router();

const products = [
  {
    id: "hydrating-primer",
    name: "Cloud Veil Hydrating Primer",
    category: "hydrating primer",
    concern: "moisture",
    lookType: "glow",
    price: "$28",
    why: "Adds cushion under makeup so the base looks fresh and flexible."
  },
  {
    id: "brightening-concealer",
    name: "Wake-Up Brightening Concealer",
    category: "brightening concealer",
    concern: "dark_circle_v2",
    lookType: "tired",
    price: "$26",
    why: "Targets under-eye focus areas while keeping the finish smooth."
  },
  {
    id: "matte-primer",
    name: "Velvet Balance Matte Primer",
    category: "matte primer",
    concern: "oiliness",
    lookType: "professional",
    price: "$30",
    why: "Helps create a comfortable soft-matte base for longer wear."
  },
  {
    id: "green-primer",
    name: "Calm Tint Balancing Primer",
    category: "green tint corrector",
    concern: "redness",
    lookType: "everyday",
    price: "$29",
    why: "Creates a calm-looking base before foundation and blush."
  },
  {
    id: "smoothing-primer",
    name: "Soft Blur Smoothing Primer",
    category: "smoothing primer",
    concern: "texture",
    lookType: "date",
    price: "$31",
    why: "Blurs visible texture so makeup sits more evenly."
  },
  {
    id: "spot-concealer",
    name: "Clean Focus Spot Concealer",
    category: "non-comedogenic concealer",
    concern: "acne",
    lookType: "everyday",
    price: "$20",
    why: "Gives precise coverage where needed while avoiding a heavy full-face layer."
  }
];

router.get("/", (req, res) => {
  const { concern, mood, lookType } = req.query;
  const query = `${mood || ""} ${lookType || ""}`.toLowerCase();

  const filtered = products.filter((product) => {
    const concernMatch = concern ? product.concern === concern : true;
    const lookMatch = query ? query.includes(product.lookType) || product.lookType === "everyday" : true;
    return concernMatch && lookMatch;
  });

  res.json({
    products: filtered.length ? filtered : products
  });
});

export default router;

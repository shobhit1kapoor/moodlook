import { Plus, ShoppingBag } from "lucide-react";

export default function ProductRecommendations({ products }) {
  if (!products?.length) return null;

  return (
    <section id="products" className="card p-5 md:p-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="section-kicker">Retail journey</p>
          <h2 className="section-title">Shop this routine</h2>
          <p className="section-copy">Product cards turn the skin-aware look into a shoppable basket.</p>
        </div>
        <button className="btn-secondary" type="button">
          <ShoppingBag size={18} aria-hidden="true" />
          Shop this routine
        </button>
      </div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {products.map((product) => (
          <article key={product.id} className="flex min-h-[260px] flex-col rounded-3xl border border-white/80 bg-white/80 p-5 shadow-soft">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-plum">{product.category}</p>
            <h3 className="mt-3 text-lg font-bold leading-6 text-charcoal">{product.name}</h3>
            <p className="mt-3 flex-1 text-sm leading-6 text-charcoal/60">{product.why}</p>
            <div className="mt-5 flex items-center justify-between gap-3">
              <span className="text-lg font-bold text-charcoal">{product.price}</span>
              <button className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-charcoal text-white transition hover:bg-plum" type="button" aria-label={`Add ${product.name} to routine`}>
                <Plus size={18} aria-hidden="true" />
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

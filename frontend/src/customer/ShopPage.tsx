import { useEffect, useState } from "react";
import { api } from "../api/client";

type Product = { sku: string; name: string; price_minor: number; search_text?: string };

export function ShopPage() {
  const [products, setProducts] = useState<Product[]>([]); const [message, setMessage] = useState(""); const [loading, setLoading] = useState(true);
  useEffect(() => { api<{items: Product[]}>("/products").then((data) => setProducts(data.items)).catch((error: Error) => setMessage(error.message)).finally(() => setLoading(false)); }, []);
  async function order(sku: string) { try { const result = await api<{order_id: string}>("/orders", {method: "POST", headers: {"Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID()}, body: JSON.stringify({sku, quantity: 1})}); setMessage(`Order ${result.order_id} was queued successfully.`); } catch (error) { setMessage(error instanceof Error ? error.message : "Order could not be created."); } }
  return <main className="page"><div className="page-heading"><div><span className="section-label">Customer workload</span><h1>Workload Shop</h1><p>Create observable orders against the sample commerce service.</p></div><span className="record-count">{products.length} products</span></div>{message && <div className="notice" role="status">{message}</div>}{loading ? <div className="empty-state">Loading product catalog...</div> : <section className="product-grid">{products.map((product) => <article className="product-card" key={product.sku}><div className="product-visual">{product.name.slice(0, 1)}</div><div className="product-body"><span className="sku">{product.sku}</span><h2>{product.name}</h2><p>{product.search_text ?? "Observable sample commerce product"}</p><div className="product-footer"><strong>${(product.price_minor / 100).toFixed(2)}</strong><button onClick={() => order(product.sku)}>Create order</button></div></div></article>)}</section>}</main>;
}

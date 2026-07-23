import { useEffect, useState } from "react";
import { api } from "../api/client";

type Product = { sku: string; name: string; price_minor: number };

export function ShopPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [message, setMessage] = useState("");
  useEffect(() => { api<{items: Product[]}>("/products").then((data) => setProducts(data.items)).catch((error: Error) => setMessage(error.message)); }, []);
  async function order(sku: string) {
    const result = await api<{order_id: string}>("/orders", {method: "POST", headers: {"Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID()}, body: JSON.stringify({sku, quantity: 1})});
    setMessage(`Order ${result.order_id} queued`);
  }
  return <main><h1>Aegis Shop</h1><p>{message}</p><section className="grid">{products.map((product) => <article key={product.sku}><h2>{product.name}</h2><p>${(product.price_minor / 100).toFixed(2)}</p><button onClick={() => order(product.sku)}>Order</button></article>)}</section></main>;
}

const database = db.getSiblingDB("mydatabase");
const collection = database.getCollection("mycollection");
const products = database.getCollection("products");

if (collection.estimatedDocumentCount() === 0) {
  const batch = [];
  for (let i = 0; i < 50000; i += 1) {
    batch.push({
      searchField: `value-${i}`,
      payload: `Aegis seed document ${i}`,
      createdAt: new Date(),
    });
    if (batch.length === 1000) {
      collection.insertMany(batch);
      batch.length = 0;
    }
  }
  collection.insertOne({
    searchField: "needle",
    payload: "Target document used by the latency scenario",
    createdAt: new Date(),
  });
}

if (products.estimatedDocumentCount() === 0) {
  const batch = [];
  for (let i = 0; i < 50000; i += 1) {
    batch.push({
      product_id: `product-demo-${i}`,
      sku: `demo-${i}`,
      name: `Aegis Demo Product ${i}`,
      search_text: `aegis demo searchable item ${i}`,
      price_minor: 1000 + (i % 500),
      createdAt: new Date(),
    });
    if (batch.length === 1000) {
      products.insertMany(batch);
      batch.length = 0;
    }
  }
  products.insertMany([
    { product_id: "product-001", sku: "sku-001", name: "Aegis Notebook", search_text: "aegis notebook reliability", price_minor: 1299, createdAt: new Date() },
    { product_id: "product-002", sku: "sku-002", name: "Signal Mug", search_text: "signal mug observability", price_minor: 899, createdAt: new Date() },
  ]);
}

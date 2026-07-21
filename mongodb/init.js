const database = db.getSiblingDB("mydatabase");
const collection = database.getCollection("mycollection");

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

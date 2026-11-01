// Comprehensive integration test simulating the StockLens React frontend workflow
const BASE_URL = 'http://localhost:8000';

async function run() {
  console.log('='.repeat(60));
  console.log('StockLens Frontend -> Backend Complete Integration Test');
  console.log('='.repeat(60));

  // 1. Open product page: Fetch all products from GET /api/products
  console.log('\n[Step 1] Fetching product list (GET /api/products)...');
  const listRes = await fetch(`${BASE_URL}/api/products`);
  if (!listRes.ok) throw new Error(`Failed to list products: ${listRes.status}`);
  const products = await listRes.json();
  console.log(`✓ Received ${products.length} products from PostgreSQL.`);
  console.log('  First product in list:', JSON.stringify(products[0]));
  if (products.length === 0) throw new Error('Expected products in database');

  // Select a product to edit
  const target = products[0];
  const targetId = target.id;
  const originalName = target.name;
  const originalQty = target.quantity;
  const originalPrice = target.unit_price;
  console.log(`\n[Step 2] Selected product: ID ${targetId} ("${originalName}")`);

  // 2. Load current information: GET /api/products/{id}
  console.log(`\n[Step 3] Loading current details for product ${targetId}...`);
  const getRes = await fetch(`${BASE_URL}/api/products/${targetId}`);
  if (!getRes.ok) throw new Error(`Failed to get product: ${getRes.status}`);
  const current = await getRes.json();
  console.log('✓ Loaded details:', current);
  if (current.id !== targetId || current.name !== originalName) {
    throw new Error('Loaded product details do not match selected item');
  }

  // 3. Edit product: Prepare updated form data
  const updatedName = `${originalName} (Updated By Owner)`;
  const updatedQty = originalQty + 5;
  const updatedPrice = Number((originalPrice + 0.50).toFixed(2));
  console.log(`\n[Step 4] Sending PUT /api/products/${targetId} with updated fields:`);
  console.log(`  Name: "${updatedName}"`);
  console.log(`  Quantity: ${updatedQty}`);
  console.log(`  Unit Price: ${updatedPrice}`);

  const putRes = await fetch(`${BASE_URL}/api/products/${targetId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: updatedName,
      quantity: updatedQty,
      unit_price: updatedPrice,
      expiration_date: current.expiration_date || '',
      alternative_names: current.alternative_names || [],
    }),
  });

  if (!putRes.ok) {
    const err = await putRes.json();
    throw new Error(`PUT failed (${putRes.status}): ${JSON.stringify(err)}`);
  }
  const updated = await putRes.json();
  console.log('✓ Successfully received updated product response:');
  console.log(' ', updated);

  if (updated.name !== updatedName || updated.quantity !== updatedQty || updated.unit_price !== updatedPrice) {
    throw new Error('Updated product values do not match submitted values');
  }

  // 4. Update product list: Verify GET /api/products displays the updated values
  console.log('\n[Step 5] Re-fetching product list to verify update reflected in UI...');
  const refreshedRes = await fetch(`${BASE_URL}/api/products`);
  const refreshedList = await refreshedRes.json();
  const found = refreshedList.find((p) => p.id === targetId);
  if (!found) throw new Error(`Product ${targetId} disappeared from product list!`);
  if (found.name !== updatedName || found.quantity !== updatedQty || found.unit_price !== updatedPrice) {
    throw new Error(`Product in list does not show updated values! Found: ${JSON.stringify(found)}`);
  }
  console.log('✓ Product list verified! Product shows new name, quantity, and price.');

  // 5. Test Frontend Error Handling: Empty name
  console.log('\n[Step 6] Testing validation error: empty name...');
  const emptyNameRes = await fetch(`${BASE_URL}/api/products/${targetId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: '   ' }),
  });
  if (emptyNameRes.status !== 422) throw new Error(`Expected 422 for empty name, got ${emptyNameRes.status}`);
  const emptyNameErr = await emptyNameRes.json();
  console.log('✓ Empty name correctly rejected with 422:', emptyNameErr.detail?.[0]?.msg || emptyNameErr.detail);

  // 6. Test Frontend Error Handling: Negative quantity
  console.log('\n[Step 7] Testing validation error: negative quantity...');
  const negQtyRes = await fetch(`${BASE_URL}/api/products/${targetId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity: -3 }),
  });
  if (negQtyRes.status !== 422) throw new Error(`Expected 422 for negative quantity, got ${negQtyRes.status}`);
  const negQtyErr = await negQtyRes.json();
  console.log('✓ Negative quantity correctly rejected with 422:', negQtyErr.detail?.[0]?.msg || negQtyErr.detail);

  // 7. Test Frontend Error Handling: Nonexistent product ID
  console.log('\n[Step 8] Testing error handling: nonexistent product ID 999999...');
  const notFoundRes = await fetch(`${BASE_URL}/api/products/999999`);
  if (notFoundRes.status !== 404) throw new Error(`Expected 404 for nonexistent product, got ${notFoundRes.status}`);
  const notFoundErr = await notFoundRes.json();
  console.log('✓ Nonexistent product correctly returned 404:', notFoundErr.detail);

  // 8. Revert the test update back to original values
  console.log(`\n[Step 9] Restoring original product values...`);
  await fetch(`${BASE_URL}/api/products/${targetId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: originalName,
      quantity: originalQty,
      unit_price: originalPrice,
    }),
  });
  console.log('✓ Original values restored in PostgreSQL.');

  console.log('\n' + '='.repeat(60));
  console.log('ALL FRONTEND -> BACKEND WORKFLOW TESTS PASSED SUCCESSFULLY!');
  console.log('='.repeat(60));
}

run().catch((err) => {
  console.error('\n[TEST FAILED]:', err);
  process.exit(1);
});

document.addEventListener('DOMContentLoaded', () => {
    // Initial data load
    loadAllData();

    // Event Listeners
    document.getElementById('refreshBtn')?.addEventListener('click', loadAllData);
    document.getElementById('addProductForm')?.addEventListener('submit', handleAddProduct);
    document.getElementById('restockForm')?.addEventListener('submit', handleRestock);
    document.getElementById('expenseForm')?.addEventListener('submit', handleAddExpense);
    document.getElementById('editProductForm')?.addEventListener('submit', handleEditProduct);
    document.getElementById('submitChecklistBtn')?.addEventListener('click', handleSubmitChecklist);
});

// Centralized Data Refresh
async function loadAllData() {
    await Promise.all([
        loadSummary(),
        loadProducts(),
        loadSalesHistory(),
        loadExpenses(),
        loadDailySummary()
    ]);
}

// Format Currency
function formatNaira(amount) {
    return '₦' + Number(amount || 0).toLocaleString('en-NG', { minimumFractionDigits: 0 });
}

// Helper to handle API responses safely using relative routes
async function safeFetch(url, options = {}) {
    try {
        const res = await fetch(url, options);
        if (!res.ok) {
            console.error(`API Error (${res.status}): ${url}`);
            return null;
        }
        return await res.json();
    } catch (err) {
        console.error(`Fetch exception for ${url}:`, err);
        return null;
    }
}

// 1. Fetch Metrics Summary
async function loadSummary() {
    const data = await safeFetch('/api/summary');
    if (!data) return;

    document.getElementById('cardAccountBalance').innerText = formatNaira(data.expected_balance);
    document.getElementById('cardTodaySales').innerText = formatNaira(data.today_sales);
    document.getElementById('cardTodayProfit').innerText = formatNaira(data.today_profit);
    document.getElementById('cardTotalSales').innerText = formatNaira(data.total_sales);
    document.getElementById('cardExpenses').innerText = formatNaira(data.total_expenses);
}

// 2. Fetch Products (Inventory & Daily Checklist)
async function loadProducts() {
    const products = await safeFetch('/api/products');
    if (!products) return;

    // Render Inventory Table
    const invBody = document.getElementById('inventoryTableBody');
    if (invBody) {
        invBody.innerHTML = products.map(p => {
            const safeName = p.name.replace(/'/g, "\\'");
            return `
                <tr>
                    <td class="fw-bold">${p.name}</td>
                    <td>${formatNaira(p.cost_price)}</td>
                    <td>${formatNaira(p.selling_price)}</td>
                    <td>${p.sales_count}</td>
                    <td><span class="badge ${p.stock_qty < 5 ? 'bg-danger' : 'bg-success'}">${p.stock_qty}</span></td>
                    <td>
                        <div class="d-flex gap-1">
                            <button class="btn btn-sm btn-outline-warning py-0 px-2" onclick="openEditModal(${p.id}, '${safeName}', ${p.cost_price}, ${p.selling_price})"><i class="bi bi-pencil"></i></button>
                            <button class="btn btn-sm btn-outline-primary py-0 px-2" onclick="openRestockModal(${p.id}, '${safeName}')">+ Stock</button>
                            <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="deleteProduct(${p.id}, '${safeName}')"><i class="bi bi-trash"></i></button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // Render Daily Sales Checklist
    const checkBody = document.getElementById('checklistTableBody');
    if (checkBody) {
        checkBody.innerHTML = products.map(p => `
            <tr>
                <td class="text-center">
                    <input type="checkbox" class="form-check-input checklist-check" data-id="${p.id}" ${p.stock_qty === 0 ? 'disabled' : ''}>
                </td>
                <td class="fw-semibold">${p.name}</td>
                <td>${formatNaira(p.selling_price)}</td>
                <td><span class="badge bg-secondary">${p.stock_qty} left</span></td>
                <td>
                    <input type="number" class="form-control form-control-sm checklist-qty" data-id="${p.id}" value="1" min="1" max="${p.stock_qty}" ${p.stock_qty === 0 ? 'disabled' : ''}>
                </td>
            </tr>
        `).join('');
    }
}

// 3. Add Product
async function handleAddProduct(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('prodName').value,
        cost_price: document.getElementById('prodCost').value,
        selling_price: document.getElementById('prodPrice').value,
        stock_qty: document.getElementById('prodStock').value
    };

    const res = await safeFetch('/api/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res) {
        const modalEl = document.getElementById('addProductModal');
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        modal.hide();
        document.getElementById('addProductForm').reset();
        await loadAllData();
    } else {
        alert('Failed to add product. Please check your backend logs.');
    }
}

// 4. Edit Product
function openEditModal(id, name, cost, price) {
    document.getElementById('editProductId').value = id;
    document.getElementById('editProductName').innerText = name;
    document.getElementById('editCostPrice').value = cost;
    document.getElementById('editSellingPrice').value = price;
    new bootstrap.Modal(document.getElementById('editProductModal')).show();
}

async function handleEditProduct(e) {
    e.preventDefault();
    const id = document.getElementById('editProductId').value;
    const payload = {
        cost_price: document.getElementById('editCostPrice').value,
        selling_price: document.getElementById('editSellingPrice').value
    };

    const res = await safeFetch(`/api/products/${id}/edit`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res) {
        const modalEl = document.getElementById('editProductModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        await loadProducts();
    }
}

// 5. Restock Product
function openRestockModal(id, name) {
    document.getElementById('restockProductId').value = id;
    document.getElementById('restockProductName').innerText = name;
    new bootstrap.Modal(document.getElementById('restockModal')).show();
}

async function handleRestock(e) {
    e.preventDefault();
    const id = document.getElementById('restockProductId').value;
    const added_qty = document.getElementById('restockQty').value;

    const res = await safeFetch(`/api/products/${id}/restock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ added_qty })
    });

    if (res) {
        const modalEl = document.getElementById('restockModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        await loadProducts();
    }
}

// 6. Delete Product
async function deleteProduct(id, name) {
    if (confirm(`Are you sure you want to delete "${name}" from inventory?`)) {
        await safeFetch(`/api/products/${id}`, { method: 'DELETE' });
        await loadAllData();
    }
}

// 7. Record Sales Checklist
async function handleSubmitChecklist() {
    const items = [];
    const checkboxes = document.querySelectorAll('.checklist-check:checked');

    checkboxes.forEach(cb => {
        const id = cb.getAttribute('data-id');
        const qtyInput = document.querySelector(`.checklist-qty[data-id="${id}"]`);
        items.push({
            product_id: parseInt(id),
            quantity: parseInt(qtyInput.value)
        });
    });

    if (items.length === 0) {
        alert('Please check at least one product sold!');
        return;
    }

    const res = await safeFetch('/api/sales', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(items)
    });

    if (res) {
        await loadAllData();
        alert('Sales recorded successfully!');
    }
}

// 8. Sales History
async function loadSalesHistory() {
    const sales = await safeFetch('/api/sales');
    if (!sales) return;

    const body = document.getElementById('historyTableBody');
    if (body) {
        body.innerHTML = sales.map(s => `
            <tr>
                <td class="text-muted small">${s.created_at}</td>
                <td class="fw-semibold">${s.product_name}</td>
                <td>${s.quantity}</td>
                <td class="text-success fw-bold">${formatNaira(s.total_amount)}</td>
                <td class="text-primary fw-bold">${formatNaira(s.profit)}</td>
            </tr>
        `).join('');
    }
}

// 9. Expenses
async function loadExpenses() {
    const expenses = await safeFetch('/api/expenses');
    if (!expenses) return;

    const body = document.getElementById('expenseTableBody');
    if (body) {
        body.innerHTML = expenses.map(e => `
            <tr>
                <td class="text-muted small">${e.created_at}</td>
                <td>${e.title}</td>
                <td class="text-danger fw-bold">${formatNaira(e.amount)}</td>
            </tr>
        `).join('');
    }
}

async function handleAddExpense(e) {
    e.preventDefault();
    const payload = {
        title: document.getElementById('expTitle').value,
        amount: document.getElementById('expAmount').value
    };

    const res = await safeFetch('/api/expenses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res) {
        const modalEl = document.getElementById('addExpenseModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        document.getElementById('expenseForm').reset();
        await loadAllData();
    }
}

// 10. Daily Summary
async function loadDailySummary() {
    const data = await safeFetch('/api/daily-summary');
    if (!data) return;

    const body = document.getElementById('dailySummaryTableBody');
    if (body) {
        body.innerHTML = data.map(d => `
            <tr>
                <td class="fw-bold">${d.date}</td>
                <td class="text-success">${formatNaira(d.sales)}</td>
                <td class="text-primary fw-bold">${formatNaira(d.profit)}</td>
                <td class="text-danger">${formatNaira(d.expenses)}</td>
                <td class="fw-bold ${d.net_cash >= 0 ? 'text-dark' : 'text-danger'}">${formatNaira(d.net_cash)}</td>
            </tr>
        `).join('');
    }
}

// 11. Reset System
async function executeReset(type) {
    const confirmMessage = type === 'full' 
        ? 'Are you sure you want to perform a FULL RESET? All products, sales history, and expenses will be permanently deleted.' 
        : 'Are you sure you want to clear all sales history and expense logs?';

    if (!confirm(confirmMessage)) return;

    const res = await safeFetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: type })
    });

    if (res) {
        const modalEl = document.getElementById('resetDataModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        await loadAllData();
        alert('Reset completed successfully!');
    }
}
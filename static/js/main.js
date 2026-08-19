document.addEventListener('DOMContentLoaded', () => {
    loadSummary();
    loadProducts();
    loadSalesHistory();
    loadExpenses();

    // Event Listeners
    document.getElementById('refreshBtn').addEventListener('click', () => {
        loadSummary();
        loadProducts();
        loadSalesHistory();
        loadExpenses();
    });

    document.getElementById('addProductForm').addEventListener('submit', handleAddProduct);
    document.getElementById('restockForm').addEventListener('submit', handleRestock);
    document.getElementById('expenseForm').addEventListener('submit', handleAddExpense);
    document.getElementById('submitChecklistBtn').addEventListener('click', handleSubmitChecklist);
});

// Format Currency
function formatNaira(amount) {
    return '₦' + Number(amount).toLocaleString('en-NG', { minimumFractionDigits: 0 });
}

// Fetch Metrics Summary
async function loadSummary() {
    const res = await fetch('/api/summary');
    const data = await res.json();

    document.getElementById('cardAccountBalance').innerText = formatNaira(data.expected_balance);
    document.getElementById('cardTodaySales').innerText = formatNaira(data.today_sales);
    document.getElementById('cardTodayProfit').innerText = formatNaira(data.today_profit);
    document.getElementById('cardTotalSales').innerText = formatNaira(data.total_sales);
    document.getElementById('cardExpenses').innerText = formatNaira(data.total_expenses);
}

// Fetch Products (Inventory & Daily Checklist)
async function loadProducts() {
    const res = await fetch('/api/products');
    const products = await res.json();

    // Render Inventory Table
const invBody = document.getElementById('inventoryTableBody');
invBody.innerHTML = products.map(p => `
    <tr>
        <td class="fw-bold">${p.name}</td>
        <td>${formatNaira(p.cost_price)}</td>
        <td>${formatNaira(p.selling_price)}</td>
        <td>${p.sales_count}</td>
        <td><span class="badge ${p.stock_qty < 5 ? 'bg-danger' : 'bg-success'}">${p.stock_qty}</span></td>
        <td>
            <div class="d-flex gap-1">
                <button class="btn btn-sm btn-outline-primary py-0 px-2" onclick="openRestockModal(${p.id}, '${p.name}')">+ Stock</button>
                <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="deleteProduct(${p.id}, '${p.name}')"><i class="bi bi-trash"></i></button>
            </div>
        </td>
    </tr>
`).join('');

    // Render Daily Sales Checklist
    const checkBody = document.getElementById('checklistTableBody');
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

// Add Product
async function handleAddProduct(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('prodName').value,
        cost_price: document.getElementById('prodCost').value,
        selling_price: document.getElementById('prodPrice').value,
        stock_qty: document.getElementById('prodStock').value
    };

    await fetch('/api/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    bootstrap.Modal.getInstance(document.getElementById('addProductModal')).hide();
    document.getElementById('addProductForm').reset();
    loadProducts();
}

// Restock
function openRestockModal(id, name) {
    document.getElementById('restockProductId').value = id;
    document.getElementById('restockProductName').innerText = name;
    new bootstrap.Modal(document.getElementById('restockModal')).show();
}

async function handleRestock(e) {
    e.preventDefault();
    const id = document.getElementById('restockProductId').value;
    const added_qty = document.getElementById('restockQty').value;

    await fetch(`/api/products/${id}/restock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ added_qty })
    });

    bootstrap.Modal.getInstance(document.getElementById('restockModal')).hide();
    loadProducts();
}

// Delete Product
async function deleteProduct(id, name) {
    if (confirm(`Are you sure you want to delete "${name}" from inventory?`)) {
        await fetch(`/api/products/${id}`, {
            method: 'DELETE'
        });
        
        loadSummary();
        loadProducts();
    }
}

// Record Sales Checklist
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

    await fetch('/api/sales', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(items)
    });

    loadSummary();
    loadProducts();
    loadSalesHistory();
    alert('Sales recorded successfully!');
}

// Sales History
async function loadSalesHistory() {
    const res = await fetch('/api/sales');
    const sales = await res.json();

    const body = document.getElementById('historyTableBody');
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

// Expenses
async function loadExpenses() {
    const res = await fetch('/api/expenses');
    const expenses = await res.json();

    const body = document.getElementById('expenseTableBody');
    body.innerHTML = expenses.map(e => `
        <tr>
            <td class="text-muted small">${e.created_at}</td>
            <td>${e.title}</td>
            <td class="text-danger fw-bold">${formatNaira(e.amount)}</td>
        </tr>
    `).join('');
}

async function handleAddExpense(e) {
    e.preventDefault();
    const payload = {
        title: document.getElementById('expTitle').value,
        amount: document.getElementById('expAmount').value
    };

    await fetch('/api/expenses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    bootstrap.Modal.getInstance(document.getElementById('addExpenseModal')).hide();
    document.getElementById('expenseForm').reset();
    loadSummary();
    loadExpenses();
}

document.addEventListener('DOMContentLoaded', () => {
    // ... Existing load calls ...
    loadDailySummary();

    // Add edit form submit listener
    document.getElementById('editProductForm').addEventListener('submit', handleEditProduct);
});

// 1. EDIT PRODUCT LOGIC
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

    await fetch(`/api/products/${id}/edit`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    bootstrap.Modal.getInstance(document.getElementById('editProductModal')).hide();
    loadProducts();
}

// Update inventory table rendering to include Edit button:
// Inside loadProducts():
// <button class="btn btn-sm btn-outline-warning py-0 px-2" onclick="openEditModal(${p.id}, '${p.name}', ${p.cost_price}, ${p.selling_price})"><i class="bi bi-pencil"></i></button>

// 2. DAILY SUMMARY FETCH & RENDER
async function loadDailySummary() {
    const res = await fetch('/api/daily-summary');
    const data = await res.json();

    const body = document.getElementById('dailySummaryTableBody');
    if (!body) return;

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

async function executeReset(type) {
    const confirmMessage = type === 'full' 
        ? 'Are you sure you want to perform a FULL RESET? All products, sales history, and expenses will be permanently deleted.' 
        : 'Are you sure you want to clear all sales history and expense logs?';

    if (!confirm(confirmMessage)) return;

    await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: type })
    });

    // Close Modal and refresh all UI sections
    const modalEl = document.getElementById('resetDataModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();

    loadSummary();
    loadProducts();
    loadSalesHistory();
    loadExpenses();
    if (typeof loadDailySummary === 'function') loadDailySummary();

    alert('Reset completed successfully!');
}
// VyaparAI OS - User-Inputtable Application Controller
let activeChatPhone = "+91 98765 43210";
let activeChatName = "Ramesh Verma";
let inventoryCache = [];
let customersCache = [];

document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
});

async function initApp() {
    await loadBusinessProfile();
    await loadDashboardStats();
    await loadInventory();
    await loadInvoices();
    await loadCustomers();
    await loadFollowups();
    await loadChatHistory(activeChatPhone);
}

function setupEventListeners() {
    const waInput = document.getElementById("waMessageInput");
    if (waInput) {
        waInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                sendSimulatorMessage();
            }
        });
    }
}

// ============================================================================
// TAB SWITCHING
// ============================================================================
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));

    const targetTab = document.getElementById(tabId);
    if (targetTab) targetTab.classList.add("active");

    const targetNav = document.getElementById(`nav-${tabId}`);
    if (targetNav) targetNav.classList.add("active");

    if (tabId === "dashboard") loadDashboardStats();
    if (tabId === "inventory") loadInventory();
    if (tabId === "invoices") loadInvoices();
    if (tabId === "customers") loadCustomers();
    if (tabId === "followups") loadFollowups();
    if (tabId === "settings") loadBusinessProfile();
    if (tabId === "security") loadAuditLogs();
}

// ============================================================================
// BUSINESS PROFILE & SETUP (INPUTABLE BY USER)
// ============================================================================
async function loadBusinessProfile() {
    try {
        const res = await fetch("/api/business/profile");
        const data = await res.json();
        if (data && data.name) {
            document.getElementById("topbarStoreName").innerText = data.name;
            document.getElementById("sidebarStoreName").innerText = data.name;
            document.getElementById("topbarUpiId").innerText = data.upi_id || "None set";

            // Populate Settings form
            if (document.getElementById("cfgStoreName")) {
                document.getElementById("cfgStoreName").value = data.name || "";
                document.getElementById("cfgTagline").value = data.tagline || "";
                document.getElementById("cfgBusinessType").value = data.business_type || "shop";
                document.getElementById("cfgOwnerName").value = data.owner_name || "";
                document.getElementById("cfgPhone").value = data.phone || "";
                document.getElementById("cfgEmail").value = data.email || "";
                document.getElementById("cfgAddress").value = data.address || "";
                document.getElementById("cfgGstin").value = data.gstin || "";
                document.getElementById("cfgStateName").value = data.state_name || "";
                document.getElementById("cfgUpiId").value = data.upi_id || "";
                document.getElementById("cfgUpiName").value = data.upi_name || "";
                document.getElementById("cfgWelcomeMsg").value = data.welcome_msg || "";
            }

            // Hide onboarding banner if user has already customized their business
            const ob = document.getElementById("onboardingBanner");
            if (ob && data.is_configured === 1 && inventoryCache.length > 0) {
                ob.style.display = "none";
            }
        }
    } catch (err) {
        console.error("Error loading profile:", err);
    }
}

function openBusinessProfileModal() {
    fetch("/api/business/profile")
        .then(res => res.json())
        .then(data => {
            document.getElementById("mStoreName").value = data.name || "";
            document.getElementById("mBusinessType").value = data.business_type || "shop";
            document.getElementById("mPhone").value = data.phone || "";
            document.getElementById("mUpiId").value = data.upi_id || "";
            document.getElementById("mAddress").value = data.address || "";
            document.getElementById("mGstin").value = data.gstin || "";
            document.getElementById("bizProfileModal").classList.add("open");
        });
}

function closeBusinessProfileModal() {
    document.getElementById("bizProfileModal").classList.remove("open");
}

async function saveBusinessProfileModal(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById("mStoreName").value.trim(),
        business_type: document.getElementById("mBusinessType").value,
        phone: document.getElementById("mPhone").value.trim(),
        upi_id: document.getElementById("mUpiId").value.trim(),
        address: document.getElementById("mAddress").value.trim(),
        gstin: document.getElementById("mGstin").value.trim()
    };

    try {
        const res = await fetch("/api/business/profile", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (d.status === "SUCCESS") {
            closeBusinessProfileModal();
            await loadBusinessProfile();
            showNotification("Business details updated successfully!");
        }
    } catch (err) {
        alert("Failed to update profile.");
    }
}

async function saveBusinessProfile(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById("cfgStoreName").value.trim(),
        tagline: document.getElementById("cfgTagline").value.trim(),
        business_type: document.getElementById("cfgBusinessType").value,
        owner_name: document.getElementById("cfgOwnerName").value.trim(),
        phone: document.getElementById("cfgPhone").value.trim(),
        email: document.getElementById("cfgEmail").value.trim(),
        address: document.getElementById("cfgAddress").value.trim(),
        gstin: document.getElementById("cfgGstin").value.trim(),
        state_name: document.getElementById("cfgStateName").value.trim(),
        upi_id: document.getElementById("cfgUpiId").value.trim(),
        upi_name: document.getElementById("cfgUpiName").value.trim(),
        welcome_msg: document.getElementById("cfgWelcomeMsg").value.trim()
    };

    try {
        const res = await fetch("/api/business/profile", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (d.status === "SUCCESS") {
            await loadBusinessProfile();
            showNotification("Business settings saved successfully!");
        }
    } catch (err) {
        alert("Failed to save settings.");
    }
}

// ============================================================================
// DASHBOARD ANALYTICS (REAL DATA)
// ============================================================================
async function loadDashboardStats() {
    try {
        const res = await fetch("/api/dashboard/stats");
        const d = await res.json();

        document.getElementById("kpiTodaySales").innerText = formatCurrency(d.today_revenue);
        document.getElementById("kpiTotalUdhaar").innerText = formatCurrency(d.total_udhaar);
        document.getElementById("kpiDebtorCount").innerText = `${d.debtor_count} customer(s) with pending balance`;
        document.getElementById("kpiStockValuation").innerText = formatCurrency(d.stock_valuation);
        document.getElementById("kpiTotalSKUs").innerText = `${d.total_items} items in catalog`;
        document.getElementById("kpiLowStockCount").innerText = d.low_stock_count;

        // Populate recent invoices or empty state
        const invBody = document.getElementById("dashRecentInvoicesBody");
        if (invBody) {
            if (d.recent_invoices.length === 0) {
                invBody.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align:center; padding:28px 12px; color:#94a3b8;">
                            <div>No invoices yet. Click <strong>+ New GST Bill</strong> to create your first bill.</div>
                        </td>
                    </tr>
                `;
            } else {
                invBody.innerHTML = d.recent_invoices.map(inv => `
                    <tr>
                        <td><strong>#${inv.invoice_no}</strong></td>
                        <td>${escapeHtml(inv.customer_name)}</td>
                        <td>${formatCurrency(inv.total_amount)}</td>
                        <td><span class="badge badge-${getStatusBadge(inv.status)}">${inv.status}</span></td>
                        <td>
                            <a href="/invoice/${inv.invoice_no}/view" target="_blank" class="btn btn-secondary" style="padding:3px 7px; font-size:11px;">View</a>
                        </td>
                    </tr>
                `).join("");
            }
        }

        // Populate low stock alerts or healthy state
        const stockList = document.getElementById("dashLowStockList");
        if (stockList) {
            if (d.low_stock_items.length === 0) {
                stockList.innerHTML = `
                    <div style="text-align:center; color:#64748b; padding:28px 16px; background:#f8fafc; border-radius:8px;">
                        <span style="font-size:22px;">✅</span>
                        <div style="font-size:12.5px; font-weight:600; margin-top:6px; color:#1e293b;">Stock levels are healthy</div>
                        <div style="font-size:11px; color:#94a3b8;">Add products to monitor low-stock thresholds.</div>
                    </div>
                `;
            } else {
                stockList.innerHTML = d.low_stock_items.map(item => `
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #f1f5f9;">
                        <div>
                            <strong style="font-size:13px; color:#1e293b;">${escapeHtml(item.name)}</strong>
                            <div style="font-size:11px; color:#64748b;">SKU: ${item.sku || '-'} &nbsp;|&nbsp; Threshold: ${item.min_threshold} ${item.unit}</div>
                        </div>
                        <div style="text-align:right;">
                            <span class="badge badge-danger">${item.stock_qty} ${item.unit} left</span>
                            <button onclick="quickRestock(${item.id}, '${escapeHtml(item.name)}')" class="btn btn-secondary" style="padding:3px 7px; font-size:11px; margin-left:6px;">+ Restock</button>
                        </div>
                    </div>
                `).join("");
            }
        }

    } catch (err) {
        console.error("Dashboard stats error:", err);
    }
}

// ============================================================================
// WHATSAPP SIMULATOR (ANY CUSTOMER INPUTABLE)
// ============================================================================
function onCustomCustomerChanged() {
    activeChatPhone = document.getElementById("waInputPhone").value.trim() || "+91 98000 00000";
    activeChatName = document.getElementById("waInputName").value.trim() || "Customer";
    document.getElementById("waChatContactName").innerText = activeChatName;
    document.getElementById("waChatContactPhone").innerText = activeChatPhone;
    loadChatHistory(activeChatPhone);
}

function onSelectSavedCustomer(sel) {
    if (!sel.value) return;
    const opt = sel.options[sel.selectedIndex];
    document.getElementById("waInputPhone").value = sel.value;
    document.getElementById("waInputName").value = opt.dataset.name;
    onCustomCustomerChanged();
}

function reloadActiveChat() {
    loadChatHistory(activeChatPhone);
}

async function loadChatHistory(phone) {
    const chatBody = document.getElementById("waChatBody");
    if (!chatBody) return;

    try {
        const res = await fetch(`/api/whatsapp/messages?phone=${encodeURIComponent(phone)}`);
        const messages = await res.json();

        chatBody.innerHTML = "";
        if (messages.length === 0) {
            chatBody.innerHTML = `
                <div style="text-align:center; margin:auto; color:#6b7280; font-size:11.5px; background:rgba(255,255,255,0.7); padding:8px 12px; border-radius:8px;">
                    🔒 End-to-end encrypted with your store's AI Operating System.
                </div>
            `;
            return;
        }

        messages.forEach(msg => {
            appendChatBubble(msg.content, msg.direction.toLowerCase(), msg.created_at);
        });

        scrollChatToBottom();
    } catch (err) {
        console.error("Load chat error:", err);
    }
}

function appendChatBubble(content, direction, timestamp) {
    const chatBody = document.getElementById("waChatBody");
    const bubble = document.createElement("div");
    bubble.className = `wa-bubble ${direction}`;

    const formattedContent = escapeHtml(content)
        .replace(/\*(.*?)\*/g, "<strong>$1</strong>")
        .replace(/(upi:\/\/pay\?[^\s]+)/g, '<a href="$1" style="color:#0284c7; font-weight:700; text-decoration:underline;">📱 Pay via UPI</a>');

    const timeStr = timestamp ? timestamp.slice(11, 16) : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const ticks = direction === "outbound" ? '<span style="color:#34b7f1; font-weight:bold;">✓✓</span>' : '';

    bubble.innerHTML = `
        <div>${formattedContent}</div>
        <div class="wa-time">${timeStr} ${ticks}</div>
    `;

    chatBody.appendChild(bubble);
    scrollChatToBottom();
}

async function sendSimulatorMessage(presetText = null) {
    const input = document.getElementById("waMessageInput");
    const text = presetText || input.value.trim();
    if (!text) return;

    if (!presetText) input.value = "";

    appendChatBubble(text, "inbound", new Date().toISOString());

    const chatBody = document.getElementById("waChatBody");
    const typingBubble = document.createElement("div");
    typingBubble.id = "typingIndicator";
    typingBubble.className = "wa-bubble outbound";
    typingBubble.style.color = "#64748b";
    typingBubble.style.fontStyle = "italic";
    typingBubble.innerHTML = "Store AI is typing... 💬";
    chatBody.appendChild(typingBubble);
    scrollChatToBottom();

    try {
        const res = await fetch("/api/whatsapp/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                phone: activeChatPhone,
                message: text,
                sender_name: activeChatName
            })
        });

        const replyData = await res.json();
        const ind = document.getElementById("typingIndicator");
        if (ind) ind.remove();

        appendChatBubble(replyData.reply, "outbound", replyData.timestamp);
        loadDashboardStats();
    } catch (err) {
        const ind = document.getElementById("typingIndicator");
        if (ind) ind.remove();
        appendChatBubble("Error communicating with store AI.", "outbound");
    }
}

function sendQuickQuery(text) {
    sendSimulatorMessage(text);
}

function scrollChatToBottom() {
    const chatBody = document.getElementById("waChatBody");
    if (chatBody) {
        chatBody.scrollTop = chatBody.scrollHeight;
    }
}

// ============================================================================
// INVOICING & GST BILLS
// ============================================================================
async function loadInvoices() {
    try {
        const res = await fetch("/api/invoices");
        const list = await res.json();

        const container = document.getElementById("invoicesListContainer");
        const tbody = document.getElementById("invoicesTableBody");
        if (!tbody || !container) return;

        if (list.length === 0) {
            container.innerHTML = `
                <div class="empty-state-box">
                    <div class="empty-state-icon">🧾</div>
                    <div class="empty-state-title">No invoices or bills created yet</div>
                    <div class="empty-state-desc">
                        Create GST tax invoices, bill walk-in customers, and share instant UPI payment QR links directly.
                    </div>
                    <button onclick="openCreateInvoiceModal()" class="btn btn-primary">+ Create First GST Bill</button>
                </div>
            `;
            return;
        }

        // Re-inject table if replaced by empty state
        if (!document.getElementById("invoicesTableBody")) {
            container.innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Invoice #</th>
                            <th>Customer &amp; Phone</th>
                            <th>Date</th>
                            <th>Due Date</th>
                            <th>Total (₹)</th>
                            <th>Paid (₹)</th>
                            <th>Balance (₹)</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="invoicesTableBody"></tbody>
                </table>
            `;
        }

        document.getElementById("invoicesTableBody").innerHTML = list.map(inv => `
            <tr>
                <td><strong>#${inv.invoice_no}</strong></td>
                <td>
                    <strong>${escapeHtml(inv.customer_name)}</strong>
                    <div style="font-size:11px; color:#64748b;">${inv.customer_phone}</div>
                </td>
                <td>${inv.created_at ? inv.created_at.slice(0, 10) : '-'}</td>
                <td>${inv.due_date || '-'}</td>
                <td><strong>${formatCurrency(inv.total_amount)}</strong></td>
                <td style="color:#059669;">${formatCurrency(inv.paid_amount)}</td>
                <td style="color:#b91c1c; font-weight:700;">${formatCurrency(inv.balance_amount)}</td>
                <td><span class="badge badge-${getStatusBadge(inv.status)}">${inv.status}</span></td>
                <td>
                    <div style="display:flex; gap:6px;">
                        <a href="/invoice/${inv.invoice_no}/view" target="_blank" class="btn btn-secondary" style="padding:4px 8px; font-size:11px;">🖨️ View/Print</a>
                        ${inv.balance_amount > 0 ? `<button onclick="openRecordPaymentModal(${inv.id}, '${inv.invoice_no}', ${inv.balance_amount})" class="btn btn-success" style="padding:4px 8px; font-size:11px;">₹ Pay</button>` : ''}
                        <button onclick="deleteInvoice(${inv.id})" class="btn btn-danger" style="padding:4px 6px; font-size:11px;" title="Delete Invoice">✕</button>
                    </div>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Load invoices error:", err);
    }
}

function openCreateInvoiceModal() {
    document.getElementById("createInvoiceModal").classList.add("open");
    populateInvoiceItemSelect();
    recalcInvoiceTotals();
}

function closeCreateInvoiceModal() {
    document.getElementById("createInvoiceModal").classList.remove("open");
}

function populateInvoiceItemSelect() {
    const sel = document.getElementById("invNewItemSelect");
    if (!sel) return;
    sel.innerHTML = `<option value="">-- Choose from Catalog or Type below --</option>` + 
        inventoryCache.map(i => `<option value="${i.id}" data-name="${escapeHtml(i.name)}" data-price="${i.selling_price}" data-gst="${i.gst_rate}" data-hsn="${i.hsn_code}" data-unit="${i.unit}">${escapeHtml(i.name)} (${formatCurrency(i.selling_price)} / ${i.unit})</option>`).join("");
}

function onInvoiceItemPicked() {
    const sel = document.getElementById("invNewItemSelect");
    const opt = sel.options[sel.selectedIndex];
    if (opt && opt.value) {
        document.getElementById("invCustomItemName").value = opt.dataset.name;
        document.getElementById("invItemRate").value = opt.dataset.price;
        document.getElementById("invItemGst").value = opt.dataset.gst;
        document.getElementById("invItemHsn").value = opt.dataset.hsn;
        document.getElementById("invItemUnit").value = opt.dataset.unit;
    }
    recalcInvoiceTotals();
}

function recalcInvoiceTotals() {
    const qty = parseFloat(document.getElementById("invItemQty").value) || 0;
    const rate = parseFloat(document.getElementById("invItemRate").value) || 0;
    const gstRate = parseFloat(document.getElementById("invItemGst").value) || 0;

    const sub = qty * rate;
    const tax = sub * (gstRate / 100.0);
    const grand = sub + tax;

    document.getElementById("lblSubtotal").innerText = formatCurrency(sub);
    document.getElementById("lblTax").innerText = formatCurrency(tax);
    document.getElementById("lblGrandTotal").innerText = formatCurrency(grand);
}

async function submitCreateInvoice() {
    const custName = document.getElementById("invCustName").value.trim();
    const custPhone = document.getElementById("invCustPhone").value.trim();
    const custAddress = document.getElementById("invCustAddress").value.trim();
    const custGstin = document.getElementById("invCustGstin").value.trim();
    const isInterstate = document.getElementById("invIsInterstate").checked;

    const sel = document.getElementById("invNewItemSelect");
    const opt = sel.options[sel.selectedIndex];
    const customName = document.getElementById("invCustomItemName").value.trim();
    const itemName = customName || (opt && opt.value ? opt.dataset.name : "");

    if (!itemName) {
        alert("Please choose an item or enter an item name!");
        return;
    }

    const qty = parseFloat(document.getElementById("invItemQty").value) || 1;
    const rate = parseFloat(document.getElementById("invItemRate").value) || 0;
    const gstRate = parseFloat(document.getElementById("invItemGst").value) || 18;
    const hsn = document.getElementById("invItemHsn").value;
    const unit = document.getElementById("invItemUnit").value || "pcs";

    const payload = {
        customer_name: custName || "Walk-in Customer",
        customer_phone: custPhone || "+91 98000 00000",
        customer_address: custAddress,
        customer_gstin: custGstin,
        is_interstate: isInterstate,
        items: [{
            item_id: opt && opt.value ? parseInt(opt.value) : null,
            item_name: itemName,
            hsn_code: hsn,
            quantity: qty,
            unit: unit,
            unit_price: rate,
            gst_rate: gstRate
        }]
    };

    try {
        const res = await fetch("/api/invoices/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            closeCreateInvoiceModal();
            loadInvoices();
            loadDashboardStats();
            loadInventory();
            loadCustomers();
            showNotification(`Invoice #${data.invoice_no} created successfully! Total: ${formatCurrency(data.total_amount)}`);
            window.open(data.invoice_view_url, "_blank");
        }
    } catch (err) {
        console.error("Create invoice error:", err);
        alert("Failed to create invoice.");
    }
}

async function deleteInvoice(id) {
    if (!confirm("Are you sure you want to cancel and delete this invoice?")) return;
    try {
        const res = await fetch(`/api/invoices/${id}`, { method: "DELETE" });
        const d = await res.json();
        loadInvoices();
        loadDashboardStats();
        loadCustomers();
        showNotification(d.message);
    } catch (err) {
        alert("Failed to delete invoice");
    }
}

function openRecordPaymentModal(invId, invNo, balance) {
    document.getElementById("recordPaymentModal").classList.add("open");
    document.getElementById("payInvId").value = invId;
    document.getElementById("payInvNoLabel").innerText = invNo;
    document.getElementById("payAmountInput").value = balance;
    document.getElementById("payAmountInput").max = balance;
}

function closeRecordPaymentModal() {
    document.getElementById("recordPaymentModal").classList.remove("open");
}

async function submitRecordPayment() {
    const invId = document.getElementById("payInvId").value;
    const amount = parseFloat(document.getElementById("payAmountInput").value) || 0;
    const mode = document.getElementById("payModeSelect").value;

    if (amount <= 0) {
        alert("Amount must be greater than zero");
        return;
    }

    try {
        const res = await fetch(`/api/invoices/${invId}/record-payment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount_paid: amount, payment_mode: mode })
        });
        const data = await res.json();
        if (data.status === "SUCCESS") {
            closeRecordPaymentModal();
            loadInvoices();
            loadDashboardStats();
            loadCustomers();
            showNotification(`Payment of ${formatCurrency(amount)} recorded for #${data.invoice_no}! Status: ${data.invoice_status}`);
        }
    } catch (err) {
        alert("Failed to record payment.");
    }
}

// ============================================================================
// INVENTORY & STOCK MANAGEMENT
// ============================================================================
async function loadInventory() {
    try {
        const res = await fetch("/api/inventory");
        inventoryCache = await res.json();

        const container = document.getElementById("inventoryListContainer");
        if (!container) return;

        if (inventoryCache.length === 0) {
            container.innerHTML = `
                <div class="empty-state-box">
                    <div class="empty-state-icon">📦</div>
                    <div class="empty-state-title">Your inventory catalog is empty</div>
                    <div class="empty-state-desc">
                        Add the goods, products, or services your business sells. You can set prices, units, HSN codes, and low-stock alerts.
                    </div>
                    <button onclick="openAddItemModal()" class="btn btn-primary">+ Add Your First Product</button>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Product / Item Name</th>
                        <th>SKU</th>
                        <th>Category</th>
                        <th>Cost (₹)</th>
                        <th>Selling Price / MRP (₹)</th>
                        <th>In Stock</th>
                        <th>HSN</th>
                        <th>GST %</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="inventoryTableBody">
                    ${inventoryCache.map(i => {
                        const isLow = i.stock_qty <= i.min_threshold;
                        return `
                            <tr>
                                <td><strong>${escapeHtml(i.name)}</strong></td>
                                <td><code>${i.sku || '-'}</code></td>
                                <td>${escapeHtml(i.category)}</td>
                                <td>${formatCurrency(i.cost_price)}</td>
                                <td><strong>${formatCurrency(i.selling_price)}</strong></td>
                                <td>
                                    <span class="badge ${isLow ? 'badge-danger' : 'badge-success'}">
                                        ${i.stock_qty} ${i.unit} ${isLow ? '⚠️ Low' : '✅'}
                                    </span>
                                </td>
                                <td>${i.hsn_code || '-'}</td>
                                <td>${i.gst_rate}%</td>
                                <td>
                                    <div style="display:flex; gap:6px;">
                                        <button onclick="quickRestock(${i.id}, '${escapeHtml(i.name)}')" class="btn btn-secondary" style="padding:3px 7px; font-size:11px;">+ Restock</button>
                                        <button onclick="deleteInventoryItem(${i.id})" class="btn btn-danger" style="padding:3px 6px; font-size:11px;" title="Delete">✕</button>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }).join("")}
                </tbody>
            </table>
        `;
    } catch (err) {
        console.error("Load inventory error:", err);
    }
}

function openAddItemModal() {
    document.getElementById("addItemModal").classList.add("open");
}

function closeAddItemModal() {
    document.getElementById("addItemModal").classList.remove("open");
}

async function submitAddItem(e) {
    e.preventDefault();
    const name = document.getElementById("newItemName").value.trim();
    const sku = document.getElementById("newItemSku").value.trim();
    const cat = document.getElementById("newItemCategory").value.trim();
    const unit = document.getElementById("newItemUnit").value.trim();
    const cost = parseFloat(document.getElementById("newItemCost").value) || 0;
    const sell = parseFloat(document.getElementById("newItemSell").value) || 0;
    const qty = parseFloat(document.getElementById("newItemQty").value) || 0;
    const min = parseFloat(document.getElementById("newItemMin").value) || 5;
    const hsn = document.getElementById("newItemHsn").value.trim();
    const gst = parseFloat(document.getElementById("newItemGst").value) || 18;

    if (!name || sell <= 0) {
        alert("Please enter a valid product name and selling price!");
        return;
    }

    try {
        const res = await fetch("/api/inventory/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name, sku, category: cat, unit, cost_price: cost,
                selling_price: sell, stock_qty: qty, min_threshold: min,
                hsn_code: hsn, gst_rate: gst
            })
        });
        const d = await res.json();
        if (d.status === "SUCCESS") {
            closeAddItemModal();
            loadInventory();
            loadDashboardStats();
            showNotification(d.message);
        }
    } catch (err) {
        alert("Failed to add inventory item.");
    }
}

async function deleteInventoryItem(id) {
    if (!confirm("Remove this product from catalog?")) return;
    try {
        const res = await fetch(`/api/inventory/${id}`, { method: "DELETE" });
        const d = await res.json();
        loadInventory();
        loadDashboardStats();
        showNotification(d.message);
    } catch (err) {
        alert("Failed to delete item");
    }
}

async function quickRestock(itemId, itemName) {
    const qty = prompt(`Enter restock quantity to add for "${itemName}":`, "10");
    if (!qty || isNaN(qty) || parseFloat(qty) <= 0) return;

    try {
        const res = await fetch(`/api/inventory/${itemId}/restock?quantity=${parseFloat(qty)}`, { method: "POST" });
        const d = await res.json();
        if (d.status === "SUCCESS") {
            loadInventory();
            loadDashboardStats();
            showNotification(`Restocked ${d.name}! New stock: ${d.new_stock} ${d.unit}`);
        }
    } catch (err) {
        alert("Restock failed");
    }
}

// ============================================================================
// CUSTOMERS & KHATA LEDGER
// ============================================================================
async function loadCustomers() {
    try {
        const res = await fetch("/api/customers");
        customersCache = await res.json();

        // Update WhatsApp customer selector picker
        const picker = document.getElementById("waCustomerPicker");
        if (picker) {
            picker.innerHTML = `<option value="">-- Pick from Customers --</option>` +
                customersCache.map(c => `<option value="${c.phone}" data-name="${escapeHtml(c.name)}">${escapeHtml(c.name)} (${c.phone})</option>`).join("");
        }

        const container = document.getElementById("customersListContainer");
        if (!container) return;

        if (customersCache.length === 0) {
            container.innerHTML = `
                <div class="empty-state-box">
                    <div class="empty-state-icon">👥</div>
                    <div class="empty-state-title">No customer accounts yet</div>
                    <div class="empty-state-desc">
                        Add regular customers to track their Udhaar balances, send payment reminders, and keep their purchase ledger.
                    </div>
                    <button onclick="openAddCustomerModal()" class="btn btn-primary">+ Add First Customer</button>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Customer Name</th>
                        <th>Phone</th>
                        <th>Business / Address</th>
                        <th>GSTIN</th>
                        <th>Total Purchases (₹)</th>
                        <th>Udhaar Balance (₹)</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="customersTableBody">
                    ${customersCache.map(c => `
                        <tr>
                            <td><strong>${escapeHtml(c.name)}</strong></td>
                            <td>${c.phone}</td>
                            <td>${escapeHtml(c.business_name || c.address || '-')}</td>
                            <td>${c.gstin || '-'}</td>
                            <td>${formatCurrency(c.total_purchases)}</td>
                            <td style="color:${c.balance_due > 0 ? '#b91c1c' : '#059669'}; font-weight:700;">
                                ${formatCurrency(c.balance_due)}
                            </td>
                            <td>
                                <div style="display:flex; gap:6px;">
                                    ${c.balance_due > 0 ? `
                                        <button onclick="sendKhataReminder('${c.phone}', '${escapeHtml(c.name)}', ${c.balance_due})" class="btn btn-warning" style="padding:3px 7px; font-size:11px;">
                                            💬 WhatsApp Reminder
                                        </button>
                                    ` : `<span style="color:#059669; font-size:11px;">Nil Due ✅</span>`}
                                    <button onclick="deleteCustomer(${c.id})" class="btn btn-danger" style="padding:3px 6px; font-size:11px;" title="Delete">✕</button>
                                </div>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    } catch (err) {
        console.error("Load customers error:", err);
    }
}

function openAddCustomerModal() {
    document.getElementById("addCustomerModal").classList.add("open");
}

function closeAddCustomerModal() {
    document.getElementById("addCustomerModal").classList.remove("open");
}

async function submitAddCustomer(e) {
    e.preventDefault();
    const name = document.getElementById("newCustName").value.trim();
    const phone = document.getElementById("newCustPhone").value.trim();
    const biz = document.getElementById("newCustBiz").value.trim();
    const balance = parseFloat(document.getElementById("newCustBalance").value) || 0;
    const gstin = document.getElementById("newCustGstin").value.trim();
    const address = document.getElementById("newCustAddress").value.trim();

    try {
        const res = await fetch("/api/customers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name, phone, business_name: biz, balance_due: balance,
                gstin, address
            })
        });
        const d = await res.json();
        if (d.status === "SUCCESS") {
            closeAddCustomerModal();
            loadCustomers();
            loadDashboardStats();
            showNotification(d.message);
        } else {
            alert(d.detail || "Error adding customer");
        }
    } catch (err) {
        alert("Failed to add customer");
    }
}

async function deleteCustomer(id) {
    if (!confirm("Are you sure you want to delete this customer record?")) return;
    try {
        const res = await fetch(`/api/customers/${id}`, { method: "DELETE" });
        const d = await res.json();
        loadCustomers();
        loadDashboardStats();
        showNotification(d.message);
    } catch (err) {
        alert("Failed to delete customer");
    }
}

function sendKhataReminder(phone, name, amount) {
    activeChatPhone = phone;
    activeChatName = name;
    document.getElementById("waInputPhone").value = phone;
    document.getElementById("waInputName").value = name;
    switchTab("whatsapp");
    sendSimulatorMessage(`Namaste ${name} ji! Polite reminder from store: aapka ${formatCurrency(amount)} ka hisab pending hai. Kindly clear via UPI.`);
}

// ============================================================================
// AUTOMATED FOLLOW-UPS
// ============================================================================
async function loadFollowups() {
    try {
        const res = await fetch("/api/followups");
        const list = await res.json();

        const container = document.getElementById("followupsListContainer");
        if (!container) return;

        if (list.length === 0) {
            container.innerHTML = `
                <div class="empty-state-box">
                    <div class="empty-state-icon">⏰</div>
                    <div class="empty-state-title">No pending follow-ups right now</div>
                    <div class="empty-state-desc">
                        When invoices become overdue or customers ask for quotes, automated follow-ups will appear here.
                    </div>
                    <button onclick="triggerFollowupCycle()" class="btn btn-success">⚡ Run Follow-Up Check Now</button>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Customer Name</th>
                        <th>Phone</th>
                        <th>Type</th>
                        <th>Message Preview</th>
                        <th>Status</th>
                        <th>Created At</th>
                    </tr>
                </thead>
                <tbody id="followupsTableBody">
                    ${list.map(f => `
                        <tr>
                            <td><strong>${escapeHtml(f.customer_name)}</strong></td>
                            <td>${f.phone}</td>
                            <td><span class="badge badge-info">${f.followup_type}</span></td>
                            <td style="max-width:320px; font-size:11.5px; color:#475569;">${escapeHtml(f.message_text.slice(0, 95))}...</td>
                            <td><span class="badge ${f.status === 'SENT' ? 'badge-success' : 'badge-warning'}">${f.status}</span></td>
                            <td>${f.created_at ? f.created_at.slice(0, 16) : '-'}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    } catch (err) {
        console.error("Load followups error:", err);
    }
}

function openCustomFollowupModal() {
    document.getElementById("customFollowupModal").classList.add("open");
}

function closeCustomFollowupModal() {
    document.getElementById("customFollowupModal").classList.remove("open");
}

async function submitCustomFollowup(e) {
    e.preventDefault();
    const name = document.getElementById("folCustName").value.trim();
    const phone = document.getElementById("folPhone").value.trim();
    const type = document.getElementById("folType").value;
    const text = document.getElementById("folText").value.trim();

    try {
        const res = await fetch("/api/followups/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_name: name,
                phone: phone,
                followup_type: type,
                message_text: text
            })
        });
        const d = await res.json();
        if (d.status === "SUCCESS") {
            closeCustomFollowupModal();
            loadFollowups();
            showNotification("Follow-up queued successfully!");
        }
    } catch (err) {
        alert("Failed to queue follow-up");
    }
}

async function triggerFollowupCycle() {
    try {
        const res = await fetch("/api/followups/trigger-cycle", { method: "POST" });
        const d = await res.json();
        loadFollowups();
        loadDashboardStats();
        showNotification(`Follow-up cycle completed! Queued: ${d.queued}, Dispatched: ${d.dispatched}`);
    } catch (err) {
        alert("Failed to run follow-up cycle.");
    }
}

// ============================================================================
// SYSTEM UTILITIES, 1-CLICK RESET & PORTABILITY
// ============================================================================
async function loadAuditLogs() {
    try {
        const res = await fetch("/api/security/audit-logs");
        const list = await res.json();
        const tbody = document.getElementById("auditLogsBody");
        if (tbody) {
            tbody.innerHTML = list.map(log => `
                <tr>
                    <td><code>${log.action_type}</code></td>
                    <td>${escapeHtml(log.description)}</td>
                    <td>${log.ip_address}</td>
                    <td>${log.created_at}</td>
                </tr>
            `).join("") || `<tr><td colspan="4" style="text-align:center; color:#94a3b8;">No audit logs yet.</td></tr>`;
        }
        await loadSystemHealth();
    } catch (err) {
        console.error("Load audit error:", err);
    }
}

async function loadSystemHealth() {
    try {
        const res = await fetch("/api/system/health");
        const d = await res.json();
        const ramEl = document.getElementById("sysMemUsage");
        if (ramEl) ramEl.innerText = d.memory_usage;
        const dbEl = document.getElementById("sysDbSize");
        if (dbEl) dbEl.innerText = d.database_size_kb;
    } catch (err) {
        console.error("System health check error:", err);
    }
}

async function optimizeDatabaseNow() {
    try {
        const res = await fetch("/api/system/optimize-db", { method: "POST" });
        const d = await res.json();
        showNotification(d.message);
        loadSystemHealth();
    } catch (err) {
        alert("Optimization failed.");
    }
}

function downloadDatabaseBackup() {
    window.location.href = "/api/system/backup";
}

function toggleLowPowerMode(enable) {
    if (enable) {
        document.body.classList.add("low-power");
        showNotification("Potato PC Mode Active (Zero animations)");
    } else {
        document.body.classList.remove("low-power");
        showNotification("Standard Visual Mode Active");
    }
}

async function confirmResetAllData() {
    const confirmation = prompt("⚠️ WARNING: This will permanently erase all your products, bills, customers, and message history!\n\nType 'RESET' to confirm:");
    if (confirmation !== "RESET") {
        alert("Reset cancelled.");
        return;
    }

    try {
        const res = await fetch("/api/system/reset-data", { method: "POST" });
        const d = await res.json();
        if (d.status === "SUCCESS") {
            alert("Database reset completely! All data erased.");
            await initApp();
            switchTab("dashboard");
        }
    } catch (err) {
        alert("Failed to reset database");
    }
}

// ============================================================================
// HELPERS
// ============================================================================
function formatCurrency(num) {
    if (num === null || num === undefined) return "₹0.00";
    return "₹" + Number(num).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getStatusBadge(status) {
    switch (status) {
        case "PAID": return "success";
        case "OVERDUE": return "danger";
        case "UNPAID": return "warning";
        case "PARTIAL": return "info";
        default: return "secondary";
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function showNotification(msg) {
    const toast = document.createElement("div");
    toast.style.position = "fixed";
    toast.style.bottom = "24px";
    toast.style.right = "24px";
    toast.style.background = "#0f172a";
    toast.style.color = "#ffffff";
    toast.style.padding = "11px 18px";
    toast.style.borderRadius = "8px";
    toast.style.fontSize = "12.5px";
    toast.style.fontWeight = "600";
    toast.style.zIndex = "999";
    toast.style.boxShadow = "0 10px 15px -3px rgba(0,0,0,0.25)";
    toast.innerText = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

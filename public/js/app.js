const api = {
  async request(path, options = {}) {
    const token = localStorage.getItem("token");
    const headers = { "Content-Type": "application/json", ...options.headers };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`/api${path}`, { ...options, headers });
    if (response.status === 401) {
      localStorage.removeItem("token");
      window.location.reload();
    }
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "API Error");
    }
    return response.json();
  },
  get: (path, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return api.request(`${path}${query ? `?${query}` : ""}`, { method: "GET" });
  },
  post: (path, data) => api.request(path, { method: "POST", body: JSON.stringify(data) }),
  put: (path, data) => api.request(path, { method: "PUT", body: JSON.stringify(data) }),
  delete: (path) => api.request(path, { method: "DELETE" }),
};

const { createApp } = Vue;

createApp({
  data() {
    return {
      user: null,
      token: null,
      view: "dashboard",
      sidebarOpen: false,
      loading: false,
      error: "",
      toast: "",
      toastType: "ok",
      unreadCount: 0,
      pendingCount: 0,

      loginForm: { username: "", password: "" },
      saleForm: { item: "", piece: 1, total_price: 0, sale_date: new Date().toISOString().split("T")[0], notes: "" },
      purchaseForm: { wholesaler_id: "", item: "", piece: 1, total_price: 0, purchase_date: new Date().toISOString().split("T")[0], on_credit: false, notes: "" },
      wholesalerForm: { name: "", phone: "", address: "" },
      khataForm: { khata_type: "debt", entry_type: "add", amount: 0, note: "" },
      userForm: { name: "", username: "", password: "", role: "staff" },

      salesDate: new Date().toISOString().split("T")[0],
      salesMonth: new Date().toISOString().slice(0, 7),
      salesMode: "daily",
      salesList: [],
      salesTotals: { amount: 0, pieces: 0 },
      monthly: { totals: { amount: 0, pieces: 0, count: 0 }, by_item: [] },

      purchaseDate: new Date().toISOString().split("T")[0],
      purchases: [],
      purchaseTotals: { amount: 0, pieces: 0 },

      wholesalers: [],
      selectedWholesaler: null,
      khataHistory: [],
      wholesalerTotals: { debt: 0, uchanti: 0 },

      pendingSales: [],
      pendingPurchases: [],
      users: [],
      notifications: [],
      dash: { todayAmount: 0, todayCount: 0, todayPieces: 0, monthAmount: 0, monthCount: 0, totalDebt: 0, totalUchanti: 0, recentSales: [], recentPurchases: [] },
    };
  },
  computed: {
    isAdmin() { return this.user?.role === "admin"; },
    navItems() {
      const items = [
        { key: "dashboard", label: "Dashboard", icon: '<svg viewBox="0 0 20 20"><rect x="2.6" y="2.6" width="6" height="6" rx="1.2"/><rect x="11.4" y="2.6" width="6" height="6" rx="1.2"/><rect x="2.6" y="11.4" width="6" height="6" rx="1.2"/><rect x="11.4" y="11.4" width="6" height="6" rx="1.2"/></svg>' },
        { key: "sales", label: "Sales", icon: '<svg viewBox="0 0 20 20"><path d="M11 2.5H8.2L2.6 8.1a1.2 1.2 0 0 0 0 1.7l7.6 7.6a1.2 1.2 0 0 0 1.7 0l5.6-5.6a1.2 1.2 0 0 0 0-1.7L11 2.5Z"/><circle cx="13.1" cy="6.7" r="0.9" fill="currentColor" stroke="none"/></svg>' },
        { key: "purchases", label: "Purchases", icon: '<svg viewBox="0 0 20 20"><path d="M2.6 6.4 10 2.9l7.4 3.5M2.6 6.4 10 9.9m-7.4-3.5v7.2L10 17m0-7.1v7.1m0-7.1 7.4-3.5m-7.4 10.6 7.4-3.5V6.4"/></svg>' },
        { key: "wholesalers", label: "Wholesalers", icon: '<svg viewBox="0 0 20 20"><path d="M3 7.6 10 3l7 4.6M4.6 8.2v8.4h10.8V8.2M8 16.6v-5h4v5"/></svg>' },
        { key: "notifications", label: "Notifications", icon: '<svg viewBox="0 0 20 20"><path d="M10 3.1a4 4 0 0 1 4 4v2.3c0 1 .4 2 1.1 2.7l.4.4H4.5l.4-.4A3.9 3.9 0 0 0 6 9.4V7.1a4 4 0 0 1 4-4Z"/><path d="M8.3 15a1.8 1.8 0 0 0 3.4 0"/></svg>' },
      ];
      if (this.isAdmin) {
        items.splice(4, 0, { key: "approvals", label: "Approvals", icon: '<svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="7.2"/><path d="M6.8 10.1l2.1 2.1 4.3-4.6"/></svg>' });
        items.push({ key: "staff", label: "Staff", icon: '<svg viewBox="0 0 20 20"><circle cx="7.1" cy="6.9" r="2.3"/><circle cx="13.2" cy="7.5" r="1.9"/><path d="M2.8 16.4c.4-2.7 2.2-4.2 4.3-4.2s3.9 1.5 4.3 4.2M12.1 12.6c1.7 0 3.4 1.2 3.8 3.7"/></svg>' });
      }
      return items;
    },
    currentViewTitle() {
      const titles = {
        dashboard: 'Dashboard',
        sales: 'Sales',
        purchases: 'Purchases',
        wholesalers: 'Wholesalers & khata',
        approvals: 'Pending approvals',
        notifications: 'Notifications',
        staff: 'Staff management'
      };
      return titles[this.view] || 'Amardeep Readymade';
    },
    currentViewSubtitle() {
      const subtitles = {
        dashboard: "A quick look at today's shop",
        sales: 'Record and review daily sales',
        purchases: 'Stock coming in from wholesalers',
        wholesalers: 'Suppliers and running balances',
        approvals: 'Entries staff have added, waiting on you',
        notifications: 'Recent activity across the shop',
        staff: 'Everyone with access to this account'
      };
      return subtitles[this.view] || 'Retail management system';
    },
    formattedDate() {
      return new Date().toLocaleDateString('en-GB', {
        weekday: 'long',
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    },
  },
  async created() {
    this.token = localStorage.getItem("token");
    if (this.token) {
      try {
        const res = await api.get("/auth/me");
        this.user = res.user;
        await this.loadDashboard();
        await this.updateCounts();
      } catch (e) {
        this.logout();
      }
    }
  },
  methods: {
    fmt(val) { return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(val || 0); },
    showToast(msg, type = "ok") {
      this.toast = msg;
      this.toastType = type;
      setTimeout(() => (this.toast = ""), 3000);
    },
    async login() {
      this.loading = true;
      this.error = "";
      try {
        const res = await api.post("/auth/login", this.loginForm);
        this.token = res.token;
        this.user = res.user;
        localStorage.setItem("token", res.token);
        await this.loadDashboard();
        await this.updateCounts();
        this.showToast("Welcome back!");
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
    logout() {
      this.user = null;
      this.token = null;
      localStorage.removeItem("token");
      this.view = "dashboard";
    },
    async updateCounts() {
      try {
        const n = await api.get("/notifications");
        this.unreadCount = n.unread_count;
        if (this.isAdmin) {
          const ps = await api.get("/sales/pending");
          const pp = await api.get("/purchases/pending");
          this.pendingCount = ps.sales.length + pp.purchases.length;
        }
      } catch (e) {}
    },
    async loadDashboard() {
      try {
        const s = await api.get("/sales");
        const m = await api.get("/sales/monthly", { month: this.salesMonth });
        const w = await api.get("/wholesalers");
        const p = await api.get("/purchases");
        
        this.dash = {
          todayAmount: s.totals.amount,
          todayCount: s.totals.count,
          todayPieces: s.totals.pieces,
          monthAmount: m.totals.amount,
          monthCount: m.totals.count,
          totalDebt: w.totals.debt,
          totalUchanti: w.totals.uchanti,
          recentSales: s.sales.slice(-5).reverse(),
          recentPurchases: p.purchases.slice(-5).reverse(),
        };
      } catch (e) {
        this.showToast(e.message, "error");
      }
    },
    go(view) {
      this.view = view;
      if (view === "sales") this.loadDailySales();
      if (view === "purchases") this.loadPurchases();
      if (view === "wholesalers") this.loadWholesalers();
      if (view === "approvals") this.loadApprovals();
      if (view === "staff") this.loadStaff();
      if (view === "notifications") this.loadNotifications();
    },
    async loadDailySales() {
      try {
        const res = await api.get("/sales", { date: this.salesDate });
        this.salesList = res.sales;
        this.salesTotals = res.totals;
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async loadMonthlySales() {
      try {
        const res = await api.get("/sales/monthly", { month: this.salesMonth });
        this.monthly = res;
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async addSale() {
      this.loading = true;
      try {
        await api.post("/sales", this.saleForm);
        this.showToast("Sale added successfully!");
        this.saleForm = { item: "", piece: 1, total_price: 0, sale_date: new Date().toISOString().split("T")[0], notes: "" };
        await this.loadDailySales();
        await this.updateCounts();
      } catch (e) { this.showToast(e.message, "error"); }
      finally { this.loading = false; }
    },
    async approveSale(id) {
      try {
        await api.post(`/sales/${id}/approve`);
        this.showToast("Sale approved");
        await this.loadDailySales();
        await this.loadApprovals();
        await this.updateCounts();
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async rejectSale(id) {
      try {
        await api.post(`/sales/${id}/reject`);
        this.showToast("Sale rejected", "error");
        await this.loadDailySales();
        await this.loadApprovals();
        await this.updateCounts();
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async loadPurchases() {
      try {
        const res = await api.get("/purchases", { date: this.purchaseDate });
        this.purchases = res.purchases;
        this.purchaseTotals = res.totals;
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async addPurchase() {
      this.loading = true;
      try {
        await api.post("/purchases", this.purchaseForm);
        this.showToast("Purchase added!");
        this.purchaseForm = { wholesaler_id: "", item: "", piece: 1, total_price: 0, purchase_date: new Date().toISOString().split("T")[0], on_credit: false, notes: "" };
        await this.loadPurchases();
        await this.updateCounts();
      } catch (e) { this.showToast(e.message, "error"); }
      finally { this.loading = false; }
    },
    async approvePurchase(id) {
      try {
        await api.post(`/purchases/${id}/approve`);
        this.showToast("Purchase approved");
        await this.loadPurchases();
        await this.loadApprovals();
        await this.updateCounts();
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async rejectPurchase(id) {
      try {
        await api.post(`/purchases/${id}/reject`);
        this.showToast("Purchase rejected", "error");
        await this.loadPurchases();
        await this.loadApprovals();
        await this.updateCounts();
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async loadWholesalers() {
      try {
        const res = await api.get("/wholesalers");
        this.wholesalers = res.wholesalers;
        this.wholesalerTotals = res.totals;
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async addWholesaler() {
      this.loading = true;
      try {
        await api.post("/wholesalers", this.wholesalerForm);
        this.showToast("Wholesaler added!");
        this.wholesalerForm = { name: "", phone: "", address: "" };
        await this.loadWholesalers();
      } catch (e) { this.showToast(e.message, "error"); }
      finally { this.loading = false; }
    },
    async selectWholesaler(w) {
      this.selectedWholesaler = w;
      try {
        const res = await api.get(`/wholesalers/${w.id}/khata-history`);
        this.khataHistory = res.transactions;
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async updateKhata() {
      this.loading = true;
      try {
        const res = await api.post(`/wholesalers/${this.selectedWholesaler.id}/khata`, this.khataForm);
        this.showToast("Khata updated!");
        this.selectedWholesaler = res.wholesaler;
        if (res.transaction) {
          this.khataHistory.unshift(res.transaction);
        }
        await this.loadWholesalers();
        this.khataForm = { khata_type: "debt", entry_type: "add", amount: 0, note: "" };
      } catch (e) { this.showToast(e.message, "error"); }
      finally { this.loading = false; }
    },
    async deleteWholesaler(w) {
      if (!confirm(`Delete ${w.name}?`)) return;
      try {
        await api.delete(`/wholesalers/${w.id}`);
        this.showToast("Wholesaler deleted");
        await this.loadWholesalers();
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async loadApprovals() {
      try {
        const s = await api.get("/sales/pending");
        const p = await api.get("/purchases/pending");
        this.pendingSales = s.sales;
        this.pendingPurchases = p.purchases;
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async loadStaff() {
      try {
        const res = await api.get("/users");
        this.users = res.users;
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async addUser() {
      this.loading = true;
      try {
        await api.post("/users", this.userForm);
        this.showToast("User added!");
        this.userForm = { name: "", username: "", password: "", role: "staff" };
        await this.loadStaff();
      } catch (e) { this.showToast(e.message, "error"); }
      finally { this.loading = false; }
    },
    async toggleActive(u) {
      try {
        await api.put(`/users/${u.id}`, { is_active: !u.is_active });
        this.showToast("Status updated");
        await this.loadStaff();
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async removeUser(u) {
      if (!confirm(`Remove ${u.name}?`)) return;
      try {
        await api.delete(`/users/${u.id}`);
        this.showToast("User removed");
        await this.loadStaff();
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async loadNotifications() {
      try {
        const res = await api.get("/notifications");
        this.notifications = res.notifications;
        this.unreadCount = res.unread_count;
      } catch (e) { this.showToast(e.message, "error"); }
    },
    async markRead(id) {
      try {
        await api.post(`/notifications/${id}/read`);
        await this.loadNotifications();
        await this.updateCounts();
      } catch (e) {}
    },
    async markAllRead() {
      try {
        await api.post("/notifications/read-all");
        await this.loadNotifications();
        await this.updateCounts();
      } catch (e) {}
    },
  },
}).mount("#app");

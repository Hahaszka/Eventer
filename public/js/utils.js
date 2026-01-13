const Utils = {
    CATEGORIES: {
        "SPORT": { label: "Sport", color: "#2ecc71", icon: "fa-running", bg: "bg-success" },
        "PARTY": { label: "Impreza", color: "#e74c3c", icon: "fa-glass-cheers", bg: "bg-danger" },
        "LEARNING": { label: "Nauka", color: "#3498db", icon: "fa-book", bg: "bg-primary" },
        "CULTURE": { label: "Kultura", color: "#9b59b6", icon: "fa-theater-masks", bg: "bg-purple" },
        "OTHER": { label: "Inne", color: "#95a5a6", icon: "fa-map-marker-alt", bg: "bg-secondary" }
    },

    getCategoryDetails: function(code) {
        return this.CATEGORIES[code] || this.CATEGORIES["OTHER"];
    },

    getCategoryBadge: function(code) {
        const cat = this.getCategoryDetails(code);
        return `<span class="badge rounded-pill text-white" style="background-color: ${cat.color}">
                    <i class="fas ${cat.icon} me-1"></i> ${cat.label}
                </span>`;
    },

    getApiError: function(xhr, defaultMsg = "Wystąpił błąd.") {
        if (xhr.responseJSON && xhr.responseJSON.detail) {
            const detail = xhr.responseJSON.detail;
            if (Array.isArray(detail)) {
                return detail[0].msg.replace("Value error, ", "");
            }
            return detail;
        }
        return defaultMsg;
    },

    escapeHtml: function(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
            .replace(/\n/g, "<br>");
    },

    formatDate: function(isoString) {
        if (!isoString) return "Brak daty";
        return new Date(isoString).toLocaleDateString('pl-PL', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    toLocalIsoString: function(isoString) {
        if (!isoString) return "";
        const d = new Date(isoString);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        return d.toISOString().slice(0, 16);
    }
};
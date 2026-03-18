class NotificationWebSocket {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3 seconds
        this.isConnected = false;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;

        // Get JWT token from localStorage or cookies
        const token = this.getAuthToken();

        if (!token) {
            console.error('No authentication token found for WebSocket connection');
            return;
        }

        const wsUrl = `${protocol}//${host}/ws/notification/?token=${token}`;
        console.log('🔔 Connecting to notification WebSocket');

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                console.log('WebSocket connected for notification updates');
                this.isConnected = true;
                this.reconnectAttempts = 0;
            };

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'notification_update') {
                    this.handleNotificationUpdate(data);
                } else if (data.type === 'notification_count_update') {
                    this.handleNotificationCountUpdate(data);
                }
            };

            this.socket.onclose = () => {
                console.log('Notification WebSocket disconnected');
                this.isConnected = false;
                this.attemptReconnect();
            };

            this.socket.onerror = (error) => {
                console.error('Notification WebSocket error:', error);
            };

        } catch (error) {
            console.error('Failed to create notification WebSocket connection:', error);
        }
    }

    getAuthToken() {
        // Try to get token from localStorage first
        let token = localStorage.getItem('accessToken');

        // If not in localStorage, try to get from cookies
        if (!token) {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'accessToken') {
                    token = value;
                    break;
                }
            }
        }

        return token;
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect to notification WebSocket... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);
        } else {
            console.error('Max reconnection attempts reached for notification WebSocket');
        }
    }

    handleNotificationUpdate(data) {
        const { notification_id, action, notification_data, unread_count } = data;

        console.log(`🔔 Notification ${action}:`, notification_data);

        // Update notification badge count
        if (unread_count !== undefined) {
            this.updateNotificationBadge(unread_count);
        }

        // Handle different notification actions
        switch (action) {
            case 'created':
                this.showNewNotification(notification_data);
                break;
            case 'marked_read':
                this.markNotificationAsRead(notification_id);
                break;
            case 'deleted':
                this.removeNotification(notification_id);
                break;
            case 'updated':
                this.updateNotification(notification_data);
                break;
        }
    }

    handleNotificationCountUpdate(data) {
        const { unread_count } = data;
        console.log(`🔢 Notification count updated: ${unread_count}`);
        this.updateNotificationBadge(unread_count);
    }

    updateNotificationBadge(count) {
        // Update notification badge in header/navbar
        const badge = document.querySelector('.notification-badge, .notification-count');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'block' : 'none';
        }

        // Update any other notification count elements
        const countElements = document.querySelectorAll('.notification-count-text');
        countElements.forEach(element => {
            element.textContent = count;
        });
    }

    showNewNotification(notification) {
        // Create notification toast
        const toast = this.createNotificationToast(notification);
        document.body.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);

        // Add to notification list if it exists
        this.addNotificationToList(notification);
    }

    createNotificationToast(notification) {
        const toast = document.createElement('div');
        toast.className = 'notification-toast';
        toast.innerHTML = `
            <div class="notification-toast-content">
                <div class="notification-toast-header">
                    <h4>${notification.subject || 'New Notification'}</h4>
                    <button class="notification-toast-close" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="notification-toast-body">
                    <p>${notification.email_type || 'You have a new notification'}</p>
                    <small>${new Date(notification.sent_at).toLocaleString()}</small>
                </div>
            </div>
        `;
        return toast;
    }

    addNotificationToList(notification) {
        const notificationList = document.querySelector('.notification-list, .notifications-dropdown');
        if (notificationList) {
            const notificationItem = document.createElement('div');
            notificationItem.className = 'notification-item unread';
            notificationItem.setAttribute('data-notification-id', notification.id);
            notificationItem.innerHTML = `
                <div class="notification-content">
                    <div class="notification-title">${notification.subject}</div>
                    <div class="notification-description">${notification.email_type}</div>
                    <div class="notification-time">${this.formatTime(notification.sent_at)}</div>
                </div>
            `;

            // Add to beginning of list
            notificationList.insertBefore(notificationItem, notificationList.firstChild);
        }
    }

    markNotificationAsRead(notificationId) {
        const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (notificationElement) {
            notificationElement.classList.remove('unread');
            notificationElement.classList.add('read');
        }
    }

    removeNotification(notificationId) {
        const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (notificationElement) {
            notificationElement.remove();
        }
    }

    updateNotification(notificationData) {
        const notificationElement = document.querySelector(`[data-notification-id="${notificationData.id}"]`);
        if (notificationElement) {
            const titleElement = notificationElement.querySelector('.notification-title');
            const descriptionElement = notificationElement.querySelector('.notification-description');

            if (titleElement) titleElement.textContent = notificationData.subject;
            if (descriptionElement) descriptionElement.textContent = notificationData.email_type;
        }
    }

    formatTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
        return date.toLocaleDateString();
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.isConnected = false;
        }
    }
}

// Initialize WebSocket connection when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize notification WebSocket for all pages that might need notifications
    if (window.location.pathname.includes('/notification') ||
        window.location.pathname.includes('/dashboard') ||
        window.location.pathname.includes('/admin') ||
        window.location.pathname === '/') {

        window.notificationWS = new NotificationWebSocket();
        window.notificationWS.connect();
    }
});

// Clean up when page is unloaded
window.addEventListener('beforeunload', function() {
    if (window.notificationWS) {
        window.notificationWS.disconnect();
    }
});

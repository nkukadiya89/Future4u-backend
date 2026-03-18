class DeviceStatusWebSocket {
    constructor(deviceId = null) {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3 seconds
        this.isConnected = false;
        this.deviceId = deviceId;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;

        // Use device-specific URL if deviceId is provided, otherwise use general URL
        let wsUrl;
        if (this.deviceId) {
            wsUrl = `${protocol}//${host}/ws/device-detail/${this.deviceId}/`;
            console.log(`📱 Connecting to device-specific WebSocket for device ${this.deviceId}`);
        } else {
            wsUrl = `${protocol}//${host}/ws/device-status/`;
            console.log('📡 Connecting to general device status WebSocket');
        }

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                console.log('WebSocket connected for device status updates');
                this.isConnected = true;
                this.reconnectAttempts = 0;
            };

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'device_status_update') {
                    this.updateDeviceStatus(data);
                }
            };

            this.socket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.attemptReconnect();
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    updateDeviceStatus(data) {
        const { device_id, device_code, is_light_on, is_online } = data;

        // Find the device row by device_code or device_id
        let deviceRow = null;

        // Try to find by device_code first
        if (device_code) {
            deviceRow = document.querySelector(`[data-device-code="${device_code}"]`);
        }

        // If not found by device_code, try by device_id
        if (!deviceRow && device_id) {
            deviceRow = document.querySelector(`[data-device-id="${device_id}"]`);
        }

        if (deviceRow) {
            // Find the bulb icon element
            const bulbIcon = deviceRow.querySelector('.device-status-bulb, .bulb-icon');

            if (bulbIcon) {
                // Update bulb icon based on light status
                if (is_light_on) {
                    bulbIcon.src = bulbIcon.src.replace('bulb-off.png', 'bulb-on.png')
                                                  .replace('bulb-grey.png', 'bulb-yellow.png');
                    bulbIcon.alt = 'Light On';
                    bulbIcon.title = 'Light On';
                } else {
                    bulbIcon.src = bulbIcon.src.replace('bulb-on.png', 'bulb-off.png')
                                                  .replace('bulb-yellow.png', 'bulb-grey.png');
                    bulbIcon.alt = 'Light Off';
                    bulbIcon.title = 'Light Off';
                }
            }

            // Update online status if needed
            const onlineStatus = deviceRow.querySelector('.online-status');
            if (onlineStatus) {
                if (is_online) {
                    onlineStatus.classList.remove('offline');
                    onlineStatus.classList.add('online');
                    onlineStatus.textContent = 'Online';
                } else {
                    onlineStatus.classList.remove('online');
                    onlineStatus.classList.add('offline');
                    onlineStatus.textContent = 'Offline';
                }
            }
        } else {
            console.log(`Device row not found for device_code: ${device_code}, device_id: ${device_id}`);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.isConnected = false;
        }
    }
}

// Initialize the WebSocket connection when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a device detail page and extract device ID
    let deviceId = null;

    if (window.location.pathname.includes('/device-detail/')) {
        // Extract device ID from URL like /device-detail/2/
        const pathMatch = window.location.pathname.match(/\/device-detail\/(\d+)\/?/);
        if (pathMatch && pathMatch[1]) {
            deviceId = pathMatch[1];
            console.log(`📱 Detected device detail page for device ID: ${deviceId}`);
        }
    }

    // Initialize WebSocket for device detail pages or general device pages
    if (window.location.pathname.includes('/device-detail') ||
        window.location.pathname.includes('/device')) {

        window.deviceStatusWS = new DeviceStatusWebSocket(deviceId);
        window.deviceStatusWS.connect();
    }
});

// Clean up when page is unloaded
window.addEventListener('beforeunload', function() {
    if (window.deviceStatusWS) {
        window.deviceStatusWS.disconnect();
    }
});

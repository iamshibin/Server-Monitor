class SinewaveStats {
    constructor() {
        this.memberData = [];
        this.messageData = [];
        this.memberChart = null;
        this.messageChart = null;
        this.autoRefreshInterval = null;
        this.isAutoRefreshEnabled = false;

        // Create loading overlay
        this.loadingOverlay = document.createElement('div');
        this.loadingOverlay.className = 'loading-overlay';
        this.loadingOverlay.innerHTML = '<div class="loading-spinner"></div>';
        document.querySelector('.container').appendChild(this.loadingOverlay);

        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadData();
        this.createCharts();
        this.updateStatusBar();
    }

    setupEventListeners() {
        document.getElementById('timeRange').addEventListener('change', () => {
            this.updateCharts();
        });

        const refreshBtn = document.getElementById('refreshBtn');
        refreshBtn.addEventListener('click', async () => {
            this.showLoading();
            await this.loadData();
            this.updateCharts();
            this.updateStatusBar();
            this.hideLoading();
        });

        document.getElementById('autoRefresh').addEventListener('click', () => {
            this.toggleAutoRefresh();
        });
    }

    showLoading() {
        this.loadingOverlay.classList.add('active');
    }

    hideLoading() {
        this.loadingOverlay.classList.remove('active');
    }

    async loadData() {
        try {
            const [memberResponse, messageResponse] = await Promise.all([
                fetch('https://raw.githubusercontent.com/ThatSINEWAVE/Server-Monitor/refs/heads/main/data/member_count.json'),
                fetch('https://raw.githubusercontent.com/ThatSINEWAVE/Server-Monitor/refs/heads/main/data/messages.json')
            ]);

            if (!memberResponse.ok || !messageResponse.ok) {
                throw new Error('Failed to fetch data');
            }

            this.memberData = await memberResponse.json();
            this.messageData = await messageResponse.json();

            // Sort data by timestamp
            this.memberData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            this.messageData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load server data. Please try again later.');
        }
    }

    filterDataByTimeRange(data) {
        const timeRange = document.getElementById('timeRange').value;
        if (timeRange === 'all') return data;

        const hours = parseInt(timeRange);
        const cutoffTime = new Date(Date.now() - hours * 60 * 60 * 1000);

        return data.filter(item => new Date(item.timestamp) >= cutoffTime);
    }

    createCharts() {
        this.createMemberChart();
        this.createMessageChart();
    }

    createMemberChart() {
        const ctx = document.getElementById('memberChart').getContext('2d');

        this.memberChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Total Members',
                    data: [],
                    borderColor: 'rgba(255, 42, 42, 1)',
                    backgroundColor: 'rgba(255, 42, 42, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(255, 42, 42, 1)',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }, {
                    label: 'Online Members',
                    data: [],
                    borderColor: 'rgba(255, 107, 107, 1)',
                    backgroundColor: 'rgba(255, 107, 107, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(255, 107, 107, 1)',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#ffffff',
                            font: {
                                family: 'Roboto',
                                size: 14
                            },
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(10, 10, 10, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: 'rgba(255, 42, 42, 0.5)',
                        borderWidth: 1,
                        padding: 12,
                        usePointStyle: true,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.raw}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#aaaaaa',
                            maxTicksLimit: 8,
                            font: {
                                family: 'Roboto'
                            }
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#aaaaaa',
                            font: {
                                family: 'Roboto'
                            }
                        },
                        beginAtZero: false
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    line: {
                        cubicInterpolationMode: 'monotone'
                    }
                }
            }
        });

        this.updateMemberChart();
    }

    createMessageChart() {
        const ctx = document.getElementById('messageChart').getContext('2d');

        this.messageChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Messages (Last 10min)',
                    data: [],
                    borderColor: 'rgba(255, 42, 42, 1)',
                    backgroundColor: 'rgba(255, 42, 42, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(255, 42, 42, 1)',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#ffffff',
                            font: {
                                family: 'Roboto',
                                size: 14
                            },
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(10, 10, 10, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: 'rgba(255, 42, 42, 0.5)',
                        borderWidth: 1,
                        padding: 12,
                        usePointStyle: true
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#aaaaaa',
                            maxTicksLimit: 8,
                            font: {
                                family: 'Roboto'
                            }
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#aaaaaa',
                            font: {
                                family: 'Roboto'
                            }
                        },
                        beginAtZero: true
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    line: {
                        cubicInterpolationMode: 'monotone'
                    }
                }
            }
        });

        this.updateMessageChart();
    }

    updateCharts() {
        this.updateMemberChart();
        this.updateMessageChart();
    }

    updateMemberChart() {
        if (!this.memberChart || !this.memberData.length) return;

        const filteredData = this.filterDataByTimeRange(this.memberData);
        const labels = filteredData.map(item =>
            new Date(item.timestamp).toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            })
        );

        this.memberChart.data.labels = labels;
        this.memberChart.data.datasets[0].data = filteredData.map(item => item.total_members);
        this.memberChart.data.datasets[1].data = filteredData.map(item => item.online_members);
        this.memberChart.update('none');
    }

    updateMessageChart() {
        if (!this.messageChart || !this.messageData.length) return;

        const filteredData = this.filterDataByTimeRange(this.messageData);
        const labels = filteredData.map(item =>
            new Date(item.timestamp).toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            })
        );

        this.messageChart.data.labels = labels;
        this.messageChart.data.datasets[0].data = filteredData.map(item => item.messages_last_10min);
        this.messageChart.update('none');
    }

    updateStatusBar() {
        if (!this.memberData.length || !this.messageData.length) return;

        const latestMember = this.memberData[this.memberData.length - 1];
        const latestMessage = this.messageData[this.messageData.length - 1];

        document.getElementById('totalMembers').textContent = latestMember.total_members;
        document.getElementById('onlineMembers').textContent = latestMember.online_members;
        document.getElementById('recentMessages').textContent = latestMessage.messages_last_10min;

        const lastUpdate = new Date(latestMember.timestamp);
        document.getElementById('lastUpdated').textContent = lastUpdate.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

        // Add pulse animation to status bar on update
        const statusBar = document.querySelector('.status-bar');
        statusBar.classList.remove('pulse');
        void statusBar.offsetWidth; // Trigger reflow
        statusBar.classList.add('pulse');
    }

    toggleAutoRefresh() {
        const btn = document.getElementById('autoRefresh');

        if (this.isAutoRefreshEnabled) {
            clearInterval(this.autoRefreshInterval);
            this.isAutoRefreshEnabled = false;
            btn.textContent = 'Enable Auto';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
        } else {
            this.autoRefreshInterval = setInterval(async () => {
                await this.loadData();
                this.updateCharts();
                this.updateStatusBar();
            }, 30000); // Refresh every 30 seconds

            this.isAutoRefreshEnabled = true;
            btn.textContent = 'Disable Auto';
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary');
        }
    }

    showError(message) {
        const container = document.querySelector('.container');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = message;
        container.appendChild(errorDiv);

        // Show error
        setTimeout(() => {
            errorDiv.classList.add('show');
        }, 10);

        // Hide after 5 seconds
        setTimeout(() => {
            errorDiv.classList.remove('show');
            setTimeout(() => {
                errorDiv.remove();
            }, 300);
        }, 5000);
    }
}

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new SinewaveStats();
});
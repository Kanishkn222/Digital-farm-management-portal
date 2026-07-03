// Digital Farm Management Portal - Analytics & Visualizations

document.addEventListener('DOMContentLoaded', function() {
    // Determine which elements exist on the page before initiating charts
    const populationChartEl = document.getElementById('populationChart');
    const biosecurityChartEl = document.getElementById('biosecurityTrendChart');
    const healthDistributionChartEl = document.getElementById('healthStatusChart');
    const diseaseIncidentChartEl = document.getElementById('diseaseIncidentChart');

    // Fetch dynamic chart metrics from API or fallback to mock representation
    fetch('/api/chart-data')
        .then(response => {
            if (!response.ok) throw new Error('API down');
            return response.json();
        })
        .then(data => {
            initializeCharts(data);
        })
        .catch(err => {
            console.warn("API unavailable, running charts with pre-populated dashboard data:", err);
            // High fidelity fallback data
            const fallbackData = {
                livestock_counts: {
                    farms: ['North Farm', 'East Valley', 'South Ridge', 'West Range'],
                    pigs: [120, 240, 180, 90],
                    poultry: [1500, 3200, 2100, 1100]
                },
                biosecurity_trends: {
                    dates: ['May 01', 'May 15', 'Jun 01', 'Jun 15', 'Jul 01'],
                    scores: [72, 78, 85, 82, 91]
                },
                health_distribution: {
                    labels: ['Healthy', 'Sick', 'Quarantined', 'Treatment'],
                    values: [88, 4, 3, 5]
                },
                disease_incidents: {
                    months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    counts: [5, 2, 8, 4, 3, 1]
                }
            };
            initializeCharts(fallbackData);
        });

    function initializeCharts(data) {
        // 1. Dashboard: Pig vs Poultry Comparison (Double Bar/Line Combo)
        if (populationChartEl) {
            new Chart(populationChartEl, {
                type: 'bar',
                data: {
                    labels: data.livestock_counts.farms,
                    datasets: [
                        {
                            label: 'Pigs (Qty)',
                            data: data.livestock_counts.pigs,
                            backgroundColor: '#3b82f6',
                            borderColor: '#3b82f6',
                            borderWidth: 1,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Poultry (Qty)',
                            data: data.livestock_counts.poultry,
                            backgroundColor: '#10b981',
                            borderColor: '#10b981',
                            borderWidth: 1,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#94a3b8', font: { family: 'Inter' } }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            grid: { color: '#334155' },
                            ticks: { color: '#3b82f6' },
                            title: { display: true, text: 'Pigs', color: '#3b82f6' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            ticks: { color: '#10b981' },
                            title: { display: true, text: 'Poultry', color: '#10b981' }
                        }
                    }
                }
            });
        }

        // 2. Dashboard: Biosecurity History Trend (Line Chart)
        if (biosecurityChartEl) {
            new Chart(biosecurityChartEl, {
                type: 'line',
                data: {
                    labels: data.biosecurity_trends.dates,
                    datasets: [{
                        label: 'Average Score (%)',
                        data: data.biosecurity_trends.scores,
                        fill: true,
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderColor: '#10b981',
                        borderWidth: 3,
                        tension: 0.4,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#ffffff',
                        pointHoverRadius: 7
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' }
                        },
                        y: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' },
                            min: 0,
                            max: 100
                        }
                    }
                }
            });
        }

        // 3. Reports: Livestock Health Distribution (Doughnut Chart)
        if (healthDistributionChartEl) {
            new Chart(healthDistributionChartEl, {
                type: 'doughnut',
                data: {
                    labels: data.health_distribution.labels,
                    datasets: [{
                        data: data.health_distribution.values,
                        backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#0ea5e9'],
                        borderWidth: 2,
                        borderColor: '#1e293b'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#94a3b8', font: { family: 'Inter' } }
                        }
                    },
                    cutout: '65%'
                }
            });
        }

        // 4. Reports: Disease Reports History (Bar Chart)
        if (diseaseIncidentChartEl) {
            new Chart(diseaseIncidentChartEl, {
                type: 'bar',
                data: {
                    labels: data.disease_incidents.months,
                    datasets: [{
                        label: 'Incident Cases Logged',
                        data: data.disease_incidents.counts,
                        backgroundColor: '#ef4444',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' }
                        },
                        y: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' },
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    }
});

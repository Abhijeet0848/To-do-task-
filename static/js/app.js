// ZenTask Client-Side Interactivity & State Management Logic

document.addEventListener('DOMContentLoaded', () => {
    // CSRF Token Cache
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    // Helper for secure API calls with automatic CSRF token injection
    const secureFetch = async (url, options = {}) => {
        options.headers = options.headers || {};
        
        // Add CSRF header for mutating HTTP verbs
        const method = (options.method || 'GET').toUpperCase();
        if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && csrfToken) {
            options.headers['X-CSRFToken'] = csrfToken;
        }

        // If body is an object and not FormData, stringify it and set Content-Type
        if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(options.body);
        }

        return fetch(url, options);
    };

    // DOM Cache
    const searchInput = document.getElementById('search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const priorityFilter = document.getElementById('priority-filter');
    const categoryChips = document.querySelectorAll('#category-filter-group .filter-chip');
    const addTaskBtn = document.getElementById('add-task-btn');
    const taskModal = document.getElementById('task-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const cancelModalBtn = document.getElementById('cancel-modal-btn');
    const taskForm = document.getElementById('task-form');
    const tasksContainer = document.getElementById('tasks-container');
    
    // Stats Cache
    const statsTotalVal = document.getElementById('stats-total-val');
    const statsPendingVal = document.getElementById('stats-pending-val');
    const statsCompletedVal = document.getElementById('stats-completed-val');
    const statsRateVal = document.getElementById('stats-rate-val');
    const statsProgressBar = document.getElementById('stats-progress-bar');
    
    // Settings DOM Cache
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    const cancelSettingsBtn = document.getElementById('cancel-settings-btn');
    const settingsForm = document.getElementById('settings-form');
    const settingsEmailInput = document.getElementById('settings-email');
    const settingsRemindersEnabledInput = document.getElementById('settings-reminders-enabled');
    const settingsSmtpServerInput = document.getElementById('settings-smtp-server');
    const settingsSmtpPortInput = document.getElementById('settings-smtp-port');
    const settingsSmtpUserInput = document.getElementById('settings-smtp-user');
    const settingsSmtpPassInput = document.getElementById('settings-smtp-pass');
    const emailLogViewer = document.getElementById('email-log-viewer');
    const refreshEmailLogsBtn = document.getElementById('refresh-email-logs-btn');

    // Notifications DOM Cache
    const notifBtn = document.getElementById('notif-btn');
    const notifPanel = document.getElementById('notif-panel');
    const notifBadge = document.getElementById('notif-badge');
    const notifList = document.getElementById('notif-list');
    const markAllReadBtn = document.getElementById('mark-all-read-btn');

    // Navigation and View Containers
    const allNavTabs = document.querySelectorAll('.nav-tab, .mobile-nav-tab');
    const viewContainers = document.querySelectorAll('.view-container');

    // Calendar Elements
    const prevMonthBtn = document.getElementById('prev-month-btn');
    const nextMonthBtn = document.getElementById('next-month-btn');
    const calendarMonthTitle = document.getElementById('calendar-month-title');
    const calendarGrid = document.getElementById('calendar-grid');

    // Attachment Form DOM Elements
    const modalAttachmentsSection = document.getElementById('modal-attachments-section');
    const modalAttachmentsList = document.getElementById('modal-attachments-list');
    const attachmentDropzone = document.getElementById('attachment-dropzone');
    const attachmentFileInput = document.getElementById('attachment-file-input');

    // Chatbot Elements
    const chatbotTriggerBtn = document.getElementById('chatbot-trigger-btn');
    const chatbotWindow = document.getElementById('chatbot-window');
    const closeChatbotBtn = document.getElementById('close-chatbot-btn');
    const chatbotForm = document.getElementById('chatbot-form');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotMessages = document.getElementById('chatbot-messages');

    // State management
    let currentCategory = '';
    let currentPriority = '';
    let currentSearch = '';
    let allTasks = [];
    let currentView = 'board';
    let calendarDate = new Date();
    let currentEditingTaskId = null;
    
    // Chart.js Instances
    let productivityChart = null;
    let priorityChart = null;
    let categoryChart = null;

    // ==========================================================================
    // Utilities: Escape HTML & Toast
    // ==========================================================================
    const escapeHTML = (str) => {
        if (!str) return '';
        const p = document.createElement('p');
        p.appendChild(document.createTextNode(str));
        return p.innerHTML;
    };

    const showToast = (message, type = 'success') => {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast-notif ${type}`;
        
        let iconClass = 'fa-solid fa-circle-info';
        if (type === 'success') iconClass = 'fa-solid fa-circle-check';
        if (type === 'warning') iconClass = 'fa-solid fa-triangle-exclamation';
        if (type === 'danger') iconClass = 'fa-solid fa-circle-exclamation';
        
        toast.innerHTML = `
            <i class="${iconClass}" style="font-size: 1.1rem;"></i>
            <span>${escapeHTML(message)}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('toast-fade-out');
            toast.addEventListener('animationend', () => toast.remove());
        }, 3500);
    };

    // ==========================================================================
    // Navigation / View Switching
    // ==========================================================================
    const switchView = async (viewName) => {
        currentView = viewName;
        
        allNavTabs.forEach(t => {
            if (t.getAttribute('data-view') === viewName) {
                t.classList.add('active');
            } else {
                t.classList.remove('active');
            }
        });

        viewContainers.forEach(container => {
            if (container.id === `${viewName}-view`) {
                container.classList.remove('hidden');
            } else {
                container.classList.add('hidden');
            }
        });

        if (viewName === 'board') {
            await fetchTasks();
        } else if (viewName === 'calendar') {
            renderCalendar();
        } else if (viewName === 'analytics') {
            loadAnalytics();
        }
    };

    allNavTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetView = tab.getAttribute('data-view');
            switchView(targetView);
        });
    });

    window.addEventListener('themechanged', () => {
        if (currentView === 'analytics') {
            loadAnalytics();
        }
    });

    // ==========================================================================
    // Fetch & Render Tasks
    // ==========================================================================
    const fetchTasks = async () => {
        const queryParams = new URLSearchParams();
        if (currentCategory) queryParams.append('category', currentCategory);
        if (currentPriority) queryParams.append('priority', currentPriority);
        if (currentSearch) queryParams.append('search', currentSearch);
        
        try {
            const response = await secureFetch(`/api/tasks?${queryParams.toString()}`);
            if (!response.ok) throw new Error('Failed to fetch tasks');
            allTasks = await response.json();
            renderTasksList(allTasks);
        } catch (error) {
            console.error('Error fetching tasks:', error);
            showToast("Failed to sync board tasks", 'danger');
        }
    };

    const renderTasksList = (tasks) => {
        if (!tasksContainer) return;
        
        if (tasks.length === 0) {
            tasksContainer.innerHTML = `
                <div class="empty-state-card glass-card" id="empty-state">
                    <div class="empty-icon-wrapper">
                        <i class="fa-solid fa-feather-pointed"></i>
                    </div>
                    <h3>Your Zen board is clear</h3>
                    <p>Relax, or tap "Add Task" to organize your next objective.</p>
                </div>
            `;
            return;
        }

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        tasksContainer.innerHTML = tasks.map(task => {
            const isOverdue = task.due_date && !task.is_completed && new Date(task.due_date + 'T00:00:00') < today;
            
            let formattedDueDate = '';
            if (task.due_date) {
                const dateObj = new Date(task.due_date + 'T00:00:00');
                formattedDueDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            }

            const createdDateObj = new Date(task.created_at);
            const formattedCreatedDate = createdDateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

            const descriptionHtml = task.description 
                ? `<p class="task-desc">${escapeHTML(task.description)}</p>` 
                : '';

            const dueHtml = task.due_date 
                ? `<span class="task-due ${isOverdue ? 'overdue' : ''}">
                    <i class="fa-regular fa-calendar-days"></i> Due: ${formattedDueDate}
                   </span>` 
                : '';

            const attachmentsHtml = task.attachments && task.attachments.length > 0
                ? `<div class="task-card-attachments">
                    ${task.attachments.map(att => `
                        <a href="/api/tasks/attachments/${att.id}/download" class="attachment-chip" title="Download ${escapeHTML(att.filename)}">
                            <i class="fa-solid fa-paperclip"></i> <span>${escapeHTML(att.filename)}</span>
                        </a>
                    `).join('')}
                   </div>`
                : '';

            return `
                <div class="glass-card task-card ${task.is_completed ? 'completed' : ''} priority-${task.priority}" data-id="${task.id}" draggable="true">
                    <div class="task-card-left">
                        <div class="drag-handle" title="Drag to reorder">
                            <i class="fa-solid fa-grip-vertical"></i>
                        </div>
                        <button class="checkbox-btn" aria-label="Toggle Complete" onclick="window.toggleTaskCompletion('${task.id}')">
                            <span class="checkbox-circle">
                                <i class="fa-solid fa-check checkmark-icon"></i>
                            </span>
                        </button>
                    </div>
                    
                    <div class="task-card-content">
                        <div class="task-header">
                            <h3 class="task-title">${escapeHTML(task.title)}</h3>
                            <div class="task-badges">
                                <span class="badge badge-priority-${task.priority}">${task.priority.toUpperCase()}</span>
                                <span class="badge badge-category-${task.category}">${task.category.toUpperCase()}</span>
                            </div>
                        </div>
                        ${descriptionHtml}
                        ${attachmentsHtml}
                        <div class="task-meta">
                            ${dueHtml}
                            <span class="task-created">
                                <i class="fa-regular fa-clock"></i> ${formattedCreatedDate}
                            </span>
                        </div>
                    </div>

                    <div class="task-card-actions">
                        <button class="action-icon-btn edit-btn" title="Edit Task" aria-label="Edit Task" onclick="window.openEditModal('${task.id}')">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button class="action-icon-btn delete-btn" title="Delete Task" aria-label="Delete Task" onclick="window.deleteTask('${task.id}')">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Bind drag-and-drop
        document.querySelectorAll('.tasks-grid .task-card').forEach(addDragAndDropListeners);
    };

    // ==========================================================================
    // Task Operations: Toggle, Delete, Edit, Create
    // ==========================================================================
    window.toggleTaskCompletion = async (taskId) => {
        try {
            const card = document.querySelector(`.task-card[data-id="${taskId}"]`);
            if (card) {
                card.classList.toggle('completed');
            }

            const res = await secureFetch(`/api/tasks/${taskId}/toggle`, { method: 'POST' });
            if (!res.ok) {
                if (card) card.classList.toggle('completed');
                throw new Error('Toggle failed');
            }
            const data = await res.json();
            
            updateStats(data.stats);
            await fetchTasks();
            showToast(data.task.is_completed ? "Task marked completed!" : "Task restored to pending", 'success');
        } catch (e) {
            showToast("Failed to update task state", 'danger');
        }
    };

    window.deleteTask = async (taskId) => {
        if (!confirm("Are you sure you want to delete this task?")) return;
        try {
            const card = document.querySelector(`.task-card[data-id="${taskId}"]`);
            if (card) card.remove();

            const res = await secureFetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Delete failed');
            const data = await res.json();
            
            updateStats(data.stats);
            await fetchTasks();
            showToast("Task deleted successfully", 'success');
        } catch (e) {
            showToast("Failed to delete task", 'danger');
            fetchTasks();
        }
    };

    window.openEditModal = async (taskId) => {
        let task = allTasks.find(t => String(t.id) === String(taskId));
        if (!task) {
            await fetchTasks();
            task = allTasks.find(t => String(t.id) === String(taskId));
        }
        if (!task) return;

        currentEditingTaskId = task.id;
        document.getElementById('modal-title').textContent = "Edit Task";
        document.getElementById('task-id-input').value = task.id;
        document.getElementById('task-title-input').value = task.title;
        document.getElementById('task-desc-input').value = task.description || '';
        document.getElementById('task-category-input').value = task.category;
        document.getElementById('task-priority-input').value = task.priority;
        document.getElementById('task-date-input').value = task.due_date || '';

        // Render attachments
        modalAttachmentsSection.style.display = 'block';
        renderModalAttachments(task.attachments || []);

        taskModal.classList.add('active');
    };

    const renderModalAttachments = (attachments) => {
        if (!modalAttachmentsList) return;
        if (attachments.length === 0) {
            modalAttachmentsList.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted);">No files attached</div>`;
            return;
        }

        modalAttachmentsList.innerHTML = attachments.map(att => `
            <div style="display: flex; justify-content: space-between; align-items: center; background: var(--input-bg); border: 1px solid var(--card-border); padding: 0.4rem 0.75rem; border-radius: 0.5rem; font-size: 0.8rem;">
                <div style="display: flex; align-items: center; gap: 0.4rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    <i class="fa-solid fa-paperclip" style="color: var(--primary);"></i>
                    <span>${escapeHTML(att.filename)}</span>
                </div>
                <button type="button" class="action-icon-btn delete-btn" onclick="window.removeAttachment('${att.id}')" title="Delete Attachment" style="width: 24px; height: 24px;">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
        `).join('');
    };

    window.removeAttachment = async (attachmentId) => {
        try {
            const res = await secureFetch(`/api/tasks/attachments/${attachmentId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete attachment');
            const data = await res.json();
            
            if (data.task) {
                const idx = allTasks.findIndex(t => t.id === data.task.id);
                if (idx !== -1) allTasks[idx] = data.task;
                renderModalAttachments(data.task.attachments || []);
                renderTasksList(allTasks);
            }
            showToast("Attachment removed", 'success');
        } catch (e) {
            showToast("Failed to remove attachment", 'danger');
        }
    };

    // Modal Events
    if (addTaskBtn) {
        addTaskBtn.addEventListener('click', () => {
            currentEditingTaskId = null;
            document.getElementById('modal-title').textContent = "Create New Task";
            taskForm.reset();
            document.getElementById('task-id-input').value = '';
            modalAttachmentsSection.style.display = 'none';
            taskModal.classList.add('active');
            document.getElementById('task-title-input').focus();
        });
    }

    const closeTaskModal = () => {
        taskModal.classList.remove('active');
        currentEditingTaskId = null;
    };

    if (closeModalBtn) closeModalBtn.addEventListener('click', closeTaskModal);
    if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeTaskModal);

    // Save Task Form Submission
    if (taskForm) {
        taskForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const id = document.getElementById('task-id-input').value;
            const title = document.getElementById('task-title-input').value.trim();
            const description = document.getElementById('task-desc-input').value.trim();
            const category = document.getElementById('task-category-input').value;
            const priority = document.getElementById('task-priority-input').value;
            const due_date = document.getElementById('task-date-input').value;

            if (!title) {
                showToast("Task title is required", 'danger');
                return;
            }

            const payload = { title, description, category, priority, due_date };

            try {
                let res;
                if (id) {
                    res = await secureFetch(`/api/tasks/${id}`, {
                        method: 'PUT',
                        body: payload
                    });
                } else {
                    res = await secureFetch('/api/tasks', {
                        method: 'POST',
                        body: payload
                    });
                }

                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.error || 'Operation failed');
                }

                const data = await res.json();
                updateStats(data.stats);
                closeTaskModal();
                await fetchTasks();
                showToast(id ? "Task updated successfully" : "Task created successfully", 'success');
            } catch (err) {
                showToast(err.message || "Failed to save task", 'danger');
            }
        });
    }

    // Attachment Dropzone Handlers
    if (attachmentDropzone && attachmentFileInput) {
        attachmentDropzone.addEventListener('click', () => attachmentFileInput.click());
        
        attachmentFileInput.addEventListener('change', async () => {
            if (!attachmentFileInput.files.length || !currentEditingTaskId) return;
            const file = attachmentFileInput.files[0];
            
            if (file.size > 16 * 1024 * 1024) {
                showToast("File exceeds 16MB limit", 'danger');
                attachmentFileInput.value = '';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await secureFetch(`/api/tasks/${currentEditingTaskId}/attachments`, {
                    method: 'POST',
                    body: formData
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.error || 'Upload failed');
                }

                const data = await res.json();
                const idx = allTasks.findIndex(t => t.id === data.task.id);
                if (idx !== -1) allTasks[idx] = data.task;
                renderModalAttachments(data.task.attachments || []);
                renderTasksList(allTasks);
                showToast("File uploaded successfully", 'success');
            } catch (err) {
                showToast(err.message || "Upload failed", 'danger');
            } finally {
                attachmentFileInput.value = '';
            }
        });
    }

    // Filters and Search Events
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value;
            if (searchClearBtn) {
                searchClearBtn.classList.toggle('hidden', !currentSearch);
            }
            fetchTasks();
        });
    }

    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', () => {
            searchInput.value = '';
            currentSearch = '';
            searchClearBtn.classList.add('hidden');
            fetchTasks();
        });
    }

    if (priorityFilter) {
        priorityFilter.addEventListener('change', (e) => {
            currentPriority = e.target.value;
            fetchTasks();
        });
    }

    categoryChips.forEach(chip => {
        chip.addEventListener('click', () => {
            categoryChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentCategory = chip.getAttribute('data-category');
            fetchTasks();
        });
    });

    const updateStats = (stats) => {
        if (!stats) return;
        if (statsTotalVal) statsTotalVal.textContent = stats.total;
        if (statsPendingVal) statsPendingVal.textContent = stats.pending;
        if (statsCompletedVal) statsCompletedVal.textContent = stats.completed;
        if (statsRateVal) statsRateVal.textContent = `${stats.completion_rate}%`;
        if (statsProgressBar) statsProgressBar.style.width = `${stats.completion_rate}%`;
    };

    // ==========================================================================
    // Calendar Implementation
    // ==========================================================================
    const renderCalendar = () => {
        if (!calendarGrid || !calendarMonthTitle) return;
        
        const year = calendarDate.getFullYear();
        const month = calendarDate.getMonth();
        
        const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        calendarMonthTitle.textContent = `${monthNames[month]} ${year}`;
        
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const daysInPrevMonth = new Date(year, month, 0).getDate();
        
        const today = new Date();
        const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;
        
        calendarGrid.innerHTML = '';
        
        // Days from previous month
        for (let i = firstDayOfMonth - 1; i >= 0; i--) {
            const cell = document.createElement('div');
            cell.className = 'calendar-day-cell other-month';
            cell.innerHTML = `<span class="day-cell-num">${daysInPrevMonth - i}</span>`;
            calendarGrid.appendChild(cell);
        }
        
        // Days of current month
        for (let day = 1; day <= daysInMonth; day++) {
            const cell = document.createElement('div');
            cell.className = 'calendar-day-cell';
            
            const cellDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            if (isCurrentMonth && today.getDate() === day) {
                cell.classList.add('today');
            }
            
            // Match tasks due on this day
            const tasksDue = allTasks.filter(t => t.due_date === cellDateStr);
            
            let tasksHtml = '';
            if (tasksDue.length > 0) {
                tasksHtml = `
                    <div style="display: flex; flex-direction: column; gap: 2px;">
                        ${tasksDue.slice(0, 2).map(t => `
                            <div class="day-task-pill" title="${escapeHTML(t.title)}">${escapeHTML(t.title)}</div>
                        `).join('')}
                        ${tasksDue.length > 2 ? `<span style="font-size: 0.65rem; color: var(--text-muted);">+${tasksDue.length - 2} more</span>` : ''}
                    </div>
                    <div style="display: flex; gap: 2px;" class="mobile-dots">
                        ${tasksDue.map(() => `<span class="day-task-dot"></span>`).join('')}
                    </div>
                `;
            }
            
            cell.innerHTML = `
                <span class="day-cell-num">${day}</span>
                ${tasksHtml}
            `;

            // Click cell to view/filter
            cell.addEventListener('click', () => {
                if (tasksDue.length > 0) {
                    showToast(`${tasksDue.length} task(s) due on ${monthNames[month]} ${day}`, 'info');
                }
            });

            calendarGrid.appendChild(cell);
        }
    };

    if (prevMonthBtn) {
        prevMonthBtn.addEventListener('click', () => {
            calendarDate.setMonth(calendarDate.getMonth() - 1);
            renderCalendar();
        });
    }

    if (nextMonthBtn) {
        nextMonthBtn.addEventListener('click', () => {
            calendarDate.setMonth(calendarDate.getMonth() + 1);
            renderCalendar();
        });
    }

    // ==========================================================================
    // Analytics & Charts (Chart.js)
    // ==========================================================================
    const loadAnalytics = async () => {
        try {
            const res = await secureFetch('/api/stats');
            if (!res.ok) throw new Error('Stats error');
            const stats = await res.json();
            
            document.getElementById('anal-total-val').textContent = stats.total;
            document.getElementById('anal-completed-val').textContent = stats.completed;
            document.getElementById('anal-pending-val').textContent = stats.pending;
            document.getElementById('anal-rate-val').textContent = `${stats.completion_rate}%`;
            
            renderProductivityChart(stats.productivity || []);
            renderPriorityChart(stats.priorities || {});
            renderCategoryChart(stats.categories || {});
        } catch (e) {
            console.error('Analytics load error:', e);
        }
    };

    const isDarkMode = () => document.documentElement.getAttribute('data-theme') === 'dark';

    const renderProductivityChart = (data) => {
        const ctx = document.getElementById('productivity-chart')?.getContext('2d');
        if (!ctx) return;
        
        if (productivityChart) productivityChart.destroy();
        
        const textColor = isDarkMode() ? '#94a3b8' : '#475569';
        const gridColor = isDarkMode() ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';

        productivityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: 'Tasks Completed',
                    data: data.map(d => d.completed),
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.12)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor, precision: 0 }, beginAtZero: true }
                }
            }
        });
    };

    const renderPriorityChart = (data) => {
        const ctx = document.getElementById('priority-chart')?.getContext('2d');
        if (!ctx) return;
        if (priorityChart) priorityChart.destroy();

        priorityChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['High', 'Medium', 'Low'],
                datasets: [{
                    data: [data.high || 0, data.medium || 0, data.low || 0],
                    backgroundColor: ['#f43f5e', '#f59e0b', '#10b981'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: isDarkMode() ? '#94a3b8' : '#475569', boxWidth: 12, padding: 12 }
                    }
                },
                cutout: '70%'
            }
        });
    };

    const renderCategoryChart = (data) => {
        const ctx = document.getElementById('category-chart')?.getContext('2d');
        if (!ctx) return;
        if (categoryChart) categoryChart.destroy();

        const categories = ['personal', 'work', 'shopping', 'fitness', 'urgent', 'coding'];
        const labels = ['Personal', 'Work', 'Shopping', 'Fitness', 'Urgent', 'Coding'];
        const values = categories.map(c => data[c] || 0);

        categoryChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Tasks',
                    data: values,
                    backgroundColor: [
                        '#3b82f6', '#a855f7', '#ec4899', '#14b8a6', '#ef4444', '#f59e0b'
                    ],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: isDarkMode() ? '#94a3b8' : '#475569' } },
                    y: { grid: { color: isDarkMode() ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }, ticks: { precision: 0, color: isDarkMode() ? '#94a3b8' : '#475569' }, beginAtZero: true }
                }
            }
        });
    };

    // ==========================================================================
    // HTML5 Drag and Drop Task Reordering
    // ==========================================================================
    let dragSrcElement = null;

    function addDragAndDropListeners(card) {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragover', handleDragOver);
        card.addEventListener('dragenter', handleDragEnter);
        card.addEventListener('dragleave', handleDragLeave);
        card.addEventListener('dragend', handleDragEnd);
        card.addEventListener('drop', handleDrop);
    }

    function handleDragStart(e) {
        dragSrcElement = this;
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this.getAttribute('data-id'));
        this.style.opacity = '0.5';
    }

    function handleDragOver(e) {
        if (e.preventDefault) e.preventDefault();
        return false;
    }

    function handleDragEnter(e) {
        if (this !== dragSrcElement) {
            this.classList.add('drag-over');
        }
    }

    function handleDragLeave(e) {
        this.classList.remove('drag-over');
    }

    function handleDragEnd(e) {
        this.style.opacity = '1';
        document.querySelectorAll('.task-card').forEach(card => card.classList.remove('drag-over'));
    }

    async function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const draggedId = e.dataTransfer.getData('text/plain');
        const targetId = this.getAttribute('data-id');
        
        if (draggedId !== targetId) {
            const draggedCard = document.querySelector(`.task-card[data-id="${draggedId}"]`);
            const rect = this.getBoundingClientRect();
            const next = (e.clientY - rect.top) / (rect.bottom - rect.top) > 0.5;
            
            if (next) {
                this.parentNode.insertBefore(draggedCard, this.nextSibling);
            } else {
                this.parentNode.insertBefore(draggedCard, this);
            }
            
            const updatedOrders = [];
            const allVisibleCards = document.querySelectorAll('.tasks-grid .task-card');
            
            allVisibleCards.forEach((card, index) => {
                const id = card.getAttribute('data-id');
                updatedOrders.push({ id: id, position: index });
            });

            try {
                const res = await secureFetch('/api/tasks/reorder', {
                    method: 'POST',
                    body: { orders: updatedOrders }
                });
                
                if (res.ok) {
                    const result = await res.json();
                    updateStats(result.stats);
                    showToast("Order saved", 'success');
                }
            } catch (err) {
                showToast("Failed to reorder", 'danger');
                fetchTasks();
            }
        }
        
        this.classList.remove('drag-over');
        return false;
    }

    // ==========================================================================
    // Settings Logic
    // ==========================================================================
    if (settingsBtn) {
        settingsBtn.addEventListener('click', async () => {
            try {
                const res = await secureFetch('/api/settings');
                if (res.ok) {
                    const s = await res.json();
                    if (settingsEmailInput) settingsEmailInput.value = s.user_email || '';
                    if (settingsRemindersEnabledInput) settingsRemindersEnabledInput.checked = Boolean(s.email_reminders_enabled);
                    if (settingsSmtpServerInput) settingsSmtpServerInput.value = s.smtp_server || '';
                    if (settingsSmtpPortInput) settingsSmtpPortInput.value = s.smtp_port || 587;
                    if (settingsSmtpUserInput) settingsSmtpUserInput.value = s.smtp_user || '';
                }
                loadEmailLogs();
                settingsModal.classList.add('active');
            } catch (e) {
                showToast("Failed to load settings", 'danger');
            }
        });
    }

    const closeSettings = () => settingsModal.classList.remove('active');
    if (closeSettingsBtn) closeSettingsBtn.addEventListener('click', closeSettings);
    if (cancelSettingsBtn) cancelSettingsBtn.addEventListener('click', closeSettings);

    const loadEmailLogs = async () => {
        if (!emailLogViewer) return;
        try {
            const res = await secureFetch('/api/settings/email-logs');
            if (res.ok) {
                const data = await res.json();
                emailLogViewer.textContent = data.logs || 'No simulation logs yet.';
            }
        } catch (e) {}
    };

    if (refreshEmailLogsBtn) refreshEmailLogsBtn.addEventListener('click', loadEmailLogs);

    if (settingsForm) {
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                user_email: settingsEmailInput.value.trim(),
                email_reminders_enabled: settingsRemindersEnabledInput.checked,
                smtp_server: settingsSmtpServerInput.value.trim(),
                smtp_port: parseInt(settingsSmtpPortInput.value) || 587,
                smtp_user: settingsSmtpUserInput.value.trim(),
                smtp_password: settingsSmtpPassInput.value
            };

            try {
                const res = await secureFetch('/api/settings', {
                    method: 'POST',
                    body: payload
                });
                if (!res.ok) throw new Error();
                showToast("Settings saved successfully", 'success');
                closeSettings();
            } catch (err) {
                showToast("Failed to save settings", 'danger');
            }
        });
    }

    // ==========================================================================
    // Notifications Logic
    // ==========================================================================
    const fetchNotifications = async () => {
        try {
            const res = await secureFetch('/api/notifications');
            if (!res.ok) return;
            const data = await res.json();
            
            if (notifBadge) {
                if (data.unread_count > 0) {
                    notifBadge.textContent = data.unread_count;
                    notifBadge.classList.remove('hidden');
                } else {
                    notifBadge.classList.add('hidden');
                }
            }
            
            if (notifList) {
                if (data.notifications.length === 0) {
                    notifList.innerHTML = `<div style="padding: 1rem; text-align: center; color: var(--text-muted); font-size: 0.8rem;">No notifications yet</div>`;
                    return;
                }
                
                notifList.innerHTML = data.notifications.map(notif => {
                    const dateObj = new Date(notif.created_at);
                    const timeStr = dateObj.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                    const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                    
                    return `
                        <div class="notif-item ${notif.is_read ? '' : 'unread'}" data-id="${notif.id}">
                            <div>${escapeHTML(notif.message)}</div>
                            <div class="notif-item-meta">${dateStr} at ${timeStr}</div>
                        </div>
                    `;
                }).join('');

                notifList.querySelectorAll('.notif-item').forEach(item => {
                    item.addEventListener('click', async () => {
                        const notifId = item.getAttribute('data-id');
                        if (item.classList.contains('unread')) {
                            await secureFetch(`/api/notifications/${notifId}/read`, { method: 'POST' });
                            item.classList.remove('unread');
                            fetchNotifications();
                        }
                    });
                });
            }
        } catch (error) {
            console.error('Error fetching notifications:', error);
        }
    };

    if (notifBtn) {
        notifBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notifPanel.classList.toggle('active');
        });
    }

    document.addEventListener('click', (e) => {
        if (notifPanel && !notifPanel.contains(e.target) && e.target !== notifBtn) {
            notifPanel.classList.remove('active');
        }
    });

    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', async () => {
            try {
                const res = await secureFetch('/api/notifications/read-all', { method: 'POST' });
                if (res.ok) {
                    showToast("All notifications marked as read", 'success');
                    fetchNotifications();
                }
            } catch (e) {
                showToast("Failed to clear notifications", 'danger');
            }
        });
    }

    // ==========================================================================
    // Chatbot Assistant Logic
    // ==========================================================================
    if (chatbotTriggerBtn && chatbotWindow) {
        chatbotTriggerBtn.addEventListener('click', () => {
            chatbotWindow.classList.toggle('active');
            if (chatbotWindow.classList.contains('active')) {
                chatbotInput?.focus();
            }
        });

        if (closeChatbotBtn) {
            closeChatbotBtn.addEventListener('click', () => {
                chatbotWindow.classList.remove('active');
            });
        }

        if (chatbotForm && chatbotInput && chatbotMessages) {
            chatbotForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const userText = chatbotInput.value.trim();
                if (!userText) return;

                // Append user message
                const userMsg = document.createElement('div');
                userMsg.className = 'chat-msg user';
                userMsg.textContent = userText;
                chatbotMessages.appendChild(userMsg);
                chatbotInput.value = '';

                chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

                // AI Response Generation
                setTimeout(() => {
                    const botMsg = document.createElement('div');
                    botMsg.className = 'chat-msg bot';
                    
                    const lower = userText.toLowerCase();
                    const pendingTasks = allTasks.filter(t => !t.is_completed);
                    const completedTasks = allTasks.filter(t => t.is_completed);
                    
                    if (lower.includes('what should i do') || lower.includes('recommend') || lower.includes('suggest') || lower.includes('priority')) {
                        const highPriority = pendingTasks.filter(t => t.priority === 'high');
                        if (highPriority.length > 0) {
                            botMsg.innerHTML = `I suggest focusing on your high priority task: <strong>"${escapeHTML(highPriority[0].title)}"</strong> first!`;
                        } else if (pendingTasks.length > 0) {
                            botMsg.innerHTML = `You have ${pendingTasks.length} pending task(s). Consider tackling: <strong>"${escapeHTML(pendingTasks[0].title)}"</strong> next!`;
                        } else {
                            botMsg.textContent = "All your tasks are completed! Enjoy your day or add a new goal.";
                        }
                    } else if (lower.includes('task') || lower.includes('list') || lower.includes('pending')) {
                        botMsg.innerHTML = `You have <strong>${pendingTasks.length}</strong> pending tasks and <strong>${completedTasks.length}</strong> completed tasks.`;
                    } else if (lower.includes('hello') || lower.includes('hi') || lower.includes('hey')) {
                        botMsg.textContent = "Hello! How can I assist with your productivity today?";
                    } else if (lower.includes('thank')) {
                        botMsg.textContent = "You're very welcome! Stay focused and productive.";
                    } else {
                        botMsg.textContent = `I received: "${userText}". You can ask me to list your tasks, check priorities, or recommend what to do next!`;
                    }

                    chatbotMessages.appendChild(botMsg);
                    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
                }, 400);
            });
        }
    }

    // Global Keydown Listeners (Escape to close modals)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (taskModal?.classList.contains('active')) closeTaskModal();
            if (settingsModal?.classList.contains('active')) closeSettings();
            if (notifPanel?.classList.contains('active')) notifPanel.classList.remove('active');
            if (chatbotWindow?.classList.contains('active')) chatbotWindow.classList.remove('active');
        }
    });

    // ==========================================================================
    // App Initialization
    // ==========================================================================
    const init = async () => {
        try {
            await fetchTasks();
            fetchNotifications();
            setInterval(fetchNotifications, 20000);
        } catch (e) {
            console.error('Initialization error:', e);
        }
    };

    init();
});

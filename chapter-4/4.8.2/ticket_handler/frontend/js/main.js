// Ticket Handler - 服务台系统
class TicketHandler {
    constructor() {
        this.tickets = JSON.parse(localStorage.getItem('tickets')) || [];
        this.nextId = parseInt(localStorage.getItem('nextTicketId')) || 1;
        this.init();
    }

    init() {
        this.bindEvents();
        this.renderTickets();
    }

    bindEvents() {
        const form = document.getElementById('requestForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
    }

    handleSubmit(e) {
        e.preventDefault();
        
        // 获取表单数据
        const formData = new FormData(e.target);
        const ticketData = {
            id: this.nextId++,
            userName: formData.get('userName'),
            userEmail: formData.get('userEmail'),
            requestType: formData.get('requestType'),
            priority: formData.get('priority'),
            subject: formData.get('subject'),
            description: formData.get('description'),
            status: 'open', // 默认状态为开放
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        // 添加到工单列表
        this.addTicket(ticketData);
        
        // 重置表单
        e.target.reset();
        
        // 显示成功消息
        this.showMessage('请求已成功提交！', 'success');
        
        // 更新本地存储
        this.saveToLocalStorage();
    }

    addTicket(ticketData) {
        this.tickets.unshift(ticketData); // 添加到数组开头
        this.renderTickets();
    }

    renderTickets() {
        const ticketList = document.getElementById('ticketList');
        if (!ticketList) return;

        // 清空现有内容
        ticketList.innerHTML = '';

        if (this.tickets.length === 0) {
            ticketList.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: #7f8c8d;">暂无请求记录</td>
                </tr>
            `;
            return;
        }

        // 渲染工单列表
        this.tickets.forEach(ticket => {
            const row = document.createElement('tr');
            
            // 格式化日期
            const date = new Date(ticket.createdAt);
            const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            
            // 获取请求类型的显示文本
            const requestTypeText = this.getRequestTypeText(ticket.requestType);
            
            row.innerHTML = `
                <td>#${ticket.id}</td>
                <td>${this.escapeHtml(ticket.subject)}</td>
                <td>${requestTypeText}</td>
                <td><span class="status-${ticket.status}">${this.getStatusText(ticket.status)}</span></td>
                <td>${formattedDate}</td>
                <td class="action-buttons">
                    <button class="btn-view" onclick="ticketHandler.viewTicket(${ticket.id})">查看</button>
                    <button class="btn-edit" onclick="ticketHandler.editTicket(${ticket.id})">编辑</button>
                    <button class="btn-delete" onclick="ticketHandler.deleteTicket(${ticket.id})">删除</button>
                </td>
            `;
            
            ticketList.appendChild(row);
        });
        
        // 更新本地存储
        this.saveToLocalStorage();
    }

    getRequestTypeText(type) {
        const types = {
            'technical': '技术问题',
            'billing': '账单查询',
            'account': '账户问题',
            'feature': '功能建议',
            'other': '其他'
        };
        return types[type] || type;
    }

    getStatusText(status) {
        const statuses = {
            'open': '待处理',
            'in-progress': '处理中',
            'resolved': '已解决',
            'closed': '已关闭'
        };
        return statuses[status] || status;
    }

    viewTicket(id) {
        const ticket = this.tickets.find(t => t.id === id);
        if (!ticket) return;

        // 创建模态框显示工单详情
        this.showTicketDetailModal(ticket);
    }

    editTicket(id) {
        const ticketIndex = this.tickets.findIndex(t => t.id === id);
        if (ticketIndex === -1) return;

        const ticket = this.tickets[ticketIndex];
        
        // 弹出编辑表单
        this.showEditModal(ticket, ticketIndex);
    }

    deleteTicket(id) {
        if (confirm('确定要删除这个请求吗？此操作不可撤销。')) {
            this.tickets = this.tickets.filter(t => t.id !== id);
            this.renderTickets();
            this.showMessage('请求已删除', 'info');
        }
    }

    showTicketDetailModal(ticket) {
        // 创建模态框元素
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        modalContent.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 8px;
            width: 90%;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        `;
        
        const date = new Date(ticket.createdAt);
        const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0;">请求详情</h3>
                <button id="closeModal" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
            </div>
            <div class="detail-item">
                <strong>编号:</strong> #${ticket.id}
            </div>
            <div class="detail-item">
                <strong>提交人:</strong> ${this.escapeHtml(ticket.userName)}
            </div>
            <div class="detail-item">
                <strong>邮箱:</strong> ${this.escapeHtml(ticket.userEmail)}
            </div>
            <div class="detail-item">
                <strong>请求类型:</strong> ${this.getRequestTypeText(ticket.requestType)}
            </div>
            <div class="detail-item">
                <strong>优先级:</strong> ${this.getPriorityText(ticket.priority)}
            </div>
            <div class="detail-item">
                <strong>状态:</strong> <span class="status-${ticket.status}">${this.getStatusText(ticket.status)}</span>
            </div>
            <div class="detail-item">
                <strong>提交时间:</strong> ${formattedDate}
            </div>
            <div class="detail-item">
                <strong>主题:</strong> ${this.escapeHtml(ticket.subject)}
            </div>
            <div class="detail-item">
                <strong>详细描述:</strong>
                <div style="margin-top: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; white-space: pre-wrap;">
                    ${this.escapeHtml(ticket.description)}
                </div>
            </div>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // 绑定关闭事件
        document.getElementById('closeModal').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        // 点击背景关闭模态框
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    showEditModal(ticket, index) {
        // 创建编辑模态框
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        modalContent.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 8px;
            width: 90%;
            max-width: 600px;
        `;
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0;">编辑请求</h3>
                <button id="closeModal" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
            </div>
            <form id="editForm">
                <div class="form-group">
                    <label for="editSubject">主题</label>
                    <input type="text" id="editSubject" value="${this.escapeHtml(ticket.subject)}" required>
                </div>
                <div class="form-group">
                    <label for="editDescription">详细描述</label>
                    <textarea id="editDescription" rows="4" required>${this.escapeHtml(ticket.description)}</textarea>
                </div>
                <div class="form-group">
                    <label for="editStatus">状态</label>
                    <select id="editStatus">
                        <option value="open" ${ticket.status === 'open' ? 'selected' : ''}>待处理</option>
                        <option value="in-progress" ${ticket.status === 'in-progress' ? 'selected' : ''}>处理中</option>
                        <option value="resolved" ${ticket.status === 'resolved' ? 'selected' : ''}>已解决</option>
                        <option value="closed" ${ticket.status === 'closed' ? 'selected' : ''}>已关闭</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="editPriority">优先级</label>
                    <select id="editPriority">
                        <option value="low" ${ticket.priority === 'low' ? 'selected' : ''}>低</option>
                        <option value="medium" ${ticket.priority === 'medium' ? 'selected' : ''}>中</option>
                        <option value="high" ${ticket.priority === 'high' ? 'selected' : ''}>高</option>
                    </select>
                </div>
                <button type="submit" class="submit-btn" style="margin-top: 20px;">更新请求</button>
            </form>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // 绑定表单提交事件
        document.getElementById('editForm').addEventListener('submit', (e) => {
            e.preventDefault();
            
            // 更新工单信息
            this.tickets[index].subject = document.getElementById('editSubject').value;
            this.tickets[index].description = document.getElementById('editDescription').value;
            this.tickets[index].status = document.getElementById('editStatus').value;
            this.tickets[index].priority = document.getElementById('editPriority').value;
            this.tickets[index].updatedAt = new Date().toISOString();
            
            // 重新渲染列表
            this.renderTickets();
            
            // 关闭模态框
            document.body.removeChild(modal);
            
            this.showMessage('请求已更新', 'success');
        });
        
        // 绑定关闭事件
        document.getElementById('closeModal').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        // 点击背景关闭模态框
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    getPriorityText(priority) {
        const priorities = {
            'low': '低',
            'medium': '中',
            'high': '高'
        };
        return priorities[priority] || priority;
    }

    showMessage(message, type = 'info') {
        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.textContent = message;
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 4px;
            color: white;
            z-index: 1001;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            animation: slideIn 0.3s, fadeOut 0.5s 2.5s forwards;
        `;
        
        // 根据类型设置颜色
        switch(type) {
            case 'success':
                messageEl.style.backgroundColor = '#2ecc71';
                break;
            case 'error':
                messageEl.style.backgroundColor = '#e74c3c';
                break;
            case 'warning':
                messageEl.style.backgroundColor = '#f39c12';
                break;
            default:
                messageEl.style.backgroundColor = '#3498db';
        }
        
        document.body.appendChild(messageEl);
        
        // 3秒后移除消息
        setTimeout(() => {
            if (document.body.contains(messageEl)) {
                document.body.removeChild(messageEl);
            }
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    saveToLocalStorage() {
        localStorage.setItem('tickets', JSON.stringify(this.tickets));
        localStorage.setItem('nextTicketId', this.nextId.toString());
    }
}

// 添加动画样式到页面
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }
    
    .detail-item {
        margin-bottom: 15px;
    }
    
    .detail-item strong {
        display: inline-block;
        width: 100px;
        color: #2c3e50;
    }
`;
document.head.appendChild(style);

// 初始化应用
let ticketHandler;
document.addEventListener('DOMContentLoaded', () => {
    ticketHandler = new TicketHandler();
});
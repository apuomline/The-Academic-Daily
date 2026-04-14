/**
 * Configuration Management JavaScript
 */

const API_BASE = '/api';
let currentConfig = { llm: {}, email: {} };

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadConfigurations();  // This will populate forms with current config
    initPasswordToggles();
    initForms();
    initSystemStatus();
});

/**
 * Initialize tab switching
 */
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;

            // Update buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabName) {
                    content.classList.add('active');
                }
            });
        });
    });
}

/**
 * Initialize password visibility toggles
 */
function initPasswordToggles() {
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const input = document.getElementById(targetId);

            if (input.type === 'password') {
                input.type = 'text';
                btn.textContent = '🙈';
            } else {
                input.type = 'password';
                btn.textContent = '👁️';
            }
        });
    });
}

/**
 * Initialize form submissions
 */
function initForms() {
    // LLM form
    document.getElementById('llm-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveLLMConfig();
    });

    // Email form
    document.getElementById('email-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveEmailConfig();
    });

    // Test buttons
    document.getElementById('test-llm').addEventListener('click', testLLMConnection);
    document.getElementById('test-email').addEventListener('click', testEmailConnection);

    // Pipeline buttons
    document.getElementById('run-pipeline').addEventListener('click', runPipeline);
    document.getElementById('check-pipeline').addEventListener('click', checkPipelineStatus);

    // Paper management buttons
    document.getElementById('search-papers').addEventListener('click', searchPapers);
    document.getElementById('fetch-papers').addEventListener('click', fetchPapers);
    document.getElementById('generate-report').addEventListener('click', generateReport);
    document.getElementById('send-report').addEventListener('click', sendReport);
}

/**
 * Initialize system status
 */
function initSystemStatus() {
    loadSystemStatus();
    // Refresh status every 30 seconds
    setInterval(loadSystemStatus, 30000);
}

/**
 * Load all configurations
 */
async function loadConfigurations() {
    await Promise.all([
        loadLLMConfig(),
        loadEmailConfig(),
    ]);
}

/**
 * Load LLM configuration
 */
async function loadLLMConfig() {
    try {
        const response = await fetch(`${API_BASE}/config/llm`);
        const result = await response.json();

        if (result.success && result.data) {
            currentConfig.llm = result.data;
            populateLLMForm(result.data);
        }
    } catch (error) {
        showToast('加载 LLM 配置失败: ' + error.message, 'error');
    }
}

/**
 * Populate LLM form with data
 */
function populateLLMForm(data) {
    if (data.LLM_PROVIDER) {
        document.getElementById('llm-provider').value = data.LLM_PROVIDER;
    }
    if (data.LLM_BASE_URL) {
        document.getElementById('llm-base-url').value = data.LLM_BASE_URL;
    }
    if (data.LLM_MODEL) {
        document.getElementById('llm-model').value = data.LLM_MODEL;
    }
    if (data.LLM_TEMPERATURE) {
        document.getElementById('llm-temperature').value = data.LLM_TEMPERATURE;
    }
    if (data.LLM_MAX_TOKENS) {
        document.getElementById('llm-max-tokens').value = data.LLM_MAX_TOKENS;
    }
    // Show masked API key to indicate it's configured
    const apiKeyInput = document.getElementById('llm-api-key');
    if (data.LLM_API_KEY && data.LLM_API_KEY !== '****') {
        apiKeyInput.value = '****';
        apiKeyInput.setAttribute('data-configured', 'true');
    }
}

/**
 * Load email configuration
 */
async function loadEmailConfig() {
    try {
        const response = await fetch(`${API_BASE}/config/email`);
        const result = await response.json();

        if (result.success && result.data) {
            currentConfig.email = result.data;
            populateEmailForm(result.data);
        }
    } catch (error) {
        showToast('加载邮箱配置失败: ' + error.message, 'error');
    }
}

/**
 * Populate email form with data
 */
function populateEmailForm(data) {
    if (data.EMAIL_ENABLED) {
        document.getElementById('email-enabled').checked =
            data.EMAIL_ENABLED.toLowerCase() === 'true';
    }
    if (data.SMTP_HOST) {
        document.getElementById('smtp-host').value = data.SMTP_HOST;
    }
    if (data.SMTP_PORT) {
        document.getElementById('smtp-port').value = data.SMTP_PORT;
    }
    if (data.SMTP_USERNAME) {
        document.getElementById('smtp-username').value = data.SMTP_USERNAME;
    }
    if (data.SMTP_FROM_EMAIL) {
        document.getElementById('smtp-from-email').value = data.SMTP_FROM_EMAIL;
    }
    // Show masked password to indicate it's configured
    const passwordInput = document.getElementById('smtp-password');
    if (data.SMTP_PASSWORD && data.SMTP_PASSWORD !== '****') {
        passwordInput.value = '****';
        passwordInput.setAttribute('data-configured', 'true');
    }
    const resendKeyInput = document.getElementById('resend-api-key');
    if (data.RESEND_API_KEY && data.RESEND_API_KEY !== '****') {
        resendKeyInput.value = '****';
        resendKeyInput.setAttribute('data-configured', 'true');
    }
}

/**
 * Save LLM configuration
 */
async function saveLLMConfig() {
    const form = document.getElementById('llm-form');
    const btn = form.querySelector('button[type="submit"]');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');

    // Get form data
    const formData = new FormData(form);
    const config = {
        provider: formData.get('provider'),
        base_url: formData.get('base_url') || null,
        model: formData.get('model') || null,
        temperature: formData.get('temperature') ?
            parseFloat(formData.get('temperature')) : null,
        max_tokens: formData.get('max_tokens') ?
            parseInt(formData.get('max_tokens')) : null,
    };

    // Only include API key if it was changed
    const apiKey = formData.get('api_key');
    if (apiKey && apiKey !== '****') {
        config.api_key = apiKey;
    }

    try {
        // Show loading state
        btn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';

        const response = await fetch(`${API_BASE}/config/llm`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });

        const result = await response.json();

        if (result.success) {
            showToast('LLM 配置保存成功! 请重启服务以应用更改。', 'success');
            await loadLLMConfig();
        } else {
            showToast('保存失败: ' + result.message, 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
}

/**
 * Save email configuration
 */
async function saveEmailConfig() {
    const form = document.getElementById('email-form');
    const btn = form.querySelector('button[type="submit"]');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');

    // Get form data
    const formData = new FormData(form);
    const config = {
        enabled: document.getElementById('email-enabled').checked,
        host: formData.get('host') || null,
        port: formData.get('port') ? parseInt(formData.get('port')) : null,
        username: formData.get('username') || null,
        from_email: formData.get('from_email') || null,
    };

    // Only include passwords if they were changed
    const password = formData.get('password');
    if (password && password !== '****') {
        config.password = password;
    }

    const resendKey = formData.get('resend_api_key');
    if (resendKey && resendKey !== '****') {
        config.resend_api_key = resendKey;
    }

    try {
        // Show loading state
        btn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';

        const response = await fetch(`${API_BASE}/config/email`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });

        const result = await response.json();

        if (result.success) {
            showToast('邮箱配置保存成功! 请重启服务以应用更改。', 'success');
            await loadEmailConfig();
        } else {
            showToast('保存失败: ' + result.message, 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
}

/**
 * Test LLM connection
 */
async function testLLMConnection() {
    const btn = document.getElementById('test-llm');
    const originalText = btn.textContent;

    try {
        btn.disabled = true;
        btn.textContent = '测试中...';

        const response = await fetch(`${API_BASE}/config/test/llm`, {
            method: 'POST',
        });

        const result = await response.json();

        if (result.success) {
            showToast('LLM 连接测试成功!', 'success');
        } else {
            showToast('LLM 连接测试失败: ' + result.message, 'error');
        }
    } catch (error) {
        showToast('测试失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

/**
 * Test email configuration
 */
async function testEmailConnection() {
    const btn = document.getElementById('test-email');
    const originalText = btn.textContent;

    try {
        btn.disabled = true;
        btn.textContent = '测试中...';

        const response = await fetch(`${API_BASE}/config/test/email`, {
            method: 'POST',
        });

        const result = await response.json();

        if (result.success) {
            showToast('邮箱配置有效: ' + result.message, 'success');
        } else {
            showToast('邮箱配置检查失败: ' + result.message, 'error');
        }
    } catch (error) {
        showToast('测试失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

/**
 * Load system status
 */
async function loadSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();

        // Update status displays
        const serviceStatus = document.getElementById('service-status');
        const dbStatus = document.getElementById('db-status');
        const llmProvider = document.getElementById('llm-provider-status');
        const llmModel = document.getElementById('llm-model-status');

        serviceStatus.textContent = data.status === 'running' ? '正常' : '异常';
        serviceStatus.className = 'status-value ' + (data.status === 'running' ? 'success' : 'error');

        dbStatus.textContent = data.database_connected ? '已连接' : '未连接';
        dbStatus.className = 'status-value ' + (data.database_connected ? 'success' : 'error');

        llmProvider.textContent = data.llm_provider || '-';
        llmModel.textContent = data.llm_model || '-';

    } catch (error) {
        console.error('Failed to load system status:', error);
    }
}

/**
 * Run pipeline
 */
async function runPipeline() {
    const btn = document.getElementById('run-pipeline');
    const originalText = btn.textContent;

    try {
        btn.disabled = true;
        btn.textContent = '启动中...';

        const response = await fetch(`${API_BASE}/pipeline/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keywords: ['llm'] }),
        });

        const result = await response.json();

        if (result.success) {
            showToast('流水线已启动，正在后台运行...', 'success');
            // Show pipeline status panel
            document.getElementById('pipeline-status').style.display = 'block';
            // Check status after a delay
            setTimeout(checkPipelineStatus, 2000);
        } else {
            showToast('启动失败: ' + result.message, 'error');
        }
    } catch (error) {
        showToast('启动失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

/**
 * Check pipeline status
 */
async function checkPipelineStatus() {
    const statusPanel = document.getElementById('pipeline-status');
    const detailsDiv = document.getElementById('pipeline-details');

    try {
        const response = await fetch(`${API_BASE}/pipeline/status`);
        const data = await response.json();

        statusPanel.style.display = 'block';

        let html = '<p><strong>运行状态:</strong> ' + (data.running ? '运行中' : '空闲') + '</p>';
        if (data.last_run) {
            html += '<p><strong>上次运行:</strong> ' + new Date(data.last_run).toLocaleString('zh-CN') + '</p>';
        }
        if (data.last_result) {
            html += '<p><strong>上次结果:</strong></p>';
            html += '<pre>' + JSON.stringify(data.last_result, null, 2) + '</pre>';
        }

        detailsDiv.innerHTML = html;

    } catch (error) {
        showToast('获取状态失败: ' + error.message, 'error');
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast ' + type + ' show';

    setTimeout(() => {
        toast.classList.remove('show');
    }, 5000);
}

/**
 * Search papers
 */
async function searchPapers() {
    const keywordsInput = document.getElementById('paper-keywords');
    const keywords = keywordsInput.value.trim();

    if (!keywords) {
        showToast('请输入搜索关键词', 'warning');
        return;
    }

    const minPapers = document.getElementById('fetch-max-results').value || 10;

    const resultsDiv = document.getElementById('papers-result');
    const listDiv = document.getElementById('papers-list');

    try {
        listDiv.innerHTML = '<p style="text-align: center; padding: 2rem;">搜索中...</p>';
        resultsDiv.style.display = 'block';

        // First fetch papers
        const response = await fetch(`${API_BASE}/pipeline/fetch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keywords,
                min_papers: parseInt(minPapers),
                max_results: 100,
                max_days_back: 30
            }),
        });

        const result = await response.json();

        if (result.success) {
            showToast(`成功获取 ${result.papers_fetched || 0} 篇论文`, 'success');
            // Load papers list after fetching
            setTimeout(() => loadPapersList(keywords), 500);
        } else {
            listDiv.innerHTML = '<p class="paper-empty">获取失败: ' + (result.error || result.message) + '</p>';
        }

    } catch (error) {
        listDiv.innerHTML = '<p class="paper-empty">获取失败: ' + error.message + '</p>';
    }
}

/**
 * Fetch papers (separate button)
 */
async function fetchPapers() {
    const keywordsInput = document.getElementById('paper-keywords');
    const keywords = keywordsInput.value.trim();

    if (!keywords) {
        showToast('请输入搜索关键词', 'warning');
        return;
    }

    const minPapers = document.getElementById('fetch-max-results').value || 10;

    const statusDiv = document.getElementById('papers-status');
    const detailsDiv = document.getElementById('papers-status-details');

    try {
        detailsDiv.innerHTML = '<p>正在获取论文...</p><p class="hint">如果当天论文数量不足，将自动回溯时间范围。</p>';
        statusDiv.style.display = 'block';

        const response = await fetch(`${API_BASE}/pipeline/fetch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keywords,
                min_papers: parseInt(minPapers),
                max_results: 100,
                max_days_back: 30
            }),
        });

        const result = await response.json();

        if (result.success) {
            detailsDiv.innerHTML = `<p>✓ 成功获取 ${result.papers_fetched || 0} 篇论文</p><p>论文已保存到数据库（关键词: ${keywords}）。</p>`;
            showToast(`获取了 ${result.papers_fetched || 0} 篇论文`, 'success');

            // Refresh papers list
            setTimeout(() => loadPapersList(keywords), 1000);
        } else {
            detailsDiv.innerHTML = '<p>✗ 获取失败: ' + (result.error || result.message) + '</p>';
        }

    } catch (error) {
        detailsDiv.innerHTML = '<p>✗ 获取失败: ' + error.message + '</p>';
        showToast('获取失败: ' + error.message, 'error');
    }
}

/**
 * Generate report
 */
async function generateReport() {
    const keywordsInput = document.getElementById('paper-keywords');
    const keywords = keywordsInput.value.trim() || 'llm';
    const limit = document.getElementById('paper-limit').value || 10;

    const statusDiv = document.getElementById('papers-status');
    const detailsDiv = document.getElementById('papers-status-details');

    try {
        detailsDiv.innerHTML = '<p>正在生成报告...</p><p class="hint">⚠️ 这可能需要几分钟，因为需要调用 LLM 为每篇论文生成结构化摘要。</p><p>请耐心等待...</p>';
        statusDiv.style.display = 'block';

        const response = await fetch(`${API_BASE}/pipeline/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keywords, limit, use_llm: true }),
        });

        const result = await response.json();

        if (result.success) {
            let message = `<p>✓ 报告生成成功</p>`;
            message += `<p>共 ${result.papers_count || 0} 篇论文</p>`;

            if (result.llm_success !== undefined) {
                message += `<p>LLM 成功: ${result.llm_success} 篇</p>`;
            }
            if (result.llm_failed !== undefined) {
                message += `<p>LLM 失败: ${result.llm_failed} 篇（使用原始摘要）</p>`;
            }

            message += `<p>文件路径: ${result.report_path || 'output/'}</p>`;

            detailsDiv.innerHTML = message;
            showToast('报告生成成功', 'success');

            // Refresh papers list
            setTimeout(() => loadPapersList(keywords), 1000);
        } else {
            detailsDiv.innerHTML = '<p>✗ 生成失败: ' + (result.error || result.message) + '</p>';
            showToast('生成失败', 'error');
        }

    } catch (error) {
        detailsDiv.innerHTML = '<p>✗ 生成失败: ' + error.message + '</p>';
        showToast('生成失败: ' + error.message, 'error');
    }
}

/**
 * Send report
 */
async function sendReport() {
    const statusDiv = document.getElementById('papers-status');
    const detailsDiv = document.getElementById('papers-status-details');

    try {
        detailsDiv.innerHTML = '<p>正在准备发送邮件...</p>';
        statusDiv.style.display = 'block';

        // Ask for recipient email
        const recipient = prompt('请输入收件人邮箱（留空则发送到配置的发件人邮箱）:');
        if (recipient === null) return;  // User cancelled

        detailsDiv.innerHTML = '<p>正在发送邮件...</p><p class="hint">将使用已生成的报告文件。</p>';

        const response = await fetch(`${API_BASE}/pipeline/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipient: recipient || null }),
        });

        const result = await response.json();

        if (result.success) {
            let message = `<p>✓ 邮件发送成功</p>`;
            message += `<p>已发送到 ${result.recipients ? result.recipients.length : 0} 个邮箱</p>`;
            if (result.recipients && result.recipients.length > 0) {
                message += `<p>收件人: ${result.recipients.join(', ')}</p>`;
            }
            if (result.report_file) {
                message += `<p>发送的报告: ${result.report_file.split('/')[-1]}</p>`;
            }
            detailsDiv.innerHTML = message;
            showToast('邮件发送成功', 'success');
        } else {
            detailsDiv.innerHTML = '<p>✗ 发送失败: ' + (result.error || result.message) + '</p>';
            showToast('发送失败', 'error');
        }

    } catch (error) {
        detailsDiv.innerHTML = '<p>✗ 发送失败: ' + error.message + '</p>';
        showToast('发送失败: ' + error.message, 'error');
    }
}

/**
 * Load papers list (future enhancement - would need papers list API)
 */
async function loadPapersList(keywords) {
    const listDiv = document.getElementById('papers-list');

    try {
        listDiv.innerHTML = '<p style="text-align: center; padding: 2rem;">加载中...</p>';

        // Pass keywords as query parameter for filtering
        const url = keywords
            ? `${API_BASE}/pipeline/papers?limit=20&keywords=${encodeURIComponent(keywords)}`
            : `${API_BASE}/pipeline/papers?limit=20`;

        const response = await fetch(url);
        const result = await response.json();

        if (result.success && result.papers.length > 0) {
            let html = '';
            result.papers.forEach(paper => {
                const date = paper.published_date ? new Date(paper.published_date).toLocaleDateString('zh-CN') : '未知';
                html += `
                    <div class="paper-item">
                        <div class="paper-item-title">${paper.title}</div>
                        <div class="paper-item-meta">
                            <span>📅 ${date}</span>
                            <span>🏷️ ${paper.source}</span>
                            ${paper.arxiv_id ? `<span>📄 ${paper.arxiv_id}</span>` : ''}
                        </div>
                        <div class="paper-item-abstract">${paper.abstract || '无摘要'}</div>
                    </div>
                `;
            });
            html += `<p class="hint">共找到 ${result.total} 篇论文</p>`;
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<p class="paper-empty">暂无论文数据</p><p class="hint">请先点击"获取论文"来抓取论文数据</p>';
        }

    } catch (error) {
        listDiv.innerHTML = '<p class="paper-empty">加载失败: ' + error.message + '</p>';
    }
}

/**
 * Claude Code Toolkit - Chat Interface JavaScript
 * Implementa dual real-time support: WebSocket + SSE fallback
 * Enhanced with markdown rendering, progressive loading, and advanced UI
 * Siguiendo standards/javascript.yaml y terminal aesthetics
 */

class ChatInterface {
    constructor() {
        // Connection management
        this.sessionId = null;
        this.websocket = null;
        this.eventSource = null;
        this.isConnected = false;
        this.connectionType = 'none';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;

        // Message handling
        this.messageQueue = [];
        this.messageCount = 0;
        this.lastMessageTime = null;
        this.currentStreamingMessage = null;

        // Enhanced input management
        this.inputHistory = [];
        this.historyIndex = -1;
        this.isMultilineMode = false;
        this.maxInputHistory = 50;

        // DOM elements
        this.elements = {};

        // Performance monitoring
        this.performanceMetrics = {
            connectionStart: null,
            latencyMeasures: [],
            messageLatencies: []
        };

        // Markdown renderer
        this.markdownRenderer = null;

        // Message templates
        this.templates = {};

        // Threading system
        this.conversationThread = [];
        this.lastMessageType = null;

        // CHAT-05 Message Actions Enhancement
        this.selectedMessages = new Set();
        this.lastSelectedIndex = -1;
        this.selectionMode = false;
        this.messageElements = [];
        this.toastQueue = [];
        this.maxToasts = 5;

        // Initialize interface
        this.init();
    }

    /**
     * Initialize chat interface con error handling
     */
    async init() {
        try {
            this.cacheElements();
            this.cacheTemplates();
            this.initializeMarkdown();
            this.setupEventListeners();
            this.showLoadingOverlay();

            await this.createSession();
            await this.establishConnection();

            this.hideLoadingOverlay();
            this.focusInput();
            this.startTimestampUpdates();

            console.log('✅ Chat interface initialized successfully');
        } catch (error) {
            console.error('❌ Failed to initialize chat interface:', error);
            this.showError('Failed to initialize chat interface. Please refresh the page.');
        }
    }

    /**
     * Cache DOM elements para performance optimization
     */
    cacheElements() {
        this.elements = {
            // Core chat elements
            chatMessages: document.getElementById('chatMessages'),
            messageInput: document.getElementById('messageInput'),
            messageForm: document.getElementById('messageForm'),
            sendButton: document.getElementById('sendButton'),

            // Enhanced input elements
            charCount: document.getElementById('charCount'),
            lineCount: document.getElementById('lineCount'),
            inputHints: document.getElementById('inputHints'),

            // Status elements
            connectionStatus: document.getElementById('connectionStatus'),
            sessionId: document.getElementById('sessionId'),
            transportType: document.getElementById('transportType'),
            messageCount: document.getElementById('messageCount'),
            latency: document.getElementById('latency'),

            // Modal elements
            loadingOverlay: document.getElementById('loadingOverlay'),
            errorModal: document.getElementById('errorModal'),
            errorMessage: document.getElementById('errorMessage'),
            retryButton: document.getElementById('retryButton'),
            closeErrorButton: document.getElementById('closeErrorButton'),

            // CHAT-05 Selection elements
            selectionToolbar: document.getElementById('selectionToolbar'),
            selectAllBtn: document.getElementById('selectAllBtn'),
            clearSelectionBtn: document.getElementById('clearSelectionBtn'),
            copySelectedBtn: document.getElementById('copySelectedBtn'),
            exportSelectedBtn: document.getElementById('exportSelectedBtn'),
            toastContainer: document.getElementById('toastContainer')
        };

        // Validate all elements exist
        for (const [key, element] of Object.entries(this.elements)) {
            if (!element) {
                throw new Error(`Required element not found: ${key}`);
            }
        }
    }

    /**
     * Cache message templates para performance
     */
    cacheTemplates() {
        this.templates = {
            message: document.getElementById('messageTemplate'),
            codeBlock: document.getElementById('codeBlockTemplate'),
            toast: document.getElementById('toastTemplate')
        };

        // Validate templates exist
        for (const [key, template] of Object.entries(this.templates)) {
            if (!template) {
                throw new Error(`Required template not found: ${key}`);
            }
        }
    }

    /**
     * Initialize markdown renderer con syntax highlighting
     */
    initializeMarkdown() {
        if (typeof markdownit === 'undefined') {
            throw new Error('markdown-it library not loaded');
        }

        // Configure markdown-it with syntax highlighting
        this.markdownRenderer = markdownit({
            html: false, // Disable HTML for security
            xhtmlOut: true,
            breaks: true,
            linkify: true,
            typographer: true,
            highlight: function (str, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(str, { language: lang }).value;
                    } catch (err) {
                        console.warn('Syntax highlighting failed:', err);
                    }
                }
                return '';
            }
        });

        // Custom renderer for code blocks to include copy functionality
        const defaultCodeRenderer = this.markdownRenderer.renderer.rules.code_block ||
                                   this.markdownRenderer.renderer.rules.fence;

        this.markdownRenderer.renderer.rules.code_block =
        this.markdownRenderer.renderer.rules.fence = (tokens, idx, options, env, slf) => {
            const token = tokens[idx];
            const langName = token.info ? token.info.trim().split(/\s+/g)[0] : '';
            const codeContent = token.content;

            return this.renderCodeBlock(codeContent, langName);
        };

        console.log('✅ Markdown renderer initialized with syntax highlighting');
    }

    /**
     * Render custom code block con copy functionality
     */
    renderCodeBlock(code, language = '') {
        const template = this.templates.codeBlock.content.cloneNode(true);
        const container = template.querySelector('.code-block-container');
        const languageSpan = template.querySelector('.code-language');
        const codeElement = template.querySelector('code');
        const copyBtn = template.querySelector('.copy-code-btn');

        // Set language display
        languageSpan.textContent = language || 'text';

        // Apply syntax highlighting
        if (language && hljs.getLanguage(language)) {
            try {
                const highlighted = hljs.highlight(code, { language }).value;
                codeElement.innerHTML = highlighted;
                codeElement.className = `hljs language-${language}`;
            } catch (err) {
                console.warn('Syntax highlighting failed:', err);
                codeElement.textContent = code;
                codeElement.className = 'hljs';
            }
        } else {
            codeElement.textContent = code;
            codeElement.className = 'hljs';
        }

        // Add copy functionality
        copyBtn.addEventListener('click', () => this.copyCodeToClipboard(code, copyBtn));

        // Return HTML string
        const wrapper = document.createElement('div');
        wrapper.appendChild(container);
        return wrapper.innerHTML;
    }

    /**
     * Start relative timestamp updates
     */
    startTimestampUpdates() {
        // Update timestamps every minute
        setInterval(() => {
            this.updateRelativeTimestamps();
        }, 60000);

        // Initial update
        this.updateRelativeTimestamps();
    }

    /**
     * Update all relative timestamps
     */
    updateRelativeTimestamps() {
        const timestampElements = document.querySelectorAll('.message-timestamp.relative');

        timestampElements.forEach(element => {
            const timestamp = element.getAttribute('data-timestamp');
            if (timestamp) {
                const relativeTime = this.getRelativeTime(new Date(timestamp));
                element.setAttribute('data-relative-time', relativeTime);
            }
        });
    }

    /**
     * Get relative time string (e.g., "2 minutes ago")
     */
    getRelativeTime(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffSeconds < 60) {
            return 'just now';
        } else if (diffMinutes < 60) {
            return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        } else {
            return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        }
    }

    /**
     * Setup enhanced input handlers para advanced text input system
     */
    setupEnhancedInputHandlers() {
        const input = this.elements.messageInput;

        // Load input history from localStorage
        this.loadInputHistory();

        // Auto-resize functionality
        input.addEventListener('input', (e) => {
            this.autoResizeTextarea(e.target);
            this.updateCharacterCount();
            this.updateLineCount();
            this.updateInputMode();
        });

        // Enhanced keyboard handling
        input.addEventListener('keydown', (e) => {
            this.handleEnhancedKeydown(e);
        });

        // Focus and blur handlers
        input.addEventListener('focus', () => {
            this.updateInputHints();
        });

        input.addEventListener('blur', () => {
            this.saveCurrentDraft();
        });

        // Initial setup
        this.autoResizeTextarea(input);
        this.updateCharacterCount();
        this.updateLineCount();
        this.loadDraft();
        this.updateSmartPlaceholder();
    }

    /**
     * Auto-resize textarea based on content
     */
    autoResizeTextarea(textarea) {
        const minRows = parseInt(textarea.dataset.minRows) || 1;
        const maxRows = parseInt(textarea.dataset.maxRows) || 8;

        // Reset height to auto to get the scroll height
        textarea.style.height = 'auto';

        // Calculate required height
        const lineHeight = parseInt(getComputedStyle(textarea).lineHeight);
        const padding = parseInt(getComputedStyle(textarea).paddingTop) * 2;
        const scrollHeight = textarea.scrollHeight;

        // Calculate rows needed
        const contentHeight = scrollHeight - padding;
        const rowsNeeded = Math.ceil(contentHeight / lineHeight);

        // Constrain to min/max rows
        const rows = Math.max(minRows, Math.min(maxRows, rowsNeeded));
        const newHeight = (rows * lineHeight) + padding;

        textarea.style.height = newHeight + 'px';
        textarea.rows = rows;

        // Update multiline mode
        if (rows > 1 && !this.isMultilineMode) {
            this.isMultilineMode = true;
            this.updateInputMode();
        } else if (rows === 1 && this.isMultilineMode) {
            this.isMultilineMode = false;
            this.updateInputMode();
        }
    }

    /**
     * Handle enhanced keyboard events
     */
    handleEnhancedKeydown(e) {
        const input = e.target;

        switch (e.key) {
            case 'Enter':
                if (e.shiftKey) {
                    // Shift+Enter: Allow new line
                    return;
                } else {
                    // Enter: Send message
                    e.preventDefault();
                    this.sendMessage();
                }
                break;

            case 'ArrowUp':
                if (e.ctrlKey || (input.selectionStart === 0 && input.selectionEnd === 0)) {
                    e.preventDefault();
                    this.navigateHistory('up');
                }
                break;

            case 'ArrowDown':
                if (e.ctrlKey || (input.selectionStart === input.value.length && input.selectionEnd === input.value.length)) {
                    e.preventDefault();
                    this.navigateHistory('down');
                }
                break;

            case 'Escape':
                if (this.isMultilineMode) {
                    e.preventDefault();
                    this.exitMultilineMode();
                }
                break;

            case 'Tab':
                if (input.value.trim() === '') {
                    e.preventDefault();
                    this.showCommandSuggestions();
                }
                break;
        }
    }

    /**
     * Navigate input history
     */
    navigateHistory(direction) {
        if (this.inputHistory.length === 0) return;

        if (direction === 'up') {
            if (this.historyIndex === -1) {
                // Save current input as draft
                this.currentDraft = this.elements.messageInput.value;
                this.historyIndex = this.inputHistory.length - 1;
            } else if (this.historyIndex > 0) {
                this.historyIndex--;
            }
        } else if (direction === 'down') {
            if (this.historyIndex === -1) return;

            this.historyIndex++;
            if (this.historyIndex >= this.inputHistory.length) {
                // Restore draft
                this.elements.messageInput.value = this.currentDraft || '';
                this.historyIndex = -1;
                this.autoResizeTextarea(this.elements.messageInput);
                this.updateCharacterCount();
                this.updateLineCount();
                return;
            }
        }

        // Set input value from history
        this.elements.messageInput.value = this.inputHistory[this.historyIndex];
        this.autoResizeTextarea(this.elements.messageInput);
        this.updateCharacterCount();
        this.updateLineCount();

        // Position cursor at end
        this.elements.messageInput.setSelectionRange(
            this.elements.messageInput.value.length,
            this.elements.messageInput.value.length
        );
    }

    /**
     * Update character count with visual feedback
     */
    updateCharacterCount() {
        const count = this.elements.messageInput.value.length;
        const maxLength = this.elements.messageInput.maxLength || 5000;

        this.elements.charCount.textContent = count;

        // Update visual feedback
        const countElement = this.elements.charCount.parentElement;
        countElement.classList.remove('warning', 'danger');

        if (count > maxLength * 0.9) {
            countElement.classList.add('danger');
        } else if (count > maxLength * 0.8) {
            countElement.classList.add('warning');
        }
    }

    /**
     * Update line count
     */
    updateLineCount() {
        const lines = this.elements.messageInput.value.split('\n').length;
        this.elements.lineCount.textContent = lines === 1 ? 'Line 1' : `${lines} lines`;
    }

    /**
     * Update input mode indicators
     */
    updateInputMode() {
        const inputContainer = this.elements.messageInput.closest('.input-container');
        const input = this.elements.messageInput;

        if (this.isMultilineMode) {
            inputContainer.classList.add('multiline-mode');
            input.classList.add('multiline-mode');
        } else {
            inputContainer.classList.remove('multiline-mode');
            input.classList.remove('multiline-mode');
        }

        this.updateInputHints();
        this.updateSmartPlaceholder();
    }

    /**
     * Update input hints based on current mode
     */
    updateInputHints() {
        const hints = this.elements.inputHints.querySelectorAll('.hint');
        hints.forEach(hint => hint.classList.remove('active'));

        if (this.isMultilineMode) {
            const multilineHint = this.elements.inputHints.querySelector('[data-hint="multiline"]');
            if (multilineHint) multilineHint.classList.add('active');
        } else {
            const basicHint = this.elements.inputHints.querySelector('[data-hint="basic"]');
            if (basicHint) basicHint.classList.add('active');
        }
    }

    /**
     * Exit multiline mode
     */
    exitMultilineMode() {
        const input = this.elements.messageInput;
        // Convert to single line by replacing newlines with spaces
        input.value = input.value.replace(/\n/g, ' ').trim();
        this.autoResizeTextarea(input);
        this.updateCharacterCount();
        this.updateLineCount();
        this.updateInputMode();
    }

    /**
     * Load input history from localStorage
     */
    loadInputHistory() {
        try {
            const saved = localStorage.getItem('claude_input_history');
            if (saved) {
                this.inputHistory = JSON.parse(saved);
                // Ensure we don't exceed max history
                if (this.inputHistory.length > this.maxInputHistory) {
                    this.inputHistory = this.inputHistory.slice(-this.maxInputHistory);
                    this.saveInputHistory();
                }
            }
        } catch (error) {
            console.warn('Failed to load input history:', error);
            this.inputHistory = [];
        }
    }

    /**
     * Save input history to localStorage
     */
    saveInputHistory() {
        try {
            localStorage.setItem('claude_input_history', JSON.stringify(this.inputHistory));
        } catch (error) {
            console.warn('Failed to save input history:', error);
        }
    }

    /**
     * Add message to input history
     */
    addToInputHistory(message) {
        const trimmed = message.trim();
        if (!trimmed || trimmed.length < 2) return;

        // Remove duplicate if it exists
        const index = this.inputHistory.indexOf(trimmed);
        if (index > -1) {
            this.inputHistory.splice(index, 1);
        }

        // Add to end
        this.inputHistory.push(trimmed);

        // Maintain max history size
        if (this.inputHistory.length > this.maxInputHistory) {
            this.inputHistory.shift();
        }

        // Reset history navigation
        this.historyIndex = -1;
        this.currentDraft = '';

        this.saveInputHistory();
    }

    /**
     * Save current draft
     */
    saveCurrentDraft() {
        const value = this.elements.messageInput.value.trim();
        if (value) {
            try {
                localStorage.setItem('claude_input_draft', value);
            } catch (error) {
                console.warn('Failed to save draft:', error);
            }
        } else {
            localStorage.removeItem('claude_input_draft');
        }
    }

    /**
     * Load saved draft
     */
    loadDraft() {
        try {
            const draft = localStorage.getItem('claude_input_draft');
            if (draft && draft.trim()) {
                this.elements.messageInput.value = draft;
                this.autoResizeTextarea(this.elements.messageInput);
                this.updateCharacterCount();
                this.updateLineCount();
                this.updateInputMode();
            }
        } catch (error) {
            console.warn('Failed to load draft:', error);
        }
    }

    /**
     * Clear saved draft
     */
    clearDraft() {
        try {
            localStorage.removeItem('claude_input_draft');
        } catch (error) {
            console.warn('Failed to clear draft:', error);
        }
    }

    /**
     * Show command suggestions (placeholder for future enhancement)
     */
    showCommandSuggestions() {
        console.log('Command suggestions feature - placeholder for future implementation');
        // TODO: Implement command suggestions dropdown
    }

    /**
     * Update smart placeholder text based on context
     */
    updateSmartPlaceholder() {
        const input = this.elements.messageInput;
        const messageCount = this.messageCount;
        const isConnected = this.isConnected;
        const isMultiline = this.isMultilineMode;

        let placeholder = '';

        if (!isConnected) {
            placeholder = 'Connecting... Please wait';
        } else if (messageCount === 0) {
            placeholder = 'Welcome! Type your first message... (Enter to send, Shift+Enter for new line)';
        } else if (isMultiline) {
            placeholder = 'Multi-line mode active... (Enter to send, Esc to exit)';
        } else if (this.inputHistory.length > 0) {
            placeholder = 'Type your message... (↑↓ for history, Shift+Enter for new line)';
        } else {
            placeholder = 'Type your message... (Enter to send, Shift+Enter for new line)';
        }

        // Add helpful hints based on time of conversation
        if (messageCount > 5 && Math.random() < 0.3) {
            const hints = [
                'Try multi-line messages with Shift+Enter...',
                'Use ↑↓ arrows to access message history...',
                'Press Tab for command suggestions...',
                'Esc to exit multi-line mode...'
            ];
            placeholder = hints[Math.floor(Math.random() * hints.length)];
        }

        input.placeholder = placeholder;
    }

    /**
     * Setup event listeners con modern patterns
     */
    setupEventListeners() {
        // Message form submission
        this.elements.messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Enhanced input event handlers
        this.setupEnhancedInputHandlers();

        // Error modal handlers
        this.elements.retryButton.addEventListener('click', () => {
            this.hideError();
            this.reconnect();
        });

        this.elements.closeErrorButton.addEventListener('click', () => {
            this.hideError();
        });

        // Chat messages event delegation for message actions
        this.elements.chatMessages.addEventListener('click', (e) => {
            this.handleMessageAction(e);
        });

        // CHAT-05 Selection toolbar event listeners
        this.setupSelectionEventListeners();

        // Window events
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });

        window.addEventListener('online', () => {
            console.log('🌐 Network connection restored');
            this.reconnect();
        });

        window.addEventListener('offline', () => {
            console.log('🚫 Network connection lost');
            this.updateConnectionStatus('offline', 'Network Offline');
        });
    }

    /**
     * Handle message action clicks - Enhanced for CHAT-05
     */
    handleMessageAction(event) {
        const target = event.target.closest('.action-btn, .copy-code-btn, .message-checkbox');
        if (!target) {
            // Check for message selection clicks
            const messageElement = event.target.closest('.message[data-selectable="true"]');
            if (messageElement && (event.ctrlKey || event.metaKey || event.shiftKey)) {
                this.handleMessageSelection(messageElement, event);
            }
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const messageElement = target.closest('.message');
        const messageId = messageElement?.getAttribute('data-message-id');

        if (target.classList.contains('copy-btn')) {
            this.copyMessageToClipboard(messageElement);
        } else if (target.classList.contains('retry-btn')) {
            this.retryFailedMessage(messageElement, messageId);
        } else if (target.classList.contains('select-btn')) {
            this.toggleMessageSelection(messageElement);
        } else if (target.classList.contains('message-checkbox')) {
            this.toggleMessageSelection(messageElement);
        } else if (target.classList.contains('copy-code-btn')) {
            // Code copy handled separately in renderCodeBlock
            return;
        }
    }

    /**
     * Copy message content to clipboard
     */
    async copyMessageToClipboard(messageElement) {
        const messageText = messageElement.querySelector('.message-text');
        if (!messageText) return;

        try {
            await navigator.clipboard.writeText(messageText.textContent);
            this.showTemporaryFeedback(messageElement.querySelector('.copy-btn'), 'Copied!');
        } catch (err) {
            console.error('Failed to copy message:', err);
            this.showTemporaryFeedback(messageElement.querySelector('.copy-btn'), 'Failed');
        }
    }

    /**
     * Copy code block to clipboard
     */
    async copyCodeToClipboard(code, button) {
        try {
            await navigator.clipboard.writeText(code);
            button.classList.add('copied');
            setTimeout(() => {
                button.classList.remove('copied');
            }, 2000);
        } catch (err) {
            console.error('Failed to copy code:', err);
            this.showTemporaryFeedback(button, 'Failed');
        }
    }

    /**
     * Show temporary feedback on action buttons
     */
    showTemporaryFeedback(button, text) {
        const originalIcon = button.querySelector('.icon');
        const originalText = originalIcon.textContent;

        originalIcon.textContent = text === 'Copied!' ? '✓' : '✗';
        button.classList.add('active');

        setTimeout(() => {
            originalIcon.textContent = originalText;
            button.classList.remove('active');
        }, 2000);
    }

    /**
     * Edit message (placeholder for future implementation)
     */
    editMessage(messageElement, messageId) {
        console.log('Edit message:', messageId);
        // TODO: Implement message editing functionality
        this.showTemporaryFeedback(messageElement.querySelector('.edit-btn'), 'Soon!');
    }

    /**
     * Resend message
     */
    resendMessage(messageElement, messageId) {
        const messageText = messageElement.querySelector('.message-text');
        if (!messageText) return;

        // Set the input value and send
        this.elements.messageInput.value = messageText.textContent;
        this.sendMessage();
    }

    /**
     * Bookmark message (placeholder for future implementation)
     */
    bookmarkMessage(messageElement, messageId) {
        console.log('Bookmark message:', messageId);
        const bookmarkBtn = messageElement.querySelector('.bookmark-btn');

        // Toggle bookmark state
        bookmarkBtn.classList.toggle('active');
        const isBookmarked = bookmarkBtn.classList.contains('active');

        this.showTemporaryFeedback(bookmarkBtn, isBookmarked ? 'Saved!' : 'Removed');

        // TODO: Persist bookmark state to backend
    }

    /**
     * Create new chat session
     */
    async createSession() {
        try {
            console.log('🚀 Creating new chat session...');

            const response = await fetch('/api/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;

            this.elements.sessionId.textContent = this.sessionId.substring(0, 8) + '...';

            console.log(`✅ Session created: ${this.sessionId}`);

            // Load session history if exists
            await this.loadSessionHistory();

        } catch (error) {
            console.error('❌ Failed to create session:', error);
            throw new Error('Unable to create chat session');
        }
    }

    /**
     * Load session history
     */
    async loadSessionHistory() {
        try {
            const response = await fetch(`/api/sessions/${this.sessionId}/history`);

            if (response.ok) {
                const data = await response.json();

                if (data.messages && data.messages.length > 0) {
                    for (const message of data.messages) {
                        this.displayMessage(message, false); // false = don't scroll yet
                    }
                    this.scrollToBottom();
                    this.messageCount = data.messages.length;
                    this.updateMessageCount();
                }
            }
        } catch (error) {
            console.warn('⚠️ Could not load session history:', error);
        }
    }

    /**
     * Establish connection con dual transport strategy
     */
    async establishConnection() {
        this.performanceMetrics.connectionStart = performance.now();

        try {
            // Primary: WebSocket connection
            await this.connectWebSocket();
        } catch (error) {
            console.warn('⚠️ WebSocket connection failed, falling back to SSE:', error);

            try {
                // Fallback: Server-Sent Events
                await this.connectSSE();
            } catch (sseError) {
                console.error('❌ Both WebSocket and SSE connections failed');
                throw new Error('Unable to establish real-time connection');
            }
        }
    }

    /**
     * WebSocket connection con async error handling
     */
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/${this.sessionId}`;

                console.log(`🔌 Connecting WebSocket to: ${wsUrl}`);

                this.websocket = new WebSocket(wsUrl);

                // Connection timeout
                const connectionTimeout = setTimeout(() => {
                    this.websocket.close();
                    reject(new Error('WebSocket connection timeout'));
                }, 10000);

                this.websocket.onopen = () => {
                    clearTimeout(connectionTimeout);
                    console.log('✅ WebSocket connected');

                    this.isConnected = true;
                    this.connectionType = 'websocket';
                    this.reconnectAttempts = 0;

                    this.updateConnectionStatus('online', 'WebSocket Connected');
                    this.updateTransportType('WebSocket');
                    this.measureLatency();

                    resolve();
                };

                this.websocket.onmessage = (event) => {
                    this.handleMessage(JSON.parse(event.data));
                };

                this.websocket.onclose = (event) => {
                    console.log(`🔌 WebSocket closed: ${event.code} - ${event.reason}`);
                    this.isConnected = false;
                    this.updateConnectionStatus('offline', 'WebSocket Disconnected');

                    if (this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.scheduleReconnect();
                    }
                };

                this.websocket.onerror = (error) => {
                    console.error('❌ WebSocket error:', error);
                    clearTimeout(connectionTimeout);
                    reject(error);
                };

            } catch (error) {
                console.error('❌ WebSocket setup failed:', error);
                reject(error);
            }
        });
    }

    /**
     * Server-Sent Events connection
     */
    async connectSSE() {
        return new Promise((resolve, reject) => {
            try {
                const sseUrl = `/api/stream/${this.sessionId}`;

                console.log(`📡 Connecting SSE to: ${sseUrl}`);

                this.eventSource = new EventSource(sseUrl);

                // Connection timeout
                const connectionTimeout = setTimeout(() => {
                    this.eventSource.close();
                    reject(new Error('SSE connection timeout'));
                }, 10000);

                this.eventSource.onopen = () => {
                    clearTimeout(connectionTimeout);
                    console.log('✅ SSE connected');

                    this.isConnected = true;
                    this.connectionType = 'sse';
                    this.reconnectAttempts = 0;

                    this.updateConnectionStatus('online', 'SSE Connected');
                    this.updateTransportType('Server-Sent Events');

                    resolve();
                };

                this.eventSource.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);

                        if (data.type === 'message') {
                            this.handleMessage(data.data);
                        } else if (data.type === 'heartbeat') {
                            this.updateLatency(Date.now() - (data.timestamp * 1000));
                        } else if (data.type === 'error') {
                            console.error('SSE error message:', data.message);
                        }
                    } catch (error) {
                        console.error('Failed to parse SSE message:', error);
                    }
                };

                this.eventSource.onerror = (error) => {
                    console.error('❌ SSE error:', error);
                    clearTimeout(connectionTimeout);

                    this.isConnected = false;
                    this.updateConnectionStatus('offline', 'SSE Disconnected');

                    if (this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.scheduleReconnect();
                    } else {
                        reject(error);
                    }
                };

            } catch (error) {
                console.error('❌ SSE setup failed:', error);
                reject(error);
            }
        });
    }

    /**
     * Send message con dual transport support
     */
    async sendMessage() {
        const content = this.elements.messageInput.value.trim();

        if (!content) return;
        if (!this.isConnected) {
            this.showError('No connection available. Please wait for reconnection.');
            return;
        }

        // Disable input durante sending
        this.setInputEnabled(false);

        try {
            const messageData = {
                content: content,
                message_type: 'user',
                timestamp: new Date().toISOString()
            };

            // Display user message immediately with sending status
            const userMessageId = this.displayMessage(messageData, true, false);
            const userMessageElement = document.querySelector(`[data-message-id="${userMessageId}"]`);
            this.updateMessageStatus(userMessageElement, 'sending', 'Sending message...');

            // Add to input history
            this.addToInputHistory(content);

            // Clear input and reset state
            this.elements.messageInput.value = '';
            this.autoResizeTextarea(this.elements.messageInput);
            this.updateCharacterCount();
            this.updateLineCount();
            this.updateInputMode();
            this.clearDraft();

            if (this.connectionType === 'websocket' && this.websocket?.readyState === WebSocket.OPEN) {
                // Send via WebSocket
                this.websocket.send(JSON.stringify(messageData));
                console.log('📤 Message sent via WebSocket');

                // Update status to sent
                this.updateMessageStatus(userMessageElement, 'sent', 'Message sent successfully');

            } else if (this.connectionType === 'sse') {
                // Send via HTTP for SSE connections
                const response = await fetch(`/api/chat?session_id=${this.sessionId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: content,
                        message_type: 'user'
                    }),
                    signal: AbortSignal.timeout(30000) // 30s timeout
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                console.log('📤 Message sent via HTTP (SSE mode)');

                // Update status to sent
                this.updateMessageStatus(userMessageElement, 'sent', 'Message sent successfully');
            }

            // Track message for latency measurement
            this.lastMessageTime = performance.now();

        } catch (error) {
            console.error('❌ Failed to send message:', error);
            this.showError('Failed to send message. Please try again.');

            // Update message status to error
            const userMessageElement = document.querySelector(`[data-message-id="${userMessageId}"]`);
            if (userMessageElement) {
                this.updateMessageStatus(userMessageElement, 'error', `Failed to send: ${error.message}`);
            }

            // Restore message in input
            this.elements.messageInput.value = content;
            this.autoResizeTextarea(this.elements.messageInput);
            this.updateCharacterCount();
            this.updateLineCount();
            this.updateInputMode();
        } finally {
            this.setInputEnabled(true);
            this.focusInput();
        }
    }

    /**
     * Handle incoming messages con enhanced processing
     */
    handleMessage(message) {
        console.log('📨 Received message:', message);

        // Measure response latency
        if (this.lastMessageTime) {
            const latency = performance.now() - this.lastMessageTime;
            this.updateLatency(latency);
            this.lastMessageTime = null;
        }

        // Check if this is a streaming message chunk
        if (message.type === 'stream_chunk') {
            this.handleStreamChunk(message);
            return;
        }

        // Check if this is a stream complete signal
        if (message.type === 'stream_complete') {
            this.completeStreamingMessage();
            return;
        }

        // Regular message display with enhanced features
        const messageId = this.displayMessage(message);

        // Update status to received for assistant messages
        if (message.message_type === 'assistant') {
            const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
            this.updateMessageStatus(messageElement, 'received', 'Message received');
        }

        this.messageCount++;
        this.updateMessageCount();
        this.updateSmartPlaceholder();
    }

    /**
     * Handle streaming message chunks
     */
    handleStreamChunk(chunkMessage) {
        // If no current streaming message, start one
        if (!this.currentStreamingMessage) {
            const streamMessageData = {
                content: '',
                message_type: 'assistant',
                timestamp: new Date().toISOString()
            };
            this.startMessageStream(streamMessageData);
        }

        // Append chunk to current streaming message
        if (chunkMessage.content) {
            this.appendToStreamingMessage(chunkMessage.content);
        }
    }

    /**
     * Display message con advanced features: markdown, threading, status indicators
     */
    displayMessage(message, shouldScroll = true, isStreaming = false) {
        const messageId = message.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const template = this.templates.message.content.cloneNode(true);
        const messageDiv = template.querySelector('.message');

        // Set message attributes
        messageDiv.className = `message ${message.message_type}-message`;
        messageDiv.setAttribute('data-message-id', messageId);

        // Handle threading
        this.applyThreading(messageDiv, message.message_type);

        // Set message author
        const authorElement = messageDiv.querySelector('.message-author');
        if (message.message_type === 'user') {
            authorElement.textContent = 'user@claude:~$ ';
        } else if (message.message_type === 'assistant') {
            authorElement.textContent = 'claude@toolkit:~$ ';
        } else {
            authorElement.textContent = 'system@toolkit:~$ ';
        }

        // Handle message content
        const messageTextElement = messageDiv.querySelector('.message-text');
        if (isStreaming) {
            messageTextElement.textContent = '';
            messageDiv.classList.add('streaming');
        } else {
            // Render markdown content
            const renderedContent = this.renderMessageContent(message.content);
            messageTextElement.innerHTML = renderedContent;
        }

        // Set timestamp
        const timestampElement = messageDiv.querySelector('.message-timestamp');
        const timestamp = new Date(message.timestamp || new Date());
        timestampElement.setAttribute('data-timestamp', timestamp.toISOString());
        timestampElement.textContent = timestamp.toLocaleTimeString();

        // Set status indicator
        this.updateMessageStatus(messageDiv, isStreaming ? 'sending' : 'sent');

        // Add to DOM
        this.elements.chatMessages.appendChild(messageDiv);

        // Store reference for streaming
        if (isStreaming) {
            this.currentStreamingMessage = {
                element: messageDiv,
                textElement: messageTextElement,
                content: '',
                messageId: messageId
            };
        }

        if (shouldScroll) {
            this.scrollToBottom();
        }

        // Add entrance animation
        messageDiv.classList.add('entering');
        requestAnimationFrame(() => {
            messageDiv.classList.remove('entering');
        });

        return messageId;
    }

    /**
     * Render message content con markdown
     */
    renderMessageContent(content) {
        if (!content) return '';

        try {
            // Render markdown
            return this.markdownRenderer.render(content);
        } catch (error) {
            console.error('Markdown rendering failed:', error);
            // Fallback to escaped HTML
            return this.escapeHtml(content);
        }
    }

    /**
     * Apply threading visual indicators
     */
    applyThreading(messageDiv, messageType) {
        // Determine if this is part of a conversation thread
        const isThreadContinuation = this.lastMessageType === messageType;

        if (isThreadContinuation) {
            messageDiv.classList.add('thread-continuation');
        } else {
            messageDiv.classList.add('thread-start');
        }

        this.lastMessageType = messageType;
        this.conversationThread.push({
            type: messageType,
            timestamp: new Date()
        });
    }

    /**
     * Update message status indicator
     */
    updateMessageStatus(messageElement, status, tooltip = '') {
        const statusIndicator = messageElement.querySelector('.status-indicator');
        if (!statusIndicator) return;

        // Remove existing status classes
        statusIndicator.className = 'status-indicator';

        // Add new status
        statusIndicator.classList.add(status);

        if (tooltip) {
            statusIndicator.setAttribute('title', tooltip);
        }

        // Update status text for screen readers
        const statusText = {
            sending: 'Sending message...',
            sent: 'Message sent',
            received: 'Message received',
            error: 'Message failed to send',
            system: 'System message'
        };

        statusIndicator.setAttribute('aria-label', statusText[status] || '');
    }

    /**
     * Start progressive message streaming
     */
    startMessageStream(messageData) {
        const messageId = this.displayMessage(messageData, true, true);

        return {
            messageId: messageId,
            append: (chunk) => this.appendToStreamingMessage(chunk),
            complete: () => this.completeStreamingMessage(),
            error: (error) => this.errorStreamingMessage(error)
        };
    }

    /**
     * Append chunk to streaming message
     */
    appendToStreamingMessage(chunk) {
        if (!this.currentStreamingMessage) return;

        this.currentStreamingMessage.content += chunk;

        // Render progressive markdown (character by character simulation)
        const textElement = this.currentStreamingMessage.textElement;
        const renderedContent = this.renderMessageContent(this.currentStreamingMessage.content);

        textElement.innerHTML = renderedContent;
        this.scrollToBottom();

        // Throttle updates for performance
        if (!this.streamingUpdateTimeout) {
            this.streamingUpdateTimeout = setTimeout(() => {
                this.streamingUpdateTimeout = null;
            }, 50);
        }
    }

    /**
     * Complete streaming message
     */
    completeStreamingMessage() {
        if (!this.currentStreamingMessage) return;

        const messageDiv = this.currentStreamingMessage.element;

        // Remove streaming state
        messageDiv.classList.remove('streaming');

        // Update status to sent
        this.updateMessageStatus(messageDiv, 'sent', 'Message sent successfully');

        // Final render
        const finalContent = this.renderMessageContent(this.currentStreamingMessage.content);
        this.currentStreamingMessage.textElement.innerHTML = finalContent;

        // Clear streaming reference
        this.currentStreamingMessage = null;

        this.scrollToBottom();
    }

    /**
     * Handle streaming message error
     */
    errorStreamingMessage(error) {
        if (!this.currentStreamingMessage) return;

        const messageDiv = this.currentStreamingMessage.element;

        // Remove streaming state
        messageDiv.classList.remove('streaming');

        // Update status to error
        this.updateMessageStatus(messageDiv, 'error', `Failed to send: ${error}`);

        // Show error in message
        this.currentStreamingMessage.textElement.innerHTML = `
            <div class="error-message">
                <span class="error-icon">⚠️</span>
                Failed to send message: ${this.escapeHtml(error)}
            </div>
        `;

        // Clear streaming reference
        this.currentStreamingMessage = null;
    }

    /**
     * Scroll to bottom con smooth behavior
     */
    scrollToBottom() {
        this.elements.chatMessages.scrollTo({
            top: this.elements.chatMessages.scrollHeight,
            behavior: 'smooth'
        });
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(status, text) {
        const statusDot = this.elements.connectionStatus.querySelector('.status-dot');
        const statusText = this.elements.connectionStatus.querySelector('.status-text');

        statusDot.className = `status-dot ${status}`;
        statusText.textContent = text;
        this.updateSmartPlaceholder();
    }

    /**
     * Update transport type display
     */
    updateTransportType(type) {
        this.elements.transportType.textContent = type;
    }

    /**
     * Update message count display
     */
    updateMessageCount() {
        this.elements.messageCount.textContent = this.messageCount.toString();
    }

    /**
     * Update latency display
     */
    updateLatency(latency) {
        this.performanceMetrics.messageLatencies.push(latency);

        // Keep only last 10 measurements
        if (this.performanceMetrics.messageLatencies.length > 10) {
            this.performanceMetrics.messageLatencies.shift();
        }

        // Calculate average latency
        const avgLatency = this.performanceMetrics.messageLatencies.reduce((a, b) => a + b, 0) /
                          this.performanceMetrics.messageLatencies.length;

        this.elements.latency.textContent = `${Math.round(avgLatency)} ms`;
    }

    /**
     * Measure connection latency
     */
    measureLatency() {
        if (this.connectionType === 'websocket' && this.websocket?.readyState === WebSocket.OPEN) {
            const start = performance.now();

            // Send ping message
            this.websocket.send(JSON.stringify({
                type: 'ping',
                timestamp: start
            }));
        }
    }

    /**
     * Schedule reconnection con exponential backoff
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.showError('Connection failed after multiple attempts. Please refresh the page.');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        this.updateConnectionStatus('connecting', `Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        console.log(`🔄 Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

        setTimeout(() => {
            this.reconnect();
        }, delay);
    }

    /**
     * Reconnect con connection strategy
     */
    async reconnect() {
        try {
            this.cleanup();
            await this.establishConnection();
            console.log('✅ Reconnection successful');
        } catch (error) {
            console.error('❌ Reconnection failed:', error);
            this.scheduleReconnect();
        }
    }

    /**
     * Show loading overlay
     */
    showLoadingOverlay() {
        this.elements.loadingOverlay.classList.remove('hidden');
    }

    /**
     * Hide loading overlay
     */
    hideLoadingOverlay() {
        this.elements.loadingOverlay.classList.add('hidden');
    }

    /**
     * Show error modal
     */
    showError(message) {
        this.elements.errorMessage.textContent = message;
        this.elements.errorModal.classList.add('visible');
    }

    /**
     * Hide error modal
     */
    hideError() {
        this.elements.errorModal.classList.remove('visible');
    }

    /**
     * Enable/disable input controls
     */
    setInputEnabled(enabled) {
        this.elements.messageInput.disabled = !enabled;
        this.elements.sendButton.disabled = !enabled;
    }

    /**
     * Focus message input
     */
    focusInput() {
        this.elements.messageInput.focus();
    }

    /**
     * Escape HTML para security
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Cleanup connections
     */
    cleanup() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }

        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        this.isConnected = false;
    }

    // =====================================
    // CHAT-05 MESSAGE ACTIONS ENHANCEMENT
    // =====================================

    /**
     * Setup selection toolbar event listeners
     */
    setupSelectionEventListeners() {
        // Select all button
        this.elements.selectAllBtn.addEventListener('click', () => {
            this.selectAllMessages();
        });

        // Clear selection button
        this.elements.clearSelectionBtn.addEventListener('click', () => {
            this.clearSelection();
        });

        // Copy selected messages button
        this.elements.copySelectedBtn.addEventListener('click', () => {
            this.copySelectedMessages();
        });

        // Export selected messages button
        this.elements.exportSelectedBtn.addEventListener('click', () => {
            this.exportSelectedMessages();
        });

        // Keyboard shortcuts for selection
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'a':
                        if (this.selectionMode) {
                            e.preventDefault();
                            this.selectAllMessages();
                        }
                        break;
                    case 'c':
                        if (this.selectedMessages.size > 0) {
                            e.preventDefault();
                            this.copySelectedMessages();
                        }
                        break;
                    case 'Escape':
                        if (this.selectedMessages.size > 0) {
                            e.preventDefault();
                            this.clearSelection();
                        }
                        break;
                }
            }
        });
    }

    /**
     * Handle message selection with range and multi-selection support
     */
    handleMessageSelection(messageElement, event) {
        const messageIndex = Array.from(this.elements.chatMessages.querySelectorAll('.message[data-selectable="true"]')).indexOf(messageElement);

        if (event.shiftKey && this.lastSelectedIndex !== -1) {
            // Range selection
            this.selectMessageRange(this.lastSelectedIndex, messageIndex);
        } else if (event.ctrlKey || event.metaKey) {
            // Multi-selection
            this.toggleMessageSelection(messageElement);
        } else {
            // Single selection
            this.clearSelection();
            this.toggleMessageSelection(messageElement);
        }

        this.lastSelectedIndex = messageIndex;
    }

    /**
     * Toggle selection state of a message
     */
    toggleMessageSelection(messageElement) {
        const messageId = messageElement.getAttribute('data-message-id');
        const checkbox = messageElement.querySelector('.message-checkbox');

        if (this.selectedMessages.has(messageId)) {
            // Deselect
            this.selectedMessages.delete(messageId);
            messageElement.classList.remove('selected');
            if (checkbox) checkbox.checked = false;
        } else {
            // Select
            this.selectedMessages.add(messageId);
            messageElement.classList.add('selected');
            if (checkbox) checkbox.checked = true;
            this.selectionMode = true;
        }

        this.updateSelectionUI();
    }

    /**
     * Select range of messages
     */
    selectMessageRange(startIndex, endIndex) {
        const messages = this.elements.chatMessages.querySelectorAll('.message[data-selectable="true"]');
        const start = Math.min(startIndex, endIndex);
        const end = Math.max(startIndex, endIndex);

        for (let i = start; i <= end; i++) {
            if (messages[i]) {
                const messageId = messages[i].getAttribute('data-message-id');
                this.selectedMessages.add(messageId);
                messages[i].classList.add('selected');
                const checkbox = messages[i].querySelector('.message-checkbox');
                if (checkbox) checkbox.checked = true;
            }
        }

        this.selectionMode = true;
        this.updateSelectionUI();
    }

    /**
     * Select all selectable messages
     */
    selectAllMessages() {
        const messages = this.elements.chatMessages.querySelectorAll('.message[data-selectable="true"]');

        messages.forEach(message => {
            const messageId = message.getAttribute('data-message-id');
            this.selectedMessages.add(messageId);
            message.classList.add('selected');
            const checkbox = message.querySelector('.message-checkbox');
            if (checkbox) checkbox.checked = true;
        });

        this.selectionMode = true;
        this.updateSelectionUI();
        this.showToast('success', 'All messages selected', `Selected ${messages.length} messages`);
    }

    /**
     * Clear all selections
     */
    clearSelection() {
        this.selectedMessages.clear();
        this.selectionMode = false;

        const messages = this.elements.chatMessages.querySelectorAll('.message.selected');
        messages.forEach(message => {
            message.classList.remove('selected');
            const checkbox = message.querySelector('.message-checkbox');
            if (checkbox) checkbox.checked = false;
        });

        this.updateSelectionUI();
    }

    /**
     * Update selection UI state
     */
    updateSelectionUI() {
        const count = this.selectedMessages.size;
        const toolbar = this.elements.selectionToolbar;
        const countElement = toolbar.querySelector('.selection-count');

        if (count > 0) {
            toolbar.style.display = 'flex';
            countElement.textContent = `${count} message${count !== 1 ? 's' : ''} selected`;

            // Update select all button text
            const allMessages = this.elements.chatMessages.querySelectorAll('.message[data-selectable="true"]');
            const selectAllBtn = this.elements.selectAllBtn;
            const selectAllText = selectAllBtn.querySelector('.text');

            if (count === allMessages.length) {
                selectAllText.textContent = 'All Selected';
                selectAllBtn.disabled = true;
            } else {
                selectAllText.textContent = 'Select All';
                selectAllBtn.disabled = false;
            }
        } else {
            toolbar.style.display = 'none';
        }
    }

    /**
     * Copy selected messages to clipboard
     */
    async copySelectedMessages() {
        if (this.selectedMessages.size === 0) {
            this.showToast('error', 'No messages selected', 'Select some messages first');
            return;
        }

        try {
            const messages = [];
            this.selectedMessages.forEach(messageId => {
                const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
                if (messageElement) {
                    const author = messageElement.querySelector('.message-author')?.textContent?.trim() || 'Unknown';
                    const content = messageElement.querySelector('.message-text')?.textContent?.trim() || '';
                    const timestamp = messageElement.querySelector('.message-timestamp')?.textContent?.trim() || '';

                    messages.push(`${author}\n${content}\n[${timestamp}]\n`);
                }
            });

            const textToCopy = messages.join('\n---\n');
            await navigator.clipboard.writeText(textToCopy);

            this.showToast('success', 'Messages copied', `Copied ${this.selectedMessages.size} messages to clipboard`);
        } catch (error) {
            console.error('Failed to copy selected messages:', error);
            this.showToast('error', 'Copy failed', 'Unable to copy messages to clipboard');
        }
    }

    /**
     * Export selected messages as text file
     */
    exportSelectedMessages() {
        if (this.selectedMessages.size === 0) {
            this.showToast('error', 'No messages selected', 'Select some messages first');
            return;
        }

        try {
            const messages = [];
            this.selectedMessages.forEach(messageId => {
                const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
                if (messageElement) {
                    const author = messageElement.querySelector('.message-author')?.textContent?.trim() || 'Unknown';
                    const content = messageElement.querySelector('.message-text')?.textContent?.trim() || '';
                    const timestamp = messageElement.querySelector('.message-timestamp')?.textContent?.trim() || '';

                    messages.push(`${author}\n${content}\n[${timestamp}]\n`);
                }
            });

            const content = `Claude Code Toolkit - Chat Export\nExported: ${new Date().toLocaleString()}\nMessages: ${messages.length}\n\n${messages.join('\n---\n')}`;

            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `claude-chat-export-${new Date().toISOString().slice(0, 10)}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showToast('success', 'Export complete', `Exported ${messages.length} messages`);
        } catch (error) {
            console.error('Failed to export messages:', error);
            this.showToast('error', 'Export failed', 'Unable to export messages');
        }
    }

    /**
     * Retry a failed message
     */
    async retryFailedMessage(messageElement, messageId) {
        const messageText = messageElement.querySelector('.message-text');
        if (!messageText) return;

        const retryBtn = messageElement.querySelector('.retry-btn');
        if (retryBtn) {
            retryBtn.classList.add('loading');
            retryBtn.disabled = true;
        }

        try {
            // Clear error state
            messageElement.classList.remove('error');
            const errorDetails = messageElement.querySelector('.error-details');
            if (errorDetails) {
                errorDetails.style.display = 'none';
            }

            // Update status to sending
            this.updateMessageStatus(messageElement, 'sending', 'Retrying message...');

            // Get message content and resend
            const content = messageText.textContent.trim();

            if (this.connectionType === 'websocket' && this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'message',
                    content: content,
                    session_id: this.sessionId,
                    message_id: messageId + '_retry_' + Date.now()
                }));
            } else if (this.connectionType === 'sse') {
                const response = await fetch('/api/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: content,
                        session_id: this.sessionId
                    }),
                    signal: AbortSignal.timeout(30000)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            }

            this.updateMessageStatus(messageElement, 'sent', 'Message sent successfully');
            this.showToast('success', 'Message retried', 'Message sent successfully');

        } catch (error) {
            console.error('Failed to retry message:', error);
            this.setMessageError(messageElement, error.message);
            this.showToast('error', 'Retry failed', error.message);
        } finally {
            if (retryBtn) {
                retryBtn.classList.remove('loading');
                retryBtn.disabled = false;
            }
        }
    }

    /**
     * Set message error state with details
     */
    setMessageError(messageElement, errorMessage) {
        messageElement.classList.add('error');

        const errorDetails = messageElement.querySelector('.error-details');
        const errorMessageSpan = messageElement.querySelector('.error-message');
        const errorTimestamp = messageElement.querySelector('.error-timestamp');

        if (errorDetails && errorMessageSpan && errorTimestamp) {
            errorMessageSpan.textContent = errorMessage;
            errorTimestamp.textContent = new Date().toLocaleTimeString();
            errorDetails.style.display = 'block';
        }

        this.updateMessageStatus(messageElement, 'error', `Failed: ${errorMessage}`);
    }

    /**
     * Show toast notification
     */
    showToast(type, message, details = '') {
        const template = this.templates.toast.content.cloneNode(true);
        const toast = template.querySelector('.toast');

        toast.setAttribute('data-type', type);

        const icon = toast.querySelector('.icon');
        const messageElement = toast.querySelector('.toast-message');
        const detailsElement = toast.querySelector('.toast-details');
        const closeBtn = toast.querySelector('.toast-close');

        // Set icon based on type
        switch (type) {
            case 'success':
                icon.textContent = '✓';
                break;
            case 'error':
                icon.textContent = '✗';
                break;
            case 'info':
                icon.textContent = 'ℹ';
                break;
            default:
                icon.textContent = '•';
        }

        messageElement.textContent = message;
        if (details) {
            detailsElement.textContent = details;
        } else {
            detailsElement.style.display = 'none';
        }

        // Add close functionality
        closeBtn.addEventListener('click', () => {
            this.removeToast(toast);
        });

        // Add to container
        this.elements.toastContainer.appendChild(toast);

        // Auto-remove after delay
        setTimeout(() => {
            this.removeToast(toast);
        }, 5000);

        // Manage toast queue
        this.manageToastQueue();
    }

    /**
     * Remove toast notification
     */
    removeToast(toast) {
        if (toast && toast.parentNode) {
            toast.style.animation = 'toastSlideOut 0.3s ease-in forwards';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    }

    /**
     * Manage toast queue to prevent overflow
     */
    manageToastQueue() {
        const toasts = this.elements.toastContainer.querySelectorAll('.toast');
        if (toasts.length > this.maxToasts) {
            // Remove oldest toasts
            for (let i = 0; i < toasts.length - this.maxToasts; i++) {
                this.removeToast(toasts[i]);
            }
        }
    }
}

// Initialize chat interface when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Claude Code Toolkit Chat Interface...');

    try {
        window.chatInterface = new ChatInterface();
    } catch (error) {
        console.error('❌ Failed to initialize chat interface:', error);

        // Show basic error message
        document.body.innerHTML = `
            <div style="
                font-family: 'JetBrains Mono', monospace;
                background: #0d1117;
                color: #c9d1d9;
                padding: 40px;
                text-align: center;
                height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            ">
                <h1 style="color: #f85149; margin-bottom: 20px;">⚠️ Initialization Failed</h1>
                <p style="margin-bottom: 20px;">Could not initialize the chat interface.</p>
                <p style="color: #8b949e; font-size: 14px;">Error: ${error.message}</p>
                <button
                    onclick="window.location.reload()"
                    style="
                        background: #58a6ff;
                        color: #0d1117;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 6px;
                        font-family: inherit;
                        font-weight: 600;
                        cursor: pointer;
                        margin-top: 20px;
                    "
                >
                    Reload Page
                </button>
            </div>
        `;
    }
});
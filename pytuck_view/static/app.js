// ================================================================
// 前端国际化管理器 (i18n)
// 负责加载、缓存和切换多语言翻译
// ================================================================
const i18n = {
    locale: 'zh_cn',
    messages: {},
    messageCache: {},
    loading: false,
    loaded: new Set(),

    t(key) {
        var val = this.messages[key];
        return val !== undefined ? val : key;
    },

    async loadLocale(locale) {
        this.loading = true;
        try {
            if (this.loaded.has(locale) && this.messageCache[locale]) {
                this.messages = this.messageCache[locale];
                this.loading = false;
                return;
            }
            const response = await fetch(`/api/locales/${locale}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const translations = await response.json();
            this.messages = translations;
            this.messageCache[locale] = translations;
            this.loaded.add(locale);
        } catch (error) {
            console.error(`加载语言失败: ${locale}`, error);
            if (locale !== 'zh_cn') await this.loadLocale('zh_cn');
        } finally {
            this.loading = false;
        }
    },

    async setLocale(locale) {
        await this.loadLocale(locale);
        this.locale = locale;
        localStorage.setItem('pytuck-view-locale', locale);
    },

    async init() {
        const saved = localStorage.getItem('pytuck-view-locale');
        if (saved) {
            await this.loadLocale(saved);
            this.locale = saved;
        } else {
            const browserLang = navigator.language || navigator.userLanguage;
            const targetLocale = browserLang.startsWith('en') ? 'en_us' : 'zh_cn';
            await this.loadLocale(targetLocale);
            this.locale = targetLocale;
        }
    }
};

// ================================================================
// 工具函数模块
// ================================================================
const utils = {
    formatFileSize(bytes) {
        if (bytes === 0 || bytes === null) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleString('zh-CN');
    },

    parseBreadcrumbs(path) {
        if (!path) return [];
        const parts = path.split(/[/\\]/).filter(p => p);
        const crumbs = [];

        if (path.match(/^[A-Z]:/i)) {
            crumbs.push({ name: parts[0], path: parts[0] + '\\' });
            for (let i = 1; i < parts.length; i++) {
                crumbs.push({ name: parts[i], path: parts.slice(0, i + 1).join('\\') });
            }
        } else {
            crumbs.push({ name: '根目录', path: '/' });
            for (let i = 0; i < parts.length; i++) {
                crumbs.push({ name: parts[i], path: '/' + parts.slice(0, i + 1).join('/') });
            }
        }
        return crumbs;
    },

    getParentPath(currentPath) {
        if (currentPath.match(/^[A-Z]:[\\\/]/i)) {
            const parts = currentPath.split(/[\\\/]/).filter(p => p);
            return parts.length === 1 ? parts[0] + '\\' : parts.slice(0, -1).join('\\');
        } else {
            const parts = currentPath.split('/').filter(p => p);
            const parent = '/' + parts.slice(0, -1).join('/');
            return parent || '/';
        }
    },

    canNavigateUp(path) {
        if (!path) return false;
        return !path.match(/^[A-Z]:[\\\/]?$/i) && path !== '/';
    }
};

// ================================================================
// API 客户端模块
// ================================================================
function createApiClient(state) {
    return async function api(path, options = {}) {
        try {
            const response = await fetch(`/api${path}`, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Language': i18n.locale,
                    ...options.headers
                },
                ...options
            });
            const result = await response.json();

            if (result.code !== undefined) {
                if (result.code !== 0) {
                    throw new Error(result.msg || `错误代码: ${result.code}`);
                }
                if (result.msg && (result.msg.includes('暂不可用') ||
                    result.msg.includes('需要') || result.msg.includes('占位符'))) {
                    state.placeholderWarning = result.msg;
                }
                return result.data;
            } else if (!response.ok) {
                throw new Error(result.detail || `HTTP ${response.status}`);
            }
            return result;
        } catch (error) {
            console.error('API 错误:', error);
            state.error = error.message;
            throw error;
        }
    };
}

// ================================================================
// Vue 应用入口
// ================================================================
(async () => {
    await i18n.init();

    const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

    createApp({
        setup() {
            // ========== 国际化状态 ==========
            const locale = ref(i18n.locale);
            const isLoadingLocale = ref(i18n.loading);
            const showLanguageMenu = ref(false);

            const t = (key) => i18n.t(key);

            const switchLocale = async (newLocale) => {
                showLanguageMenu.value = false;
                if (newLocale === locale.value && i18n.loaded.has(newLocale)) return;

                isLoadingLocale.value = true;
                await i18n.setLocale(newLocale);
                locale.value = newLocale;
                isLoadingLocale.value = false;

                if (state.currentDatabase) await loadTables();
            };

            const toggleLanguageMenu = () => {
                showLanguageMenu.value = !showLanguageMenu.value;
            };

            const handleGlobalClick = (event) => {
                if (!event.target.closest('.language-switcher')) {
                    showLanguageMenu.value = false;
                }
                if (!event.target.closest('.column-picker-wrapper')) {
                    state.showColumnPicker = false;
                }
            };

            // 复制错误消息到剪贴板
            const copyErrorMessage = async () => {
                if (state.error) {
                    try {
                        await navigator.clipboard.writeText(state.error);
                    } catch (err) {
                        // 降级方案：使用传统方式复制
                        const textarea = document.createElement('textarea');
                        textarea.value = state.error;
                        textarea.style.position = 'fixed';
                        textarea.style.opacity = '0';
                        document.body.appendChild(textarea);
                        textarea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textarea);
                    }
                }
            };

            watch(locale, (newLocale) => {
                document.documentElement.setAttribute('lang',
                    newLocale === 'zh_cn' ? 'zh-CN' : 'en-US');
            });

            // ========== 应用状态 ==========
            const state = reactive({
                currentPage: 'file-selector',
                recentFiles: [],
                currentDatabase: null,
                tables: [],
                currentTable: null,
                activeTab: 'data',  // 默认显示数据视图
                tableSchema: null,
                tableData: [],
                currentPageNum: 1,
                totalRows: 0,
                rowsPerPage: 50,
                jumpPageInput: '',
                loading: false,
                error: null,
                placeholderWarning: null,
                sortBy: null,
                sortOrder: 'asc',
                // 编辑相关状态
                primaryKeyColumn: null,       // 当前表的主键列名
                hasPrimaryKey: false,         // 当前表是否有主键
                isPseudoPk: false,            // 是否使用隐式 _pytuck_rowid
                selectedRowIndex: null,       // 当前选中行索引
                editRowIndex: null,           // 正在编辑的行索引
                editBuffer: null,             // 编辑缓冲区
                isAddingRow: false,           // 是否正在添加新行
                newRowData: {},               // 新行数据
                viewMode: 'table',            // 视图模式: 'table' | 'record'
                // 表/列编辑状态
                editingTableName: false,      // 是否正在编辑表名
                editingTableComment: false,   // 是否正在编辑表备注
                editingColumnComment: null,   // 正在编辑备注的列名
                editTableNameValue: '',       // 表名编辑值
                editTableCommentValue: '',    // 表备注编辑值
                editColumnCommentValue: '',   // 列备注编辑值
                // 表编辑弹窗状态
                showTableEditModal: false,    // 是否显示表编辑弹窗
                tableEditForm: {              // 表编辑表单数据
                    originalName: '',
                    name: '',
                    comment: ''
                },
                // 单元格展开/列宽拖拽状态
                expandedCells: {},            // { 'rowIndex-colName': true }
                columnWidths: {},             // { colName: widthPx }
                resizingColumn: null,         // 当前拖拽的列名
                resizeStartX: 0,              // 拖拽起始X坐标
                resizeStartWidth: 0,          // 拖拽起始宽度
                // 侧边栏状态
                sidebarCollapsed: false,      // 侧边栏是否折叠
                sidebarWidth: 250,            // 侧边栏宽度(px)
                showSidebarSearch: false,     // 是否显示搜索框
                sidebarFilter: '',            // 搜索筛选文本
                // 列可见性状态
                hiddenColumns: {},            // { colName: true } 隐藏的列
                showColumnPicker: false,      // 是否显示列选择器
                // 成功消息
                successMessage: null,         // 成功消息（绿色 toast）
            });

            // ========== 引擎转换状态 ==========
            const convertModal = reactive({
                visible: false,
                file: null,                   // 选中的文件
                availableEngines: {},         // { engine_name: is_available }
                targetEngine: '',             // 选中的目标引擎
                targetPath: '',               // 目标文件路径
                converting: false,            // 是否正在转换
            });

            const ENGINE_EXTENSIONS = {
                binary: '.ptk',
                sqlite: '.db',
                json: '.json',
                csv: '.csv.zip',
                excel: '.xlsx',
                xml: '.xml',
            };

            // ========== 文件浏览器状态 ==========
            const fileBrowser = reactive({
                visible: false,
                path: "",
                pathInput: "",
                entries: [],
                loading: false
            });

            // ========== 计算属性 ==========
            const totalPages = computed(() => Math.ceil(state.totalRows / state.rowsPerPage));
            const hasData = computed(() => state.tableData && state.tableData.length > 0);
            const visibleColumns = computed(() => {
                if (!state.tableSchema || !state.tableSchema.columns) return [];
                return state.tableSchema.columns.filter(col =>
                    col.name !== '_pytuck_rowid' && !state.hiddenColumns[col.name]
                );
            });
            const filteredTables = computed(() => {
                if (!state.sidebarFilter) return state.tables;
                var kw = state.sidebarFilter.toLowerCase();
                return state.tables.filter(t =>
                    t.name.toLowerCase().includes(kw) ||
                    (t.comment && t.comment.toLowerCase().includes(kw))
                );
            });
            const sidebarWidthStyle = computed(() => {
                return state.sidebarCollapsed ? '48px' : (state.sidebarWidth + 'px');
            });
            // 所有列（除 _pytuck_rowid，用于列选择器面板）
            const allUserColumns = computed(() => {
                if (!state.tableSchema || !state.tableSchema.columns) return [];
                return state.tableSchema.columns.filter(col => col.name !== '_pytuck_rowid');
            });
            const breadcrumbs = computed(() => utils.parseBreadcrumbs(fileBrowser.path));
            const canGoUp = computed(() => utils.canNavigateUp(fileBrowser.path));

            // ========== API 客户端 ==========
            const api = createApiClient(state);

            // ========== 文件管理操作 ==========
            async function loadRecentFiles() {
                try {
                    state.loading = true;
                    const data = await api('/recent-files');
                    const files = data.files || [];
                    files.sort((a, b) => String(a.path).localeCompare(String(b.path)));
                    state.recentFiles = files;
                } catch (error) {
                    console.error('加载最近文件失败:', error);
                } finally {
                    state.loading = false;
                }
            }

            async function openFile(filePath) {
                try {
                    state.loading = true;
                    state.error = null;
                    state.placeholderWarning = null;

                    const data = await api('/open-file', {
                        method: 'POST',
                        body: JSON.stringify({ path: filePath })
                    });

                    state.currentDatabase = data;
                    state.currentPage = 'database-view';
                    await loadTables();
                } catch (error) {
                    state.error = `${t('error.openFileFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            async function removeHistory(fileId) {
                try {
                    state.loading = true;
                    await api(`/recent-files/${fileId}`, { method: 'DELETE' });
                    if (state.currentDatabase && state.currentDatabase.file_id === fileId) {
                        backToFileSelector();
                    }
                    await loadRecentFiles();
                } catch (error) {
                    state.error = `${t('error.removeFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            async function updateFileNote(fileId, note) {
                try {
                    await api(`/recent-files/${fileId}/note`, {
                        method: 'PATCH',
                        body: JSON.stringify({ note: note })
                    });
                } catch (error) {
                    state.error = `${t('error.removeFailed')}: ${error.message}`;
                }
            }

            // ========== 文件浏览器操作 ==========
            async function openFileBrowser() {
                fileBrowser.visible = true;
                fileBrowser.loading = true;
                try {
                    const data = await api('/last-browse-directory');
                    await browseTo(data.directory);
                } catch (error) {
                    state.error = `${t('error.cannotOpenFileBrowser')}: ${error.message}`;
                } finally {
                    fileBrowser.loading = false;
                }
            }

            function closeFileBrowser() {
                fileBrowser.visible = false;
            }

            async function browseTo(path) {
                fileBrowser.loading = true;
                try {
                    const data = await api(`/browse-directory?path=${encodeURIComponent(path)}`);
                    fileBrowser.path = data.path;
                    fileBrowser.pathInput = data.path;
                    fileBrowser.entries = data.entries || [];
                } catch (error) {
                    state.error = error.message;
                } finally {
                    fileBrowser.loading = false;
                }
            }

            async function goToPath() {
                if (!fileBrowser.pathInput.trim()) return;
                await browseTo(fileBrowser.pathInput.trim());
            }

            async function goUp() {
                if (!canGoUp.value) return;
                await browseTo(utils.getParentPath(fileBrowser.path));
            }

            async function goToBreadcrumb(index) {
                const crumb = breadcrumbs.value[index];
                if (crumb) await browseTo(crumb.path);
            }

            async function selectAndOpenFile(filePath) {
                closeFileBrowser();
                await openFile(filePath);
            }

            // ========== 数据库/表操作 ==========
            async function loadTables() {
                if (!state.currentDatabase) return;
                try {
                    const data = await api(`/tables/${state.currentDatabase.file_id}`);
                    state.tables = data.tables || [];
                    // 按表名排序
                    state.tables.sort((a, b) => a.name.localeCompare(b.name));
                    if (data.has_placeholder) {
                        state.placeholderWarning = '部分功能需要 pytuck 库支持，表列表可能不完整';
                    }
                } catch (error) {
                    console.error('加载表列表失败:', error);
                }
            }

            async function selectTable(tableName) {
                try {
                    state.loading = true;
                    state.currentTable = tableName;
                    state.currentPageNum = 1;
                    state.activeTab = 'data';  // 默认显示数据视图
                    state.viewMode = 'table';  // 重置视图模式
                    state.selectedRowIndex = null;
                    state.editRowIndex = null;
                    state.editBuffer = null;
                    state.isAddingRow = false;
                    state.newRowData = {};
                    state.expandedCells = {};
                    state.columnWidths = {};
                    state.hiddenColumns = {};

                    // 并行加载表结构和数据
                    await Promise.all([
                        loadTableSchema(tableName),
                        loadTableData(tableName, 1),
                        loadPrimaryKeyInfo(tableName)
                    ]);

                    // 默认选中第一行
                    if (state.tableData.length > 0) {
                        state.selectedRowIndex = 0;
                    }
                } catch (error) {
                    state.error = `${t('error.loadTableDataFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            async function loadPrimaryKeyInfo(tableName) {
                if (!state.currentDatabase) return;
                try {
                    const data = await api(`/schema/${state.currentDatabase.file_id}/${tableName}/primary-key`);
                    state.primaryKeyColumn = data.primary_key;
                    state.hasPrimaryKey = data.has_primary_key;
                    state.isPseudoPk = data.is_pseudo_pk || false;
                } catch (error) {
                    console.error('获取主键信息失败:', error);
                    state.primaryKeyColumn = null;
                    state.hasPrimaryKey = false;
                    state.isPseudoPk = false;
                }
            }

            async function loadTableSchema(tableName) {
                if (!state.currentDatabase) return;
                const data = await api(`/schema/${state.currentDatabase.file_id}/${tableName}`);
                state.tableSchema = data;
                if (data.columns && data.columns.some(col => col.name && col.name.startsWith('⚠️'))) {
                    state.placeholderWarning = '表结构功能需要 pytuck 库完善，列信息可能不准确';
                }
            }

            async function loadTableData(tableName, page = 1) {
                if (!state.currentDatabase) return;
                const params = new URLSearchParams({
                    page: page.toString(),
                    limit: state.rowsPerPage.toString()
                });
                if (state.sortBy) {
                    params.append('sort', state.sortBy);
                    params.append('order', state.sortOrder);
                }

                const data = await api(`/rows/${state.currentDatabase.file_id}/${tableName}?${params}`);
                state.tableData = data.rows || [];
                state.totalRows = data.total || 0;
                state.currentPageNum = data.page || 1;

                if (data.rows && data.rows.length > 0 && data.rows[0].is_placeholder) {
                    state.placeholderWarning = '数据查询功能暂不可用，需要 pytuck 库支持';
                }
            }

            async function switchToDataTab() {
                state.activeTab = 'data';
                if (state.currentTable && (!state.tableData || state.tableData.length === 0)) {
                    await loadTableData(state.currentTable, state.currentPageNum || 1);
                }
            }

            async function sortTable(columnName) {
                // 拖拽列宽后跳过排序
                if (state.resizingColumn || state._justResized) {
                    state._justResized = false;
                    return;
                }
                if (state.sortBy === columnName) {
                    state.sortOrder = state.sortOrder === 'asc' ? 'desc' : 'asc';
                } else {
                    state.sortBy = columnName;
                    state.sortOrder = 'asc';
                }
                if (state.currentTable) {
                    await loadTableData(state.currentTable, state.currentPageNum);
                }
            }

            async function goToPage(page) {
                if (page < 1 || page > totalPages.value || !state.currentTable) return;
                state.activeTab = 'data';
                await loadTableData(state.currentTable, page);
                // 默认选中第一行
                if (state.tableData.length > 0) {
                    state.selectedRowIndex = 0;
                }
            }

            async function changeRowsPerPage(newSize) {
                state.rowsPerPage = newSize;
                state.currentPageNum = 1;
                if (state.currentTable) {
                    await loadTableData(state.currentTable, 1);
                    if (state.tableData.length > 0) {
                        state.selectedRowIndex = 0;
                    }
                }
            }

            function jumpToPage() {
                var page = state.jumpPageInput;
                if (!page || page < 1 || page > totalPages.value) return;
                goToPage(page);
                state.jumpPageInput = '';
            }

            // ========== 表/列编辑操作 ==========

            function startEditTableName() {
                state.editingTableName = true;
                state.editTableNameValue = state.currentTable || '';
            }

            function cancelEditTableName() {
                state.editingTableName = false;
                state.editTableNameValue = '';
            }

            async function saveTableName() {
                if (!state.currentDatabase || !state.currentTable) return;
                if (!state.editTableNameValue.trim()) {
                    state.error = t('dataEdit.tableNameRequired');
                    return;
                }
                if (state.editTableNameValue === state.currentTable) {
                    cancelEditTableName();
                    return;
                }

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/tables/${state.currentDatabase.file_id}/${state.currentTable}/rename`, {
                        method: 'POST',
                        body: JSON.stringify({ new_name: state.editTableNameValue })
                    });
                    const newName = state.editTableNameValue;
                    state.currentTable = newName;
                    cancelEditTableName();
                    await loadTables();
                    await loadTableSchema(newName);
                } catch (error) {
                    state.error = `${t('dataEdit.renameFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            function startEditTableComment() {
                state.editingTableComment = true;
                state.editTableCommentValue = state.tableSchema?.table_comment || '';
            }

            function cancelEditTableComment() {
                state.editingTableComment = false;
                state.editTableCommentValue = '';
            }

            async function saveTableComment() {
                if (!state.currentDatabase || !state.currentTable) return;

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/tables/${state.currentDatabase.file_id}/${state.currentTable}/comment`, {
                        method: 'POST',
                        body: JSON.stringify({ comment: state.editTableCommentValue || null })
                    });
                    cancelEditTableComment();
                    await loadTables();
                    await loadTableSchema(state.currentTable);
                } catch (error) {
                    state.error = `${t('dataEdit.saveCommentFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            function startEditColumnComment(columnName, currentComment) {
                state.editingColumnComment = columnName;
                state.editColumnCommentValue = currentComment || '';
            }

            function cancelEditColumnComment() {
                state.editingColumnComment = null;
                state.editColumnCommentValue = '';
            }

            async function saveColumnComment(columnName) {
                if (!state.currentDatabase || !state.currentTable) return;

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/columns/${state.currentDatabase.file_id}/${state.currentTable}/${columnName}/comment`, {
                        method: 'POST',
                        body: JSON.stringify({ comment: state.editColumnCommentValue || null })
                    });
                    cancelEditColumnComment();
                    await loadTableSchema(state.currentTable);
                } catch (error) {
                    state.error = `${t('dataEdit.saveCommentFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            // ========== 表编辑弹窗操作 ==========

            function openTableEditModal(table) {
                state.showTableEditModal = true;
                state.tableEditForm = {
                    originalName: table.name,
                    name: table.name,
                    comment: table.comment || ''
                };
            }

            function closeTableEditModal() {
                state.showTableEditModal = false;
                state.tableEditForm = { originalName: '', name: '', comment: '' };
            }

            async function saveTableEdit() {
                if (!state.currentDatabase) return;
                const { originalName, name, comment } = state.tableEditForm;

                if (!name.trim()) {
                    state.error = t('dataEdit.tableNameRequired');
                    return;
                }

                try {
                    state.loading = true;
                    state.error = null;

                    // 如果表名改变，先重命名
                    if (name !== originalName) {
                        await api(`/tables/${state.currentDatabase.file_id}/${originalName}/rename`, {
                            method: 'POST',
                            body: JSON.stringify({ new_name: name })
                        });
                    }

                    // 更新备注（无论是否改变都更新，以简化逻辑）
                    await api(`/tables/${state.currentDatabase.file_id}/${name}/comment`, {
                        method: 'POST',
                        body: JSON.stringify({ comment: comment || null })
                    });

                    // 如果当前选中的表被重命名，更新状态
                    if (state.currentTable === originalName) {
                        state.currentTable = name;
                        await loadTableSchema(name);
                    }

                    closeTableEditModal();
                    await loadTables();
                } catch (error) {
                    state.error = `${t('dataEdit.renameFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            async function deleteTable() {
                if (!state.currentDatabase) return;
                const tableName = state.tableEditForm.originalName;

                const msg = t('dataEdit.confirmDeleteTable').replace('{name}', tableName);
                if (!confirm(msg)) return;

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/tables/${state.currentDatabase.file_id}/${tableName}`, {
                        method: 'DELETE'
                    });

                    closeTableEditModal();

                    // 如果删除的是当前选中的表，清空右侧内容
                    if (state.currentTable === tableName) {
                        state.currentTable = null;
                        state.tableSchema = null;
                        state.tableData = [];
                        state.totalRows = 0;
                    }

                    await loadTables();
                } catch (error) {
                    state.error = `${t('dataEdit.deleteFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            // ========== 单元格展开/列宽拖拽 ==========

            function isCellExpanded(rowIndex, colName) {
                return !!state.expandedCells[rowIndex + '-' + colName];
            }

            function toggleCellExpand(rowIndex, colName) {
                var key = rowIndex + '-' + colName;
                if (state.expandedCells[key]) {
                    delete state.expandedCells[key];
                } else {
                    state.expandedCells[key] = true;
                }
            }

            function getColWidth(colName) {
                return state.columnWidths[colName] || 150;
            }

            function startColResize(event, colName) {
                state.resizingColumn = colName;
                state.resizeStartX = event.clientX;
                state.resizeStartWidth = getColWidth(colName);

                var onMouseMove = function(e) {
                    if (!state.resizingColumn) return;
                    var diff = e.clientX - state.resizeStartX;
                    var newWidth = Math.max(50, state.resizeStartWidth + diff);
                    state.columnWidths[colName] = newWidth;
                };

                var onMouseUp = function() {
                    state.resizingColumn = null;
                    state._justResized = true;
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            }

            // ========== 侧边栏操作 ==========

            function toggleSidebar() {
                state.sidebarCollapsed = !state.sidebarCollapsed;
            }

            function startSidebarResize(event) {
                if (state.sidebarCollapsed) return;
                var startX = event.clientX;
                var startWidth = state.sidebarWidth;

                var onMouseMove = function(e) {
                    var diff = e.clientX - startX;
                    state.sidebarWidth = Math.max(150, Math.min(600, startWidth + diff));
                };

                var onMouseUp = function() {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            }

            function toggleSidebarSearch() {
                state.showSidebarSearch = !state.showSidebarSearch;
                if (!state.showSidebarSearch) {
                    state.sidebarFilter = '';
                } else {
                    Vue.nextTick(() => {
                        var input = document.querySelector('.sidebar-search-input');
                        if (input) input.focus();
                    });
                }
            }

            // ========== 列可见性操作 ==========

            function toggleColumnPicker() {
                state.showColumnPicker = !state.showColumnPicker;
            }

            function toggleColumnVisibility(colName) {
                if (state.hiddenColumns[colName]) {
                    delete state.hiddenColumns[colName];
                } else {
                    state.hiddenColumns[colName] = true;
                }
            }

            // ========== 数据行验证 ==========

            function validateRowData(data, columns, isNew = false) {
                const errors = [];
                for (const col of columns) {
                    const value = data[col.name];
                    const isEmpty = value === null || value === undefined ||
                                   (typeof value === 'string' && value.trim() === '');

                    // 主键必填（新增时）
                    if (isNew && col.primary_key && isEmpty) {
                        errors.push(`${col.name} (${t('dataEdit.primaryKey')}) ${t('dataEdit.fieldRequired')}`);
                    }
                    // 非空字段必填（排除主键，主键单独检查）
                    if (!col.nullable && isEmpty && !col.primary_key) {
                        errors.push(`${col.name} ${t('dataEdit.fieldRequired')}`);
                    }
                }
                return errors;
            }

            // ========== 数据行编辑操作 ==========

            function selectRow(index) {
                state.selectedRowIndex = index;
            }

            function startEditRow(index) {
                state.editRowIndex = index;
                state.editBuffer = JSON.parse(JSON.stringify(state.tableData[index]));
            }

            function cancelEditRow() {
                state.editRowIndex = null;
                state.editBuffer = null;
            }

            async function saveEditRow() {
                if (!state.currentDatabase || !state.currentTable || state.editBuffer === null) return;
                if (!state.primaryKeyColumn) {
                    state.error = t('dataEdit.noPkCannotSave');
                    return;
                }

                // 验证非空字段
                if (state.tableSchema?.columns) {
                    const errors = validateRowData(state.editBuffer, state.tableSchema.columns, false);
                    if (errors.length > 0) {
                        state.error = errors.join('\n');
                        return;
                    }
                }

                const pkValue = state.tableData[state.editRowIndex][state.primaryKeyColumn];
                // 发送前移除 _pytuck_rowid（内部字段不作为更新数据）
                const sendData = Object.assign({}, state.editBuffer);
                delete sendData._pytuck_rowid;

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/rows/${state.currentDatabase.file_id}/${state.currentTable}`, {
                        method: 'PUT',
                        body: JSON.stringify({ pk: pkValue, data: sendData })
                    });
                    cancelEditRow();
                    await loadTableData(state.currentTable, state.currentPageNum);
                } catch (error) {
                    state.error = `${t('dataEdit.updateFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            async function deleteRow(index) {
                if (!state.currentDatabase || !state.currentTable) return;
                if (!state.primaryKeyColumn) {
                    state.error = t('dataEdit.noPkCannotDelete');
                    return;
                }

                const pkValue = state.tableData[index][state.primaryKeyColumn];
                if (!confirm(`${t('dataEdit.confirmDelete')}\n${t('dataEdit.primaryKey')}: ${pkValue}`)) return;

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/rows/${state.currentDatabase.file_id}/${state.currentTable}`, {
                        method: 'DELETE',
                        body: JSON.stringify({ pk: pkValue })
                    });
                    await loadTableData(state.currentTable, state.currentPageNum);
                    await loadTableSchema(state.currentTable);
                    state.selectedRowIndex = null;
                } catch (error) {
                    state.error = `${t('dataEdit.deleteFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            function startAddRow() {
                // 切换到表格视图以显示新增表单
                state.viewMode = 'table';
                state.isAddingRow = true;
                state.newRowData = {};
                // 初始化默认值
                if (state.tableSchema?.columns) {
                    state.tableSchema.columns.forEach(col => {
                        // 跳过隐式行号字段
                        if (col.name === '_pytuck_rowid') return;
                        if (col.default_value && col.default_value !== 'None') {
                            state.newRowData[col.name] = col.default_value;
                        } else {
                            state.newRowData[col.name] = '';
                        }
                    });
                }
            }

            function cancelAddRow() {
                state.isAddingRow = false;
                state.newRowData = {};
            }

            async function saveNewRow() {
                if (!state.currentDatabase || !state.currentTable) return;

                // 验证必填字段（新增时包括主键）
                if (state.tableSchema?.columns) {
                    const errors = validateRowData(state.newRowData, state.tableSchema.columns, true);
                    if (errors.length > 0) {
                        state.error = errors.join('\n');
                        return;
                    }
                }

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/rows/${state.currentDatabase.file_id}/${state.currentTable}`, {
                        method: 'POST',
                        body: JSON.stringify({ data: state.newRowData })
                    });
                    cancelAddRow();
                    // 新增成功后切换到表格视图并刷新数据
                    state.viewMode = 'table';
                    await loadTableData(state.currentTable, state.currentPageNum);
                    // 重新加载表结构以更新行数
                    await loadTableSchema(state.currentTable);
                } catch (error) {
                    state.error = `${t('dataEdit.insertFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            // ========== 视图模式切换 ==========

            function switchViewMode(mode) {
                // 切换视图时取消正在进行的新增操作
                if (state.isAddingRow) {
                    cancelAddRow();
                }
                // 取消正在进行的编辑操作
                if (state.editRowIndex !== null) {
                    cancelEditRow();
                }
                state.viewMode = mode;
                // 切换到记录视图时，确保有选中的行
                if (mode === 'record' && state.selectedRowIndex === null && state.tableData.length > 0) {
                    state.selectedRowIndex = 0;
                }
            }

            function prevRecord() {
                if (state.selectedRowIndex > 0) {
                    state.selectedRowIndex--;
                }
            }

            function nextRecord() {
                if (state.selectedRowIndex < state.tableData.length - 1) {
                    state.selectedRowIndex++;
                }
            }

            function startEditRecord() {
                if (state.selectedRowIndex === null) return;
                state.editBuffer = JSON.parse(JSON.stringify(state.tableData[state.selectedRowIndex]));
                state.editRowIndex = state.selectedRowIndex;
            }

            function cancelEditRecord() {
                state.editBuffer = null;
                state.editRowIndex = null;
            }

            async function saveEditRecord() {
                if (!state.currentDatabase || !state.currentTable || state.editBuffer === null) return;
                if (!state.primaryKeyColumn) {
                    state.error = t('dataEdit.noPkCannotSave');
                    return;
                }

                // 验证非空字段
                if (state.tableSchema?.columns) {
                    const errors = validateRowData(state.editBuffer, state.tableSchema.columns, false);
                    if (errors.length > 0) {
                        state.error = errors.join('\n');
                        return;
                    }
                }

                const pkValue = state.tableData[state.selectedRowIndex][state.primaryKeyColumn];
                // 发送前移除 _pytuck_rowid（内部字段不作为更新数据）
                const sendData = Object.assign({}, state.editBuffer);
                delete sendData._pytuck_rowid;

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/rows/${state.currentDatabase.file_id}/${state.currentTable}`, {
                        method: 'PUT',
                        body: JSON.stringify({ pk: pkValue, data: sendData })
                    });
                    cancelEditRecord();
                    await loadTableData(state.currentTable, state.currentPageNum);
                } catch (error) {
                    state.error = `${t('dataEdit.updateFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            async function deleteRecord() {
                if (state.selectedRowIndex === null) return;
                if (!state.currentDatabase || !state.currentTable) return;
                if (!state.primaryKeyColumn) {
                    state.error = t('dataEdit.noPkCannotDelete');
                    return;
                }

                const pkValue = state.tableData[state.selectedRowIndex][state.primaryKeyColumn];
                if (!confirm(`${t('dataEdit.confirmDelete')}\n${t('dataEdit.primaryKey')}: ${pkValue}`)) return;

                try {
                    state.loading = true;
                    state.error = null;
                    await api(`/rows/${state.currentDatabase.file_id}/${state.currentTable}`, {
                        method: 'DELETE',
                        body: JSON.stringify({ pk: pkValue })
                    });
                    // 删除成功后切换回表格视图
                    state.viewMode = 'table';
                    state.selectedRowIndex = null;
                    await loadTableData(state.currentTable, state.currentPageNum);
                    await loadTableSchema(state.currentTable);
                } catch (error) {
                    state.error = `${t('dataEdit.deleteFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
                }
            }

            // ========== 导航操作 ==========
            async function backToFileSelector() {
                state.currentPage = 'file-selector';
                state.currentDatabase = null;
                state.tables = [];
                state.currentTable = null;
                state.activeTab = 'structure';
                state.tableSchema = null;
                state.tableData = [];
                state.totalRows = 0;
                state.currentPageNum = 1;
                await loadRecentFiles();
            }

            // ========== 引擎转换操作 ==========
            async function loadAvailableEngines() {
                try {
                    const result = await api('/available-engines');
                    convertModal.availableEngines = result.engines || {};
                } catch (error) {
                    state.error = error.message;
                }
            }

            function openConvertModal(file) {
                convertModal.file = file;
                convertModal.targetEngine = '';
                convertModal.targetPath = '';
                convertModal.visible = true;
                convertModal.converting = false;
                loadAvailableEngines();
            }

            function closeConvertModal() {
                convertModal.visible = false;
            }

            function onTargetEngineChange() {
                const file = convertModal.file;
                if (!file || !convertModal.targetEngine) return;
                const ext = ENGINE_EXTENSIONS[convertModal.targetEngine] || '';
                // 提取目录和文件名
                const sep = file.path.includes('\\') ? '\\' : '/';
                const lastSep = file.path.lastIndexOf(sep);
                const dir = lastSep >= 0 ? file.path.substring(0, lastSep) : '';
                const stem = file.name;
                convertModal.targetPath = dir + sep + stem + ext;
            }

            async function startConvert() {
                const { file, targetEngine, targetPath } = convertModal;
                if (!file || !targetEngine || !targetPath) return;
                convertModal.converting = true;
                try {
                    const result = await api('/convert-engine', {
                        method: 'POST',
                        body: JSON.stringify({
                            source_path: file.path,
                            source_engine: file.engine_name,
                            target_engine: targetEngine,
                            target_path: targetPath,
                        })
                    });
                    closeConvertModal();
                    // 显示成功消息
                    const msg = t('convert.convertSuccess')
                        .replace('{tables}', result.tables)
                        .replace('{records}', result.records);
                    state.successMessage = msg;
                    setTimeout(() => { state.successMessage = null; }, 5000);
                    // 刷新文件列表
                    await loadRecentFiles();
                } catch (error) {
                    state.error = `${t('convert.convertFailed')}: ${error.message}`;
                } finally {
                    convertModal.converting = false;
                }
            }

            // ========== 生命周期 ==========
            onMounted(async () => {
                await loadRecentFiles();
            });

            // ========== 导出到模板 ==========
            return {
                // 国际化
                locale, isLoadingLocale, showLanguageMenu, t,
                switchLocale, toggleLanguageMenu, handleGlobalClick, copyErrorMessage,
                // 状态
                state, fileBrowser, totalPages, hasData, visibleColumns,
                filteredTables, sidebarWidthStyle, allUserColumns,
                breadcrumbs, canGoUp,
                // 文件操作
                openFile, removeHistory, loadRecentFiles, updateFileNote,
                openFileBrowser, closeFileBrowser, browseTo,
                goToPath, goUp, goToBreadcrumb, selectAndOpenFile,
                // 表操作
                selectTable, switchToDataTab, sortTable, goToPage,
                changeRowsPerPage, jumpToPage,
                // 表/列编辑
                startEditTableName, cancelEditTableName, saveTableName,
                startEditTableComment, cancelEditTableComment, saveTableComment,
                startEditColumnComment, cancelEditColumnComment, saveColumnComment,
                // 表编辑弹窗
                openTableEditModal, closeTableEditModal, saveTableEdit, deleteTable,
                // 单元格展开/列宽拖拽
                isCellExpanded, toggleCellExpand, getColWidth, startColResize,
                // 侧边栏
                toggleSidebar, startSidebarResize, toggleSidebarSearch,
                // 列可见性
                toggleColumnPicker, toggleColumnVisibility,
                // 数据行编辑
                selectRow, startEditRow, cancelEditRow, saveEditRow, deleteRow,
                startAddRow, cancelAddRow, saveNewRow,
                // 视图模式
                switchViewMode, prevRecord, nextRecord,
                startEditRecord, cancelEditRecord, saveEditRecord, deleteRecord,
                // 导航
                backToFileSelector,
                // 引擎转换
                convertModal, openConvertModal, closeConvertModal,
                onTargetEngineChange, startConvert,
                // 工具函数
                formatFileSize: utils.formatFileSize,
                formatDate: utils.formatDate
            };
        }
    }).mount('#app');
})();

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
        return this.messages[key] || key;
    },

    async loadLocale(locale) {
        this.loading = true;
        try {
            if (this.loaded.has(locale) && this.messageCache[locale]) {
                this.messages = this.messageCache[locale];
                this.loading = false;
                return;
            }
            const response = await fetch(`/static/locales/${locale}.json`);
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
                activeTab: 'structure',
                tableSchema: null,
                tableData: [],
                currentPageNum: 1,
                totalRows: 0,
                rowsPerPage: 50,
                loading: false,
                error: null,
                placeholderWarning: null,
                sortBy: null,
                sortOrder: 'asc'
            });

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
                    files.sort((a, b) => String(b.last_opened).localeCompare(String(a.last_opened)));
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
                    state.activeTab = 'structure';
                    await loadTableSchema(tableName);
                    state.tableData = [];
                    state.totalRows = 0;
                } catch (error) {
                    state.error = `${t('error.loadTableDataFailed')}: ${error.message}`;
                } finally {
                    state.loading = false;
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

            // ========== 生命周期 ==========
            onMounted(async () => {
                await loadRecentFiles();
            });

            // ========== 导出到模板 ==========
            return {
                // 国际化
                locale, isLoadingLocale, showLanguageMenu, t,
                switchLocale, toggleLanguageMenu, handleGlobalClick,
                // 状态
                state, fileBrowser, totalPages, hasData, breadcrumbs, canGoUp,
                // 文件操作
                openFile, removeHistory, loadRecentFiles,
                openFileBrowser, closeFileBrowser, browseTo,
                goToPath, goUp, goToBreadcrumb, selectAndOpenFile,
                // 表操作
                selectTable, switchToDataTab, sortTable, goToPage,
                // 导航
                backToFileSelector,
                // 工具函数
                formatFileSize: utils.formatFileSize,
                formatDate: utils.formatDate
            };
        }
    }).mount('#app');
})();

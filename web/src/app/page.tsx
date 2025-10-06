'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { MagnifyingGlassIcon, ChartBarIcon, BookOpenIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import ArticleCard from '../components/ArticleCard'

interface Article {
  title: string
  link?: string
  url?: string
  published_time?: string
  published_at?: string
  content: string
  source?: string
  author?: string
  updated_at?: string
  platform?: string
  llm_result?: {
    deep_summary?: string
    open_question?: string
  }
  processed_at?: string
}

interface FilteredArticle extends Article {
  _filtered_reason?: string
  _duplicate_of_title?: string
  _duplicate_of_source?: string
}

interface Stats {
  total_articles: number
  sources: Record<string, number>
  last_processed?: string | null
  filtered_count?: number
  source_tree?: SourceNode[]
}

interface SourceNode {
  label: string
  count: number
  children?: SourceNode[]
}

const WECHAT_ALIASES = new Set(['wechat', '微信公众号', 'weixin', 'wx', 'mp', '公众号'])

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([])
  const [filteredArticles, setFilteredArticles] = useState<FilteredArticle[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Article[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [currentView, setCurrentView] = useState<'all' | 'search'>('all')
  const [activeSource, setActiveSource] = useState<string>('全部')
  const [showFiltered, setShowFiltered] = useState(false)
  const [sortOrder, setSortOrder] = useState<'default' | 'updated_desc' | 'updated_asc'>('default')
  const [sourceTree, setSourceTree] = useState<SourceNode[]>([])
  const [expandedSources, setExpandedSources] = useState<string[]>(['微信公众号'])

  const getSourceLabel = useCallback((source?: string) => {
    if (source && source.trim()) {
      const trimmed = source.trim()
      if (WECHAT_ALIASES.has(trimmed.toLowerCase())) {
        return '微信公众号'
      }
      return trimmed
    }
    return '未知来源'
  }, [])

  const parseDateValue = useCallback((raw?: string | null) => {
    if (!raw) return null
    const trimmed = raw.trim()
    if (!trimmed) return null

    const attempts: string[] = []
    attempts.push(trimmed)

    const normalized = trimmed
      .replace(/年|月/g, '-')
      .replace(/日/g, ' ')
      .replace(/[\.\/]/g, '-')
    attempts.push(normalized)

    if (/^\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}$/.test(normalized)) {
      attempts.push(normalized.replace(/\s+/, 'T'))
      attempts.push(`${normalized.replace(/\s+/, 'T')}:00`)
    }

    if (/^\d{4}-\d{1,2}-\d{1,2}$/.test(normalized)) {
      attempts.push(`${normalized}T00:00:00`)
    }

    for (const candidate of attempts) {
      const parsed = Date.parse(candidate)
      if (!Number.isNaN(parsed)) {
        return parsed
      }
    }
    return null
  }, [])

  const getArticleTimestamp = useCallback((article: Article) => {
    const candidates = [article.processed_at, article.published_time, article.published_at]
    for (const value of candidates) {
      const parsed = parseDateValue(value)
      if (parsed !== null) {
        return parsed
      }
    }
    return null
  }, [parseDateValue])

  const formatDateTime = (value?: string | null) => {
    if (!value) return null
    try {
      return new Date(value).toLocaleString('zh-CN', {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return value
    }
  }

  // 加载文章数据
  const fetchData = useCallback(async (showFullScreenLoader = false) => {
    if (showFullScreenLoader) {
      setLoading(true)
    } else {
      setRefreshing(true)
    }

    try {
      const [articlesRes, statsRes] = await Promise.all([
        fetch('http://localhost:5000/api/articles'),
        fetch('http://localhost:5000/api/stats')
      ])

      const articlesData = await articlesRes.json()
      const statsData = await statsRes.json()

      if (articlesData.success) {
        setArticles(articlesData.data)
      } else {
        setArticles(articlesData.data || [])
      }
      setFilteredArticles(Array.isArray(articlesData.filtered) ? articlesData.filtered : [])

      if (statsData.success) {
        setStats(statsData.data)
        if (Array.isArray(statsData.data?.source_tree)) {
          setSourceTree(statsData.data.source_tree)
        } else {
          setSourceTree([])
        }
      } else {
        setStats(statsData.data || null)
        setSourceTree([])
      }
    } catch (error) {
      console.error('加载数据失败:', error)
    } finally {
      if (showFullScreenLoader) {
        setLoading(false)
      } else {
        setRefreshing(false)
      }
    }
  }, [])

  useEffect(() => {
    fetchData(true)
  }, [fetchData])

  const handleRefresh = useCallback(async () => {
  setCurrentView('all')
  setSearchResults([])
  setActiveSource('全部')
  setFilteredArticles([])
  setExpandedSources(['微信公众号'])
  setRefreshing(true)

    try {
      const response = await fetch('http://localhost:5000/api/refresh', {
        method: 'POST'
      })
      const result = await response.json()

      if (!response.ok || !result.success) {
        console.error('刷新数据失败:', result?.message || response.statusText)
      }
    } catch (error) {
      console.error('刷新数据请求异常:', error)
    } finally {
      await fetchData(false)
    }
  }, [fetchData])

  // 搜索功能
  const handleSearch = async (query: string) => {
    if (!query.trim()) {
  setCurrentView('all')
  setActiveSource('全部')
      return
    }

    setIsSearching(true)
    try {
      const response = await fetch(`http://localhost:5000/api/search?q=${encodeURIComponent(query)}`)
      const data = await response.json()
      
      if (data.success) {
        setSearchResults(data.data)
        setCurrentView('search')
      }
    } catch (error) {
      console.error('搜索失败:', error)
    } finally {
      setIsSearching(false)
    }
  }

  const sourceOptions = useMemo(() => {
    if (sourceTree.length === 0) {
      const fallbackSet = new Set<string>()
      if (stats?.sources) {
        Object.keys(stats.sources).forEach((sourceKey) => fallbackSet.add(sourceKey))
      }
      const baseArticles = currentView === 'search' ? searchResults : articles
      baseArticles.forEach((article) => fallbackSet.add(getSourceLabel(article.source)))
      const options = Array.from(fallbackSet).sort((a, b) => a.localeCompare(b, 'zh-CN'))
      return ['全部', ...options]
    }
    const labels: string[] = ['全部']
    const traverse = (nodes: SourceNode[]) => {
      nodes.forEach((node) => {
        labels.push(node.label)
        if (node.children?.length) {
          traverse(node.children)
        }
      })
    }
    traverse(sourceTree)
    return labels
  }, [articles, currentView, getSourceLabel, searchResults, sourceTree, stats?.sources])

  const displayArticles = useMemo(() => {
    const base = currentView === 'search' ? searchResults : articles
    let filtered: Article[]
    if (activeSource === '全部') {
      filtered = base
    } else if (activeSource === '微信公众号') {
      filtered = base.filter((article) => (article.platform || '').trim() === '微信公众号')
    } else {
      filtered = base.filter((article) => getSourceLabel(article.source) === activeSource)
    }

    if (sortOrder === 'updated_desc' || sortOrder === 'updated_asc') {
      const direction = sortOrder === 'updated_desc' ? -1 : 1
      filtered = filtered
        .map((article, index) => ({ article, index }))
        .sort((a, b) => {
          const timeA = getArticleTimestamp(a.article)
          const timeB = getArticleTimestamp(b.article)

          if (timeA === null && timeB === null) {
            return a.index - b.index
          }
          if (timeA === null) {
            return 1
          }
          if (timeB === null) {
            return -1
          }
          if (timeA === timeB) {
            return a.index - b.index
          }
          return direction === -1 ? timeB - timeA : timeA - timeB
        })
        .map((item) => item.article)
    }

    return filtered
  }, [activeSource, articles, currentView, getArticleTimestamp, getSourceLabel, searchResults, sortOrder])

  const sortOrderLabel = useMemo(() => {
    switch (sortOrder) {
      case 'updated_desc':
        return '当前：按更新时间排序（最新在前）'
      case 'updated_asc':
        return '当前：按更新时间排序（最早在前）'
      default:
        return '当前：默认顺序（保持导入顺序）'
    }
  }, [sortOrder])

  const isExpanded = useCallback((label: string) => expandedSources.includes(label), [expandedSources])

  const toggleExpansion = useCallback((label: string) => {
    setExpandedSources((prev) => {
      if (prev.includes(label)) {
        return prev.filter((item) => item !== label)
      }
      return [...prev, label]
    })
  }, [])

  const normalizeFilterNodes = (nodes: SourceNode[]): SourceNode[] => {
    const map = new Map<string, SourceNode>()
    nodes.forEach((node) => {
      const key = node.label
      if (map.has(key)) {
        const existing = map.get(key)!
        existing.count += node.count
        if (node.children?.length) {
          existing.children = [...(existing.children ?? []), ...node.children]
        }
      } else {
        map.set(key, {
          label: node.label,
          count: node.count,
          children: node.children ? [...node.children] : undefined
        })
      }
    })
    return Array.from(map.values())
  }

  const renderSourceTreeList = (nodes: SourceNode[], level = 0): JSX.Element | null => {
    if (!nodes.length) return null
    const isRootLevel = level === 0

    return (
      <ul className={isRootLevel ? 'space-y-2' : 'space-y-1 pl-4 border-l border-gray-200'}>
        {nodes.map((node) => {
          const allowChildren = level > 0
          const hasChildren = allowChildren && !!node.children?.length
          const expanded = hasChildren && isExpanded(node.label)

          return (
            <li key={`${level}-${node.label}`}>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  {hasChildren && (
                    <button
                      onClick={() => toggleExpansion(node.label)}
                      className="text-xs text-blue-500 hover:text-blue-600 transition"
                    >
                      {expanded ? '▾' : '▸'}
                    </button>
                  )}
                  <span className="truncate" title={node.label}>{node.label}</span>
                </div>
                <span className="font-medium flex-shrink-0">{node.count}</span>
              </div>
              {hasChildren && expanded && renderSourceTreeList(node.children!, level + 1)}
            </li>
          )
        })}
      </ul>
    )
  }

  const renderSourceFilter = (nodes: SourceNode[], level = 0): JSX.Element | null => {
    if (!nodes.length) return null

    let nodesToRender = nodes
    if (level === 0) {
      const flattened = nodes.flatMap((node) => (node.children?.length ? node.children! : [node]))
      nodesToRender = normalizeFilterNodes(flattened)
    }

    return (
      <div className={`${level === 0 ? 'flex flex-wrap items-center gap-2' : 'mt-2 pl-4 border-l border-gray-200 space-y-2'}`}>
        {nodesToRender.map((node) => {
          const hasChildren = !!node.children?.length
          const expanded = hasChildren && isExpanded(node.label)
          const isActive = activeSource === node.label

          return (
            <div key={`filter-${level}-${node.label}`} className="flex flex-col gap-1">
              <div className="flex items-center gap-1">
                {hasChildren && (
                  <button
                    onClick={() => toggleExpansion(node.label)}
                    className="text-xs text-blue-500 hover:text-blue-600 transition"
                  >
                    {expanded ? '▾' : '▸'}
                  </button>
                )}
                <button
                  onClick={() => setActiveSource(node.label)}
                  className={`px-3 py-1.5 text-sm rounded-full border transition flex items-center gap-1 ${
                    isActive
                      ? 'bg-blue-600 text-white border-blue-600 shadow'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-blue-200 hover:text-blue-600'
                  }`}
                >
                  <span>{node.label}</span>
                  <span className={`text-xs ${isActive ? 'text-blue-100' : 'text-gray-400'}`}>{node.count}</span>
                </button>
              </div>
              {hasChildren && expanded && (
                <div className="ml-4">
                  {renderSourceFilter(node.children!, level + 1)}
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">正在加载知识库...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur border-b border-white/60 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <BookOpenIcon className="h-7 w-7 sm:h-8 sm:w-8 text-blue-600" />
              <div>
                <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900">信息融合知识库</h1>
                <p className="text-sm text-gray-500 mt-1">聚合多源内容的智能摘要与洞见</p>
              </div>
            </div>
            
            {stats && (
              <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600">
                <div className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-blue-700">
                  <ChartBarIcon className="h-4 w-4 flex-shrink-0" />
                  <span className="whitespace-nowrap">收录 {stats.total_articles} 篇文章</span>
                </div>
                <button
                  onClick={handleRefresh}
                  className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-sm font-medium text-gray-600 hover:text-blue-600 hover:shadow transition"
                  disabled={refreshing}
                >
                  <ArrowPathIcon className={`h-4 w-4 ${refreshing ? 'animate-spin text-blue-500' : ''}`} />
                  {refreshing ? '刷新中...' : '刷新数据'}
                </button>
              </div>
            )}
          </div>

          {/* Search Bar */}
          <div className="mt-4 w-full max-w-2xl">
            <div className="relative rounded-xl border border-gray-200 bg-white shadow-sm">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="搜索文章内容、标题或AI分析..."
                className="w-full bg-transparent pl-11 pr-4 py-3 text-sm sm:text-base focus:outline-none"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchQuery)}
              />
            </div>
            
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                onClick={() => handleSearch(searchQuery)}
                disabled={isSearching}
                className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex-shrink-0"
              >
                {isSearching ? '搜索中...' : '搜索'}
              </button>
              <button
                onClick={() => {
                  setSearchQuery('')
                  setCurrentView('all')
                  setSearchResults([])
                  setActiveSource('全部')
                }}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 flex-shrink-0"
              >
                显示全部
              </button>
              {!stats && (
                <button
                  onClick={handleRefresh}
                  className="px-3 py-1 text-sm bg-white text-gray-600 border border-gray-200 rounded hover:border-blue-200 hover:text-blue-600 flex-shrink-0"
                  disabled={refreshing}
                >
                  {refreshing ? '刷新中...' : '刷新数据'}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Stats */}
      {stats && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white/80 backdrop-blur rounded-xl shadow-sm border border-white p-4">
              <h3 className="text-sm font-medium text-gray-600 mb-3">数据源分布</h3>
              {sourceTree.length > 0 ? (
                <div className="space-y-2">
                  <button
                    onClick={() => toggleExpansion('微信公众号')}
                    className="hidden"
                    aria-hidden="true"
                  >
                    toggle
                  </button>
                  {renderSourceTreeList(sourceTree)}
                </div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(stats.sources).map(([source, count]) => (
                    <div key={source} className="flex justify-between text-sm">
                      <span className="truncate mr-2">{source}:</span>
                      <span className="font-medium flex-shrink-0">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="bg-white/80 backdrop-blur rounded-xl shadow-sm border border-white p-4">
              <h3 className="text-sm font-medium text-gray-600 mb-3">最近更新</h3>
              <div className="space-y-2 text-sm text-gray-700">
                <div className="flex justify-between">
                  <span className="truncate mr-2">最后处理时间:</span>
                  <span className="font-medium flex-shrink-0">
                    {formatDateTime(stats.last_processed) ?? '暂无数据'}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-2">刷新以获取最新处理批次。</p>
              </div>
            </div>
          </div>
        </div>
      )}

        {sourceOptions.length > 1 && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="bg-white/70 backdrop-blur rounded-2xl border border-white px-4 py-3 shadow-sm">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex flex-col gap-2">
                  <span className="text-sm text-gray-500">按来源筛选:</span>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => setActiveSource('全部')}
                      className={`px-3 py-1.5 text-sm rounded-full border transition flex items-center gap-1 ${
                        activeSource === '全部'
                          ? 'bg-blue-600 text-white border-blue-600 shadow'
                          : 'bg-white text-gray-600 border-gray-200 hover:border-blue-200 hover:text-blue-600'
                      }`}
                    >
                      <span>全部</span>
                      <span className={`text-xs ${activeSource === '全部' ? 'text-blue-100' : 'text-gray-400'}`}>
                        {stats?.total_articles ?? displayArticles.length}
                      </span>
                    </button>
                  </div>
                  {sourceTree.length > 0 ? (
                    <div className="space-y-2">
                      {renderSourceFilter(sourceTree)}
                    </div>
                  ) : (
                    <div className="flex flex-wrap items-center gap-2">
                      {sourceOptions.slice(1).map((option) => {
                        const isActive = option === activeSource
                        const count =
                          stats?.sources?.[option] ?? articles.filter((article) => getSourceLabel(article.source) === option).length
                        return (
                          <button
                            key={option}
                            onClick={() => setActiveSource(option)}
                            className={`px-3 py-1.5 text-sm rounded-full border transition flex items-center gap-1 ${
                              isActive
                                ? 'bg-blue-600 text-white border-blue-600 shadow'
                                : 'bg-white text-gray-600 border-gray-200 hover:border-blue-200 hover:text-blue-600'
                            }`}
                          >
                            <span>{option}</span>
                            <span className={`text-xs ${isActive ? 'text-blue-100' : 'text-gray-400'}`}>{count}</span>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-gray-500 mr-2">排序:</span>
                  <button
                    onClick={() => setSortOrder('default')}
                    className={`px-3 py-1.5 text-sm rounded-full border transition ${
                      sortOrder === 'default'
                        ? 'bg-blue-50 text-blue-700 border-blue-200 shadow'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-blue-200 hover:text-blue-600'
                    }`}
                  >
                    默认顺序
                  </button>
                  <button
                    onClick={() => setSortOrder('updated_desc')}
                    className={`px-3 py-1.5 text-sm rounded-full border transition ${
                      sortOrder === 'updated_desc'
                        ? 'bg-blue-600 text-white border-blue-600 shadow'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-blue-200 hover:text-blue-600'
                    }`}
                  >
                    更新时间（新→旧）
                  </button>
                  <button
                    onClick={() => setSortOrder('updated_asc')}
                    className={`px-3 py-1.5 text-sm rounded-full border transition ${
                      sortOrder === 'updated_asc'
                        ? 'bg-blue-600 text-white border-blue-600 shadow'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-blue-200 hover:text-blue-600'
                    }`}
                  >
                    更新时间（旧→新）
                  </button>
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-500">{sortOrderLabel}</p>
            </div>
          </div>
        )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        {currentView === 'search' && (
          <div className="mb-6">
            <p className="text-gray-600">
              找到 <span className="font-medium">{searchResults.length}</span> 篇相关文章
              {searchQuery && <span> 关于 “{searchQuery}”</span>}
            </p>
          </div>
        )}

        {displayArticles.length === 0 ? (
          <div className="text-center py-12">
            <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-500">
              {currentView === 'search' ? '没有找到相关文章' : '暂无文章数据'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {displayArticles.map((article, index) => (
              <ArticleCard key={index} article={article} />
            ))}
          </div>
        )}
      </main>

      {filteredArticles.length > 0 && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
          <div className="bg-white/80 backdrop-blur rounded-2xl border border-white shadow-sm">
            <button
              onClick={() => setShowFiltered((prev) => !prev)}
              className="w-full flex items-center justify-between px-4 sm:px-6 py-4 text-left"
            >
              <div>
                <h3 className="text-sm sm:text-base font-semibold text-gray-800">被过滤的文章</h3>
                <p className="text-xs sm:text-sm text-gray-500 mt-1">
                  共 {filteredArticles.length} 篇（未进入 AI 处理，仅保留原文信息）
                </p>
              </div>
              <span className="text-blue-600 text-sm font-medium">
                {showFiltered ? '收起' : '展开'}
              </span>
            </button>

            {showFiltered && (
              <div className="border-t border-gray-100 divide-y divide-gray-100">
                {filteredArticles.map((article, index) => (
                  <div key={`filtered-${index}`} className="px-4 sm:px-6 py-5">
                    <div className="flex flex-col gap-2">
                      <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm text-gray-500">
                        <span className="font-semibold text-gray-700">
                          {article.title || '未命名'}
                        </span>
                        <span>· 来源：{getSourceLabel(article.source)}</span>
                        {article.author && <span>· 作者：{article.author}</span>}
                        {(article.published_time || article.published_at) && (
                          <span>
                            · 时间：
                            {formatDateTime(article.published_time || article.published_at) ?? '未知'}
                          </span>
                        )}
                      </div>

                      {article._filtered_reason && (
                        <p className="text-xs sm:text-sm text-amber-600">
                          过滤原因：
                          {article._filtered_reason === 'duplicate'
                            ? `与已有内容相似${article._duplicate_of_title ? `（参考：${article._duplicate_of_title}）` : ''}`
                            : article._filtered_reason}
                        </p>
                      )}

                      {article._filtered_reason === 'duplicate' && article._duplicate_of_source && (
                        <p className="text-xs sm:text-sm text-gray-500">
                          对应来源：{article._duplicate_of_source}
                        </p>
                      )}

                      <div className="mt-2 text-xs sm:text-sm text-gray-600 whitespace-pre-wrap bg-gray-50/70 border border-gray-100 rounded-lg p-3">
                        {article.content || '（无内容）'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
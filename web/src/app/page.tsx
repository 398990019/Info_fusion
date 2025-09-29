'use client'

import { useState, useEffect } from 'react'
import { MagnifyingGlassIcon, ChartBarIcon, BookOpenIcon, CalendarIcon } from '@heroicons/react/24/outline'
import ArticleCard from '@/components/ArticleCard'

interface Article {
  title: string
  link?: string
  published_time: string
  content: string
  source?: string
  llm_result?: {
    deep_summary: string
    cross_disciplinary_insights: Array<{
      domain: string
      analysis: string
      connection: string
    }>
    open_question: string
  }
  processed_at: string
}

interface Stats {
  total_articles: number
  sources: Record<string, number>
  domains: Record<string, number>
  last_processed: string
}

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Article[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [currentView, setCurrentView] = useState<'all' | 'search'>('all')

  // 加载文章数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [articlesRes, statsRes] = await Promise.all([
          fetch('http://localhost:5000/api/articles'),
          fetch('http://localhost:5000/api/stats')
        ])
        
        const articlesData = await articlesRes.json()
        const statsData = await statsRes.json()
        
        if (articlesData.success) {
          setArticles(articlesData.data)
        }
        
        if (statsData.success) {
          setStats(statsData.data)
        }
      } catch (error) {
        console.error('加载数据失败:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // 搜索功能
  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      setCurrentView('all')
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

  const displayArticles = currentView === 'search' ? searchResults : articles

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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <BookOpenIcon className="h-8 w-8 text-blue-600" />
              <h1 className="text-3xl font-bold text-gray-900">信息融合知识库</h1>
            </div>
            
            {stats && (
              <div className="flex items-center space-x-6 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <ChartBarIcon className="h-4 w-4" />
                  <span>总文章: {stats.total_articles}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <CalendarIcon className="h-4 w-4" />
                  <span>最后更新: {stats.last_processed ? new Date(stats.last_processed).toLocaleDateString('zh-CN') : '未知'}</span>
                </div>
              </div>
            )}
          </div>

          {/* Search Bar */}
          <div className="mt-6 max-w-md">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="搜索文章内容、标题或AI分析..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchQuery)}
              />
            </div>
            
            <div className="mt-2 flex space-x-2">
              <button
                onClick={() => handleSearch(searchQuery)}
                disabled={isSearching}
                className="px-4 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {isSearching ? '搜索中...' : '搜索'}
              </button>
              <button
                onClick={() => {
                  setSearchQuery('')
                  setCurrentView('all')
                }}
                className="px-4 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                显示全部
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stats */}
      {stats && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-500">数据源分布</h3>
              <div className="mt-2">
                {Object.entries(stats.sources).map(([source, count]) => (
                  <div key={source} className="flex justify-between text-sm">
                    <span>{source}:</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-medium text-gray-500">热门学科领域</h3>
              <div className="mt-2">
                {Object.entries(stats.domains)
                  .sort(([,a], [,b]) => b - a)
                  .slice(0, 5)
                  .map(([domain, count]) => (
                    <div key={domain} className="flex justify-between text-sm">
                      <span>{domain}:</span>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        {currentView === 'search' && (
          <div className="mb-6">
            <p className="text-gray-600">
              找到 <span className="font-medium">{searchResults.length}</span> 篇相关文章
              {searchQuery && <span> 关于 "{searchQuery}"</span>}
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
    </div>
  )
}
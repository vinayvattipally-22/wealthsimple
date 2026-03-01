import { useState, useEffect, useCallback } from 'react'
import { Newspaper, TrendingUp, RefreshCw, Loader2, ExternalLink, Info, ChevronDown } from 'lucide-react'
import { getStockNews, refreshStockNews, getStockInsights, generateStockInsights } from '../services/api'
import ReviewPendingBanner from './ReviewPendingBanner'
import '../styles/dashboard.css'

const TIMEFRAME_LABELS = {
  short: 'Short Term (1-2 weeks)',
  mid: 'Mid Term (1-3 months)',
  long: 'Long Term (6-12 months)',
}

function SentimentBadge({ score, label }) {
  const color = score > 0.2 ? 'var(--ws-green)' :
                score < -0.2 ? '#ef4444' : 'var(--ws-amber)'
  return (
    <span className="sentiment-badge" style={{ color, borderColor: color }}>
      {label || 'neutral'} ({score != null ? score.toFixed(2) : '—'})
    </span>
  )
}

function DirectionBadge({ direction }) {
  const cls = direction === 'bullish' ? 'direction-bullish' :
              direction === 'bearish' ? 'direction-bearish' : 'direction-neutral'
  return <span className={`direction-badge ${cls}`}>{direction}</span>
}

function NewsArticle({ article }) {
  const date = article.published_at
    ? new Date(article.published_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : ''

  return (
    <div className="news-article-card">
      <div className="news-article-header">
        <span className="news-article-publisher">{article.publisher || 'Unknown'}</span>
        <span className="news-article-date">{date}</span>
      </div>
      <h4 className="news-article-title">
        {article.url ? (
          <a href={article.url} target="_blank" rel="noopener noreferrer">
            {article.title} <ExternalLink size={12} style={{ marginLeft: 4, opacity: 0.5 }} />
          </a>
        ) : article.title}
      </h4>
      {article.summary && (
        <p className="news-article-summary">{article.summary}</p>
      )}
      {article.is_analyzed && (
        <SentimentBadge score={article.sentiment_score} label={article.sentiment_label} />
      )}
    </div>
  )
}

function InsightCard({ insight }) {
  return (
    <div className="insight-timeframe-card">
      <div className="insight-timeframe-header">
        <span className="insight-timeframe-label">
          {TIMEFRAME_LABELS[insight.timeframe] || insight.timeframe}
        </span>
        <DirectionBadge direction={insight.direction} />
      </div>

      {insight.confidence != null && (
        <div className="insight-confidence-wrap">
          <div className="insight-confidence-bar">
            <div
              className="insight-confidence-fill"
              style={{
                width: `${(insight.confidence * 100)}%`,
                background: insight.direction === 'bullish' ? 'var(--ws-green)' :
                            insight.direction === 'bearish' ? '#ef4444' : 'var(--ws-amber)'
              }}
            />
          </div>
          <span className="insight-confidence-text">{(insight.confidence * 100).toFixed(0)}% confidence</span>
        </div>
      )}

      {insight.reasoning && (
        <p className="insight-reasoning">{insight.reasoning}</p>
      )}

      {insight.referenced_articles && insight.referenced_articles.length > 0 && (
        <div className="insight-sources">
          <span className="insight-sources-label">Based on:</span>
          {insight.referenced_articles.map((a) => (
            <a key={a.id} href={a.url} target="_blank" rel="noopener noreferrer" className="insight-source-link">
              {a.title?.length > 60 ? a.title.slice(0, 60) + '...' : a.title}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

export default function StockNewsInsights({ ticker, companyName }) {
  const [activeTab, setActiveTab] = useState('news')
  const [news, setNews] = useState([])
  const [newsTotal, setNewsTotal] = useState(0)
  const [newsOffset, setNewsOffset] = useState(0)
  const [insights, setInsights] = useState([])
  const [reviewPending, setReviewPending] = useState(false)
  const [disclaimer, setDisclaimer] = useState('')
  const [generatedAt, setGeneratedAt] = useState(null)
  const [loadingNews, setLoadingNews] = useState(false)
  const [loadingInsights, setLoadingInsights] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [generating, setGenerating] = useState(false)

  const NEWS_LIMIT = 15

  const fetchNews = useCallback(async (offset = 0, append = false) => {
    if (!ticker) return
    setLoadingNews(true)
    try {
      const data = await getStockNews(ticker, NEWS_LIMIT, offset)
      setNews(prev => append ? [...prev, ...data.news] : data.news)
      setNewsTotal(data.total)
      setNewsOffset(offset)
    } catch (e) {
      console.error('Failed to fetch news:', e)
    } finally {
      setLoadingNews(false)
    }
  }, [ticker])

  const fetchInsights = useCallback(async () => {
    if (!ticker) return
    setLoadingInsights(true)
    try {
      const data = await getStockInsights(ticker)
      setInsights(data.insights || [])
      setReviewPending(data.review_pending === true)
      setDisclaimer(data.disclaimer || '')
      setGeneratedAt(data.generated_at)
    } catch (e) {
      console.error('Failed to fetch insights:', e)
    } finally {
      setLoadingInsights(false)
    }
  }, [ticker])

  useEffect(() => {
    fetchNews(0)
    fetchInsights()
  }, [ticker, fetchNews, fetchInsights])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await refreshStockNews(ticker)
      await fetchNews(0)
    } catch (e) {
      console.error('Failed to refresh news:', e)
    } finally {
      setRefreshing(false)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      await generateStockInsights(ticker)
      await fetchInsights()
    } catch (e) {
      console.error('Failed to generate insights:', e)
    } finally {
      setGenerating(false)
    }
  }

  const handleLoadMore = () => {
    fetchNews(newsOffset + NEWS_LIMIT, true)
  }

  const hasMore = news.length < newsTotal

  return (
    <div className="stock-news-insights">
      <div className="stock-news-tabs">
        <button
          className={`stock-news-tab ${activeTab === 'news' ? 'stock-news-tab-active' : ''}`}
          onClick={() => setActiveTab('news')}
        >
          <Newspaper size={14} /> News Feed
        </button>
        <button
          className={`stock-news-tab ${activeTab === 'insights' ? 'stock-news-tab-active' : ''}`}
          onClick={() => setActiveTab('insights')}
        >
          <TrendingUp size={14} /> Price Insights
        </button>
      </div>

      {activeTab === 'news' && (
        <div className="stock-news-feed">
          <div className="stock-news-feed-header">
            <span className="stock-news-feed-count">{newsTotal} article{newsTotal !== 1 ? 's' : ''}</span>
            <button
              className="btn-sm btn-outline"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              {refreshing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              {refreshing ? 'Refreshing...' : 'Refresh News'}
            </button>
          </div>

          {loadingNews && news.length === 0 ? (
            <div className="stock-news-loading">
              <Loader2 size={20} className="animate-spin" /> Loading news...
            </div>
          ) : news.length === 0 ? (
            <div className="stock-news-empty">No news articles found for {ticker}.</div>
          ) : (
            <>
              {news.map((article) => (
                <NewsArticle key={article.id} article={article} />
              ))}
              {hasMore && (
                <button
                  className="btn-sm btn-outline stock-news-load-more"
                  onClick={handleLoadMore}
                  disabled={loadingNews}
                >
                  {loadingNews ? <Loader2 size={14} className="animate-spin" /> : <ChevronDown size={14} />}
                  Load More
                </button>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === 'insights' && (
        <div className="stock-insights-panel">
          <div className="stock-insights-header">
            {generatedAt && (
              <span className="stock-insights-generated">
                Generated: {new Date(generatedAt).toLocaleString()}
              </span>
            )}
            <button
              className="btn-sm btn-outline"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? <Loader2 size={14} className="animate-spin" /> : <TrendingUp size={14} />}
              {generating ? 'Generating...' : 'Generate Insights'}
            </button>
          </div>

          {reviewPending && (
            <ReviewPendingBanner message="Stock insights are under advisor review. Only approved insights are shown below." />
          )}

          {loadingInsights ? (
            <div className="stock-news-loading">
              <Loader2 size={20} className="animate-spin" /> Loading insights...
            </div>
          ) : insights.length === 0 && reviewPending ? (
            <div className="stock-news-empty">
              Insights have been generated and are awaiting advisor review.
            </div>
          ) : insights.length === 0 ? (
            <div className="stock-news-empty">
              No insights generated yet. Click "Generate Insights" to analyze stored news.
            </div>
          ) : (
            <>
              {insights.map((insight) => (
                <InsightCard key={insight.id} insight={insight} />
              ))}
            </>
          )}

          {disclaimer && (
            <div className="stock-insights-disclaimer">
              <Info size={14} />
              <span>{disclaimer}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

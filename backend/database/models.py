"""
SQLAlchemy ORM models for TaxFolio AI Tax Analyzer.
SQLite local file DB — auto-create tables on app startup.
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    LargeBinary,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(255), unique=True, nullable=True)  # External platform user id
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    role = Column(String(16), default="USER")  # USER or ADVISOR
    province = Column(String(2), nullable=True)  # Default province for user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    profile_id = Column(Integer, ForeignKey("financial_profiles.id"), nullable=True)
    doc_type = Column(String(32), nullable=False)  # T4, RRSP, etc.
    file_name = Column(String(255), nullable=True)
    extracted_data = Column(JSON, nullable=True)  # Redacted structured data only
    redacted_file_path = Column(String(512), nullable=True)  # Legacy: path to redacted PDF
    redacted_file_data = Column(LargeBinary, nullable=True)  # Redacted PDF binary stored in DB
    created_at = Column(DateTime, default=datetime.utcnow)


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tax_year = Column(Integer, nullable=False)
    province_code = Column(String(2), nullable=False)
    profile_data = Column(JSON, nullable=True)  # Unified profile per Section 12
    review_status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    advisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    insights = relationship("Insight", back_populates="profile")
    review_cases = relationship("ReviewCase", back_populates="profile")


class Insight(Base):
    __tablename__ = "insights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("financial_profiles.id"), nullable=False)
    insight_type = Column(String(64), nullable=False)
    priority = Column(String(16), nullable=True)  # HIGH, MEDIUM, LOW
    category = Column(String(32), nullable=True)  # ACT_NOW, THIS_YEAR, LONG_TERM
    headline = Column(String(512), nullable=True)
    detail = Column(Text, nullable=True)
    estimated_value = Column(Float, nullable=True)
    calculation_shown = Column(Text, nullable=True)
    action_required = Column(Text, nullable=True)
    product_link = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=True)
    requires_additional_info = Column(JSON, nullable=True)  # list of strings
    review_status = Column(String(32), default="PENDING")
    advisor_comment = Column(Text, nullable=True)  # Advisor feedback on this insight
    advisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    profile = relationship("FinancialProfile", back_populates="insights")


class ReviewCase(Base):
    __tablename__ = "review_cases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("financial_profiles.id"), nullable=False)
    status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED, ESCALATED
    flags = Column(JSON, nullable=True)  # TAX_RATE_ANOMALY, etc.
    confidence_score = Column(Float, nullable=True)
    sla_due_at = Column(DateTime, nullable=True)
    advisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile = relationship("FinancialProfile", back_populates="review_cases")


class ActionItem(Base):
    __tablename__ = "action_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("financial_profiles.id"), nullable=False)
    insight_id = Column(Integer, ForeignKey("insights.id"), nullable=True)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String(16), nullable=True)  # HIGH, MEDIUM, LOW
    status = Column(String(32), default="pending")  # pending, in_progress, completed, skipped
    estimated_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StockResearch(Base):
    __tablename__ = "stock_research"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String(16), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    signal = Column(String(8), nullable=True)  # BUY, HOLD, SELL
    confidence = Column(Float, nullable=True)
    price_at_research = Column(Float, nullable=True)
    market_data = Column(JSON, nullable=True)
    technical_indicators = Column(JSON, nullable=True)
    news_sentiment = Column(JSON, nullable=True)
    geo_policy = Column(JSON, nullable=True)
    volatility_risk = Column(JSON, nullable=True)
    aggregated_signal = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockNews(Base):
    __tablename__ = "stock_news"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(16), nullable=False, index=True)
    title = Column(String(1024), nullable=False)
    url = Column(String(2048), nullable=True)
    publisher = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(32), nullable=False)  # yfinance or alpha_vantage
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    sentiment_label = Column(String(32), nullable=True)  # bullish/neutral/bearish
    summary = Column(String(1024), nullable=True)  # 1-sentence LLM summary
    is_analyzed = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("ticker", "title", "published_at", name="uq_stock_news_dedup"),
    )


class StockInsight(Base):
    __tablename__ = "stock_insights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(16), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    timeframe = Column(String(16), nullable=False)  # short, mid, long
    direction = Column(String(16), nullable=False)  # bullish, neutral, bearish
    confidence = Column(Float, nullable=True)  # 0.0 to 0.85
    reasoning = Column(Text, nullable=True)
    news_article_ids = Column(JSON, nullable=True)  # [1, 5, 12] StockNews IDs
    review_status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    advisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    advisor_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TrackedStock(Base):
    __tablename__ = "tracked_stocks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(16), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    last_news_fetch = Column(DateTime, nullable=True)
    news_fetch_interval_hours = Column(Integer, default=4)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(64), nullable=True)
    purpose = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)

import { createContext, useContext, useState, useCallback } from 'react'

const PageDataContext = createContext(null)

export function PageDataProvider({ children }) {
  const [pageData, setPageDataState] = useState(null)

  const setPageData = useCallback((data) => {
    setPageDataState(data)
  }, [])

  const clearPageData = useCallback(() => {
    setPageDataState(null)
  }, [])

  return (
    <PageDataContext.Provider value={{ pageData, setPageData, clearPageData }}>
      {children}
    </PageDataContext.Provider>
  )
}

export function usePageData() {
  const ctx = useContext(PageDataContext)
  if (!ctx) throw new Error('usePageData must be used within PageDataProvider')
  return ctx
}

const ACTIVE_BRAND_ID_KEY = 'brandgen.active_brand_id'

/**
 * Persist the currently active brand id so users can continue post-onboarding flows.
 */
export const setActiveBrandId = (brandId) => {
  if (typeof window === 'undefined') return

  const normalized = String(brandId || '').trim()
  if (!normalized) return

  window.localStorage.setItem(ACTIVE_BRAND_ID_KEY, normalized)
}

/**
 * Get the most recently used brand id from persistent storage.
 */
export const getActiveBrandId = () => {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(ACTIVE_BRAND_ID_KEY) || ''
}

/**
 * Remove the active brand id from storage.
 */
export const clearActiveBrandId = () => {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(ACTIVE_BRAND_ID_KEY)
}

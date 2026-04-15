import { Navigate } from 'react-router-dom'
import { getActiveBrandId } from '../services/brandSession'

export default function BrandRouteRedirect({ targetPath }) {
  const activeBrandId = getActiveBrandId()

  if (activeBrandId) {
    return <Navigate to={`/${targetPath}/${activeBrandId}`} replace />
  }

  return <Navigate to="/onboarding" state={{ redirectAfterOnboarding: targetPath }} replace />
}

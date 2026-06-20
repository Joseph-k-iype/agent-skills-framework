import { Link } from 'react-router-dom'
import { Compass, ArrowLeft } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="card mx-auto mt-16 max-w-md text-center">
      <Compass size={48} className="mx-auto text-gray-700" />
      <h2 className="mt-4 text-2xl font-bold text-gray-100">Page not found</h2>
      <p className="mt-1 text-sm text-gray-500">
        The page you&apos;re looking for doesn&apos;t exist or has moved.
      </p>
      <Link to="/" className="btn-primary mt-6 inline-flex">
        <ArrowLeft size={16} /> Back to Dashboard
      </Link>
    </div>
  )
}

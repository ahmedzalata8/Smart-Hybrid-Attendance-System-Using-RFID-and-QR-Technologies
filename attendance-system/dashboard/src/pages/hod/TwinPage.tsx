import { useParams, useNavigate } from 'react-router-dom';
import SeatMapView from '../lecturer/views/SeatMapView';

/* Standalone seat-map page (used by the HoD route and the direct twin link). */
export default function TwinPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  if (!id) return <div className="page"><p className="text-muted">Session not found</p></div>;

  return (
    <div className="page">
      <SeatMapView
        sessionId={id}
        showHeader
        actions={<button className="btn btn-secondary" onClick={() => navigate(-1)}>Back</button>}
      />
    </div>
  );
}

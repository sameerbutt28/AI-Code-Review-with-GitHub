import type { ReviewRequest, ReviewStatusResponse } from './types';

const API_BASE = '/api';

export async function startReview(request: ReviewRequest): Promise<ReviewStatusResponse> {
  const res = await fetch(`${API_BASE}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Failed to start review');
  }
  return res.json();
}

export async function getReviewStatus(reviewId: string): Promise<ReviewStatusResponse> {
  const res = await fetch(`${API_BASE}/review/${reviewId}`);
  if (!res.ok) throw new Error('Failed to fetch review status');
  return res.json();
}

export function getReportUrl(reviewId: string, format: 'pdf' | 'md' = 'pdf'): string {
  return `${API_BASE}/review/${reviewId}/report?format=${format}`;
}

export async function pollReview(
  reviewId: string,
  onProgress?: (status: ReviewStatusResponse) => void,
  intervalMs = 2000,
): Promise<ReviewStatusResponse> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getReviewStatus(reviewId);
        onProgress?.(status);
        if (status.status === 'completed') {
          resolve(status);
        } else if (status.status === 'failed') {
          reject(new Error(status.message));
        } else {
          setTimeout(poll, intervalMs);
        }
      } catch (err) {
        reject(err);
      }
    };
    poll();
  });
}

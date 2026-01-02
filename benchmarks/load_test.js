import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const predictLatency = new Trend('predict_latency');

// Configuration
export const options = {
  stages: [
    { duration: '1m', target: 100 },   // Ramp up to 100 RPS
    { duration: '5m', target: 1000 },  // Maintain 1000 RPS
    { duration: '1m', target: 0 },      // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<150'], // P95 latency < 150ms
    'errors': ['rate<0.01'],             // Error rate < 1%
  },
};

// Generate synthetic user IDs
function randomUserId() {
  return `user_${Math.floor(Math.random() * 10000)}`;
}

// Main test function
export default function () {
  const EC2_IP = __ENV.EC2_IP || 'localhost';
  const baseUrl = `http://${EC2_IP}:8001`;
  
  const userId = randomUserId();
  
  // Test prediction endpoint
  const predictPayload = JSON.stringify({
    user_id: userId,
  });
  
  const predictParams = {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'predict' },
  };
  
  const predictResponse = http.post(`${baseUrl}/predict`, predictPayload, predictParams);
  
  // Check response
  const predictSuccess = check(predictResponse, {
    'predict status is 200': (r) => r.status === 200,
    'predict has decision': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.decision !== undefined;
      } catch {
        return false;
      }
    },
  });
  
  // Track metrics
  errorRate.add(!predictSuccess);
  predictLatency.add(predictResponse.timings.duration);
  
  sleep(1); // 1 second between requests per VU
}


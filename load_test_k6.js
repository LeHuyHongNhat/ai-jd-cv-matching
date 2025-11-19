/*
 * Load Testing Script cho CV-JD Matching API sử dụng k6
 *
 * Cài đặt k6:
 *   Mac: brew install k6
 *   Linux: https://k6.io/docs/getting-started/installation/
 *   Windows: choco install k6 hoặc download từ GitHub
 *
 * Chạy test:
 *   k6 run load_test_k6.js
 *
 * Options:
 *   k6 run --vus 100 --duration 30s load_test_k6.js
 *   k6 run --out json=results.json load_test_k6.js
 *   k6 run --out influxdb=http://localhost:8086/k6 load_test_k6.js
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// Custom metrics
let errorRate = new Rate("errors");
let rootResponseTime = new Trend("root_response_time");
let jdProcessTime = new Trend("jd_process_time");
let matchTime = new Trend("match_response_time");
let totalRequests = new Counter("total_requests");

// Configuration
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

// Test stages - ramp up và ramp down
export let options = {
  stages: [
    // Warmup
    { duration: "30s", target: 10 }, // Ramp up to 10 users in 30s

    // Light load
    { duration: "1m", target: 50 }, // Ramp up to 50 users
    { duration: "2m", target: 50 }, // Stay at 50 users for 2 minutes

    // Medium load
    { duration: "1m", target: 100 }, // Ramp up to 100 users
    { duration: "3m", target: 100 }, // Stay at 100 users for 3 minutes

    // Heavy load (stress test)
    { duration: "1m", target: 200 }, // Ramp up to 200 users
    { duration: "2m", target: 200 }, // Stay at 200 users for 2 minutes

    // Ramp down
    { duration: "30s", target: 0 }, // Ramp down to 0 users
  ],

  // Thresholds - định nghĩa success criteria
  thresholds: {
    // 95% of requests must complete below 2000ms
    http_req_duration: ["p(95)<2000"],

    // 99% of requests must complete below 5000ms
    "http_req_duration{name:root}": ["p(99)<1000"],
    "http_req_duration{name:process_jd}": ["p(99)<5000"],
    "http_req_duration{name:match}": ["p(99)<3000"],

    // Error rate must be below 1%
    http_req_failed: ["rate<0.01"],
    errors: ["rate<0.01"],

    // Throughput: at least 50 requests per second
    http_reqs: ["rate>50"],
  },

  // Other options
  noConnectionReuse: false,
  userAgent: "K6LoadTest/1.0",

  // Graceful stop
  gracefulStop: "30s",
};

// Sample JD text for testing
const SAMPLE_JD = {
  text: `Job Title: Senior Python Developer

Requirements:
- 5+ years of experience in Python development
- Strong knowledge of FastAPI, Django, or Flask
- Experience with RESTful API design and development
- Knowledge of SQL and NoSQL databases
- Experience with Docker and Kubernetes
- Understanding of CI/CD pipelines

Skills Required:
- Python, FastAPI, Django, Flask
- PostgreSQL, MongoDB, Redis
- Docker, Kubernetes
- REST API, GraphQL
- Git, CI/CD

Education:
- Bachelor's degree in Computer Science or related field
- Relevant certifications are a plus

Responsibilities:
- Design and develop scalable backend services
- Write clean, maintainable code
- Collaborate with frontend developers
- Participate in code reviews
- Mentor junior developers`,
};

// Store created IDs for matching
let cvIds = [];
let jdIds = [];

// Setup function - runs once per VU at the start
export function setup() {
  console.log("=".repeat(60));
  console.log("Starting Load Test");
  console.log(`Base URL: ${BASE_URL}`);
  console.log("=".repeat(60));

  // Check if server is running
  let res = http.get(`${BASE_URL}/`);
  if (res.status !== 200) {
    console.error("❌ Server is not responding properly!");
    console.error(`Status: ${res.status}`);
    return { serverReady: false };
  }

  console.log("✅ Server is ready");
  return { serverReady: true };
}

// Main test function - runs repeatedly for each VU
export default function (data) {
  if (!data.serverReady) {
    console.error("Server not ready, skipping test");
    return;
  }

  // Test root endpoint
  group("Test Root Endpoint", function () {
    let res = http.get(`${BASE_URL}/`, {
      tags: { name: "root" },
    });

    let success = check(res, {
      "root: status is 200": (r) => r.status === 200,
      "root: has message": (r) => r.json("message") !== undefined,
      "root: response time < 500ms": (r) => r.timings.duration < 500,
    });

    errorRate.add(!success);
    rootResponseTime.add(res.timings.duration);
    totalRequests.add(1);
  });

  sleep(1);

  // Test process JD endpoint
  group("Test Process JD", function () {
    let payload = JSON.stringify(SAMPLE_JD);
    let params = {
      headers: { "Content-Type": "application/json" },
      tags: { name: "process_jd" },
    };

    let res = http.post(`${BASE_URL}/process/jd`, payload, params);

    let success = check(res, {
      "process_jd: status is 200": (r) => r.status === 200,
      "process_jd: has doc_id": (r) => {
        try {
          let json = r.json();
          return json.doc_id !== undefined && json.doc_id !== null;
        } catch (e) {
          return false;
        }
      },
      "process_jd: has structured_data": (r) => {
        try {
          let json = r.json();
          return json.structured_data !== undefined;
        } catch (e) {
          return false;
        }
      },
      "process_jd: response time < 10s": (r) => r.timings.duration < 10000,
    });

    // Store JD ID for matching
    if (res.status === 200) {
      try {
        let json = res.json();
        if (json.doc_id) {
          jdIds.push(json.doc_id);
          // Keep only last 100 IDs to avoid memory issues
          if (jdIds.length > 100) {
            jdIds.shift();
          }
        }
      } catch (e) {
        console.error("Failed to parse JD response:", e);
      }
    }

    errorRate.add(!success);
    jdProcessTime.add(res.timings.duration);
    totalRequests.add(1);
  });

  sleep(1);

  // Test match endpoint (only if we have IDs)
  if (jdIds.length > 0) {
    group("Test Match CV-JD", function () {
      // Use a dummy CV ID or a real one if available
      let cvId =
        cvIds.length > 0
          ? cvIds[Math.floor(Math.random() * cvIds.length)]
          : "dummy-cv-id-for-404-test";
      let jdId = jdIds[Math.floor(Math.random() * jdIds.length)];

      let res = http.get(`${BASE_URL}/match/${cvId}/${jdId}`, {
        tags: { name: "match" },
      });

      // If we're using dummy CV ID, we expect 404
      let expectedStatus = cvIds.length > 0 ? 200 : 404;

      let success = check(res, {
        "match: status is expected": (r) =>
          r.status === expectedStatus || r.status === 404,
        "match: response time < 5s": (r) => r.timings.duration < 5000,
      });

      errorRate.add(!success);
      matchTime.add(res.timings.duration);
      totalRequests.add(1);
    });
  }

  sleep(2);
}

// Teardown function - runs once at the end
export function teardown(data) {
  console.log("=".repeat(60));
  console.log("Load Test Completed");
  console.log("=".repeat(60));
  console.log(`Total JD IDs created: ${jdIds.length}`);
  console.log(`Total CV IDs created: ${cvIds.length}`);
  console.log("=".repeat(60));
}

// Handle summary - custom output
export function handleSummary(data) {
  console.log("");
  console.log("=".repeat(60));
  console.log("SUMMARY");
  console.log("=".repeat(60));

  // Calculate totals
  let totalReqs = data.metrics.http_reqs.values.count;
  let totalFailed = data.metrics.http_req_failed.values.passes || 0;
  let avgDuration = data.metrics.http_req_duration.values.avg;
  let p95Duration = data.metrics.http_req_duration.values["p(95)"];
  let p99Duration = data.metrics.http_req_duration.values["p(99)"];
  let rps = data.metrics.http_reqs.values.rate;

  console.log(`Total Requests:       ${totalReqs}`);
  console.log(
    `Failed Requests:      ${totalFailed} (${(
      (totalFailed / totalReqs) *
      100
    ).toFixed(2)}%)`
  );
  console.log(`Requests per Second:  ${rps.toFixed(2)}`);
  console.log(`Avg Response Time:    ${avgDuration.toFixed(2)}ms`);
  console.log(`p95 Response Time:    ${p95Duration.toFixed(2)}ms`);
  console.log(`p99 Response Time:    ${p99Duration.toFixed(2)}ms`);
  console.log("=".repeat(60));

  // Check thresholds
  let thresholdsPassed = true;
  for (let threshold in data.thresholds) {
    if (!data.thresholds[threshold].ok) {
      thresholdsPassed = false;
      console.log(`❌ Threshold FAILED: ${threshold}`);
    }
  }

  if (thresholdsPassed) {
    console.log("✅ All thresholds passed!");
  } else {
    console.log("⚠️  Some thresholds failed!");
  }
  console.log("=".repeat(60));

  // Return the default summary
  return {
    stdout: data,
    "summary.json": JSON.stringify(data, null, 2),
  };
}

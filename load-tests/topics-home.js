import http from "k6/http";
import { check, sleep } from "k6";

const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "30s", target: 1 },
    { duration: "30s", target: 10 },
    { duration: "30s", target: 25 },
    { duration: "30s", target: 50 },
    { duration: "30s", target: 100 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const response = http.get(`${baseUrl}/topics/home`);

  check(response, {
    "status is 200": (res) => res.status === 200,
    "has home payload": (res) => {
      try {
        const body = res.json();
        return (
          Object.prototype.hasOwnProperty.call(body, "generated_at") &&
          Object.prototype.hasOwnProperty.call(body, "topic_date") &&
          Array.isArray(body.items)
        );
      } catch {
        return false;
      }
    },
  });

  sleep(1);
}

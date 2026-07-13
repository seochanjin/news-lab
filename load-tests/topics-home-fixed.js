import http from "k6/http";
import { check, sleep } from "k6";

const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000";
const vus = parseInt(__ENV.VUS || "1", 10);
const duration = __ENV.DURATION || "30s";

export const options = {
  vus: vus,
  duration: duration,
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const response = http.get(baseUrl + "/topics/home");

  check(response, {
    "status is 200": function (res) {
      return res.status === 200;
    },
    "has home payload": function (res) {
      try {
        const body = res.json();
        return (
          Object.prototype.hasOwnProperty.call(body, "generated_at") &&
          Object.prototype.hasOwnProperty.call(body, "topic_date") &&
          Array.isArray(body.items)
        );
      } catch (error) {
        return false;
      }
    },
  });

  sleep(1);
}

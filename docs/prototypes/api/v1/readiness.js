import { handleRoute } from "./[...path].js";

export default function handler(req, res) {
  return handleRoute(req, res, "readiness");
}

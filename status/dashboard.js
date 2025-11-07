<script src="/status/dashboard.js"></script>

const r = await fetch("/status/status.json", { cache: "no-store" });
const status = r.ok ? await r.json() : { agents: [] };

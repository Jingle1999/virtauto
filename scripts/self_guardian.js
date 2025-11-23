// scripts/self_guardian.js

/**
 * Self_Guardian v2 – Security & Override Monitor
 *
 * Aufgaben:
 *  - Liest strukturierte Security-Logs (JSON oder JSONL)
 *  - Erzwingt ein Mindest-Logformat
 *  - Erkennt manual_override-Ereignisse
 *  - Prüft Signatur, Actor und Scope
 *  - Gibt eine Zusammenfassung + Exit-Code zurück
 *
 * Nutzung:
 *  node scripts/self_guardian.js [pfad-zur-logdatei]
 *
 * Default-Logdatei: logs/security_events.jsonl
 */

const fs = require("fs");
const path = require("path");

// -----------------------------
// Konfiguration
// -----------------------------

// Erlaubte Actor für Overrides
const ALLOWED_OVERRIDE_ACTORS = ["GEORGE", "admin_panel"];

// Erlaubte Scopes für Overrides
const ALLOWED_OVERRIDE_SCOPES = [
  "deploy_pipeline",
  "content_pipeline",
  "activity_feed",
];

// Pflichtfelder im Log
const REQUIRED_FIELDS = [
  "timestamp",
  "actor",
  "action",
  "scope",
  "level",
  "signature",
];

// -----------------------------
// Hilfsfunktionen
// -----------------------------

/**
 * Sehr einfache Signaturprüfung als Platzhalter.
 * Später kannst Du hier HMAC/Ed25519 etc. integrieren.
 */
function verifySignature(signature) {
  if (typeof signature !== "string") return false;

  // Platzhalter-Regel:
  //  - muss mit "sha256:" beginnen
  //  - muss mehr als 10 Zeichen lang sein
  if (!signature.startsWith("sha256:")) return false;
  if (signature.length < "sha256:".length + 10) return false;

  return true;
}

/**
 * Prüft, ob alle Pflichtfelder vorhanden sind.
 */
function validateRequiredFields(entry) {
  const missing = REQUIRED_FIELDS.filter((f) => !(f in entry));
  return missing;
}

/**
 * Analysiert EIN Log-Event und liefert Sicherheits-Flags zurück.
 */
function analyzeLogEntry(entry) {
  const flags = [];

  // 1. Pflichtfelder prüfen
  const missing = validateRequiredFields(entry);
  if (missing.length > 0) {
    flags.push({
      type: "invalid_log_format",
      severity: "medium",
      detail: `missing fields: ${missing.join(", ")}`,
    });
    // Ohne Pflichtfelder lohnt sich der Rest kaum
    return flags;
  }

  const action = entry.action;
  const actor = entry.actor;
  const scope = entry.scope;
  const signature = entry.signature;

  // 2. Signatur prüfen (für alle sicherheitsrelevanten Actions)
  const securityRelevantActions = [
    "manual_override",
    "config_change",
    "policy_update",
  ];

  if (securityRelevantActions.includes(action)) {
    if (!verifySignature(signature)) {
      flags.push({
        type: "security_alert_invalid_signature",
        severity: "critical",
        detail: `invalid signature for action=${action}`,
      });
    }
  }

  // 3. Spezielle Behandlung: manual_override
  if (action === "manual_override") {
    // 3a) Actor prüfen
    if (!ALLOWED_OVERRIDE_ACTORS.includes(actor)) {
      flags.push({
        type: "security_alert_unauthorized_override",
        severity: "critical",
        detail: `actor=${actor} not allowed to perform manual_override`,
      });
    }

    // 3b) Scope prüfen
    if (!ALLOWED_OVERRIDE_SCOPES.includes(scope)) {
      flags.push({
        type: "security_alert_illegal_scope",
        severity: "high",
        detail: `scope=${scope} is not allowed for manual_override`,
      });
    }

    // 3c) If keine kritischen Flags → autorisierter Override
    const hasCritical = flags.some((f) => f.severity === "critical");
    if (!hasCritical) {
      flags.push({
        type: "authorized_override",
        severity: "info",
        detail: `authorized manual_override by ${actor} on ${scope}`,
      });
    }
  }

  return flags;
}

/**
 * Liest Logdatei (JSON oder JSONL).
 */
function readLogFile(logPath) {
  if (!fs.existsSync(logPath)) {
    throw new Error(`Log file not found: ${logPath}`);
  }

  const raw = fs.readFileSync(logPath, "utf8").trim();
  if (!raw) return [];

  // Versuch 1: JSON-Array
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
  } catch (e) {
    // ignore, wir versuchen JSONL
  }

  // Versuch 2: JSONL (eine Zeile = ein JSON-Objekt)
  const lines = raw.split("\n").map((l) => l.trim()).filter(Boolean);
  const entries = [];
  for (const line of lines) {
    try {
      entries.push(JSON.parse(line));
    } catch (e) {
      console.warn("[Self_Guardian] Could not parse line as JSON:", line);
    }
  }
  return entries;
}

/**
 * Hauptfunktion: liest Logs, analysiert sie, gibt Zusammenfassung aus.
 */
function runSelfGuardian(logPath) {
  console.log("🛡  Self_Guardian v2 starting…");
  console.log(`   Log source: ${logPath}\n`);

  const entries = readLogFile(logPath);
  console.log(`   Found ${entries.length} log entries.\n`);

  const allFlags = [];
  let criticalCount = 0;
  let highCount = 0;
  let infoOverrides = 0;

  entries.forEach((entry, idx) => {
    const flags = analyzeLogEntry(entry);

    if (flags.length === 0) return;

    console.log(`📄 Entry #${idx + 1} (${entry.action} by ${entry.actor})`);
    flags.forEach((flag) => {
      allFlags.push(flag);

      if (flag.type === "authorized_override") {
        infoOverrides += 1;
      }

      if (flag.severity === "critical") criticalCount += 1;
      if (flag.severity === "high") highCount += 1;

      console.log(
        `   [${flag.severity.toUpperCase()}] ${flag.type} – ${flag.detail}`
      );
    });
    console.log("");
  });

  console.log("📊 Summary:");
  console.log(`   Critical alerts : ${criticalCount}`);
  console.log(`   High alerts     : ${highCount}`);
  console.log(`   Authorized overrides : ${infoOverrides}`);
  console.log("");

  if (criticalCount > 0) {
    console.log("❌ Self_Guardian status: FAIL (critical security issues found)");
    process.exitCode = 1;
  } else if (highCount > 0) {
    console.log("⚠️  Self_Guardian status: ISSUE (high severity alerts present)");
    process.exitCode = 1;
  } else {
    console.log("✅ Self_Guardian status: OK (no security-relevant issues)");
    process.exitCode = 0;
  }
}

// -----------------------------
// CLI-Einstiegspunkt
// -----------------------------

if (require.main === module) {
  const defaultLogPath = path.join("logs", "security_events.jsonl");
  const logPath = process.argv[2] || defaultLogPath;

  try {
    runSelfGuardian(logPath);
  } catch (err) {
    console.error("💥 Self_Guardian runtime error:", err.message);
    process.exitCode = 1;
  }
}

module.exports = {
  analyzeLogEntry,
  runSelfGuardian,
};
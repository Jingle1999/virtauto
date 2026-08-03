import { loadDecisionObject } from "./loader.js";    

    const DECISION_OBJECT_URL =
    "./data/decision-object-energy-001.json";

    const getFirst = (...values) =>
      values.find(
        (value) =>
          value !== undefined &&
          value !== null &&
          value !== ""
      );

    const formatValue = (value) => {
      if (value === undefined || value === null || value === "") {
        return "—";
      }

      if (typeof value === "boolean") {
        return value ? "Yes" : "No";
      }

      if (Array.isArray(value)) {
        return value.length ? value.join(", ") : "—";
      }

      if (typeof value === "object") {
        return JSON.stringify(value);
      }

      return String(value);
    };

    const setText = (id, value) => {
      const element = document.getElementById(id);

      if (element) {
        element.textContent = formatValue(value);
      }
    };

    const renderList = (containerId, entries) => {
      const container = document.getElementById(containerId);
      container.innerHTML = "";

      const usableEntries = entries.filter(
        ([, value]) =>
          value !== undefined &&
          value !== null &&
          value !== ""
      );

      if (!usableEntries.length) {
        container.innerHTML =
          '<div class="empty-state">No information available.</div>';
        return;
      }

      usableEntries.forEach(([label, value]) => {
        const row = document.createElement("div");
        row.className = "list-item";

        const labelElement = document.createElement("div");
        labelElement.className = "list-label";
        labelElement.textContent = label;

        const valueElement = document.createElement("div");
        valueElement.className = "list-value";
        valueElement.textContent = formatValue(value);

        row.append(labelElement, valueElement);
        container.appendChild(row);
      });
    };

    const renderOptions = (decisionObject) => {
      const container =
        document.getElementById("optionsContainer");

      const recommendation =
        decisionObject.recommendation || {};

      const options =
        getFirst(
          decisionObject.options,
          decisionObject.alternatives,
          decisionObject.decision?.options,
          []
        ) || [];

      container.innerHTML = "";

      if (!Array.isArray(options) || options.length === 0) {
        const fallback = document.createElement("div");
        fallback.className = "empty-state";
        fallback.textContent =
          "This Decision Object currently contains no separate option list.";
        container.appendChild(fallback);
        return;
      }

      options.forEach((option, index) => {
        const optionId = getFirst(
          option.option_id,
          option.id,
          option.type,
          `OPTION_${index + 1}`
        );

        const recommendedId = getFirst(
          recommendation.option_id,
          recommendation.recommended_option_id,
          decisionObject.recommended_option_id
        );

        const card = document.createElement("div");
        card.className =
          "option-card" +
          (optionId === recommendedId ? " recommended" : "");

        const title = document.createElement("div");
        title.className = "option-title";
        title.textContent = getFirst(
          option.title,
          option.name,
          option.explanation,
          optionId
        );

        const description = document.createElement("div");
        description.className = "recommendation-description";
        description.textContent = getFirst(
          option.explanation,
          option.description,
          "No additional explanation available."
        );

        const meta = document.createElement("div");
        meta.className = "option-meta";

        [
          ["ID", optionId],
          ["Score", option.score],
          ["Status", option.status],
          ["Confidence", option.confidence]
        ].forEach(([label, value]) => {
          if (
            value === undefined ||
            value === null ||
            value === ""
          ) {
            return;
          }

          const badge = document.createElement("span");
          badge.className = "badge";
          badge.textContent = `${label}: ${formatValue(value)}`;
          meta.appendChild(badge);
        });

        card.append(title, description, meta);
        container.appendChild(card);
      });
    };

    const renderDecisionObject = (data) => {
      const title = getFirst(
        data.title?.en,
        data.title,
        data.recommendation?.title,
        data.decision?.headline,
        "Industrial Decision"
      );

      const recommendation =
        data.recommendation || data.decision || {};

      const governance = data.governance || {};
      const scope = data.scope || {};
      const trigger = data.trigger || {};
      const situation = data.situation || {};
      const impact =
        data.expected_impact ||
        recommendation.expected_effects ||
        {};

      setText("decisionTitle", title);

      setText(
        "decisionDescription",
        getFirst(
          recommendation.explanation,
          recommendation.description,
          situation.summary,
          "A governed industrial decision generated from operational context."
        )
      );

      setText(
        "statusBadge",
        `Status: ${getFirst(data.status, governance.status, "—")}`
      );

      setText(
        "priorityBadge",
        `Priority: ${getFirst(data.priority, "—")}`
      );

      setText(
        "domainBadge",
        `Domain: ${getFirst(data.domain, "—")}`
      );

      setText(
        "decisionIdBadge",
        `ID: ${getFirst(
          data.decision_object_id,
          data.decision_id,
          "—"
        )}`
      );

      setText("siteValue", scope.site_id);
      setText(
        "lineValue",
        [scope.area_id, scope.line_id]
          .filter(Boolean)
          .join(" / ")
      );

      setText(
        "triggerValue",
        getFirst(trigger.type, situation.trigger)
      );

      setText(
        "triggerSubtitle",
        getFirst(
          trigger.detected_at,
          trigger.severity
            ? `Severity: ${trigger.severity}`
            : "Operational signal"
        )
      );

      setText(
        "actionValue",
        getFirst(
          recommendation.type,
          recommendation.option_id,
          data.decision_type
        )
      );

      setText(
        "recommendationTitle",
        getFirst(
          recommendation.title,
          recommendation.headline,
          title
        )
      );

      setText(
        "recommendationDescription",
        getFirst(
          recommendation.explanation,
          recommendation.description,
          "No recommendation explanation available."
        )
      );

      setText(
        "governanceBadge",
        `Governance: ${getFirst(governance.status, data.status, "—")}`
      );

      setText(
        "scoreBadge",
        `Score: ${getFirst(
          recommendation.score,
          data.score,
          "—"
        )}`
      );

      setText(
        "confidenceBadge",
        `Confidence: ${getFirst(
          recommendation.confidence,
          data.confidence,
          data.data_quality?.recommendation_confidence,
          "—"
        )}`
      );

      setText(
        "executionModeBadge",
        `Mode: ${getFirst(
          governance.execution_mode,
          data.execution_mode,
          "—"
        )}`
      );

      renderList("situationList", [
        ["Trigger", getFirst(trigger.type, situation.trigger)],
        ["Severity", getFirst(trigger.severity, situation.severity)],
        ["Detected at", trigger.detected_at],
        ["Valid until", getFirst(trigger.valid_until, governance.valid_until)],
        ["Site", scope.site_id],
        ["Area", scope.area_id],
        ["Line", scope.line_id],
        ["Stations", scope.station_ids],
        ["Maximum power", situation.maximum_power_kw],
        ["Threshold", situation.threshold_kw],
        ["Excess", situation.excess_kw]
      ]);

      renderList("governanceList", [
        ["Status", getFirst(governance.status, data.status)],
        ["Execution mode", governance.execution_mode],
        ["Decision owner", governance.decision_owner],
        ["Required approvals", governance.required_approvals],
        ["Required reviews", governance.required_reviews],
        ["Veto roles", governance.veto_roles],
        ["Valid until", governance.valid_until],
        ["Conditions", governance.conditions]
      ]);

      renderList(
        "impactList",
        Object.entries(impact)
      );

      renderOptions(data);

      document.getElementById("rawJson").textContent =
        JSON.stringify(data, null, 2);
    };

    const showError = (message) => {
      const errorBox = document.getElementById("errorBox");
      errorBox.style.display = "block";
      errorBox.textContent = message;
    };

    const clearError = () => {
      const errorBox = document.getElementById("errorBox");
      errorBox.style.display = "none";
      errorBox.textContent = "";
    };

    const startDecisionCenter = async () => {
  clearError();

  try {
    const data = await loadDecisionObject(
      `${DECISION_OBJECT_URL}?t=${Date.now()}`
    );

    renderDecisionObject(data);
  } catch (error) {
    console.error(error);

    showError(
      `${error.message}. Open this page through the local HTTP server, not directly as a file.`
    );

    setText(
      "decisionTitle",
      "Decision Object could not be loaded"
    );
  }
};

document
  .getElementById("reloadButton")
  .addEventListener("click", startDecisionCenter);

startDecisionCenter();
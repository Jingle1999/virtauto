/**
 * Loads and validates a Decision Object from a JSON resource.
 *
 * @param {string} url - Path to the Decision Object JSON file.
 * @returns {Promise<object>} Parsed Decision Object.
 * @throws {Error} If the resource cannot be loaded or parsed.
 */
export async function loadDecisionObject(url) {
  if (!url || typeof url !== "string") {
    throw new Error("A valid Decision Object URL is required.");
  }

  const response = await fetch(url, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `Decision Object could not be loaded: HTTP ${response.status} ${response.statusText}`
    );
  }

  let decisionObject;

  try {
    decisionObject = await response.json();
  } catch (error) {
    throw new Error(
      `Decision Object contains invalid JSON: ${error.message}`
    );
  }

  if (
    !decisionObject ||
    typeof decisionObject !== "object" ||
    Array.isArray(decisionObject)
  ) {
    throw new Error(
      "The loaded Decision Object is not a valid JSON object."
    );
  }

  return decisionObject;
}
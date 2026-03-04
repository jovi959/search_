const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const OUTPUT_DIR = path.join(__dirname, "output");
const LOG_FILE = path.join(OUTPUT_DIR, "eval.log");
const RESULTS_FILE = path.join(OUTPUT_DIR, "results.json");
const MAIN_CONFIG = "promptfooconfig.yaml";
const DEBUG_CONFIG = "promptfooconfig-debug.yaml";

function ensureOutputDir() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }
}

function rewriteDebugConfig(testFiles) {
  const content = fs.readFileSync(
    path.join(__dirname, DEBUG_CONFIG),
    "utf-8"
  );
  const testsIndex = content.indexOf("\ntests:");
  if (testsIndex === -1) {
    console.error("Could not find 'tests:' section in " + DEBUG_CONFIG);
    process.exit(1);
  }

  const before = content.substring(0, testsIndex);
  const testsBlock = testFiles.map((f) => `  - ${f}`).join("\n");
  fs.writeFileSync(
    path.join(__dirname, DEBUG_CONFIG),
    `${before}\ntests:\n${testsBlock}\n`
  );
}

function runEval(configFile) {
  const cmd = [
    "npx promptfoo eval",
    "--no-cache",
    "--no-table",
    "--no-progress-bar",
    `-c ${configFile}`,
    `-o ${RESULTS_FILE}`,
  ].join(" ");

  try {
    execSync(cmd, {
      cwd: __dirname,
      stdio: ["ignore", fs.openSync(LOG_FILE, "w"), fs.openSync(LOG_FILE, "a")],
      timeout: 5 * 60 * 1000,
    });
  } catch {
    // non-zero exit is expected when tests fail — results.json still gets written
  }
}

function parseResults() {
  if (!fs.existsSync(RESULTS_FILE)) {
    console.error("No results file found. Check " + LOG_FILE + " for errors.");
    process.exit(1);
  }

  const raw = JSON.parse(fs.readFileSync(RESULTS_FILE, "utf-8"));
  const rows = raw.results?.results ?? raw.results ?? [];

  return rows.map((r) => {
    const description =
      r.testCase?.description ?? r.description ?? "unnamed test";
    const pass = r.success ?? r.gradingResult?.pass ?? false;

    const failedAssertions = [];
    if (!pass && r.gradingResult?.componentResults) {
      for (const c of r.gradingResult.componentResults) {
        if (!c.pass) {
          const metric =
            c.assertion?.metric ??
            Object.keys(c.namedScores || {})[0] ??
            c.assertion?.type ??
            "assertion";
          failedAssertions.push({ metric, reason: c.reason ?? "" });
        }
      }
    }

    return { description, pass, failedAssertions };
  });
}

function printSummary(results) {
  const passed = results.filter((r) => r.pass);
  const failed = results.filter((r) => !r.pass);

  console.log();

  if (failed.length === 0) {
    console.log(`All ${results.length} tests passed.`);
  } else {
    console.log(
      `Results: ${passed.length} passed, ${failed.length} failed\n`
    );
    console.log("FAILED:");
    failed.forEach((f, i) => {
      console.log(`  [${i + 1}] ${f.description}`);
      for (const a of f.failedAssertions) {
        const detail = a.reason ? `: ${a.reason}` : "";
        console.log(`      x ${a.metric}${detail}`);
      }
      console.log();
    });
  }

  console.log(`Full log:     output/eval.log`);
  console.log(`Full results: output/results.json`);
  console.log();

  return failed.length > 0 ? 1 : 0;
}

// --- main ---

const testFiles = process.argv.slice(2);
let configFile = MAIN_CONFIG;

if (testFiles.length > 0) {
  const missing = testFiles.filter((f) => !fs.existsSync(path.join(__dirname, f)));
  if (missing.length > 0) {
    console.error("Test files not found: " + missing.join(", "));
    process.exit(1);
  }
  rewriteDebugConfig(testFiles);
  configFile = DEBUG_CONFIG;
  console.log(`Running ${testFiles.length} test(s): ${testFiles.join(", ")}`);
} else {
  console.log("Running full test suite...");
}

ensureOutputDir();
runEval(configFile);

const results = parseResults();
const exitCode = printSummary(results);
process.exit(exitCode);

const assert = require("node:assert/strict");
const test = require("node:test");

test("web package exposes the expected runtime scripts", () => {
  const pkg = require("../package.json");

  assert.equal(pkg.scripts.build, "next build");
  assert.equal(pkg.scripts.test, "node --test");
});

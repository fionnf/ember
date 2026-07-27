#!/usr/bin/env node
/*
 * Scene-sync merge tests.
 *
 * Scenes are mirrored to the retained `P/scenes` topic so every client
 * converges on one library. The merge rules exist so that no device can
 * destroy another's work: a phone that has never saved a scene must not
 * wipe the laptop's library, and a deleted scene must not be helpfully
 * synced back by a device that still has it.
 *
 * Run from the repo root:   node tests/test_scene_sync.js
 */
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const js = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));
const block = js.slice(js.indexOf("const SCENE_TOMBSTONE_CAP"), js.indexOf("function swatchRGB"));

let store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
global.BOARD_ID = "web_app";
global.publishRetained = () => {};
global.topicScenes = () => "p/scenes";
eval(block);

const fails = [];
const check = (n, c, d = "") => {
  console.log((c ? "  PASS  " : "  FAIL  ") + n + (c ? "" : "  " + d));
  if (!c) fails.push(n);
};
const reset = (scenes = [], dead = []) => {
  store = { ll_scenes: JSON.stringify(scenes), ll_scenes_deleted: JSON.stringify(dead) };
};

console.log("\n=== a device with no scenes must not wipe the library ===");
reset([]);
const adopted = mergeScenes({ v: 1, scenes: [{ id: "a", updated: 100, name: "Sunset" }], deleted: [] });
check("empty device adopts remote scenes", loadScenes().length === 1 && adopted);

console.log("\n=== a remote list missing our scene must not delete it ===");
reset([{ id: "mine", updated: 200, name: "Mine" }]);
mergeScenes({ v: 1, scenes: [{ id: "theirs", updated: 100, name: "Theirs" }], deleted: [] });
check("both scenes survive", JSON.stringify(loadScenes().map(s => s.id).sort()) === '["mine","theirs"]',
      JSON.stringify(loadScenes()));

console.log("\n=== last edit wins ===");
reset([{ id: "a", updated: 500, name: "NEW" }]);
mergeScenes({ v: 1, scenes: [{ id: "a", updated: 100, name: "OLD" }], deleted: [] });
check("older remote edit does not clobber", loadScenes()[0].name === "NEW");
reset([{ id: "a", updated: 100, name: "OLD" }]);
mergeScenes({ v: 1, scenes: [{ id: "a", updated: 500, name: "NEW" }], deleted: [] });
check("newer remote edit is adopted", loadScenes()[0].name === "NEW");

console.log("\n=== deletions propagate instead of resurrecting ===");
reset([{ id: "a", updated: 100, name: "Doomed" }]);
mergeScenes({ v: 1, scenes: [], deleted: ["a"] });
check("remote tombstone deletes locally", loadScenes().length === 0);
reset([], ["a"]);
mergeScenes({ v: 1, scenes: [{ id: "a", updated: 999, name: "Zombie" }], deleted: [] });
check("our tombstone blocks resurrection", loadScenes().length === 0);

console.log("\n=== idempotent, so no republish storm ===");
reset([{ id: "a", updated: 100, name: "X" }]);
const payload = { v: 1, scenes: [{ id: "a", updated: 100, name: "X" }], deleted: [] };
mergeScenes(payload);
check("identical payload reports no change", mergeScenes(payload) === false);

console.log("\n=== hostile payloads ===");
let ok = true;
reset([{ id: "keep", updated: 1, name: "Keep" }]);
for (const bad of [null, undefined, 42, "str", {}, { scenes: "x" },
                   { scenes: [null, 7, {}] }, { deleted: "x" }]) {
  try { mergeScenes(bad); } catch (e) { ok = false; console.log("    threw on", JSON.stringify(bad)); }
}
check("junk never throws", ok);
check("junk never destroys the library", loadScenes().some(s => s.id === "keep"));

console.log("\n=== tombstones stay bounded ===");
reset([], Array.from({ length: 80 }, (_, i) => "id" + i));
saveTombstones(loadTombstones());
check("capped at 50", loadTombstones().length === 50, String(loadTombstones().length));

console.log();
if (fails.length) { console.log("FAILED: " + fails.join(", ")); process.exit(1); }
console.log("ALL SCENE SYNC TESTS PASSED");

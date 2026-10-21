// Allswell dashboard client. Polls /api/state and renders the calm-or-alert view.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  async function getState() {
    const r = await fetch("/api/state");
    if (!r.ok) throw new Error("state " + r.status);
    return r.json();
  }

  function render(s) {
    const card = $("statusCard");
    const live = $("live");
    const sev = s.is_all_well ? "ok" : (s.digest.status || "warn");

    // hero
    card.className = "status" + (s.is_all_well ? "" : " " + sev);
    $("statusEyebrow").textContent = s.is_all_well ? "Today · all's well" : "Today · needs a look";
    $("statusHeadline").textContent = s.digest.headline;
    $("statusMessage").textContent = s.digest.message;
    $("digestSrc").textContent = s.digest.source === "bedrock" ? "written by Amazon Bedrock" : "auto-summary";

    live.className = "live " + (s.is_all_well ? "ok" : "alert");
    live.textContent = s.is_all_well ? "all's well" : "attention";

    // check-in button shows only when something is off
    const btn = $("checkinBtn");
    btn.hidden = s.is_all_well;
    const note = $("checkedNote");
    if (s.checked_in_at) {
      note.hidden = false;
      const t = new Date(s.checked_in_at);
      note.textContent = "You reached out at " + t.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) + ".";
    } else {
      note.hidden = true;
    }

    // alerts
    const alertsSec = $("alertsSection");
    const alerts = $("alerts");
    alerts.innerHTML = "";
    if (s.anomalies && s.anomalies.length) {
      alertsSec.hidden = false;
      s.anomalies.forEach((a) => {
        const div = document.createElement("div");
        div.className = "alert " + (a.severity === "critical" ? "critical" : "");
        div.innerHTML =
          '<div class="a-head"><span class="pill ' + (a.severity === "critical" ? "critical" : "warn") +
          '">' + a.severity + '</span><b></b></div><p></p>';
        div.querySelector("b").textContent = a.title;
        div.querySelector("p").textContent = a.detail;
        alerts.appendChild(div);
      });
    } else {
      alertsSec.hidden = true;
    }

    // timeline
    const tl = $("timeline");
    tl.innerHTML = "";
    const quietZone = (iso) => { const h = new Date(iso).getHours(); return h < 5 || (h === 5 && new Date(iso).getMinutes() < 30); };
    if (s.timeline && s.timeline.length) {
      s.timeline.forEach((e) => {
        const li = document.createElement("li");
        if (quietZone(e.at)) li.className = "off";
        const label = describe(e);
        li.innerHTML = '<div class="t"></div><div class="e"></div>';
        li.querySelector(".t").textContent = e.time_label;
        li.querySelector(".e").textContent = label;
        tl.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No activity recorded today.";
      tl.appendChild(li);
    }

    // baseline
    $("baselineNote").textContent =
      "Learned from " + s.baseline.days_observed + " days. Tracked areas: " +
      s.baseline.zones.map((z) => z.replace(/_/g, " ")).join(", ") + ".";

    // scenarios
    const sc = $("scenarios");
    sc.innerHTML = "";
    Object.entries(s.scenarios).forEach(([key, label]) => {
      const b = document.createElement("button");
      b.className = "scn" + (key === s.scenario ? " active" : "");
      b.innerHTML = "<b></b><span></span>";
      b.querySelector("b").textContent = key.replace(/_/g, " ");
      b.querySelector("span").textContent = label;
      b.addEventListener("click", async () => {
        await fetch("/api/scenario/" + key, { method: "POST" });
        refresh();
      });
      sc.appendChild(b);
    });
  }

  function describe(e) {
    const zone = e.zone.replace(/_/g, " ");
    const map = {
      doorbell: "Doorbell rang at the " + zone,
      person: "Someone at the " + zone,
      motion: "Movement in the " + zone,
      delivery: "Delivery at the " + zone,
    };
    return map[e.type] || (e.type + " · " + zone);
  }

  async function refresh() {
    try { render(await getState()); }
    catch (e) { $("live").textContent = "offline"; }
  }

  // check-in
  $("checkinBtn").addEventListener("click", async () => {
    await fetch("/api/check-in", { method: "POST" });
    refresh();
  });


  refresh();
  setInterval(refresh, 8000);
})();
